"""Colours as people with colour vision deficiency see them: sRGB to CIELAB, the CIEDE2000 difference (Sharma, Wu and
Dalal 2005), and the simulation of protanopia, deuteranopia and tritanopia by Machado, Oliveira and Fernandes (2009),
severity 1.0, applied to linear RGB values (the authors' page gives the matrices, not the colour space; linear RGB is the usual reading)."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

RGB = tuple[float, float, float]  # sRGB, 0..1

# Machado, Oliveira and Fernandes 2009, Table: simulation matrices for severity 1.0 (linear RGB)
MACHADO: dict[str, tuple[RGB, RGB, RGB]] = {
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gamma(c: float) -> float:
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def simulate(rgb: RGB, kind: str) -> RGB:
    """The colour as seen with the deficiency `kind` (protanopia, deuteranopia, tritanopia).

    >>> [round(x, 3) for x in simulate((1.0, 0.0, 0.0), "deuteranopia")]
    [0.64, 0.566, 0.0]
    """
    m = MACHADO[kind]
    lin = [_linear(c) for c in rgb]
    out = [sum(m[i][j] * lin[j] for j in range(3)) for i in range(3)]
    return (_gamma(out[0]), _gamma(out[1]), _gamma(out[2]))


def lab(rgb: RGB) -> tuple[float, float, float]:
    """sRGB (D65) to CIELAB.

    >>> [round(x, 2) + 0 for x in lab((1.0, 1.0, 1.0))]  # + 0: -0.0 reads as 0.0
    [100.0, 0.0, 0.0]
    """
    r, g, b = (_linear(c) for c in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """The CIEDE2000 colour difference (kL = kC = kH = 1), as Sharma, Wu and Dalal give it.

    >>> round(ciede2000((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485)), 4)
    2.0425
    """
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    cbar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(cbar**7 / (cbar**7 + 25**7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if c1p else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if c2p else 0.0
    dlp = l2 - l1
    dcp = c2p - c1p
    if c1p * c2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dH = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp / 2))
    lbar = (l1 + l2) / 2
    cbarp = (c1p + c2p) / 2
    if c1p * c2p == 0:
        hbarp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbarp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbarp = (h1p + h2p + 360) / 2
    else:
        hbarp = (h1p + h2p - 360) / 2
    t = (1 - 0.17 * math.cos(math.radians(hbarp - 30)) + 0.24 * math.cos(math.radians(2 * hbarp))
         + 0.32 * math.cos(math.radians(3 * hbarp + 6)) - 0.20 * math.cos(math.radians(4 * hbarp - 63)))  # fmt: skip
    dtheta = 30 * math.exp(-(((hbarp - 275) / 25) ** 2))
    rc = 2 * math.sqrt(cbarp**7 / (cbarp**7 + 25**7))
    sl = 1 + (0.015 * (lbar - 50) ** 2) / math.sqrt(20 + (lbar - 50) ** 2)
    sc = 1 + 0.045 * cbarp
    sh = 1 + 0.015 * cbarp * t
    rt = -math.sin(math.radians(2 * dtheta)) * rc
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 + (dH / sh) ** 2 + rt * (dcp / sc) * (dH / sh))


def delta(c1: RGB, c2: RGB) -> float:
    """CIEDE2000 between two sRGB colours."""
    return ciede2000(lab(c1), lab(c2))


@dataclass
class Clash:
    a: RGB
    b: RGB
    kind: str  # protanopia, deuteranopia or tritanopia
    seen: float  # ΔE2000 as seen with the deficiency
    normal: float  # ΔE2000 with typical colour vision


DISTINCT = 15.0  # colours this far apart (ΔE2000) are meant to be told apart
CLASH = 6.0  # under simulation, closer than this they are hard to tell apart


def clashes(colours: Iterable[RGB], distinct: float = DISTINCT, clash: float = CLASH) -> list[Clash]:
    """Pairs of colours that are clearly different with typical colour vision but nearly the same with a deficiency;
    near-greys are left out (black lines and grey grids are not what a reader tells apart by hue).

    >>> [(c.kind, round(c.seen, 1)) for c in clashes([(0.8, 0.2, 0.2), (0.2, 0.6, 0.2)])]  # red and green
    [('deuteranopia', 3.6)]
    """
    cs = [c for c in dict.fromkeys(_round(c) for c in colours) if not _grey(c)]
    out = []
    for i, a in enumerate(cs):
        for b in cs[i + 1 :]:
            normal = delta(a, b)
            if normal < distinct:
                continue
            for kind in MACHADO:
                seen = delta(simulate(a, kind), simulate(b, kind))
                if seen < clash:
                    out.append(Clash(a, b, kind, seen, normal))
    return out


def _round(c: RGB) -> RGB:
    return (round(c[0], 3), round(c[1], 3), round(c[2], 3))


def _grey(c: RGB) -> bool:
    _, a, b = lab(c)
    return math.hypot(a, b) < 8


def hexed(c: RGB) -> str:
    """#rrggbb.

    >>> hexed((1.0, 0.5, 0.0))
    '#ff8000'
    """
    return "#" + "".join(f"{round(min(1, max(0, x)) * 255):02x}" for x in c)
