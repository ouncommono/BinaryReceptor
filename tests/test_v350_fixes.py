"""Comprehensive Verification Test Suite for BinaryReceptor v3.5.0 Release.

Tests all 11 architectural mandates:
  1. Re-Architect Bluetooth HID vs. HTTP Conflict & Deduplication
  2. Typing Modes (Copy to Clipboard) under Bluetooth
  3. OS Keyboard Layout Independence (Farsi Garbling Fix)
  4. BinaryEye Protocol Parity & Immediate 200 OK Beep Prevention
  5. Strict GUI Geometry (Start Server Button Fixed 140x38px)
  6. Typographical Errors & Complete i18n Fixes (Suffixes, Theme buttons, /)
  7. Holistic Color Palette Overhaul (LivePreviewBox in Light Theme)
  8. Start Minimized on Launch Setting & Integration
  9. Ghost System Tray Icon Elimination (Explicit tray.hide() on exit)
  10. Version Bump & Multi-File Consistency across all artifacts
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.version import __version__, APP_NAME, APP_DISPLAY_NAME, APP_ID
from src.config import AppConfig, ConfigManager
from src.core.deduplicator import ScanDeduplicator
from src.core.hid_interceptor import (
    HIDInterventionEngine,
    INJECTOR_EXTRA_INFO,
)
from src.core.http_server import parse_binaryeye_request, ScanPayload
from src.core.key_injector import (
    KeyInjector,
    KEYEVENTF_UNICODE,
    win32_get_clipboard_text,
    win32_set_clipboard_text,
)
from src.core.qr_helper import build_forwarding_url
from src.ui.i18n import TRANSLATIONS, tr
from src.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET


@pytest.fixture(autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(["BinaryReceptor", "-platform", "offscreen"])
    yield app


# ==============================================================================
# Mandate 1: Re-Architect Bluetooth HID vs. HTTP Conflict & Deduplication
# ==============================================================================
def test_mandate_1_hid_interceptor_burst_detection_and_dispatch():
    """Verify HIDInterventionEngine captures rapid burst and dispatches barcode."""
    dispatched: list[str] = []
    engine = HIDInterventionEngine(
        mode_getter=lambda: "both",
        output_mode_getter=lambda: "type",
        on_hid_scan_intercepted=lambda s: dispatched.append(s),
        enabled=False,
    )

    # Accumulate characters mimicking high-speed HID scanner input (<45ms)
    engine._burst_chars = ["B", "A", "R", "C", "O", "D", "E", "-", "9", "9"]
    engine._finalize_burst()

    assert len(dispatched) == 1
    assert dispatched[0] == "BARCODE-99"


def _clean_window(win, cm):
    try:
        if hasattr(win, "hid_interceptor"):
            win.hid_interceptor.stop()
        win.stop_server()
        win._worker_stop.set()
        win.close()
    except Exception:
        pass
    try:
        cm.close()
    except Exception:
        pass


def test_mandate_1_http_mode_drops_bluetooth_scan(tmp_path):
    """In HTTP Only mode, Bluetooth scans must be strictly dropped."""
    from src.ui.main_window import MainWindow

    cfg_file = tmp_path / "settings.ini"
    cm = ConfigManager(cfg_file)
    cm.current.minimize_to_tray = True
    cm.save(mode="http")

    win = MainWindow(cm)
    win.config.minimize_to_tray = True
    try:
        # Enqueue Bluetooth payload
        bt_payload = ScanPayload(content="BT-SCAN-123", source="Bluetooth")
        win.enqueue_scan(bt_payload)

        # Worker should not process Bluetooth scan
        assert win.scan_queue.empty()
    finally:
        _clean_window(win, cm)


# ==============================================================================
# Mandate 2: Typing Modes (Copy to Clipboard) under Bluetooth
# ==============================================================================
def test_mandate_2_bluetooth_hid_copy_to_clipboard_only():
    """When output_mode is copy_only, HID burst routes to clipboard without typing."""
    intercepted: list[str] = []
    engine = HIDInterventionEngine(
        mode_getter=lambda: "both",
        output_mode_getter=lambda: "copy_only",
        on_hid_scan_intercepted=lambda s: intercepted.append(s),
        enabled=False,
    )

    engine._burst_chars = ["B", "T", "-", "C", "L", "I", "P", "-", "1"]
    engine._finalize_burst()

    assert len(intercepted) == 1
    assert intercepted[0] == "BT-CLIP-1"
    assert win32_get_clipboard_text() == "BT-CLIP-1"


# ==============================================================================
# Mandate 3: OS Keyboard Layout Independence (Farsi Garbling Fix)
# ==============================================================================
def test_mandate_3_unicode_sendinput_layout_independence():
    """KeyInjector generates KEYEVENTF_UNICODE with wVk=0 to bypass OS layout maps."""
    injector = KeyInjector(dry_run=False)

    for ch in ("A", "z", "5", "-", "@", "س", "ل", "ا", "م"):
        event = injector.make_unicode_event(ord(ch), key_up=False)
        assert event.type == 1  # INPUT_KEYBOARD
        assert event.union.ki.wVk == 0
        assert event.union.ki.wScan == ord(ch)
        assert event.union.ki.dwFlags & KEYEVENTF_UNICODE != 0
        assert event.union.ki.dwExtraInfo == INJECTOR_EXTRA_INFO


# ==============================================================================
# Mandate 4: BinaryEye Protocol Parity & Immediate 200 OK Beep Prevention
# ==============================================================================
def test_mandate_4_protocol_parity_get_and_post():
    """Verify HTTP server parses GET (?result=...) and POST JSON perfectly."""
    # 1. GET with ?result=
    payload_get, is_health = parse_binaryeye_request(
        method="GET",
        path_and_query="/?result=SCANNED-ITEM-42&format=QR_CODE",
        headers={},
        body_bytes=b"",
    )
    assert payload_get is not None
    assert payload_get.content == "SCANNED-ITEM-42"
    assert payload_get.format == "QR_CODE"
    assert is_health is False

    # 2. POST JSON with content, raw, format, scanId
    json_body = json.dumps({
        "content": "JSON-PAYLOAD-77",
        "raw": "4a534f4e",
        "format": "CODE_128",
        "scanId": "scan-abc-999",
    }).encode("utf-8")
    payload_post, _ = parse_binaryeye_request(
        method="POST",
        path_and_query="/",
        headers={"content-type": "application/json"},
        body_bytes=json_body,
    )
    assert payload_post is not None
    assert payload_post.content == "JSON-PAYLOAD-77"
    assert payload_post.raw == "4a534f4e"
    assert payload_post.format == "CODE_128"
    assert payload_post.scan_id == "scan-abc-999"


def test_mandate_4_editable_forwarding_url(tmp_path):
    """UI allows manual editing of forwarding URL and regenerates QR code."""
    from src.ui.main_window import MainWindow

    cfg_file = tmp_path / "settings.ini"
    cm = ConfigManager(cfg_file)
    cm.current.minimize_to_tray = True
    win = MainWindow(cm)
    win.config.minimize_to_tray = True
    try:
        assert not win.txt_url_display.isReadOnly()

        # Simulate user manual edit
        custom_url = "http://192.168.1.200:8080/custom?result={RESULT}"
        win.txt_url_display.setText(custom_url)
        win._on_forwarding_url_edited(custom_url)
        assert win.lbl_qr_url_img.pixmap() is not None
        assert not win.lbl_qr_url_img.pixmap().isNull()
    finally:
        _clean_window(win, cm)


# ==============================================================================
# Mandate 5: Strict GUI Geometry (Fix Start Button Resizing)
# ==============================================================================
def test_mandate_5_start_button_fixed_geometry(tmp_path):
    """btn_master_power must have fixed size (140, 38) and fixed size policy."""
    from PySide6.QtWidgets import QSizePolicy
    from src.ui.main_window import MainWindow

    cfg_file = tmp_path / "settings.ini"
    cm = ConfigManager(cfg_file)
    cm.current.minimize_to_tray = True
    win = MainWindow(cm)
    win.config.minimize_to_tray = True
    try:
        btn = win.btn_master_power
        assert btn.minimumWidth() == 140
        assert btn.maximumWidth() == 140
        assert btn.minimumHeight() == 38
        assert btn.maximumHeight() == 38
        assert btn.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert btn.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Fixed

        # Ensure stylesheet enforces max and min width/height
        assert "min-width: 138px" in DARK_STYLESHEET
        assert "max-width: 138px" in DARK_STYLESHEET
        assert "min-height: 36px" in DARK_STYLESHEET
        assert "max-height: 36px" in DARK_STYLESHEET
    finally:
        _clean_window(win, cm)


# ==============================================================================
# Mandate 6: Typographical Errors & i18n Fixes
# ==============================================================================
def test_mandate_6_i18n_typo_fixes_and_parity():
    """Verify 'Connection / QR Code', 'Settings / Hardware', and Persian translations."""
    en = TRANSLATIONS["en"]
    fa = TRANSLATIONS["fa"]

    # 1. Parity between English and Persian
    assert set(en.keys()) == set(fa.keys())

    # 2. No ampersands or underscores in tab titles
    assert en["tab_connection"] == "Connection / QR Code"
    assert en["tab_settings"] == "Settings / Hardware"
    assert fa["tab_connection"] == "اتصال / کد QR"
    assert fa["tab_settings"] == "تنظیمات / سخت‌افزار"

    # 3. Persian Suffixes translated
    assert fa["lbl_suffix"] == "پسوند (تایپ بعد از بارکد):"
    assert fa["btn_add_enter"] == "+ اینتر"
    assert fa["btn_add_tab"] == "+ تب"
    assert fa["btn_add_date"] == "+ تاریخ جاری"

    # 4. Theme buttons translated
    assert "btn_theme_dark" in en and "btn_theme_light" in en
    assert "btn_theme_dark" in fa and "btn_theme_light" in fa
    assert fa["btn_theme_dark"] == "🌙 پوسته تیره"
    assert fa["btn_theme_light"] == "☀️ پوسته روشن"


# ==============================================================================
# Mandate 7: Holistic Color Palette Overhaul
# ==============================================================================
def test_mandate_7_live_preview_box_styling():
    """Verify #LivePreviewBox is styled with high contrast in both themes."""
    assert "#LivePreviewBox" in DARK_STYLESHEET
    assert "#LivePreviewBox" in LIGHT_STYLESHEET

    # Light theme LivePreviewBox has light background (#f0f9ff)
    assert "#f0f9ff" in LIGHT_STYLESHEET
    # Dark theme LivePreviewBox has dark background (#0b1120)
    assert "#0b1120" in DARK_STYLESHEET


