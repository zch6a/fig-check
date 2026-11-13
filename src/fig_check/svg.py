"""SVG figures: their size, the text sizes (font-size in attributes, style attributes and simple <style> rules, scaled
by the transforms around them), and the fill and stroke colours. Parsed with xml.etree without loading DTDs or
external entities (a document that declares entities is refused)."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from .color import RGB
from .pdf import Matrix, Text, _mul

UNITS = {"pt": 1.0, "px": 0.75, "in": 72.0, "cm": 72 / 2.54, "mm": 72 / 25.4, "pc": 12.0, "": 0.75}
NAMED = {"black": (0, 0, 0), "white": (1, 1, 1), "red": (1, 0, 0), "green": (0, 128 / 255, 0), "blue": (0, 0, 1), "orange": (1, 165 / 255, 0),
         "gray": (128 / 255,) * 3, "grey": (128 / 255,) * 3, "purple": (128 / 255, 0, 128 / 255), "yellow": (1, 1, 0), "lime": (0, 1, 0),
         "magenta": (1, 0, 1), "cyan": (0, 1, 1), "brown": (165 / 255, 42 / 255, 42 / 255), "pink": (1, 192 / 255, 203 / 255)}  # fmt: skip


class SVGError(Exception):
    pass


@dataclass
class SVGFigure:
    width: float  # points
    height: float
    texts: list[Text] = field(default_factory=list)
    fills: list[RGB] = field(default_factory=list)
    strokes: list[RGB] = field(default_factory=list)


def length(value: str | None, default: float | None = None) -> float | None:
    """An SVG length in points (px are 0.75 pt); None when absent or a percentage.

    >>> length("10pt"), length("96px"), length("1in"), length("50%")
    (10.0, 72.0, 72.0, None)
    """
    if not value:
        return default
    m = re.fullmatch(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)\s*(pt|px|in|cm|mm|pc)?\s*", value, flags=re.I)
    return float(m.group(1)) * UNITS[(m.group(2) or "").lower()] if m else default


def colour(value: str | None) -> RGB | None:
    """#rgb, #rrggbb, rgb(r, g, b) or a basic name; None for none, url(...) and the like.

    >>> colour("#ff8000"), colour("rgb(0, 0, 255)"), colour("none")
    ((1.0, 0.5019607843137255, 0.0), (0.0, 0.0, 1.0), None)
    """
    if not value:
        return None
    v = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{6}", v):
        return (int(v[1:3], 16) / 255, int(v[3:5], 16) / 255, int(v[5:7], 16) / 255)
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        return tuple(int(c * 2, 16) / 255 for c in v[1:])  # type: ignore[return-value]
    m = re.fullmatch(r"rgb\(\s*(\d+%?)\s*,\s*(\d+%?)\s*,\s*(\d+%?)\s*\)", v)
    if m:
        return tuple(float(x[:-1]) / 100 if x.endswith("%") else int(x) / 255 for x in m.groups())  # type: ignore[return-value]
    named = NAMED.get(v)
    return (float(named[0]), float(named[1]), float(named[2])) if named else None


def _transform(value: str | None) -> Matrix:
    m: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for fn, args in re.findall(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)", value or ""):
        a = [float(x) for x in re.findall(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?", args)]
        if fn == "matrix" and len(a) == 6:
            t: Matrix = (a[0], a[1], a[2], a[3], a[4], a[5])
        elif fn == "translate" and a:
            t = (1.0, 0.0, 0.0, 1.0, a[0], a[1] if len(a) > 1 else 0.0)
        elif fn == "scale" and a:
            t = (a[0], 0.0, 0.0, a[1] if len(a) > 1 else a[0], 0.0, 0.0)
        elif fn == "rotate" and a:
            r = math.radians(a[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0.0, 0.0)
        else:
            continue
        m = _mul(t, m)
    return m


def read_svg(data: bytes) -> SVGFigure:
    if b"<!ENTITY" in data[:4096] or b"<!DOCTYPE" in data[:4096] and b"[" in data[: data.find(b">", data.find(b"<!DOCTYPE")) + 1]:
        raise SVGError("an SVG that declares entities: not read")
    try:
        root = ET.fromstring(data)  # noqa: S314 - no DTD or entities (refused above)
    except ET.ParseError as e:
        raise SVGError(f"not XML ({e})") from e
    if not root.tag.endswith("svg"):
        raise SVGError("not an SVG")
    vb = [float(x) for x in re.findall(r"[+-]?(?:\d+\.?\d*|\.\d+)", root.get("viewBox") or "")]
    w = length(root.get("width"))
    h = length(root.get("height"))
    if w is None and len(vb) == 4:
        w, h = vb[2] * 0.75, vb[3] * 0.75
    if w is None or h is None:
        raise SVGError("an SVG without a size (width/height or viewBox)")
    # user units to points: the viewBox mapped onto width × height
    base: Matrix = (w / vb[2], 0.0, 0.0, h / vb[3], 0.0, 0.0) if len(vb) == 4 and vb[2] and vb[3] else (0.75, 0.0, 0.0, 0.75, 0.0, 0.0)
    rules = _style_rules(root)
    fig = SVGFigure(w, h)
    _walk(root, base, {"font-size": "16px", "fill": "#000000", "stroke": "none"}, rules, fig, 0)
    return fig


def _style_rules(root: ET.Element) -> dict[str, dict[str, str]]:
    """`.class { ... }`, `#id { ... }` and `tag { ... }` rules from <style> elements (simple selectors only)."""
    out: dict[str, dict[str, str]] = {}
    for el in root.iter():
        if el.tag.endswith("style") and el.text:
            for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", el.text):
                props = _props(body)
                for s in sel.split(","):
                    out.setdefault(s.strip(), {}).update(props)
    return out


def _props(style: str) -> dict[str, str]:
    return {k.strip().lower(): v.strip() for k, v in (p.split(":", 1) for p in style.split(";") if ":" in p)}


def _walk(el: ET.Element, ctm: Matrix, inherited: dict[str, str], rules: dict[str, dict[str, str]], fig: SVGFigure, depth: int) -> None:
    if depth > 64:
        return
    tag = el.tag.rsplit("}", 1)[-1]
    if tag in ("defs", "style", "title", "desc", "metadata", "clipPath", "mask", "symbol", "marker", "pattern"):
        return
    props = dict(inherited)
    props.update(rules.get(tag, {}))
    for cls in (el.get("class") or "").split():
        props.update(rules.get("." + cls, {}))
    if el.get("id"):
        props.update(rules.get("#" + str(el.get("id")), {}))
    for k in ("font-size", "fill", "stroke"):
        if el.get(k):
            props[k] = str(el.get(k))
    props.update(_props(el.get("style") or ""))
    ctm = _mul(_transform(el.get("transform")), ctm)
    if tag in ("text", "tspan", "textPath"):
        own = "".join(t for t in [el.text] if t).strip()
        size = length(props.get("font-size"))
        if own and size:
            # font-size is in user units (CSS px; `length` gives points, so back to px), and the transforms around it
            # (the viewBox included) take user units to points
            fig.texts.append(Text((size / 0.75) * math.hypot(ctm[2], ctm[3]), props.get("font-family", "")))
    elif tag in ("path", "rect", "circle", "ellipse", "polygon", "polyline", "line"):
        f = colour(props.get("fill"))
        s = colour(props.get("stroke"))
        if f is not None and tag != "line" and tag != "polyline":
            fig.fills.append(f)
        if s is not None:
            fig.strokes.append(s)
    for child in el:
        _walk(child, ctm, props, rules, fig, depth + 1)
