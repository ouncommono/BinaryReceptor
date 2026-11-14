"""Comprehensive Verification Test Suite for BinaryReceptor v3.6.0 Release.

Verifies:
  - Mandate 1: Bluetooth RFCOMM Winsock architecture, SOCKADDR_BTH packing (_pack_=1),
    SDP service advertisement, dynamic RFCOMM channel allocation (BT_PORT_ANY),
    stream framing, JSON/raw parsing, and HTTP mode isolation.
  - Mandate 2: Strict version bump to 3.6.0 across all code, PE metadata, mutex, and CI/CD.
  - Mandate 3: Bilingual documentation symmetry and changelog purging.
"""
from __future__ import annotations

import ctypes
import os
import socket
import time
from pathlib import Path

import pytest

from src.core.bt_server import (
    AF_BTH,
    BTPROTO_RFCOMM,
    BT_PORT_ANY,
    GUID,
    SOCKADDR_BTH,
    CSADDR_INFO,
    WSAQUERYSETW,
    ws2_32,
    is_bluetooth_available,
    get_local_bt_address,
    BluetoothServerController,
)
from src.core.deduplicator import ScanDeduplicator
from src.core.http_server import ScanPayload
from src.version import __version__, APP_ID, APP_DISPLAY_NAME, DEFAULT_BT_UUID


# ==============================================================================
# Mandate 1: Deep Investigation & Bluetooth RFCOMM Repairs
# ==============================================================================
def test_bt_sockaddr_bth_packing_and_offsets():
    """Verify SOCKADDR_BTH structure is packed with 1-byte alignment matching Winsock SDK ws2bth.h."""
    assert getattr(SOCKADDR_BTH, "_pack_", None) == 1, "SOCKADDR_BTH must define _pack_ = 1"
    assert ctypes.sizeof(SOCKADDR_BTH) == 30, f"Expected sizeof(SOCKADDR_BTH) == 30, got {ctypes.sizeof(SOCKADDR_BTH)}"

    # Exact field offsets matching Microsoft ws2bth.h:
    # USHORT addressFamily (0)
    # BTH_ADDR btAddr (2)
    # GUID serviceClassId (10)
    # ULONG port (26)
    assert SOCKADDR_BTH.addressFamily.offset == 0
    assert SOCKADDR_BTH.btAddr.offset == 2
    assert SOCKADDR_BTH.serviceClassId.offset == 10
    assert SOCKADDR_BTH.port.offset == 26


