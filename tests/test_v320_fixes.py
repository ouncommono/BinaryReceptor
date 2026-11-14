"""Comprehensive unit tests for BinaryReceptor Version 3.2.0 requirements.

Validates:
1. Auto-start server is disabled by default (auto_start = False).
2. BinaryEye native HTTP request types compatibility.
3. Barcodes containing URLs and port numbers are never intercepted or dropped.
4. Continuous mode and /start route are completely removed.
5. 100% Persian (fa) and English (en) dictionary parity across all dropdowns, chips, and status keys.
6. Pure-Python PNG matrix generation without Pillow dependency.
7. Compact status bar and version 3.2.0 metadata consistency.
"""
from __future__ import annotations

import io
import json
import urllib.request
import urllib.parse
from PIL import Image
import pytest

from src.version import __version__, APP_ID, APP_DISPLAY_NAME
from src.config import AppConfig, ConfigManager, DEFAULT_SETTINGS_INI
from src.core.http_server import parse_binaryeye_request
from src.core.qr_helper import (
    build_forwarding_url,
    matrix_to_png_bytes,
    generate_qr_png_bytes,
)
from src.ui.i18n import TRANSLATIONS, tr


def test_v320_version_and_metadata():
    """Verify version 3.2.0 metadata across all exports."""
    assert __version__ == "3.2.0"
    assert APP_ID == "BinaryReceptor.3.2.0"
    assert "v3.2.0" in APP_DISPLAY_NAME


def test_auto_start_disabled_by_default(tmp_path):
    """Specification 1: Verify auto_start defaults to False in dataclass, INI template, and ConfigManager."""
    # 1. Default dataclass
    cfg = AppConfig()
    assert cfg.auto_start is False

    # 2. Default settings template
    assert "auto_start = false" in DEFAULT_SETTINGS_INI.lower()

    # 3. New ConfigManager generation
    test_ini = tmp_path / "settings.ini"
    mgr = ConfigManager(test_ini)
    try:
        assert mgr.current.auto_start is False
        content = test_ini.read_text(encoding="utf-8")
        assert "auto_start = false" in content.lower()
    finally:
        mgr.close()


def test_binaryeye_native_request_types():
    """Specification 3: Verify BinaryEye HTTP request modes."""
    # Mode 1: POST application/json (Recommended)
    json_bytes = json.dumps({
        "content": "TEST-JSON-BARCODE-99",
        "format": "QR_CODE",
        "raw": "dGVzdA==",
    }).encode("utf-8")
    payload1, is_health1 = parse_binaryeye_request(
        "POST", "/scan", {"content-type": "application/json"}, json_bytes
    )
    assert not is_health1
    assert payload1 is not None
    assert payload1.content == "TEST-JSON-BARCODE-99"
    assert payload1.format == "QR_CODE"

    # Mode 2: POST application/x-www-form-urlencoded
    form_bytes = b"content=TEST-FORM-BARCODE-88&format=CODE_128&raw=123"
    payload2, is_health2 = parse_binaryeye_request(
        "POST", "/scan", {"content-type": "application/x-www-form-urlencoded"}, form_bytes
    )
    assert not is_health2
    assert payload2 is not None
    assert payload2.content == "TEST-FORM-BARCODE-88"
    assert payload2.format == "CODE_128"

    # Mode 3: GET with full query string
    payload3, is_health3 = parse_binaryeye_request(
        "GET", "/?content=GET-QUERY-77&format=EAN_13&raw=456", {}, b""
    )
    assert not is_health3
    assert payload3 is not None
    assert payload3.content == "GET-QUERY-77"
    assert payload3.format == "EAN_13"

    # Mode 4: GET and simply add content (prefix query or direct path)
    payload4a, is_health4a = parse_binaryeye_request(
        "GET", "/?content=APPENDED-BARCODE-66", {}, b""
    )
    assert not is_health4a
    assert payload4a is not None
    assert payload4a.content == "APPENDED-BARCODE-66"

    payload4b, is_health4b = parse_binaryeye_request(
        "GET", "/DIRECT-RAW-VALUE-55", {}, b""
    )
    assert not is_health4b
    assert payload4b is not None
    assert payload4b.content == "DIRECT-RAW-VALUE-55"

    # Mode 5: GET with custom template {RESULT}, {FORMAT}, {RESULT_BYTES}
    payload5, is_health5 = parse_binaryeye_request(
        "GET", "/?content=TEMPLATE-RESULT-11&format=QR_CODE&raw=ABCD", {}, b""
    )
    assert not is_health5
    assert payload5 is not None
    assert payload5.content == "TEMPLATE-RESULT-11"
    assert payload5.format == "QR_CODE"
    assert payload5.raw == "ABCD"


