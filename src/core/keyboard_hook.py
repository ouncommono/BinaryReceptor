"""Windows Low-Level Keyboard Hook (WH_KEYBOARD_LL) for BinaryReceptor v3.4.0.

Provides Tier-1 OS-level Bluetooth HID barcode interception and suppression:
  - In HTTP Server Only mode: Suppresses (swallows by returning non-zero in WH_KEYBOARD_LL)
    high-velocity barcode bursts from OS-level Bluetooth HID so only the HTTP server handles scans.
  - In Hybrid or Bluetooth mode: Intercepts and suppresses raw OS Bluetooth keystrokes from the
    screen, assembles the captured barcode in memory, and dispatches it directly to BinaryReceptor's
    central processing pipeline (enqueue_scan) so it respects the unified Deduplication Engine
    and configured Typing/Output Mode (e.g. Copy to Clipboard Only).
  - Immunity for Injected Keys: Injected keystrokes signed with EXTRA_INFO_SIGNATURE (0x5B524350)
    are recognized immediately and passed through untouched.
"""
from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
from ctypes import wintypes
from typing import Callable, Any

from src.core.bt_radio import BluetoothRadioController

logger = logging.getLogger("BinaryReceptor.KeyboardHook")

# Win32 Hook & Message Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_CAPITAL = 0x14

LLKHF_INJECTED = 0x00000010
EXTRA_INFO_SIGNATURE = 0x5B524350  # "BRCP" in hex

