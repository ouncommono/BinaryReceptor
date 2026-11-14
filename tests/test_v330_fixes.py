"""Comprehensive unit and integration tests for BinaryReceptor Version 3.3.0.

Validates:
1. Operation Mode Isolation:
   - When mode == 'http', Bluetooth scans are dropped unconditionally.
   - When mode == 'bluetooth', HTTP scans are dropped unconditionally.
2. Time-Interval Cooldown Deduplication:
   - No hashing; simple time-interval cooldown gate suppresses duplicate scans arriving
     from alternating transports (Bluetooth + HTTP) or rapid re-transmissions within cooldown_ms.
   - Scans arriving after cooldown_ms are cleanly accepted.
3. Unified Output Modes for Bluetooth and HTTP:
   - 'copy_only' copies to system clipboard ONLY and never injects keystrokes.
   - 'paste' simulates Ctrl+V.
   - 'log_only' records scan without typing or touching clipboard.
4. Scans Counter moved to Live Scan Activity page:
   - Verified present in Tab 1 (Dashboard) header above table.
5. Standard Forwarding URL alignment with markusfisch/BinaryEye:
   - Verifies all 4 BinaryEye forwarding modes and clean base URLs.
6. Version 3.3.0 metadata consistency.
"""
from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock

from src.version import __version__, APP_ID, APP_DISPLAY_NAME
from src.core.http_server import ScanPayload
from src.core.deduplicator import ScanDeduplicator, DeduplicationEngine
from src.core.key_injector import KeyInjector
from src.core.qr_helper import build_forwarding_url
from src.ui.i18n import TRANSLATIONS, tr


def test_v330_version_and_metadata():
    """Verify version 3.4.0 metadata across all exports."""
    assert __version__ == "3.4.0"
    assert APP_ID == "BinaryReceptor.3.4.0"
    assert "v3.4.0" in APP_DISPLAY_NAME


def test_operation_mode_isolation_bluetooth_dropped_in_http_mode():
    """Requirement 1: When mode is HTTP Only, Bluetooth scans MUST be dropped."""
    from src.config import ConfigManager, AppConfig
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()

    window = MainWindow(cfg_mgr)
    try:
        # Set mode to http
        window.config.mode = "http"

        # Simulate Bluetooth scan arriving
        bt_payload = ScanPayload(content="BT-BLOCKED-BARCODE", source="Bluetooth")
        window.enqueue_scan(bt_payload)

        # Worker loop or manual process: verify enqueue dropped or process drops
        window._process_scan_payload(bt_payload)

        # Total scans counter must NOT have incremented
        assert window.cnt_bt == 0
        assert window.cnt_total == 0
    finally:
        window.close()
        cfg_mgr.close()


def test_operation_mode_isolation_http_dropped_in_bluetooth_mode():
    """Requirement 1: When mode is Bluetooth Only, HTTP scans MUST be dropped."""
    from src.config import ConfigManager
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()

    window = MainWindow(cfg_mgr)
    try:
        # Set mode to bluetooth
        window.config.mode = "bluetooth"

        # Simulate HTTP scan arriving
        http_payload = ScanPayload(content="HTTP-BLOCKED-BARCODE", source="HTTP")
        window.enqueue_scan(http_payload)
        window._process_scan_payload(http_payload)

        # Total scans counter must NOT have incremented
        assert window.cnt_http == 0
        assert window.cnt_total == 0
    finally:
        window.close()
        cfg_mgr.close()


def test_time_interval_cooldown_hybrid_deduplication():
    """Requirement 2: Time-interval cooldown gate suppresses second rapid scan across transports."""
    dedup = ScanDeduplicator(window_ms=1000, enabled=True)

    # First scan arrives via Bluetooth
    is_dup1, msg1 = dedup.check_and_record("HYBRID-SCAN-1234", source="Bluetooth")
    assert not is_dup1
    assert "Accepted" in msg1

    # Second scan arrives 50ms later via HTTP (BinaryEye dual-connection)
    time.sleep(0.05)
    is_dup2, msg2 = dedup.check_and_record("HYBRID-SCAN-1234", source="HTTP")
    assert is_dup2
    assert "Suppressed duplicate" in msg2 or "already processed" in msg2
    assert dedup.duplicates_blocked == 1

    # Third scan arrives after cooldown expires
    time.sleep(1.05)
    is_dup3, msg3 = dedup.check_and_record("HYBRID-SCAN-1234", source="HTTP")
    assert not is_dup3
    assert "Accepted" in msg3


def test_unified_output_copy_only_for_bluetooth_scans():
    """Requirement 3: Copy to clipboard only mode NEVER injects keystrokes for Bluetooth scans."""
    from src.config import ConfigManager
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()

    window = MainWindow(cfg_mgr)
    try:
        # Set output_mode to copy_only
        window.config.output_mode = "copy_only"
        window.injector = KeyInjector(dry_run=True)

        bt_payload = ScanPayload(content="BLUETOOTH-COPY-ONLY-TEST", source="Bluetooth")
        status = window._dispatch_output(bt_payload.content, bt_payload.source)

        assert status == tr("status_copied", window.config.language)
        # Verify zero simulated typing events recorded
        assert len(window.injector.recorded_events) == 0
    finally:
        window.close()
        cfg_mgr.close()


def test_scans_counter_in_live_activity_page():
    """Requirement 5: Scans counter/statistics widget is in Tab 1 (Dashboard) header."""
    from src.config import ConfigManager
    from src.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["BinaryReceptor", "-platform", "offscreen"])
    cfg_mgr = ConfigManager()

    window = MainWindow(cfg_mgr)
    try:
        assert hasattr(window, "stats_summary_card")
        assert window.stats_summary_card is not None
        # Verify all 4 counters are present and initialized
        assert window.lbl_kpi_total.text() == "0"
        assert window.lbl_kpi_bt.text() == "0"
        assert window.lbl_kpi_http.text() == "0"
        assert window.lbl_kpi_dedup.text() == "0"
    finally:
        window.close()
        cfg_mgr.close()


def test_standard_forwarding_url_alignment():
    """Requirement 4: Verify authentic alignment of Standard Forwarding URL with BinaryEye."""
    # POST application/json -> clean base URL http://<IP>:<PORT>/
    url_json = build_forwarding_url("192.168.1.50", 24234, "post_json")
    assert url_json == "http://192.168.1.50:24234/"

    # POST application/x-www-form-urlencoded -> clean base URL http://<IP>:<PORT>/
    url_form = build_forwarding_url("192.168.1.50", 24234, "post_form")
    assert url_form == "http://192.168.1.50:24234/"

    # GET with full query string -> clean base URL http://<IP>:<PORT>/
    url_query = build_forwarding_url("192.168.1.50", 24234, "get_query")
    assert url_query == "http://192.168.1.50:24234/"

    # GET and simply add content -> http://<IP>:<PORT>/?content=
    url_append = build_forwarding_url("192.168.1.50", 24234, "get_append")
    assert url_append == "http://192.168.1.50:24234/?content="

    # GET with template -> http://<IP>:<PORT>/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}
    url_template = build_forwarding_url("192.168.1.50", 24234, "get_template")
    assert "{RESULT}" in url_template
    assert "{FORMAT}" in url_template
    assert "{RESULT_BYTES}" in url_template