def test_forwarding_url_builder_binaryeye_options():
    """Specification 3: Verify UI Forwarding URL Builder matches BinaryEye options."""
    # POST - JSON / Form (Recommended) -> http://<IP>:<PORT>/
    assert build_forwarding_url("192.168.1.50", 24234, "post_json") == "http://192.168.1.50:24234/"
    assert build_forwarding_url("192.168.1.50", 24234, "post_form") == "http://192.168.1.50:24234/"

    # GET - Full Query String -> http://<IP>:<PORT>/
    assert build_forwarding_url("192.168.1.50", 24234, "get_query") == "http://192.168.1.50:24234/"

    # GET - Simply Add Content (Prefix Query) -> http://<IP>:<PORT>/?content=
    assert build_forwarding_url("192.168.1.50", 24234, "get_append") == "http://192.168.1.50:24234/?content="

    # GET - Custom Template -> http://<IP>:<PORT>/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}
    expected_tpl = "http://192.168.1.50:24234/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}"
    assert build_forwarding_url("192.168.1.50", 24234, "get_template") == expected_tpl


def test_barcodes_containing_urls_are_never_dropped():
    """Specification 3 & 4: Ensure barcodes containing URLs, ports, or /scan are preserved verbatim."""
    url_barcodes = [
        "https://github.com/markusfisch/BinaryEye",
        "http://192.168.1.100:24234/scan",
        "http://myerp.local:8080/products/item?id=992",
        "binaryeye://encode?content=test",
    ]

    for raw_url in url_barcodes:
        # Test via JSON POST
        data = json.dumps({"content": raw_url}).encode("utf-8")
        payload, is_health = parse_binaryeye_request("POST", "/scan", {"content-type": "application/json"}, data)
        assert not is_health
        assert payload is not None
        assert payload.content == raw_url

        # Test via GET query
        encoded = urllib.parse.quote(raw_url)
        payload_get, is_health_get = parse_binaryeye_request("GET", f"/?content={encoded}", {}, b"")
        assert not is_health_get
        assert payload_get is not None
        assert payload_get.content == raw_url


def test_continuous_mode_fully_removed():
    """Specification 4: Verify continuous scan callback deep links and /start route are removed."""
    # Ensure build_continuous_scan_url does not exist
    import src.core.qr_helper as qr_mod
    assert not hasattr(qr_mod, "build_continuous_scan_url")

    # In http_server, /start is not a special HTML landing page
    # It parses normally as either raw path or health
    payload, is_health = parse_binaryeye_request("GET", "/start", {}, b"")
    # In v3.2.0, GET /start is treated as a raw path scan payload "start"
    assert payload is not None
    assert payload.content == "start"


def test_i18n_v320_keys_parity():
    """Specification 5: Verify 100% parity across all new v3.2.0 keys."""
    en = TRANSLATIONS["en"]
    fa = TRANSLATIONS["fa"]

    required_keys = [
        "lbl_binaryeye_req_type",
        "opt_req_post_json",
        "opt_req_post_form",
        "opt_req_get_query",
        "opt_req_get_append",
        "opt_req_get_template",
        "desc_req_post_json",
        "desc_req_post_form",
        "desc_req_get_query",
        "desc_req_get_append",
        "desc_req_get_template",
        "strip_server",
        "strip_mode",
        "strip_bt",
        "strip_http",
        "strip_stats",
        "strip_total",
        "strip_dedup",
    ]

    for key in required_keys:
        assert key in en, f"Missing key '{key}' in English dictionary"
        assert key in fa, f"Missing key '{key}' in Persian dictionary"
        assert en[key].strip() != "", f"Empty English value for '{key}'"
        assert fa[key].strip() != "", f"Empty Persian value for '{key}'"

    # Overall exact parity
    assert set(en.keys()) == set(fa.keys())


def test_pure_python_png_validity():
    """Specification 9: Test pure Python PNG generation produces a valid, readable PNG."""
    matrix = [
        [True, False, True, False],
        [False, True, False, True],
        [True, True, False, False],
        [False, False, True, True],
    ]
    png_bytes = matrix_to_png_bytes(matrix, box_size=6, border=2)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # Verify PNG structure: IHDR, IDAT, IEND chunks present
    assert b"IHDR" in png_bytes
    assert b"IDAT" in png_bytes
    assert b"IEND" in png_bytes

    # Verify Pillow can open and verify dimensions
    img = Image.open(io.BytesIO(png_bytes))
    dim = (4 + 2 * 2) * 6  # 8 * 6 = 48
    assert img.size == (dim, dim)
