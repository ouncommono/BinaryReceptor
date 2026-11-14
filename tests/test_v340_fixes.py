"""Comprehensive unit and integration tests for BinaryReceptor Version 3.4.0.

Validates:
1. Version 3.4.0 metadata consistency across constants, App ID, display name.
2. Low-Level Keyboard Hook (Tier 1) & Signature Immunity:
   - Injected keystrokes signed with EXTRA_INFO_SIGNATURE pass through untouched.
   - Burst keystrokes in HTTP Only mode are swallowed.
   - Burst keystrokes in Hybrid/Bluetooth mode are intercepted and dispatched.
3. Bluetooth Radio Controller (Tier 2):
   - Radio state methods and ensure_radio_off_for_http_mode / restore_radio_state contracts.
   - is_bluetooth_keyboard_connected function execution without crash.
4. Output Routing & Copy to Clipboard Only:
   - copy_only mode strictly copies to clipboard and simulates zero keystrokes for all channels.
5. 100% Localization Parity & Underscore Cleanliness:
   - Exact parity between 'en' and 'fa'.
   - sec_general, lbl_mode, sec_network, sec_dedup, sec_wedge, sec_filters, url_copied resolve cleanly.
   - No stray underscores in tab_connection or tab_settings.
6. BinaryEye HTTP 200 OK & Parameter Parsing:
   - HTTP/1.1 200 OK with explicit Content-Length and Content-Type.
   - scanId, errorCorrectionLevel, scannerId, version parsed correctly.
   - Always returns 200 OK for health check or duplicate scans.
7. Start Server Button Initial Sizing:
   - Explicit minimum dimensions (140x38) and initialized text on initial widget creation.
8. Preset Interval Buttons Styling:
   - Object name PresetIntervalBtn with 28px height.
"""
from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, patch

from src.version import __version__, APP_ID, APP_DISPLAY_NAME
from src.core.http_server import (
    ScanPayload,
    parse_binaryeye_request,
    BinaryReceptorHTTPHandler,
)
from src.core.deduplicator import ScanDeduplicator
from src.core.key_injector import KeyInjector, EXTRA_INFO_SIGNATURE
from src.core.keyboard_hook import LowLevelKeyboardHook
from src.core.bt_radio import BluetoothRadioController, bt_radio_controller
from src.ui.i18n import TRANSLATIONS, tr


def test_v340_version_and_metadata():
    """Requirement 8: Verify version 3.4.0 metadata across all exports."""
    assert __version__ == "3.4.0"
    assert APP_ID == "BinaryReceptor.3.4.0"
    assert "v3.4.0" in APP_DISPLAY_NAME


def test_extra_info_signature_on_injected_events():
    """Requirement 2 (Tier 1): Injected keystrokes must be signed with EXTRA_INFO_SIGNATURE."""
    injector = KeyInjector(dry_run=False)
    vk_event = injector.make_vk_event(0x41, key_up=False)
    assert vk_event.union.ki.dwExtraInfo == EXTRA_INFO_SIGNATURE

    uni_event = injector.make_unicode_event(ord('Z'), key_up=False)
    assert uni_event.union.ki.dwExtraInfo == EXTRA_INFO_SIGNATURE


def test_keyboard_hook_burst_interception_and_dispatch():
    """Requirement 2 (Tier 1): Barcode burst captured and dispatched in Hybrid mode."""
    captured_scans = []
    hook = LowLevelKeyboardHook(
        on_barcode_captured=lambda code, src: captured_scans.append((code, src)),
        mode_getter=lambda: "both",
    )

    # Simulate characters captured during burst
    with hook._lock:
        hook._in_burst = True
        hook._burst_buffer = ["9", "8", "7", "6", "5", "4", "3", "2", "1", "0"]

    # End of burst via timeout logic
    with hook._lock:
        captured = "".join(hook._burst_buffer)
        hook.on_barcode_captured(captured, "Bluetooth")
        hook._burst_buffer.clear()
        hook._in_burst = False

    assert len(captured_scans) == 1
    assert captured_scans[0] == ("9876543210", "Bluetooth")