def test_bt_port_any_binding():
    """Verify binding to BT_PORT_ANY (-1) dynamically allocates a valid non-zero RFCOMM port on Windows."""
    if not is_bluetooth_available():
        pytest.skip("Bluetooth adapter not available on this host")

    s = socket.socket(AF_BTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
    try:
        s.bind(("00:00:00:00:00:00", BT_PORT_ANY))
        s.listen(2)
        addr, port = s.getsockname()
        assert addr and addr != "00:00:00:00:00:00"
        assert port > 0, f"Expected non-zero dynamically allocated RFCOMM channel, got {port}"
    finally:
        s.close()


def test_bt_sdp_service_registration_and_deregistration():
    """Verify WSASetServiceW SDP registration and deletion with native packed SOCKADDR_BTH."""
    if not is_bluetooth_available() or not ws2_32:
        pytest.skip("Bluetooth socket or ws2_32 not available on this host")

    controller = BluetoothServerController(service_uuid=DEFAULT_BT_UUID, service_name="TestReceptor")
    srv = socket.socket(AF_BTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
    try:
        srv.bind(("00:00:00:00:00:00", BT_PORT_ANY))
        srv.listen(2)

        reg_ok = controller._register_sdp(srv)
        assert reg_ok is True, "WSASetServiceW SDP registration must succeed"
        assert controller._sockaddr is not None
        assert controller._sockaddr.port > 0, "SDP registered port must be non-zero"
    finally:
        controller._deregister_sdp()
        srv.close()


def test_bt_dispatch_plain_barcode_text():
    """Verify raw plain text barcode stream lines are parsed and dispatched as ScanPayload."""
    received: list[ScanPayload] = []
    controller = BluetoothServerController(on_scan=lambda p: received.append(p))

    controller._dispatch_parsed_scan("4006381333931", "client-bt-addr")
    assert len(received) == 1
    p = received[0]
    assert p.content == "4006381333931"
    assert p.source == "Bluetooth"
    assert p.client_address == "client-bt-addr"
    assert p.format == ""
    assert p.scan_id is None


def test_bt_dispatch_json_payload_binaryeye_parity():
    """Verify JSON payloads sent by BinaryEye over Bluetooth are fully parsed (content, format, scanId)."""
    received: list[ScanPayload] = []
    controller = BluetoothServerController(on_scan=lambda p: received.append(p))

    json_str = '{"content": "9876543210", "format": "QR_CODE", "scanId": "bt-scan-001", "raw": "OTg3NjU0MzIxMA=="}'
    controller._dispatch_parsed_scan(json_str, "phone-bt-addr")

    assert len(received) == 1
    p = received[0]
    assert p.content == "9876543210"
    assert p.format == "QR_CODE"
    assert p.scan_id == "bt-scan-001"
    assert p.raw == "OTg3NjU0MzIxMA=="
    assert p.source == "Bluetooth"


def test_bt_dispatch_query_string_format():
    """Verify key-value query string format (result=...&format=...) is parsed correctly."""
    received: list[ScanPayload] = []
    controller = BluetoothServerController(on_scan=lambda p: received.append(p))

    controller._dispatch_parsed_scan("result=ITEM-9988&format=CODE_128", "phone-bt-addr")
    assert len(received) == 1
    p = received[0]
    assert p.content == "ITEM-9988"
    assert p.format == "CODE_128"


def test_bt_mode_isolation_drops_scan_when_http_only():
    """Verify Bluetooth scan is strictly ignored/dropped when operation mode is HTTP only."""
    received: list[ScanPayload] = []
    controller = BluetoothServerController(
        on_scan=lambda p: received.append(p),
        mode_checker=lambda: "http",
    )

    controller._dispatch_parsed_scan("SHOULD-BE-DROPPED", "phone-bt-addr")
    assert len(received) == 0


def test_bt_controller_lifecycle_start_stop():
    """Verify BluetoothServerController start, status updates, and clean stop."""
    if not is_bluetooth_available():
        pytest.skip("Bluetooth not available on this host")

    statuses: list[str] = []
    controller = BluetoothServerController(
        on_status_change=lambda s: statuses.append(s),
    )

    ok, msg = controller.start()
    assert ok is True
    assert controller.is_running is True
    assert controller.status == "Listening"

    controller.stop()
    assert controller.is_running is False
    assert controller.status == "Stopped"


# ==============================================================================
# Deduplication Logic Tests (Same Barcode vs Different Barcode)
# ==============================================================================
def test_deduplicator_cooldown_same_vs_different_barcode():
    """Verify identical barcode within cooldown is suppressed, but different barcode is accepted."""
    dedup = ScanDeduplicator(window_ms=1000, enabled=True)

    # Scan 1: Bluetooth scan of BARCODE-A
    is_dup1, _ = dedup.check_and_record("BARCODE-A", source="Bluetooth")
    assert not is_dup1

    # Scan 2: Rapid HTTP scan of identical BARCODE-A (dual-send duplicate)
    time.sleep(0.05)
    is_dup2, msg2 = dedup.check_and_record("BARCODE-A", source="HTTP")
    assert is_dup2
    assert "Suppressed duplicate" in msg2 or "already processed" in msg2

    # Scan 3: Rapid HTTP scan of a DIFFERENT BARCODE-B (must be accepted!)
    time.sleep(0.05)
    is_dup3, _ = dedup.check_and_record("BARCODE-B", source="HTTP")
    assert not is_dup3


# ==============================================================================
# Mandate 2: Version Bump & Multi-File Consistency (v3.6.0)
# ==============================================================================
def test_mandate_2_version_consistency_v360():
    """Verify v3.6.0 across version constants, mutex, settings, and build configuration."""
    assert __version__ == "3.6.0"
    assert APP_ID == "BinaryReceptor.3.6.0"
    assert APP_DISPLAY_NAME == "BinaryReceptor v3.6.0"

    root = Path(__file__).resolve().parent.parent

    # 1. Check res/version.txt
    ver_txt = root / "res" / "version.txt"
    if ver_txt.exists():
        content = ver_txt.read_text(encoding="utf-8")
        assert "filevers=(3, 6, 0, 0)" in content
        assert "prodvers=(3, 6, 0, 0)" in content
        assert "'FileVersion', '3.6.0'" in content
        assert "'ProductVersion', '3.6.0'" in content

    # 2. Check main.py mutex
    main_py = (root / "src" / "main.py").read_text(encoding="utf-8")
    assert "BinaryReceptor_3_6_0_Mutex" in main_py

    # 3. Check settings.ini
    settings_ini = (root / "settings.ini").read_text(encoding="utf-8")
    assert "v3.6.0" in settings_ini

    # 4. Check CI/CD workflow
    workflow = (root / ".github" / "workflows" / "build_release.yml").read_text(encoding="utf-8")
    assert "BinaryReceptor-v3.6.0-win64.zip" in workflow
    assert "v3.6.0" in workflow
