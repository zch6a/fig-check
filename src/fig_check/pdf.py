"""A figure's PDF, read as far as checking it needs, with the standard library only: its size, every piece of text at
the size it is drawn (the text and transformation matrices applied, Type 3 font matrices too), the colours of the
paths it fills and strokes and of its text, and every image with its pixel size and its size on the page.

The page's content stream is interpreted (q/Q, cm, the text operators, colour operators, path painting, form XObjects
with their matrices, images and inline images). Streams compressed with Flate, ASCIIHex or ASCII85 are read; object
streams too. Encrypted files are refused. Limits keep a hostile file from running long: a size cap, an operator cap,
a depth cap and cycle detection for nested forms."""

from __future__ import annotations

import base64
import math
import re
import zlib
from dataclasses import dataclass, field
from typing import Any

MAX_BYTES = 200 * 1024 * 1024
MAX_OPS = 3_000_000
MAX_DEPTH = 24
Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


class PDFError(Exception):
    pass


@dataclass(frozen=True)
class Ref:
    num: int
    gen: int


@dataclass
class Text:
    size: float  # points, in the figure's own space
    font: str


@dataclass
class Image:
    pixels: tuple[int, int]
    size: tuple[float, float]  # points on the figure


@dataclass
class Figure:
    width: float  # points
    height: float
    texts: list[Text] = field(default_factory=list)
    fills: list[tuple[float, float, float]] = field(default_factory=list)  # colours of filled paths, in order of use
    strokes: list[tuple[float, float, float]] = field(default_factory=list)
    text_colours: list[tuple[float, float, float]] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # what could not be read


def _mul(m: Matrix, n: Matrix) -> Matrix:
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (a * a2 + b * c2, a * b2 + b * d2, c * a2 + d * c2, c * b2 + d * d2, e * a2 + f * c2 + e2, e * b2 + f * d2 + f2)


# --- the lexer and parser (objects and content streams) ---

DELIMS = b"()<>[]{}/%"
WHITESPACE = b" \t\r\n\f\x00"
NUMBER = re.compile(rb"[+-]?(?:\d+\.?\d*|\.\d+)")


