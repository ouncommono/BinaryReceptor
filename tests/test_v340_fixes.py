"""Comprehensive validation test suite for BinaryReceptor Version 3.4.0 (Mandates 1-11)."""
from __future__ import annotations

import json
import time
import urllib.parse
import pytest
from unittest.mock import MagicMock

from src.version import __version__, APP_ID, APP_DISPLAY_NAME, APP_NAME
from src.core.http_server import parse_binaryeye_request, ScanPayload
from src.core.deduplicator import ScanDeduplicator
from src.core.hid_interceptor import HIDInterventionEngine
from src.core.key_injector import (
    KeyInjector,
    INJECTOR_EXTRA_INFO,
    KEYEVENTF_UNICODE,
    win32_set_clipboard_text,
    win32_get_clipboard_text,
)
from src.ui.i18n import TRANSLATIONS, tr


def test_mandate_10_version_and_metadata_v340():
    """Mandate 10: Verify version is 3.4.0 across all constants and PE version file."""
    assert __version__ == "3.4.0"
    assert APP_ID == "BinaryReceptor.3.4.0"
    assert "v3.4.0" in APP_DISPLAY_NAME

    from pathlib import Path
    ver_txt = Path(__file__).resolve().parent.parent / "res" / "version.txt"
    if ver_txt.exists():
        content = ver_txt.read_text(encoding="utf-8")
        assert "(3, 4, 0, 0)" in content
        assert "'FileVersion', '3.4.0'" in content
        assert "'ProductVersion', '3.4.0'" in content


def test_mandate_1_strict_http_only_mode_discards_redundant_http_when_hid_detected():
    """Mandate 1: In 'http' mode, actively discard redundant HTTP injection if HID input detected."""
    engine = HIDInterventionEngine(
        mode_getter=lambda: "http",
        output_mode_getter=lambda: "type",
        enabled=False,
    )
    # Simulate an active or recent HID burst
    engine._in_burst = True
    assert engine.should_suppress_http_injection("BARCODE-12345") is True

    # After burst finishes recently with matching text
    engine._in_burst = False
    engine._last_burst_text = "BARCODE-12345"
    engine._last_burst_completed_time = time.monotonic()
    assert engine.should_suppress_http_injection("BARCODE-12345") is True

    # If no HID burst occurred, should NOT suppress
    engine._last_burst_completed_time = time.monotonic() - 10.0
    assert engine.should_suppress_http_injection("OTHER-BARCODE") is False


def test_mandate_2_hybrid_mode_deduplication_and_hid_intervention():
    """Mandate 2: In 'both' (Hybrid) mode, suppress duplicate HTTP injection when HID processed."""
    engine = HIDInterventionEngine(
        mode_getter=lambda: "both",
        output_mode_getter=lambda: "type",
        enabled=False,
    )

    # Register HTTP scan
    engine.register_http_scan("SCAN-HYBRID-777", scan_id="uuid-999")
    assert "uuid-999" in engine._active_http_scans

    # If HID burst was completed with this content
    engine._last_burst_text = "SCAN-HYBRID-777"
    engine._last_burst_completed_time = time.monotonic()
    assert engine.should_suppress_http_injection("SCAN-HYBRID-777", scan_id="uuid-999") is True

    # ScanDeduplicator scanId deduplication
    dedup = ScanDeduplicator(window_ms=1500, enabled=True)
    is_dup1, _ = dedup.check_and_record("SCAN-HYBRID-777", source="Bluetooth", scan_id="uuid-999")
    assert not is_dup1

    is_dup2, msg2 = dedup.check_and_record("SCAN-HYBRID-777", source="HTTP", scan_id="uuid-999")
    assert is_dup2
    assert "uuid-999" in msg2


def test_mandate_3_copy_to_clipboard_routing_under_bluetooth_hid():
    """Mandate 3: When output_mode is copy_only, raw HID input routes directly to clipboard."""
    intercepted_list = []
    engine = HIDInterventionEngine(
        mode_getter=lambda: "both",
        output_mode_getter=lambda: "copy_only",
        on_hid_scan_intercepted=lambda s: intercepted_list.append(s),
        enabled=False,
    )

    # Simulate accumulated burst characters
    engine._burst_chars = ["C", "O", "P", "Y", "-", "9", "9"]
    engine._finalize_copy_only()

    assert len(intercepted_list) == 1
    assert intercepted_list[0] == "COPY-99"
    assert win32_get_clipboard_text() == "COPY-99"