ULONG_PTR = ctypes.c_size_t


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class LowLevelKeyboardHook:
    """Manages WH_KEYBOARD_LL hook on a dedicated Windows message pump thread."""

    def __init__(
        self,
        on_barcode_captured: Callable[[str, str], None] | None = None,
        mode_getter: Callable[[], str] | None = None,
    ) -> None:
        self.on_barcode_captured = on_barcode_captured or (lambda code, src: None)
        self.mode_getter = mode_getter or (lambda: "both")

        self._hook = None
        self._hook_thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._is_running = threading.Event()
        self._hook_installed = threading.Event()
        self._proc_ref = None  # Prevent GC of hook proc callback

        # Burst detection state
        self._lock = threading.Lock()
        self._last_key_time: float = 0.0
        self._in_burst: bool = False
        self._burst_buffer: list[str] = []
        self._burst_key_count: int = 0
        self._swallowed_current_burst: bool = False

    @property
    def is_running(self) -> bool:
        return self._is_running.is_set()

    def _vk_to_char(self, vk: int, scan_code: int) -> str:
        """Convert virtual key code and scan code to Unicode character."""
        if os.name != "nt":
            return ""
        try:
            user32 = ctypes.windll.user32
            keyboard_state = (ctypes.c_ubyte * 256)()
            user32.GetKeyboardState(keyboard_state)
            buf = (ctypes.c_wchar * 16)()
            ret = user32.ToUnicode(vk, scan_code, keyboard_state, buf, 16, 0)
            if ret > 0:
                return buf[:ret]
        except Exception:
            pass
        return ""

    def _hook_callback(self, nCode: int, wParam: int, lParam: int) -> int:
        user32 = ctypes.windll.user32

        if nCode < 0:
            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        try:
            kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

            # 1. Immunity: Always pass through keystrokes injected by BinaryReceptor itself
            if kbd.dwExtraInfo == EXTRA_INFO_SIGNATURE:
                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
            is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)

            now = time.monotonic()
            active_mode = self.mode_getter().strip().lower()

            with self._lock:
                delta_ms = (now - self._last_key_time) * 1000.0 if self._last_key_time > 0 else 999.0

                # Check if this keystroke is part of a high-velocity barcode burst (< 35ms between keys)
                is_fast_key = delta_ms < 35.0

                # Check if Bluetooth keyboard/scanner is physically connected
                bt_connected = BluetoothRadioController.is_bluetooth_keyboard_connected()

                # Timeout reset: if > 80ms elapsed, any previous burst has ended
                if delta_ms > 80.0 and self._in_burst:
                    if len(self._burst_buffer) >= 3 and active_mode in ("both", "bluetooth"):
                        captured = "".join(self._burst_buffer).strip()
                        if captured:
                            logger.info("[Tier 1 Hook] Captured timeout burst barcode: %s", captured)
                            try:
                                self.on_barcode_captured(captured, "Bluetooth")
                            except Exception as e:
                                logger.error("Error in on_barcode_captured callback: %s", e)
                    self._in_burst = False
                    self._burst_buffer.clear()
                    self._burst_key_count = 0
                    self._swallowed_current_burst = False

                if is_down:
                    self._last_key_time = now

                    # Start or continue burst
                    if is_fast_key or (self._in_burst and delta_ms < 60.0):
                        self._in_burst = True
                        self._burst_key_count += 1
                    elif bt_connected and delta_ms < 50.0:
                        self._in_burst = True
                        self._burst_key_count += 1

                    if self._in_burst:
                        # Append character if alphanumeric or printable
                        char = self._vk_to_char(kbd.vkCode, kbd.scanCode)
                        if char and char not in ("\r", "\n", "\t"):
                            self._burst_buffer.append(char)

                        # Check for burst terminator (Enter or Tab)
                        if kbd.vkCode in (VK_RETURN, VK_TAB):
                            if active_mode in ("both", "bluetooth") and len(self._burst_buffer) >= 2:
                                captured = "".join(self._burst_buffer).strip()
                                if captured:
                                    logger.info("[Tier 1 Hook] Captured Enter-terminated barcode: %s", captured)
                                    try:
                                        self.on_barcode_captured(captured, "Bluetooth")
                                    except Exception as e:
                                        logger.error("Error in on_barcode_captured callback: %s", e)
                            self._in_burst = False
                            self._burst_buffer.clear()
                            self._burst_key_count = 0
                            self._swallowed_current_burst = True
                            return 1  # Swallow terminating Enter/Tab

                        # Mode-dependent suppression
                        if active_mode == "http":
                            # In HTTP Only mode: completely swallow Bluetooth HID keystrokes
                            self._swallowed_current_burst = True
                            return 1
                        elif active_mode in ("both", "bluetooth"):
                            # In Hybrid or Bluetooth mode: swallow keystrokes so OS does not type them directly
                            self._swallowed_current_burst = True
                            return 1

                elif is_up:
                    if self._swallowed_current_burst or self._in_burst:
                        return 1

        except Exception as e:
            logger.debug("Exception in WH_KEYBOARD_LL hook proc: %s", e)

        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _message_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self._thread_id = kernel32.GetCurrentThreadId()
        self._proc_ref = HOOKPROC(self._hook_callback)

        hmod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._proc_ref,
            hmod,
            0,
        )

        if not self._hook:
            err = ctypes.get_last_error()
            logger.error("Failed to install WH_KEYBOARD_LL hook: %d", err)
            self._hook_installed.set()
            self._is_running.clear()
            return

        logger.info("WH_KEYBOARD_LL hook installed successfully (handle=%s)", self._hook)
        self._is_running.set()
        self._hook_installed.set()

        msg = wintypes.MSG()
        while self._is_running.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
            logger.info("WH_KEYBOARD_LL hook uninstalled cleanly")

        self._is_running.clear()

    def start(self) -> bool:
        """Start the keyboard hook in a background message pump thread."""
        if os.name != "nt":
            return False
        if self.is_running:
            return True

        self._hook_installed.clear()
        self._hook_thread = threading.Thread(
            target=self._message_loop,
            name="BinaryReceptor-KeyboardHook",
            daemon=True,
        )
        self._hook_thread.start()
        self._hook_installed.wait(timeout=3.0)
        return self.is_running

    def stop(self) -> None:
        """Stop the keyboard hook and post WM_QUIT to terminate message pump."""
        if not self.is_running:
            return

        self._is_running.clear()
        if self._thread_id and os.name == "nt":
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass

        if self._hook_thread and self._hook_thread.is_alive():
            self._hook_thread.join(timeout=1.0)
        self._hook_thread = None
        self._thread_id = None