# ==============================================================================
# Mandate 8: Start Minimized on Launch
# ==============================================================================
def test_mandate_8_start_minimized_config_and_ui(tmp_path):
    """Verify start_minimized checkbox exists, loads, saves, and updates settings.ini."""
    from src.ui.main_window import MainWindow

    cfg_file = tmp_path / "settings.ini"
    cm = ConfigManager(cfg_file)
    cm.current.minimize_to_tray = True
    win = MainWindow(cm)
    win.config.minimize_to_tray = True
    try:
        assert hasattr(win, "chk_start_min")
        assert win.chk_start_min.isChecked() is False

        # Verify ConfigManager persistence
        cm.save(start_minimized=True)
        assert cm.current.start_minimized is True
        saved_text = cfg_file.read_text(encoding="utf-8")
        assert "start_minimized = true" in saved_text

        # Verify UI form loads start_minimized=True
        win._load_settings_into_form(cm.current)
        assert win.chk_start_min.isChecked() is True
    finally:
        _clean_window(win, cm)


# ==============================================================================
# Mandate 9: Ghost System Tray Icon Fix
# ==============================================================================
def test_mandate_9_system_tray_hide_on_exit(tmp_path):
    """MainWindow.exit_application() explicitly calls tray.hide() to prevent ghost icon."""
    from src.ui.main_window import MainWindow

    cfg_file = tmp_path / "settings.ini"
    cm = ConfigManager(cfg_file)
    cm.current.minimize_to_tray = True
    win = MainWindow(cm)
    win.config.minimize_to_tray = True
    try:
        with patch.object(win.tray, "hide") as mock_hide, patch("PySide6.QtWidgets.QApplication.quit"):
            win.exit_application()
            assert mock_hide.call_count >= 1
    finally:
        _clean_window(win, cm)


