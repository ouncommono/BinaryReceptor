"""Global Windows Low-Level Keyboard Hook (WH_KEYBOARD_LL) and HID Intervention Engine for BinaryReceptor v3.6.0.

Provides:
  - Global low-level keyboard interception using native Win32 SetWindowsHookExW.
  - Tag-based bypass for keystrokes synthesized by BinaryReceptor's KeyInjector (dwExtraInfo).
  - High-speed burst detection for incoming Bluetooth HID / barcode scanner keystrokes (< 45ms).
  - Non-destructive tentative hold on the first character of a burst to prevent character leakage.
  - Full OS-level suppression of raw Bluetooth HID keystrokes:
      * Hybrid Mode: Suppresses native OS typing, deduplicates against HTTP payloads, and processes via internal logic.
      * HTTP Server Only Mode: Strictly suppresses native Bluetooth HID keystrokes from reaching focused windows.
      * Copy to Clipboard Only Mode: Suppresses native typing and routes barcode directly to Windows clipboard.
      * Layout-Independent Typing: Intercepts raw scancodes and dispatches for SendInput Unicode injection.
  - Graceful fallback when hook installation is unavailable.
"""
from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
from ctypes import wintypes
from typing import Callable, Any

from src.core.key_injector import (
    KeyInjector,
    win32_set_clipboard_text,
    INJECTOR_EXTRA_INFO,
    VK_RETURN,
    VK_TAB,
    user32,
    kernel32,
)

logger = logging.getLogger("BinaryReceptor.HID")

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

# Threshold in seconds for detecting rapid scanner bursts (barcode scanners transmit at 5-25ms)
BURST_THRESHOLD_SEC = 0.045
BURST_TIMEOUT_SEC = 0.150
FIRST_KEY_HOLD_SEC = 0.035

ULONG_PTR = ctypes.c_size_t


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

if user32:
    try:
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_long
        user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostThreadMessageW.restype = wintypes.BOOL
    except Exception:
        pass