class Lexer:
    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    def skip(self) -> None:
        d = self.data
        while self.pos < len(d):
            c = d[self.pos]
            if c in WHITESPACE:
                self.pos += 1
            elif c == 0x25:  # % comment
                end = d.find(b"\n", self.pos)
                self.pos = len(d) if end < 0 else end + 1
            else:
                return

    def token(self) -> Any:
        """The next object or keyword (keywords as bytes), or None at the end."""
        self.skip()
        d = self.data
        if self.pos >= len(d):
            return None
        c = d[self.pos : self.pos + 1]
        if c == b"/":
            m = re.compile(rb"/[^\s()<>\[\]{}/%]*").match(d, self.pos)
            self.pos = m.end() if m else self.pos + 1
            raw = m.group(0)[1:] if m else b""
            return Name(re.sub(rb"#([0-9A-Fa-f]{2})", lambda x: bytes([int(x.group(1), 16)]), raw).decode("latin-1"))
        if c == b"(":
            return self._string()
        if d.startswith(b"<<", self.pos):
            self.pos += 2
            return _DICT_START
        if d.startswith(b">>", self.pos):
            self.pos += 2
            return _DICT_END
        if c == b"<":
            end = d.find(b">", self.pos)
            hexd = re.sub(rb"\s", b"", d[self.pos + 1 : end if end >= 0 else len(d)])
            self.pos = len(d) if end < 0 else end + 1
            if len(hexd) % 2:
                hexd += b"0"
            try:
                return bytes.fromhex(hexd.decode("latin-1"))
            except ValueError:
                return b""
        if c == b"[":
            self.pos += 1
            return _ARRAY_START
        if c == b"]":
            self.pos += 1
            return _ARRAY_END
        if c in (b"{", b"}"):
            self.pos += 1
            return self.token()
        m = NUMBER.match(d, self.pos)
        if m and (m.end() >= len(d) or d[m.end()] in WHITESPACE + DELIMS):
            self.pos = m.end()
            text = m.group(0)
            return float(text) if b"." in text else int(text)
        m = re.compile(rb"[^\s()<>\[\]{}/%]+").match(d, self.pos)
        if not m:
            self.pos += 1
            return self.token()
        self.pos = m.end()
        word = m.group(0)
        return {b"true": True, b"false": False, b"null": None}.get(word, Keyword(word))

    def _string(self) -> bytes:
        d = self.data
        i = self.pos + 1
        depth = 1
        out = bytearray()
        escapes = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
        while i < len(d) and depth:
            c = d[i]
            if c == 0x5C and i + 1 < len(d):  # backslash
                n = d[i + 1]
                if n in escapes:
                    out.append(escapes[n])
                    i += 2
                elif 0x30 <= n <= 0x37:
                    m = re.compile(rb"[0-7]{1,3}").match(d, i + 1)
                    out.append(int(m.group(0), 8) & 0xFF if m else 0)
                    i = m.end() if m else i + 2
                elif n in (0x0D, 0x0A):
                    i += 3 if d[i + 1 : i + 3] == b"\r\n" else 2
                else:
                    out.append(n)
                    i += 2
                continue
            if c == 0x28:
                depth += 1
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            out.append(c)
            i += 1
        self.pos = i
        return bytes(out)

    def object(self, tok: Any = None) -> Any:
        """A whole object: dictionaries and arrays assembled, `n g R` references resolved to Ref."""
        tok = self.token() if tok is None else tok
        if tok is _DICT_START:
            out: dict[str, Any] = {}
            while True:
                k = self.token()
                if k is _DICT_END or k is None:
                    return out
                if isinstance(k, Name):
                    out[k] = self.object()
        if tok is _ARRAY_START:
            items: list[Any] = []
            while True:
                t = self.token()
                if t is _ARRAY_END or t is None:
                    return items
                items.append(self.object(t))
                if len(items) >= 3 and items[-1] == Keyword(b"R") and isinstance(items[-2], int) and isinstance(items[-3], int):
                    items[-3:] = [Ref(items[-3], items[-2])]
        if isinstance(tok, int):
            save = self.pos
            t2 = self.token()
            if isinstance(t2, int):
                t3 = self.token()
                if t3 == Keyword(b"R"):
                    return Ref(tok, t2)
            self.pos = save
        return tok


class Name(str):
    pass


class Keyword(bytes):
    pass


_DICT_START = Keyword(b"<<")
_DICT_END = Keyword(b">>")
_ARRAY_START = Keyword(b"[")
_ARRAY_END = Keyword(b"]")


# --- the file ---