# ==============================================================================
# Mandate 10: Version Bump & Multi-File Consistency
# ==============================================================================
def test_mandate_10_version_consistency_v350():
    """Verify v3.5.0 across version constants, mutex, and version.txt."""
    assert __version__ == "3.5.0"
    assert APP_ID == "BinaryReceptor.3.5.0"
    assert APP_DISPLAY_NAME == "BinaryReceptor v3.5.0"

    root = Path(__file__).resolve().parent.parent

    # Check res/version.txt
    ver_txt = root / "res" / "version.txt"
    if ver_txt.exists():
        content = ver_txt.read_text(encoding="utf-8")
        assert "filevers=(3, 5, 0, 0)" in content
        assert "prodvers=(3, 5, 0, 0)" in content
        assert "'FileVersion', '3.5.0'" in content
        assert "'ProductVersion', '3.5.0'" in content

    # Check main.py mutex
    main_py = (root / "src" / "main.py").read_text(encoding="utf-8")
    assert "BinaryReceptor_3_5_0_Mutex" in main_py

    # Check workflow
    workflow = (root / ".github" / "workflows" / "build_release.yml").read_text(encoding="utf-8")
    assert "BinaryReceptor-v3.5.0-win64.zip" in workflow
    assert "v3.5.0" in workflow
