"""Exits 1 unless two PNG files hold the same image: same header and the same decompressed image data.
CI uses it to check that scripts/example.py reproduces the committed PNG, whose compressed bytes depend on zlib's version."""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


def image(path: str) -> tuple[bytes, bytes]:
    data = Path(path).read_bytes()
    pos, header, idat = 8, b"", b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            header = body
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    return header, zlib.decompress(idat)


if __name__ == "__main__":
    a, b = sys.argv[1:3]
    if image(a) != image(b):
        sys.exit(f"{b} differs from {a}")
