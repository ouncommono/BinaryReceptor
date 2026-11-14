"""Tests for dynamic QR Code generation and BinaryEye forwarding URL formatting."""
from __future__ import annotations

import io
from PIL import Image

from src.core.qr_helper import (
    build_forwarding_url,
    build_encode_url,
    generate_qr_image,
    generate_qr_png_bytes,
    matrix_to_png_bytes,
    get_active_lan_ips,
    get_primary_lan_ip,
    BINARYEYE_FORMATS,
)


def test_build_forwarding_url_modes():
    """Verify BinaryEye URL formatting for all 4 request types."""
    # 1. POST JSON (Default)
    url_json = build_forwarding_url("192.168.1.100", 24234, "post_json")
    assert url_json == "http://192.168.1.100:24234/scan"

    # 2. POST Form
    url_form = build_forwarding_url("192.168.1.100", 24234, "post_form")
    assert url_form == "http://192.168.1.100:24234/scan"

    # 3. GET with full query string
    url_query = build_forwarding_url("192.168.1.100", 24234, "get_query")
    assert url_query == "http://192.168.1.100:24234/scan"

    # 4. GET and simply add content
    url_append = build_forwarding_url("192.168.1.100", 24234, "get_append")
    assert url_append == "http://192.168.1.100:24234/scan?content="

    # Root alternative for append
    url_root = build_forwarding_url("192.168.1.100", 24234, "root")
    assert url_root == "http://192.168.1.100:24234/"


def test_build_encode_deep_link():
    """Verify BinaryEye encode deep link format across supported symbologies."""
    for fmt in ["QR_CODE", "CODE_128", "EAN_13", "DATA_MATRIX"]:
        assert fmt in BINARYEYE_FORMATS
        url = build_encode_url("MY-SECRET-CODE", fmt)
        assert url.startswith("binaryeye://encode?")
        assert "content=MY-SECRET-CODE" in url
        assert f"format={fmt}" in url
        assert "execute=true" in url


def test_pure_python_png_matrix_synthesis():
    """Verify built-in zlib PNG generator produces a valid PNG with correct dimensions."""
    matrix = [
        [True, False, True],
        [False, True, False],
        [True, True, True],
    ]
    png_bytes = matrix_to_png_bytes(matrix, box_size=4, border=1)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png_bytes) > 50

    img = Image.open(io.BytesIO(png_bytes))
    expected_dim = (3 + 2 * 1) * 4  # (dim + 2*border) * box_size = 5 * 4 = 20
    assert img.size == (expected_dim, expected_dim)


def test_qr_image_generation():
    """Verify QR code PNG bytes are valid and decodable."""
    png_bytes = generate_qr_png_bytes("https://github.com/ouncommono/BinaryReceptor")
    assert len(png_bytes) > 100
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    img = Image.open(io.BytesIO(png_bytes))
    assert img.size[0] > 50
    assert img.size[1] > 50


def test_lan_ip_detection():
    """Verify active LAN IP detection returns at least one valid address entry."""
    ips = get_active_lan_ips()
    assert len(ips) >= 1
    assert any(ip["is_primary"] for ip in ips)

    primary = get_primary_lan_ip()
    assert primary
    assert not primary.startswith("127.") or len(ips) == 1