class PDF:
    def __init__(self, data: bytes) -> None:
        if len(data) > MAX_BYTES:
            raise PDFError(f"larger than {MAX_BYTES // 2**20} MB")
        if not data.startswith(b"%PDF"):
            raise PDFError("not a PDF")
        self.data = data
        self.offsets: dict[int, int] = {}  # object number -> where `n g obj` starts (the last definition wins)
        for m in re.finditer(rb"(?<![\d])(\d+)\s+(\d+)\s+obj\b", data):
            self.offsets[int(m.group(1))] = m.end()
        self.cache: dict[int, Any] = {}
        self.in_streams: dict[int, tuple[int, int]] = {}  # object number -> (object stream, index)
        self.trailer: dict[str, Any] = {}
        for m in re.finditer(rb"trailer\s*<<", data):
            t = Lexer(data, m.end() - 2).object()
            if isinstance(t, dict):
                self.trailer.update(t)
        for num in list(self.offsets):
            obj = self.get(Ref(num, 0))
            if isinstance(obj, Stream) and obj.dict.get("Type") == "XRef":
                self.trailer.update({k: v for k, v in obj.dict.items() if k in ("Root", "Encrypt", "Info")})
            if isinstance(obj, Stream) and obj.dict.get("Type") == "ObjStm":
                self._index_objstm(num, obj)
        if "Encrypt" in self.trailer:
            raise PDFError("encrypted: save it without a password first")

    def get(self, ref: Any, depth: int = 0) -> Any:
        if not isinstance(ref, Ref):
            return ref
        if depth > 32:
            return None
        if ref.num in self.cache:
            return self.cache[ref.num]
        self.cache[ref.num] = None  # a cycle reads as null
        obj: Any = None
        if ref.num in self.offsets:
            lex = Lexer(self.data, self.offsets[ref.num])
            obj = lex.object()
            lex.skip()
            if isinstance(obj, dict) and self.data.startswith(b"stream", lex.pos):
                obj = self._stream(obj, lex.pos + 6, depth)
        elif ref.num in self.in_streams:
            obj = self._from_objstm(*self.in_streams[ref.num])
        self.cache[ref.num] = obj
        return obj

    def _stream(self, d: dict[str, Any], start: int, depth: int) -> Stream:
        data = self.data
        if data[start : start + 2] == b"\r\n":
            start += 2
        elif data[start : start + 1] in (b"\n", b"\r"):
            start += 1
        length = self.get(d.get("Length"), depth + 1)
        if isinstance(length, int) and length >= 0 and data[start + length : start + length + 20].lstrip().startswith(b"endstream"):
            raw = data[start : start + length]
        else:
            end = data.find(b"endstream", start)
            raw = data[start : end if end >= 0 else len(data)].rstrip(b"\r\n")
        return Stream(d, raw, self)

    def _index_objstm(self, num: int, s: Stream) -> None:
        body = s.decoded()
        if body is None:
            return
        n = s.dict.get("N")
        if not isinstance(n, int):
            return
        lex = Lexer(body)
        for i in range(n):
            onum = lex.token()
            lex.token()
            if isinstance(onum, int) and onum not in self.offsets:
                self.in_streams[onum] = (num, i)

    def _from_objstm(self, num: int, index: int) -> Any:
        s = self.get(Ref(num, 0))
        if not isinstance(s, Stream):
            return None
        body = s.decoded()
        first = s.dict.get("First")
        if body is None or not isinstance(first, int):
            return None
        lex = Lexer(body)
        pairs = [(lex.token(), lex.token()) for _ in range(int(s.dict.get("N") or 0))]
        if index >= len(pairs) or not isinstance(pairs[index][1], int):
            return None
        return Lexer(body, first + pairs[index][1]).object()

    def first_page(self) -> dict[str, Any]:
        """The first page (by the page tree), with the attributes it inherits."""
        root = self.get(self.trailer.get("Root"))
        if not isinstance(root, dict):  # no trailer found: any catalog
            root = next((o for n in self.offsets if isinstance(o := self.get(Ref(n, 0)), dict) and o.get("Type") == "Catalog"), None)
        node = self.get(root.get("Pages")) if isinstance(root, dict) else None
        inherited: dict[str, Any] = {}
        for _ in range(64):
            if not isinstance(node, dict):
                break
            for k in ("Resources", "MediaBox", "CropBox", "Rotate"):
                if k in node:
                    inherited[k] = node[k]
            if node.get("Type") == "Page" or "Kids" not in node:
                return {**node, **inherited}
            kids = self.get(node.get("Kids"))
            node = self.get(kids[0]) if isinstance(kids, list) and kids else None
        raise PDFError("no page found")