class HIDInterventionEngine:
    """Manages global keyboard hook, rapid HID input detection, suppression, and deduplication."""

    def __init__(
        self,
        mode_getter: Callable[[], str] | None = None,
        output_mode_getter: Callable[[], str] | None = None,
        on_hid_scan_intercepted: Callable[[str], None] | None = None,
        enabled: bool = True,
    ) -> None:
        self.mode_getter = mode_getter or (lambda: "both")
        self.output_mode_getter = output_mode_getter or (lambda: "type")
        self.on_hid_scan_intercepted = on_hid_scan_intercepted or (lambda s: None)
        self.enabled = enabled

        self._lock = threading.Lock()
        self._hook_handle = None
        self._hook_thread: threading.Thread | None = None
        self._hook_thread_id: int = 0
        self._hook_ready = threading.Event()
        self._stop_event = threading.Event()
        self._hook_proc_ref = None  # Prevent GC of ctypes callback

        self._injector = KeyInjector()

        # Burst tracking state
        self._last_key_time: float = 0.0
        self._burst_chars: list[str] = []
        self._in_burst: bool = False
        self._last_burst_completed_time: float = 0.0
        self._last_burst_text: str = ""

        # Tentative first-key hold state
        self._pending_timer: threading.Timer | None = None
        self._pending_first_char: str | None = None

        # Shift state tracking for punctuation
        self._shift_down: bool = False

        # HTTP scan registration for deduplication (scanId -> (content, timestamp))
        self._active_http_scans: dict[str, tuple[str, float]] = {}
        # Recent content timestamp map (content -> timestamp)
        self._recent_content_scans: dict[str, float] = {}

    @property
    def is_hooked(self) -> bool:
        return self._hook_handle is not None

    def start(self) -> bool:
        """Start background thread and install WH_KEYBOARD_LL hook."""
        if not self.enabled or os.name != "nt" or not user32:
            return False

        with self._lock:
            if self._hook_thread and self._hook_thread.is_alive():
                return True

            self._stop_event.clear()
            self._hook_ready.clear()
            self._hook_thread = threading.Thread(
                target=self._hook_loop,
                name="BinaryReceptor-HIDHook",
                daemon=True,
            )
            self._hook_thread.start()

        return self._hook_ready.wait(timeout=2.0)

    def stop(self) -> None:
        """Unhook and terminate message pump thread."""
        with self._lock:
            self._stop_event.set()
            if self._pending_timer:
                self._pending_timer.cancel()
                self._pending_timer = None
            self._pending_first_char = None

            if self._hook_thread_id and user32:
                try:
                    user32.PostThreadMessageW(self._hook_thread_id, WM_QUIT, 0, 0)
                except Exception:
                    pass
            self._hook_handle = None

        if self._hook_thread and self._hook_thread.is_alive():
            self._hook_thread.join(timeout=1.5)
            self._hook_thread = None

    def register_http_scan(self, content: str, scan_id: str | None = None) -> None:
        """Register an incoming HTTP scan payload for cross-protocol deduplication."""
        now = time.monotonic()
        with self._lock:
            clean = content.strip("\r\n\t ")
            if scan_id and scan_id.strip():
                self._active_http_scans[scan_id.strip()] = (clean, now)
            self._recent_content_scans[clean] = now

            # Clean expired entries (> 5.0 seconds old)
            expired = [k for k, v in self._recent_content_scans.items() if now - v > 5.0]
            for k in expired:
                del self._recent_content_scans[k]

            expired_ids = [k for k, v in self._active_http_scans.items() if now - v[1] > 5.0]
            for k in expired_ids:
                del self._active_http_scans[k]

    def should_suppress_http_injection(self, content: str, scan_id: str | None = None) -> bool:
        """Check if HTTP keystroke injection should be suppressed due to HID input."""
        now = time.monotonic()
        clean = content.strip("\r\n\t ")
        mode = self.mode_getter().strip().lower()

        with self._lock:
            recent_burst_time = self._last_burst_completed_time
            burst_text = self._last_burst_text
            in_burst = self._in_burst

        # Mandate 1: In HTTP Server Only mode, if HID input was detected, discard redundant HTTP injection
        if mode == "http":
            if in_burst or (now - recent_burst_time < 1.5 and (not burst_text or clean == burst_text)):
                logger.info("Mandate 1: Suppressing redundant HTTP injection in HTTP Only mode (HID detected)")
                return True

        # Mandate 1 & 2: In Hybrid mode, prevent double-typing if HID already typed or is typing
        if mode == "both":
            if (now - recent_burst_time < 1.5 and clean == burst_text) or (in_burst and clean.startswith(burst_text)):
                logger.info("Mandate 1: Suppressing redundant HTTP injection (HID burst matched)")
                return True

        return False

    def _vk_to_char(self, vk_code: int) -> str | None:
        """Convert standard alphanumeric and punctuation VK codes to characters."""
        # 0 - 9
        if 0x30 <= vk_code <= 0x39:
            base = chr(vk_code)
            if self._shift_down:
                shift_map = {"1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&", "8": "*", "9": "(", "0": ")"}
                return shift_map.get(base, base)
            return base

        # A - Z
        if 0x41 <= vk_code <= 0x5A:
            char = chr(vk_code)
            return char if self._shift_down else char.lower()

        # Numpad 0-9
        if 0x60 <= vk_code <= 0x69:
            return chr(vk_code - 0x60 + ord("0"))

        if vk_code == 0x20:  # Space
            return " "

        # Standard punctuation
        punct_map = {
            0xBD: ("-", "_"),
            0xBB: ("=", "+"),
            0xBC: (",", "<"),
            0xBE: (".", ">"),
            0xBF: ("/", "?"),
            0xBA: (";", ":"),
            0xDE: ("'", '"'),
            0xDB: ("[", "{"),
            0xDD: ("]", "}"),
            0xDC: ("\\", "|"),
            0xC0: ("`", "~"),
            0x6A: ("*", "*"),
            0x6B: ("+", "+"),
            0x6D: ("-", "-"),
            0x6E: (".", "."),
            0x6F: ("/", "/"),
        }
        if vk_code in punct_map:
            normal, shifted = punct_map[vk_code]
            return shifted if self._shift_down else normal

        if vk_code == VK_RETURN:
            return "\n"
        if vk_code == VK_TAB:
            return "\t"

        return ""

    def _flush_pending_first_key(self) -> None:
        """Timeout callback: 35ms elapsed with no second key. It was a normal human keypress."""
        with self._lock:
            ch = self._pending_first_char
            self._pending_first_char = None
            self._pending_timer = None

        if ch and not self._stop_event.is_set():
            # Re-inject the single human keypress with INJECTOR_EXTRA_INFO bypass
            self._injector.type_unicode_string(ch)

    def _finalize_burst(self) -> None:
        """Complete an HID burst sequence and dispatch the barcode payload."""
        with self._lock:
            text = "".join(self._burst_chars).strip("\r\n\t ")
            self._burst_chars.clear()
            self._in_burst = False
            if self._pending_timer:
                self._pending_timer.cancel()
                self._pending_timer = None
            self._pending_first_char = None

            if text:
                self._last_burst_text = text
                self._last_burst_completed_time = time.monotonic()

        if text:
            # Mandate 2: Route directly to Windows Clipboard if in copy_only mode
            try:
                out_mode = (self.output_mode_getter() or "type").strip().lower()
                if out_mode in ("copy_only", "copy", "clipboard_only"):
                    win32_set_clipboard_text(text)
            except Exception as e:
                logger.error("Failed to copy HID barcode to clipboard: %s", e)

            logger.info("Captured raw Bluetooth HID barcode: '%s'", text)
            try:
                self.on_hid_scan_intercepted(text)
            except Exception as e:
                logger.error("Error dispatching on_hid_scan_intercepted: %s", e)

    def _finalize_copy_only(self) -> None:
        """Backward-compatible alias for _finalize_burst."""
        self._finalize_burst()

    def _on_key_event(self, nCode: int, wParam: int, lParam: int) -> int:
        """Low-level hook callback executed synchronously on the hook thread."""
        if nCode < 0 or not user32:
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        p_kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

        # 1. Bypass events synthesized by our own KeyInjector
        if p_kbd.dwExtraInfo == INJECTOR_EXTRA_INFO:
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        is_key_down = (wParam in (WM_KEYDOWN, WM_SYSKEYDOWN))
        is_key_up = (wParam in (WM_KEYUP, WM_SYSKEYUP))
        now = time.monotonic()
        vk = p_kbd.vkCode

        # Track Shift key state
        if vk in (0x10, 0xA0, 0xA1):  # VK_SHIFT, VK_LSHIFT, VK_RSHIFT
            self._shift_down = is_key_down
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        # Allow other modifier keys (Ctrl, Alt, Win, CapsLock, NumLock) to pass directly
        if vk in (0x11, 0x12, 0x5B, 0x5C, 0x14, 0x90, 0x91):
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        # Handle key up: suppress key up for keys consumed as part of a burst
        if is_key_up:
            if self._in_burst or self._pending_first_char:
                return 1
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        if not is_key_down:
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        # ----------------------------------------------------------------------
        # KEY DOWN PROCESSING
        # ----------------------------------------------------------------------
        delta = now - self._last_key_time
        self._last_key_time = now

        # Case A: We are already in an active HID burst
        if self._in_burst:
            # Idle timeout inside a burst (>150ms)
            if delta > BURST_TIMEOUT_SEC:
                self._finalize_burst()
                # Fall through to evaluate as a new keystroke

            if vk in (VK_RETURN, VK_TAB):
                self._finalize_burst()
                return 1  # Suppress terminator from focused window

            ch = self._vk_to_char(vk)
            if ch:
                self._burst_chars.append(ch)
            return 1  # Suppress all burst characters from focused window

        # Case B: Fast arrival (< BURST_THRESHOLD_SEC) - Burst Confirmed!
        if delta < BURST_THRESHOLD_SEC:
            self._in_burst = True
            with self._lock:
                if self._pending_timer:
                    self._pending_timer.cancel()
                    self._pending_timer = None
                if self._pending_first_char:
                    self._burst_chars.append(self._pending_first_char)
                    self._pending_first_char = None

            if vk in (VK_RETURN, VK_TAB):
                self._finalize_burst()
                return 1

            ch = self._vk_to_char(vk)
            if ch:
                self._burst_chars.append(ch)
            return 1  # Suppress from focused window

        # Case C: Idle arrival - could be normal typing OR start of a barcode burst
        ch = self._vk_to_char(vk)
        if not ch:
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        # Immediate match check: does an incoming HTTP scan match this character?
        with self._lock:
            matched_http = any(
                c.startswith(ch) for c in self._recent_content_scans.keys()
            ) or any(
                c[0].startswith(ch) for c in self._active_http_scans.values()
            )

        if matched_http:
            # Concurrently confirmed by HTTP scan!
            self._in_burst = True
            self._burst_chars = [ch]
            return 1  # Suppress from focused window

        # Tentative hold on first key: wait FIRST_KEY_HOLD_SEC for second key
        with self._lock:
            if self._pending_timer:
                self._pending_timer.cancel()
            self._pending_first_char = ch
            self._pending_timer = threading.Timer(FIRST_KEY_HOLD_SEC, self._flush_pending_first_key)
            self._pending_timer.daemon = True
            self._pending_timer.start()

        return 1  # Tentatively suppress from focused window

    def _hook_loop(self) -> None:
        """Background thread executing SetWindowsHookExW and the Win32 message pump."""
        if not user32 or not kernel32:
            self._hook_ready.set()
            return

        self._hook_thread_id = kernel32.GetCurrentThreadId()
        self._hook_proc_ref = HOOKPROC(self._on_key_event)

        h_mod = kernel32.GetModuleHandleW(None)
        self._hook_handle = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            h_mod,
            0,
        )

        if not self._hook_handle:
            logger.warning("Failed to install WH_KEYBOARD_LL hook; fallback routing will be used.")
            self._hook_ready.set()
            return

        logger.info("WH_KEYBOARD_LL low-level keyboard hook installed successfully.")
        self._hook_ready.set()

        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook_handle:
            try:
                user32.UnhookWindowsHookEx(self._hook_handle)
            except Exception:
                pass
            self._hook_handle = None
        logger.info("WH_KEYBOARD_LL hook uninstalled cleanly.")