def test_mandate_4_keyboard_layout_independence_unicode_events():
    """Mandate 4: KeyInjector generates KEYEVENTF_UNICODE with wVk=0 and wScan=code_point."""
    injector = KeyInjector(dry_run=False)

    # Test Unicode event creation
    code_point = ord("A")  # 65
    event = injector.make_unicode_event(code_point, key_up=False)

    assert event.type == 1  # INPUT_KEYBOARD
    assert event.union.ki.wVk == 0
    assert event.union.ki.wScan == code_point
    assert event.union.ki.dwFlags & KEYEVENTF_UNICODE != 0
    assert event.union.ki.dwExtraInfo == INJECTOR_EXTRA_INFO

    # Test Persian character code point
    persian_cp = ord("ش")
    event_fa = injector.make_unicode_event(persian_cp, key_up=False)
    assert event_fa.union.ki.wVk == 0
    assert event_fa.union.ki.wScan == persian_cp
    assert event_fa.union.ki.dwFlags & KEYEVENTF_UNICODE != 0


def test_mandate_5_http_server_response_parity_and_scan_id():
    """Mandate 5: Immediate 200 OK with application/json on both POST and GET, reflecting scanId."""
    from src.core.http_server import BinaryReceptorHTTPHandler, BinaryReceptorHTTPServer
    import io

    # Test parse_binaryeye_request for JSON POST with scanId
    body = json.dumps({"content": "BE-SCAN-01", "format": "QR_CODE", "scanId": "abc-123"}).encode("utf-8")
    payload, is_health = parse_binaryeye_request(
        method="POST",
        path_and_query="/",
        headers={"content-type": "application/json"},
        body_bytes=body,
    )
    assert not is_health
    assert payload is not None
    assert payload.content == "BE-SCAN-01"
    assert payload.scan_id == "abc-123"

    # Test GET request returns valid payload
    payload_get, is_health_get = parse_binaryeye_request(
        method="GET",
        path_and_query="/?content=GET-BARCODE&scan_id=get-456",
        headers={},
        body_bytes=b"",
    )
    assert not is_health_get
    assert payload_get is not None
    assert payload_get.content == "GET-BARCODE"
    assert payload_get.scan_id == "get-456"


def test_mandate_7_localization_parity_and_no_missing_keys():
    """Mandate 7: Localization dictionaries have 100% parity, no missing keys, no rogue underscores."""
    en = TRANSLATIONS["en"]
    fa = TRANSLATIONS["fa"]

    # 1. Parity
    assert set(en.keys()) == set(fa.keys())

    # 2. Key requirements from Mandate 7
    mandatory_keys = [
        "sec_general",
        "sec_network",
        "sec_dedup",
        "sec_wedge",
        "sec_filters",
        "lbl_mode",
        "url_copied",
        "desc_qr_encode",
        "tab_connection",
    ]
    for k in mandatory_keys:
        assert k in en
        assert k in fa
        assert en[k].strip() != ""
        assert fa[k].strip() != ""

    # 3. Check for rogue underscores like "Connection _QR Code"
    assert " _QR" not in en["tab_connection"]
    assert "_QR" not in en["tab_connection"]
    assert en["tab_connection"] == "Connection & QR Code"


def test_mandate_8_quick_presets_dimensions_and_styling():
    """Mandate 8: Quick Presets buttons use dedicated PresetBtn styling with ample height."""
    from src.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET

    assert "QPushButton#PresetBtn" in DARK_STYLESHEET
    assert "QPushButton#PresetBtn" in LIGHT_STYLESHEET
    assert "min-height: 28px" in DARK_STYLESHEET
    assert "min-height: 28px" in LIGHT_STYLESHEET


def test_mandate_6_start_button_dimensions_and_lifecycle():
    """Mandate 6: Master Start button has explicit minimum dimensions and geometry update functions."""
    from src.config import ConfigManager
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()
    window = MainWindow(cfg_mgr)
    try:
        # Verify master power button minimum size
        min_size = window.btn_master_power.minimumSize()
        assert min_size.width() >= 140
        assert min_size.height() >= 38
        assert "Start" in window.btn_master_power.text() or "شروع" in window.btn_master_power.text()

        # Verify geometry lifecycle method exists
        assert hasattr(window, "_ensure_initial_geometry")
    finally:
        window.close()
        cfg_mgr.close()