class Stream:
    def __init__(self, d: dict[str, Any], raw: bytes, pdf: PDF) -> None:
        self.dict = d
        self.raw = raw
        self.pdf = pdf

    def decoded(self) -> bytes | None:
        """The stream's bytes with its filters undone, or None when a filter is not one this reads (DCT, JPX...)."""
        filters = self.pdf.get(self.dict.get("Filter"))
        if filters is None:
            return self.raw
        if not isinstance(filters, list):
            filters = [filters]
        data = self.raw
        for f in filters:
            f = self.pdf.get(f)
            try:
                if f in ("FlateDecode", "Fl"):
                    data = _inflate(data)
                elif f in ("ASCIIHexDecode", "AHx"):
                    hexd = re.sub(rb"\s", b"", data.split(b">")[0])
                    data = bytes.fromhex((hexd + (b"0" if len(hexd) % 2 else b"")).decode("latin-1"))
                elif f in ("ASCII85Decode", "A85"):
                    data = base64.a85decode(data.strip().removeprefix(b"<~").split(b"~>")[0], adobe=False)
                else:
                    return None
            except (ValueError, zlib.error):
                return None
        return data


def _inflate(data: bytes) -> bytes:
    d = zlib.decompressobj()
    out = d.decompress(data, MAX_BYTES)
    if d.unconsumed_tail:
        raise ValueError("a stream larger than the cap")
    return out


# --- the interpreter ---


def read_figure(data: bytes) -> Figure:
    """The figure on a PDF's first page."""
    pdf = PDF(data)
    page = pdf.first_page()
    box = pdf.get(page.get("CropBox")) or pdf.get(page.get("MediaBox"))
    if not (isinstance(box, list) and len(box) == 4 and all(isinstance(pdf.get(x), (int, float)) for x in box)):
        raise PDFError("the page has no size (MediaBox)")
    x0, y0, x1, y1 = (float(pdf.get(x)) for x in box)
    fig = Figure(abs(x1 - x0), abs(y1 - y0))
    rotate = pdf.get(page.get("Rotate"))
    if isinstance(rotate, int) and rotate % 180 == 90:
        fig.width, fig.height = fig.height, fig.width
    contents = pdf.get(page.get("Contents"))
    parts = contents if isinstance(contents, list) else [contents]
    body = b""
    for part in parts:
        s = pdf.get(part)
        if isinstance(s, Stream):
            dec = s.decoded()
            if dec is None:
                fig.notes.append("a content stream in a filter this does not read")
            else:
                body += dec + b"\n"
    Interpreter(pdf, fig).run(body, pdf.get(page.get("Resources")) or {}, IDENTITY, 0, set())
    return fig


