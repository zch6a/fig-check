"""Made-up figures for the tests: small, valid PDFs (plain or compressed, with object streams, Type 3 fonts, forms and
images), PNGs and LaTeX projects, written here."""

from __future__ import annotations

import struct
import zlib


def pdf(content: bytes, width: float = 200, height: float = 100, objects: dict[int, bytes] | None = None, resources: bytes = b"",
        compress: bool = False, objstm: bool = False) -> bytes:  # fmt: skip
    """A one-page PDF drawing `content`; `objects` adds numbered objects (from 10 up) the resources can refer to."""
    stream = zlib.compress(content) if compress else content
    filt = b"/Filter /FlateDecode " if compress else b""
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %g %g] /Contents 4 0 R /Resources << %s >> >>" % (width, height, resources),
        4: b"<< /Length %d %s>>\nstream\n" % (len(stream), filt) + stream + b"\nendstream",
        **(objects or {}),
    }
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    if objstm:
        # objects 1-3 inside an object stream (as pdfLaTeX writes them), the rest outside
        inner = b""
        header = b""
        for n in (1, 2, 3):
            header += b"%d %d " % (n, len(inner))
            inner += objs.pop(n) + b"\n"
        body = header + inner
        objs[9] = b"<< /Type /ObjStm /N 3 /First %d /Length %d >>\nstream\n" % (len(header), len(body)) + body + b"\nendstream"
    for n in sorted(objs):
        offsets[n] = len(out)
        out += b"%d 0 obj\n" % n + objs[n] + b"\nendobj\n"
    out += b"trailer\n<< /Root 1 0 R /Size %d >>\n%%%%EOF\n" % (max(objs) + 1)
    return bytes(out)


def png(width: int, height: int, colour: tuple[int, int, int] | list[tuple[int, int, int]] = (255, 255, 255), dpi: float | None = None) -> bytes:
    """An RGB PNG: one colour, or vertical stripes of several."""
    colours = colour if isinstance(colour, list) else [colour]
    rows = b""
    for _ in range(height):
        rows += b"\x00" + b"".join(bytes(colours[(x * len(colours)) // width]) for x in range(width))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    phys = chunk(b"pHYs", struct.pack(">IIB", round(dpi / 0.0254), round(dpi / 0.0254), 1)) if dpi else b""
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + phys
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def jpeg_header(width: int, height: int, dpi: int | None = None) -> bytes:
    """The start of a JPEG: its JFIF segment and frame header (enough for its size)."""
    jfif = b"JFIF\x00\x01\x02" + (bytes([1]) + struct.pack(">HH", dpi, dpi) if dpi else bytes([0]) + struct.pack(">HH", 1, 1)) + b"\x00\x00"
    app0 = b"\xff\xe0" + struct.pack(">H", len(jfif) + 2) + jfif
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"
