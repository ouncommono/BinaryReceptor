"""Dynamic QR Code generator and BinaryEye connection assistant for BinaryReceptor v3.2.0.

Provides:
  - Local LAN IP address auto-detection prioritizing active Wi-Fi and Ethernet interfaces.
  - Forwarding URL generator for all 4 BinaryEye HTTP Request Types:
      1. POST - JSON / Form (Recommended) -> http://<IP>:<PORT>/
      2. GET - Full Query String -> http://<IP>:<PORT>/
      3. GET - Simply Add Content (Prefix Query) -> http://<IP>:<PORT>/?content=
      4. GET - Custom Template -> http://<IP>:<PORT>/?content={RESULT}&format={FORMAT}&raw={RESULT_BYTES}
  - Pure-Python zero-dependency PNG synthesis directly from boolean matrices using built-in zlib.
  - Barcode generator for 11 symbologies.
"""
from __future__ import annotations

import io
import socket
import struct
import urllib.parse
import zlib
from typing import Any

import qrcode

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import psutil
except ImportError:
    psutil = None

BINARYEYE_FORMATS = [
    "QR_CODE",
    "DATA_MATRIX",
    "AZTEC",
    "PDF_417",
    "CODE_128",
    "CODE_39",
    "EAN_13",
    "EAN_8",
    "UPC_A",
    "ITF",
    "CODABAR",
]


def get_active_lan_ips() -> list[dict[str, Any]]:
    """Detect and rank all active local IPv4 addresses.

    Prioritizes active Wi-Fi and Ethernet adapters with private LAN ranges
    (192.168.x.x, 10.x.x.x, 172.16-31.x.x) over APIPA (169.254.x.x) or virtual NICs.
    """
    results: list[dict[str, Any]] = []

    if psutil:
        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()

            for iface_name, addr_list in addrs.items():
                is_up = stats.get(iface_name).isup if iface_name in stats else True
                for a in addr_list:
                    if a.family == socket.AF_INET:
                        ip = a.address
                        if ip.startswith("127."):
                            continue

                        # Score interfaces
                        score = 0
                        lower_name = iface_name.lower()
                        if "wi-fi" in lower_name or "wlan" in lower_name or "wireless" in lower_name:
                            score += 50
                        elif "ethernet" in lower_name or "eth" in lower_name or "lan" in lower_name:
                            score += 40

                        if ip.startswith(("192.168.", "10.")):
                            score += 30
                        elif ip.startswith("172."):
                            score += 20
                        elif ip.startswith("169.254."):
                            score -= 50  # APIPA fallback

                        if is_up:
                            score += 10

                        results.append({
                            "interface": iface_name,
                            "ip": ip,
                            "score": score,
                            "is_primary": False,
                        })
        except Exception:
            pass

    # Fallback to standard socket resolution if psutil returned nothing
    if not results:
        try:
            host_name = socket.gethostname()
            _, _, ip_list = socket.gethostbyname_ex(host_name)
            for ip in ip_list:
                if not ip.startswith("127."):
                    score = 20 if not ip.startswith("169.254.") else 0
                    results.append({
                        "interface": "Local Network",
                        "ip": ip,
                        "score": score,
                        "is_primary": False,
                    })
        except Exception:
            pass

    if not results:
        results.append({
            "interface": "Loopback",
            "ip": "127.0.0.1",
            "score": 0,
            "is_primary": True,
        })
    else:
        results.sort(key=lambda x: x["score"], reverse=True)
        results[0]["is_primary"] = True

    return results


def get_primary_lan_ip() -> str:
    """Return the single best LAN IPv4 address for QR encoding."""
    ips = get_active_lan_ips()
    return ips[0]["ip"] if ips else "127.0.0.1"


def build_forwarding_url(ip: str, port: int, request_type: str = "post_json") -> str:
    """Build BinaryEye HTTP Forwarding URL matching one of the 4 BinaryEye request modes."""
    clean_ip = ip.strip() or "127.0.0.1"
    req_type = request_type.lower().strip()
    if req_type in ("get_template", "template"):
        return f"http://{clean_ip}:{port}/?content={{RESULT}}&format={{FORMAT}}&raw={{RESULT_BYTES}}"
    elif req_type in ("get_append", "get_add", "append", "prefix"):
        return f"http://{clean_ip}:{port}/?content="
    elif req_type in ("scan", "post_scan"):
        return f"http://{clean_ip}:{port}/scan"
    else:
        # Default for post_json, post_form, post, get_query, root:
        return f"http://{clean_ip}:{port}/"


def build_encode_url(content: str, format_name: str = "QR_CODE") -> str:
    """Build BinaryEye barcode generation deep link.

    Format:
      binaryeye://encode?content=...&format=...&execute=true
    """
    clean_format = format_name.upper() if format_name.upper() in BINARYEYE_FORMATS else "QR_CODE"
    encoded_content = urllib.parse.quote(content, safe="")
    return f"binaryeye://encode?content={encoded_content}&format={clean_format}&execute=true"


def matrix_to_png_bytes(matrix: list[list[bool]], box_size: int = 8, border: int = 2) -> bytes:
    """Pure-Python pixel-perfect PNG synthesis directly from boolean matrix using built-in zlib."""
    dim = len(matrix)
    width = (dim + 2 * border) * box_size
    height = width

    raw_scanlines = bytearray()
    for y in range(height):
        raw_scanlines.append(0)  # Filter byte 0 (None)
        module_y = (y // box_size) - border
        for x in range(width):
            module_x = (x // box_size) - border
            if 0 <= module_y < dim and 0 <= module_x < dim and matrix[module_y][module_x]:
                raw_scanlines.append(0)  # Black pixel
            else:
                raw_scanlines.append(255)  # White pixel

    compressed_idat = zlib.compress(bytes(raw_scanlines), level=9)

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    out = bytearray(b"\x89PNG\r\n\x1a\n")
    # IHDR: width, height, bit_depth=8, color_type=0 (grayscale), compression=0, filter=0, interlace=0
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    out.extend(_chunk(b"IHDR", ihdr_data))
    out.extend(_chunk(b"IDAT", compressed_idat))
    out.extend(_chunk(b"IEND", b""))
    return bytes(out)


def generate_qr_png_bytes(data: str, box_size: int = 8, border: int = 2) -> bytes:
    """Generate raw PNG bytes for a QR code in pure Python without heavy Pillow dependencies."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    return matrix_to_png_bytes(matrix, box_size=box_size, border=border)


def generate_qr_image(
    data: str,
    box_size: int = 8,
    border: int = 2,
    fill_color: str = "black",
    back_color: str = "white",
) -> Any:
    """Generate PIL Image containing QR Code if PIL is available, or return synthesized PNG bytes."""
    png_bytes = generate_qr_png_bytes(data, box_size=box_size, border=border)
    if Image is not None:
        return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    return png_bytes