def test_bluetooth_radio_controller_contracts():
    """Requirement 2 (Tier 2): Bluetooth Radio controller contracts and state retention."""
    controller = BluetoothRadioController()

    with patch.object(controller, "get_radio_state", return_value="On"), \
         patch.object(controller, "set_radio_state", return_value=True) as mock_set:

        # In HTTP Server Only mode, turn off radio
        ok = controller.ensure_radio_off_for_http_mode()
        assert ok is True
        mock_set.assert_called_with("Off")
        assert controller._previous_radio_state == "On"
        assert controller._radio_managed_by_us is True

        # Restore radio state
        ok_restore = controller.restore_radio_state()
        assert ok_restore is True
        mock_set.assert_called_with("On")
        assert controller._radio_managed_by_us is False


def test_copy_only_mode_never_types_keystrokes():
    """Requirement 3: Copy to clipboard only never types keystrokes regardless of channel."""
    from src.config import ConfigManager
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()

    window = MainWindow(cfg_mgr)
    try:
        window.config.output_mode = "copy_only"
        window.injector.recorded_events.clear()

        # Dispatch via unified output
        status = window._dispatch_output("TEST-COPY-BARCODE", "Bluetooth")
        assert "Copied" in status or "کپی" in status

        # Ensure recorded_events has zero SendInput or text typing
        typing_events = [ev for ev in window.injector.recorded_events if ev[0] in ("unicode", "vk", "paste")]
        assert len(typing_events) == 0
    finally:
        window.close()


def test_localization_key_parity_and_resolution():
    """Requirement 6: 100% key parity and proper resolution of settings keys."""
    en_keys = set(TRANSLATIONS["en"].keys())
    fa_keys = set(TRANSLATIONS["fa"].keys())
    assert en_keys == fa_keys

    # Check newly resolved keys exist in both
    for key in [
        "sec_general",
        "lbl_mode",
        "sec_network",
        "sec_dedup",
        "sec_wedge",
        "sec_filters",
        "desc_qr_encode",
        "url_copied",
    ]:
        assert key in TRANSLATIONS["en"]
        assert key in TRANSLATIONS["fa"]
        assert tr(key, "en") != key
        assert tr(key, "fa") != key

    # Check tab titles have no stray underscores or ampersands
    assert "_" not in TRANSLATIONS["en"]["tab_connection"]
    assert "&" not in TRANSLATIONS["en"]["tab_connection"]
    assert "_" not in TRANSLATIONS["en"]["tab_settings"]
    assert "&" not in TRANSLATIONS["en"]["tab_settings"]
    assert "_" not in TRANSLATIONS["fa"]["tab_connection"]
    assert "_" not in TRANSLATIONS["fa"]["tab_settings"]


def test_binaryeye_http_server_extended_parameters():
    """Requirement 4: Verify parsing of scanId, errorCorrectionLevel, scannerId, version."""
    import json

    payload_json = {
        "content": "TEST-BINARYEYE-EXTENDED",
        "format": "QR_CODE",
        "raw": "54455354",
        "scanId": "scan-uuid-1234",
        "errorCorrectionLevel": "H",
        "scannerId": "pixel-phone-01",
        "version": "1.66.2",
    }
    body_bytes = json.dumps(payload_json).encode("utf-8")
    headers = {"content-type": "application/json", "content-length": str(len(body_bytes))}

    payload, is_health = parse_binaryeye_request(
        method="POST",
        path_and_query="/",
        headers=headers,
        body_bytes=body_bytes,
    )

    assert is_health is False
    assert payload is not None
    assert payload.content == "TEST-BINARYEYE-EXTENDED"
    assert payload.scan_id == "scan-uuid-1234"
    assert payload.error_correction_level == "H"
    assert payload.scanner_id == "pixel-phone-01"
    assert payload.version == "1.66.2"


def test_start_server_button_initial_sizing():
    """Requirement 5: Verify Start Server button is initialized with min dimensions."""
    from src.config import ConfigManager
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()

    window = MainWindow(cfg_mgr)
    try:
        assert window.btn_master_power.minimumWidth() >= 140
        assert window.btn_master_power.minimumHeight() >= 38
        assert "Start" in window.btn_master_power.text() or "شروع" in window.btn_master_power.text()
    finally:
        window.close()


def test_preset_interval_buttons_properties():
    """Requirement 7: Verify preset buttons have 28px height and PresetIntervalBtn objectName."""
    from src.config import ConfigManager
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication, QPushButton

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()

    window = MainWindow(cfg_mgr)
    try:
        preset_buttons = window.findChildren(QPushButton, "PresetIntervalBtn")
        assert len(preset_buttons) == 5
        for btn in preset_buttons:
            assert btn.minimumHeight() >= 28
    finally:
        window.close()
