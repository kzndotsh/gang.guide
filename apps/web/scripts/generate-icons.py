#!/usr/bin/env python3
"""Generate favicon.png and apple-touch-icon.png from the brand palette."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "static"
BG = (0x0D, 0x11, 0x17)
CENTER = (0xC9, 0xD1, 0xD9)
NODE = (0x6E, 0x76, 0x81)


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def write_png(path: Path, size: int) -> None:
    pixels = bytearray()
    cx = cy = size // 2
    radius = max(2, size // 16)
    node_r = max(1, size // 32)
    nodes = [
        (size // 4, size // 3),
        (3 * size // 4, size // 3),
        (size // 3, 3 * size // 4),
        (2 * size // 3, 2 * size // 3),
    ]

    for y in range(size):
        row = bytearray([0])  # filter byte
        for x in range(size):
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy <= radius * radius:
                row.extend(CENTER)
            elif any((x - nx) ** 2 + (y - ny) ** 2 <= node_r * node_r for nx, ny in nodes):
                row.extend(NODE)
            else:
                row.extend(BG)
        pixels.extend(row)

    compressed = zlib.compress(bytes(pixels), 9)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    write_png(ROOT / "favicon.png", 32)
    write_png(ROOT / "apple-touch-icon.png", 180)
    print(f"Wrote icons to {ROOT}")


if __name__ == "__main__":
    main()
