"""Bluetooth Radio state controller and connection detector for BinaryReceptor v3.4.0.

Provides programmatic Win32 / WinRT Bluetooth radio control and active connection detection:
  - Programmatic Radio Toggle: Turn Bluetooth radio On/Off via WinRT Windows.Devices.Radios.Radio
    (used to unconditionally isolate HTTP Server Only mode from OS-level Bluetooth HID injection).
  - State Restoration: Restores previous Bluetooth radio state when stopping or switching modes.
  - Active Connection Detection: Detects connected Bluetooth HID keyboards and barcode scanners via Win32 Raw Input.
"""
from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import threading
import time
from ctypes import wintypes
from typing import Any

logger = logging.getLogger("BinaryReceptor.BTRadio")

# Win32 Raw Input Constants
RIM_TYPEKEYBOARD = 1
RIDI_DEVICENAME = 0x20000007


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ("hDevice", wintypes.HANDLE),
        ("dwType", wintypes.DWORD),
    ]


class BluetoothRadioController:
    """Manages system Bluetooth radio state and detects connected Bluetooth HID devices."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._previous_radio_state: str | None = None
        self._radio_managed_by_us: bool = False

    @staticmethod
    def _run_powershell(script: str, timeout: float = 8.0) -> str:
        """Execute a PowerShell command safely and return stdout."""
        try:
            res = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return res.stdout.strip()
        except Exception as e:
            logger.error("PowerShell radio command failed: %s", e)
            return ""

    def get_radio_state(self) -> str:
        """Query active Bluetooth radio state ('On', 'Off', or 'Unknown')."""
        if os.name != "nt":
            return "Unknown"

        script = """
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }[0]
        Function Await($asyncOp, $type) {
            $asTask = $asTaskGeneric.MakeGenericMethod($type)
            $netTask = $asTask.Invoke($null, @($asyncOp))
            $netTask.Wait(4000) | Out-Null
            $netTask.Result
        }
        try {
            [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
            $radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
            $bt = $radios | Where-Object { $_.Kind -eq 'Bluetooth' } | Select-Object -First 1
            if ($bt) { Write-Output $bt.State } else { Write-Output "NotFound" }
        } catch {
            Write-Output "Error"
        }
        """
        output = self._run_powershell(script)
        if "On" in output:
            return "On"
        elif "Off" in output:
            return "Off"
        elif "Disabled" in output:
            return "Off"
        return "Unknown"

    def set_radio_state(self, target_state: str) -> bool:
        """Programmatically set Bluetooth radio state ('On' or 'Off')."""
        if os.name != "nt":
            return False

        target = "Off" if target_state.lower() in ("off", "disable", "disabled", "0") else "On"

        script = f"""
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }}[0]
        Function Await($asyncOp, $type) {{
            $asTask = $asTaskGeneric.MakeGenericMethod($type)
            $netTask = $asTask.Invoke($null, @($asyncOp))
            $netTask.Wait(4000) | Out-Null
            $netTask.Result
        }}
        try {{
            [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
            [Windows.Devices.Radios.Radio]::RequestAccessAsync() | Out-Null
            $radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
            $bt = $radios | Where-Object {{ $_.Kind -eq 'Bluetooth' }} | Select-Object -First 1
            if ($bt) {{
                $targetEnum = [Windows.Devices.Radios.RadioState]::{target}
                $res = Await ($bt.SetStateAsync($targetEnum)) ([Windows.Devices.Radios.RadioAccessStatus])
                Write-Output "$res"
            }} else {{
                Write-Output "NotFound"
            }}
        }} catch {{
            Write-Output "Error: $_"
        }}
        """
        output = self._run_powershell(script)
        logger.info("Set Bluetooth Radio state to %s: %s", target, output)
        return "Allowed" in output or "Success" in output

    def ensure_radio_off_for_http_mode(self) -> bool:
        """Save current radio state and turn Bluetooth radio OFF for strict HTTP Only isolation."""
        with self._lock:
            current = self.get_radio_state()
            if current == "On":
                self._previous_radio_state = "On"
                self._radio_managed_by_us = True
                logger.info("Turning Bluetooth radio OFF to enforce HTTP Server Only isolation")
                return self.set_radio_state("Off")
            elif current == "Off":
                self._previous_radio_state = "Off"
            return True

    def restore_radio_state(self) -> bool:
        """Restore previous Bluetooth radio state if it was turned off by us."""
        with self._lock:
            if self._radio_managed_by_us and self._previous_radio_state == "On":
                logger.info("Restoring Bluetooth radio state to ON")
                success = self.set_radio_state("On")
                self._radio_managed_by_us = False
                self._previous_radio_state = None
                return success
            return True

    @staticmethod
    def is_bluetooth_keyboard_connected() -> bool:
        """Check if any Bluetooth HID keyboard or barcode scanner is connected via Raw Input.

        Returns:
            True if an active keyboard device is detected with Bluetooth HID service GUID
            (00001124) or BTHENUM in its device path.
        """
        if os.name != "nt":
            return False

        try:
            user32 = ctypes.windll.user32
            num_devices = wintypes.UINT()
            if user32.GetRawInputDeviceList(None, ctypes.byref(num_devices), ctypes.sizeof(RAWINPUTDEVICELIST)) != 0:
                return False
            if num_devices.value == 0:
                return False

            device_list = (RAWINPUTDEVICELIST * num_devices.value)()
            if user32.GetRawInputDeviceList(device_list, ctypes.byref(num_devices), ctypes.sizeof(RAWINPUTDEVICELIST)) < 0:
                return False

            for dev in device_list:
                if dev.dwType == RIM_TYPEKEYBOARD:
                    name_len = wintypes.UINT()
                    user32.GetRawInputDeviceInfoW(dev.hDevice, RIDI_DEVICENAME, None, ctypes.byref(name_len))
                    if name_len.value > 0:
                        name_buf = ctypes.create_unicode_buffer(name_len.value)
                        user32.GetRawInputDeviceInfoW(dev.hDevice, RIDI_DEVICENAME, name_buf, ctypes.byref(name_len))
                        name = name_buf.value.upper()
                        # 00001124 is Bluetooth SIG Human Interface Device profile UUID
                        if "00001124" in name or "BTHENUM" in name or "BTH" in name:
                            return True
        except Exception as e:
            logger.debug("Raw input check exception: %s", e)

        return False


# Global singleton instance
bt_radio_controller = BluetoothRadioController()
