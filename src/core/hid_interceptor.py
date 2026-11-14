"""Global Windows Low-Level Keyboard Hook (WH_KEYBOARD_LL) and HID Intervention Engine.

Provides:
  - Global low-level keyboard interception using native Win32 SetWindowsHookExW.
  - Tag-based bypass for keystrokes synthesized by BinaryReceptor's KeyInjector (dwExtraInfo).
  - High-speed burst detection for incoming Bluetooth HID / barcode scanner keystrokes (< 50ms).
  - Mode-aware intervention:
      * 'copy_only' mode: Intercepts raw HID keystrokes, blocks them from the focused window,
        and routes the accumulated string directly to the clipboard (Win32 / pyperclip).
      * 'both' (Hybrid) mode: Deduplicates incoming physical/HID keystrokes against HTTP payloads
        (via scanId and content matching) to eliminate double-typing.
      * 'http' (HTTP Server Only) mode: Discards redundant HTTP processing pathways when HID
        input is detected, preventing the app from behaving erroneously as Hybrid mode.
  - Graceful fallback routing logic when hook installation is unavailable.
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
    win32_set_clipboard_text,
    INJECTOR_EXTRA_INFO,
    VK_RETURN,
    VK_BACK,
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

# Threshold in seconds for detecting rapid scanner bursts (normal typing is > 100ms)
BURST_THRESHOLD_SEC = 0.050
BURST_TIMEOUT_SEC = 0.080

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
    """Manages the global keyboard hook, rapid HID input detection, and deduplication."""

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
        self._hook_proc_ref = None  # Prevent garbage collection of ctypes callback

        # Burst tracking state
        self._last_key_time: float = 0.0
        self._burst_chars: list[str] = []
        self._in_burst: bool = False
        self._last_burst_completed_time: float = 0.0
        self._last_burst_text: str = ""

        # HTTP scan registration for deduplication (scanId -> (content, timestamp))
        self._active_http_scans: dict[str, tuple[str, float]] = {}
        # Recent content timestamp map (content -> timestamp)
        self._recent_content_scans: dict[str, float] = {}

    @property
    def is_hooked(self) -> bool:
        return self._hook_handle is not None

    def start(self) -> bool:
        """Start the background thread and install the WH_KEYBOARD_LL hook."""
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
        """Unhook and terminate the hook message pump thread."""
        with self._lock:
            self._stop_event.set()
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

    def is_hid_burst_active(self) -> bool:
        """Check if an HID keystroke burst is currently in progress or finished within 500ms."""
        now = time.monotonic()
        with self._lock:
            if self._in_burst:
                return True
            return (now - self._last_burst_completed_time) < 0.500

    def should_suppress_http_injection(self, content: str, scan_id: str | None = None) -> bool:
        """Check if HTTP keystroke injection should be suppressed due to HID input.

        Rules:
          - Mandate 1: If strictly 'http' mode and HID input was detected, discard redundant HTTP injection.
          - Mandate 2: If 'both' (Hybrid) mode and an identical scan was processed via HID within 1500ms,
            suppress HTTP typing.
        """
        now = time.monotonic()
        clean = content.strip("\r\n\t ")
        mode = self.mode_getter().strip().lower()

        with self._lock:
            recent_burst_time = self._last_burst_completed_time
            burst_text = self._last_burst_text
            in_burst = self._in_burst

        # Mandate 1: In HTTP Server Only mode, actively discard redundant HTTP processing if HID input detected
        if mode == "http":
            if in_burst or (now - recent_burst_time < 1.5 and (not burst_text or clean == burst_text)):
                logger.info("Mandate 1: Suppressing redundant HTTP injection in HTTP Only mode (HID detected)")
                return True

        # Mandate 2: In Hybrid mode, prevent double-typing if HID already typed or is typing
        if mode == "both":
            if (now - recent_burst_time < 1.5 and clean == burst_text) or (in_burst and clean.startswith(burst_text)):
                logger.info("Mandate 2: Suppressing redundant HTTP injection (HID keystroke deduplication)")
                return True

        return False

    def _vk_to_char(self, vk_code: int) -> str | None:
        """Convert standard alphanumeric and punctuation VK codes to characters."""
        if 0x30 <= vk_code <= 0x39:  # '0' - '9'
            return chr(vk_code)
        if 0x41 <= vk_code <= 0x5A:  # 'A' - 'Z'
            return chr(vk_code)
        if vk_code == 0x20:  # Space
            return " "
        if vk_code in (0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xC0, 0xDB, 0xDC, 0xDD, 0xDE):
            # Basic punctuation mapping fallback
            punct_map = {
                0xBD: "-", 0xBB: "=", 0xBC: ",", 0xBE: ".", 0xBF: "/",
                0xBA: ";", 0xDE: "'", 0xDB: "[", 0xDD: "]", 0xDC: "\\",
            }
            return punct_map.get(vk_code, "")
        if vk_code == VK_RETURN:
            return "\n"
        if vk_code == VK_TAB:
            return "\t"
        return ""

    def _on_key_event(self, nCode: int, wParam: int, lParam: int) -> int:
        """Low-level hook callback executed synchronously on the hook thread."""
        if nCode < 0 or not user32:
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        p_kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

        # 1. Bypass events synthesized by our own KeyInjector
        if p_kbd.dwExtraInfo == INJECTOR_EXTRA_INFO:
            return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

        # We inspect KEYDOWN and SYSKEYDOWN
        is_key_down = (wParam in (WM_KEYDOWN, WM_SYSKEYDOWN))
        is_key_up = (wParam in (WM_KEYUP, WM_SYSKEYUP))
        now = time.monotonic()
        vk = p_kbd.vkCode

        # Compute inter-keystroke interval
        delta = now - self._last_key_time
        self._last_key_time = now

        # Detect burst start or continuation
        if is_key_down:
            if delta < BURST_THRESHOLD_SEC:
                self._in_burst = True
            elif delta > BURST_TIMEOUT_SEC:
                # Idle gap: reset prior burst
                if self._in_burst:
                    self._finalize_burst()
                self._in_burst = False
                self._burst_chars.clear()

            ch = self._vk_to_char(vk)
            if ch:
                self._burst_chars.append(ch)

        # Check mode constraints
        out_mode = self.output_mode_getter().strip().lower()
        op_mode = self.mode_getter().strip().lower()

        # Mandate 3: Copy to clipboard only mode
        # Intercept and block raw HID keystrokes from reaching focused window
        if out_mode in ("copy_only", "clipboard_only", "copy"):
            if self._in_burst:
                if is_key_down and vk == VK_RETURN:
                    self._finalize_copy_only()
                # Return 1 to suppress this keystroke from reaching the active window!
                return 1

        # Mandate 2: Hybrid Mode deduplication
        # If an active HTTP scan matches the burst or was received, intercept raw HID
        # to ensure only the layout-independent Unicode Python injector types it
        if op_mode == "both" and self._in_burst:
            current_str = "".join(self._burst_chars).strip("\r\n\t ")
            with self._lock:
                # Check if current burst matches any registered HTTP scan
                matched = any(
                    (content == current_str or content.startswith(current_str))
                    for content, _ in self._active_http_scans.values()
                ) or any(
                    (content == current_str or content.startswith(current_str))
                    for content in self._recent_content_scans.keys()
                )

            if matched:
                if is_key_down and vk == VK_RETURN:
                    self._finalize_burst()
                # Intercept HID keystroke to avoid double typing
                return 1

        if is_key_down and vk == VK_RETURN and self._in_burst:
            self._finalize_burst()

        return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

    def _finalize_burst(self) -> None:
        """Complete an HID burst sequence."""
        text = "".join(self._burst_chars).strip("\r\n\t ")
        if text:
            self._last_burst_text = text
            self._last_burst_completed_time = time.monotonic()
        self._in_burst = False
        self._burst_chars.clear()

    def _finalize_copy_only(self) -> None:
        """Route intercepted HID burst string directly to clipboard (Mandate 3)."""
        text = "".join(self._burst_chars).strip("\r\n\t ")
        self._finalize_burst()
        if text:
            # Set to Windows clipboard natively via ctypes
            win32_set_clipboard_text(text)
            try:
                import pyperclip
                pyperclip.copy(text)
            except Exception:
                pass
            logger.info("Mandate 3: Intercepted raw HID barcode and routed to clipboard: '%s'", text)
            try:
                self.on_hid_scan_intercepted(text)
            except Exception:
                pass

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
            # GetMessage blocks until a window message arrives
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