class Interpreter:
    def __init__(self, pdf: PDF, fig: Figure) -> None:
        self.pdf = pdf
        self.fig = fig
        self.ops = 0

    def run(self, body: bytes, resources: dict[str, Any], ctm: Matrix, depth: int, seen: set[int]) -> None:
        pdf = self.pdf
        res = pdf.get(resources) if isinstance(pdf.get(resources), dict) else {}
        fonts = pdf.get(res.get("Font")) or {}
        xobjects = pdf.get(res.get("XObject")) or {}
        colorspaces = pdf.get(res.get("ColorSpace")) or {}
        state: dict[str, Any] = {
            "ctm": ctm,
            "fill": (0.0, 0.0, 0.0),
            "stroke": (0.0, 0.0, 0.0),
            "fcs": 1,
            "scs": 1,
            "size": 0.0,
            "font": "",
            "scale": 1.0,
            "tl": 0.0,
        }
        stack: list[dict[str, Any]] = []
        tm: Matrix = IDENTITY
        tlm: Matrix = IDENTITY
        lex = Lexer(body)
        operands: list[Any] = []
        while True:
            if self.ops > MAX_OPS:
                self.fig.notes.append("stopped early: more drawing operators than the cap")
                return
            tok = lex.token()
            if tok is None:
                return
            if not isinstance(tok, Keyword) or tok in (_DICT_START, _ARRAY_START):
                operands.append(lex.object(tok))
                continue
            self.ops += 1
            op = bytes(tok)
            nums = [float(x) for x in operands if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if op == b"q":
                stack.append(dict(state))
            elif op == b"Q":
                if stack:
                    state = stack.pop()
            elif op == b"cm" and len(nums) >= 6:
                state["ctm"] = _mul(tuple(nums[-6:]), state["ctm"])  # type: ignore[arg-type]
            elif op == b"BT":
                tm = tlm = IDENTITY
            elif op == b"Tf" and operands:
                name = operands[0] if isinstance(operands[0], Name) else ""
                state["font"] = name
                state["size"] = nums[-1] if nums else 0.0
                state["scale"] = self._font_scale(pdf.get(fonts.get(name)) if isinstance(fonts, dict) else None)
            elif op == b"TL" and nums:
                state["tl"] = nums[-1]
            elif op == b"Tm" and len(nums) >= 6:
                tm = tlm = tuple(nums[-6:])  # type: ignore[assignment]
            elif op in (b"Td", b"TD") and len(nums) >= 2:
                if op == b"TD":
                    state["tl"] = -nums[-1]
                tlm = _mul((1.0, 0.0, 0.0, 1.0, nums[-2], nums[-1]), tlm)
                tm = tlm
            elif op == b"T*":
                tlm = _mul((1.0, 0.0, 0.0, 1.0, 0.0, -state["tl"]), tlm)
                tm = tlm
            elif op in (b"Tj", b"TJ", b"'", b'"'):
                if op in (b"'", b'"'):
                    tlm = _mul((1.0, 0.0, 0.0, 1.0, 0.0, -state["tl"]), tlm)
                    tm = tlm
                m = _mul(tm, state["ctm"])
                size = abs(state["size"]) * state["scale"] * math.hypot(m[2], m[3])
                if size > 0 and self._shows_glyphs(operands):
                    self.fig.texts.append(Text(size, state["font"]))
                    self.fig.text_colours.append(state["fill"])
            elif op in (b"g", b"G", b"rg", b"RG", b"k", b"K"):
                n = {b"g": 1, b"G": 1, b"rg": 3, b"RG": 3, b"k": 4, b"K": 4}[op]
                colour = _colour(nums, n)
                if colour is not None:
                    state["fill" if op.islower() else "stroke"] = colour
                    state["fcs" if op.islower() else "scs"] = n  # these operators also set the colour space
            elif op in (b"cs", b"CS") and operands:
                n = self._components(operands[0], colorspaces)
                state["fcs" if op == b"cs" else "scs"] = n
                state["fill" if op == b"cs" else "stroke"] = (0.0, 0.0, 0.0)
            elif op in (b"sc", b"scn", b"SC", b"SCN"):
                fill = op in (b"sc", b"scn")
                n = state["fcs" if fill else "scs"]
                colour = _colour(nums, n) if n in (1, 3, 4) and len(nums) >= n else None
                if colour is not None:
                    state["fill" if fill else "stroke"] = colour
            elif op in (b"f", b"F", b"f*"):
                self.fig.fills.append(state["fill"])
            elif op in (b"S", b"s"):
                self.fig.strokes.append(state["stroke"])
            elif op in (b"B", b"B*", b"b", b"b*"):
                self.fig.fills.append(state["fill"])
                self.fig.strokes.append(state["stroke"])
            elif op == b"Do" and operands and isinstance(operands[-1], Name) and isinstance(xobjects, dict):
                self._do(operands[-1], xobjects, res, state["ctm"], depth, seen)
            elif op == b"BI":
                self._inline_image(lex, state["ctm"])
            operands = []

    def _font_scale(self, font: Any) -> float:
        """Type 3 fonts scale their glyphs by their FontMatrix; the usual one is 1/1000 a unit."""
        if isinstance(font, dict) and font.get("Subtype") == "Type3":
            fm = self.pdf.get(font.get("FontMatrix"))
            if isinstance(fm, list) and len(fm) == 6 and all(isinstance(self.pdf.get(x), (int, float)) for x in fm):
                return abs(float(self.pdf.get(fm[3]))) * 1000 or 1.0
        return 1.0

    @staticmethod
    def _shows_glyphs(operands: list[Any]) -> bool:
        for x in operands:
            if isinstance(x, bytes) and x.strip(b" \x00"):
                return True
            if isinstance(x, list) and any(isinstance(y, bytes) and y.strip(b" \x00") for y in x):
                return True
        return False

    def _components(self, cs: Any, colorspaces: Any) -> int:
        cs = self.pdf.get(cs)
        if isinstance(cs, Name) and cs not in ("DeviceGray", "DeviceRGB", "DeviceCMYK", "G", "RGB", "CMYK") and isinstance(colorspaces, dict):
            cs = self.pdf.get(colorspaces.get(cs))
        if cs in ("DeviceGray", "G", "CalGray"):
            return 1
        if cs in ("DeviceRGB", "RGB", "CalRGB"):
            return 3
        if cs in ("DeviceCMYK", "CMYK"):
            return 4
        if isinstance(cs, list) and cs:
            kind = self.pdf.get(cs[0])
            if kind == "ICCBased" and len(cs) > 1:
                d = self.pdf.get(cs[1])
                n = self.pdf.get(d.dict.get("N")) if isinstance(d, Stream) else None
                return n if n in (1, 3, 4) else 0
            if kind in ("CalRGB",):
                return 3
            if kind in ("CalGray",):
                return 1
        return 0  # a pattern, separation, indexed space: not followed

    def _do(self, name: str, xobjects: dict[str, Any], res: dict[str, Any], ctm: Matrix, depth: int, seen: set[int]) -> None:
        ref = xobjects.get(name)
        x = self.pdf.get(ref)
        if not isinstance(x, Stream):
            return
        sub = x.dict.get("Subtype")
        if sub == "Image":
            w, h = self.pdf.get(x.dict.get("Width")), self.pdf.get(x.dict.get("Height"))
            if isinstance(w, int) and isinstance(h, int):
                self.fig.images.append(Image((w, h), (math.hypot(ctm[0], ctm[1]), math.hypot(ctm[2], ctm[3]))))
        elif sub == "Form":
            key = ref.num if isinstance(ref, Ref) else id(x)
            if depth >= MAX_DEPTH or key in seen:
                self.fig.notes.append("a nested drawing too deep or drawn within itself: not followed")
                return
            matrix = self.pdf.get(x.dict.get("Matrix"))
            m: Matrix = tuple(float(self.pdf.get(v)) for v in matrix) if isinstance(matrix, list) and len(matrix) == 6 else IDENTITY  # type: ignore[assignment]
            body = x.decoded()
            if body is None:
                self.fig.notes.append("a nested drawing in a filter this does not read")
                return
            self.run(body, self.pdf.get(x.dict.get("Resources")) or res, _mul(m, ctm), depth + 1, seen | {key})

    def _inline_image(self, lex: Lexer, ctm: Matrix) -> None:
        params: dict[str, Any] = {}
        while True:
            k = lex.token()
            if k is None or k == Keyword(b"ID"):
                break
            if isinstance(k, Name):
                params[k] = lex.object()
        end = re.compile(rb"\sEI(?=[\s]|$)").search(lex.data, lex.pos)
        lex.pos = end.end() if end else len(lex.data)
        w, h = params.get("W", params.get("Width")), params.get("H", params.get("Height"))
        if isinstance(w, int) and isinstance(h, int):
            self.fig.images.append(Image((w, h), (math.hypot(ctm[0], ctm[1]), math.hypot(ctm[2], ctm[3]))))


def _colour(nums: list[float], n: int) -> tuple[float, float, float] | None:
    if len(nums) < n:
        return None
    v = [min(1.0, max(0.0, x)) for x in nums[-n:]]
    if n == 1:
        return (v[0], v[0], v[0])
    if n == 3:
        return (v[0], v[1], v[2])
    c, m, y, k = v
    return ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
