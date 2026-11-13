"""Raster figures: a PNG's size, its stated resolution and its main colours (decoded with zlib and the PNG filters), a
JPEG's size and stated resolution (read from its headers, not decoded)."""

from __future__ import annotations

import contextlib
import struct
import zlib
from collections import Counter
from dataclasses import dataclass, field

from .color import RGB, lab

MAX_PIXELS = 100_000_000
SAMPLE = 400_000  # pixels looked at for the colours, evenly spread


class RasterError(Exception):
    pass


@dataclass
class Raster:
    pixels: tuple[int, int]
    dpi: tuple[float, float] | None  # stated in the file, if it says
    colours: list[RGB] = field(default_factory=list)  # main colours, the most used first (PNG only)
    kind: str = "png"


def read_png(data: bytes, colours: bool = True) -> Raster:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RasterError("not a PNG")
    pos = 8
    ihdr = None
    dpi = None
    idat = bytearray()
    palette = b""
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR" and len(body) >= 13:
            ihdr = struct.unpack(">IIBBBBB", body[:13])
        elif kind == b"pHYs" and len(body) >= 9:
            px, py, unit = struct.unpack(">IIB", body[:9])
            if unit == 1 and px and py:  # pixels per metre
                dpi = (px * 0.0254, py * 0.0254)
        elif kind == b"PLTE":
            palette = body
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
    if ihdr is None:
        raise RasterError("a PNG without its header")
    w, h, depth, ctype, _, _, interlace = ihdr
    if w * h > MAX_PIXELS:
        raise RasterError(f"{w}×{h}: more pixels than the cap")
    r = Raster((w, h), dpi)
    if colours and not interlace and depth == 8 and ctype in (0, 2, 3, 4, 6):
        with contextlib.suppress(zlib.error, ValueError, IndexError):  # a damaged image: its size still counts
            r.colours = _main_colours(_unfilter(zlib.decompress(bytes(idat)), w, h, {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]), w, h, ctype, palette)
    return r


def _unfilter(raw: bytes, w: int, h: int, bpp: int) -> list[bytearray]:
    stride = w * bpp
    rows: list[bytearray] = []
    prev = bytearray(stride)
    i = 0
    for _ in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1 : i + 1 + stride])
        i += 1 + stride
        if len(line) < stride:
            raise ValueError("short PNG data")
        if f == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 0xFF
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif f == 3:
            for x in range(stride):
                left = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 0xFF
        elif f == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
        rows.append(line)
        prev = line
    return rows


def _main_colours(rows: list[bytearray], w: int, h: int, ctype: int, palette: bytes) -> list[RGB]:
    """The saturated colours that cover a visible share of the image (greys, near-white and anti-aliasing left out)."""
    step = max(1, int(((w * h) / SAMPLE) ** 0.5))
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    counts: Counter[tuple[int, int, int]] = Counter()
    for y in range(0, h, step):
        row = rows[y]
        for x in range(0, w, step):
            p = row[x * bpp : x * bpp + bpp]
            rgb: tuple[int, ...]
            if ctype == 0 or ctype == 4:
                rgb = (p[0], p[0], p[0])
            elif ctype == 3:
                k = p[0] * 3
                rgb = tuple(palette[k : k + 3]) if k + 3 <= len(palette) else (0, 0, 0)
            else:
                rgb = (p[0], p[1], p[2])
            if (ctype in (4, 6)) and p[-1] < 128:
                continue  # transparent
            counts[(rgb[0] >> 3 << 3, rgb[1] >> 3 << 3, rgb[2] >> 3 << 3)] += 1  # 32 levels a channel
    total = sum(counts.values()) or 1
    out = []
    for (r, g, b), n in counts.most_common(64):
        if n / total < 0.002:
            break
        c = (r / 255 + 4 / 255, g / 255 + 4 / 255, b / 255 + 4 / 255)
        L, a, bb = lab(c)
        if (a * a + bb * bb) ** 0.5 >= 15 and L < 97:
            out.append(c)
    return out[:12]


def read_jpeg(data: bytes) -> Raster:
    if not data.startswith(b"\xff\xd8"):
        raise RasterError("not a JPEG")
    pos = 2
    dpi = None
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        (length,) = struct.unpack(">H", data[pos + 2 : pos + 4])
        seg = data[pos + 4 : pos + 2 + length]
        if marker == 0xE0 and seg.startswith(b"JFIF\x00") and len(seg) >= 12:
            unit, xd, yd = seg[7], *struct.unpack(">HH", seg[8:12])
            if unit == 1 and xd and yd:
                dpi = (float(xd), float(yd))
            elif unit == 2 and xd and yd:
                dpi = (xd * 2.54, yd * 2.54)
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF) and len(seg) >= 5:
            h, w = struct.unpack(">HH", seg[1:5])
            return Raster((w, h), dpi, kind="jpeg")
        pos += 2 + length
    raise RasterError("a JPEG without its size")
