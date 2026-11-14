r"""A model's architecture as a paper figure: its blocks in order, repeated blocks collapsed, as editable TikZ (in the
paper's own font and size) or SVG.

>>> import torchvision                                                       # doctest: +SKIP
>>> from fig_check import diagram                                            # doctest: +SKIP
>>> d = diagram(torchvision.models.resnet18(weights=None))                   # doctest: +SKIP
>>> d.save_tikz("figures/resnet18.tex")  # \input{figures/resnet18.tex}; edit the labels in the file   # doctest: +SKIP

Any object with `named_children()` works (a PyTorch module; torch is not a dependency). Children of the same kind
and shape that follow each other become one block with "×N"; `depth=2` opens each block into its parts. Labels are the
class names, with the parameter count when the module has parameters; `labels={"layer1": "Stage 1"}` renames.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Block:
    name: str  # the attribute name ("layer1", "encoder.layers")
    kind: str  # the class name ("Sequential", "TransformerEncoderLayer")
    params: int
    count: int = 1  # how many identical blocks in a row this stands for
    children: list[Block] = field(default_factory=list)

    @property
    def signature(self) -> tuple:
        """What makes two blocks "the same" for collapsing: kind, parameter count and the children's signatures."""
        return (self.kind, self.params, tuple(c.signature for c in self.children))


def _params(m: Any) -> int:
    try:
        return int(sum(p.numel() for p in m.parameters()))
    except (AttributeError, TypeError):
        return 0


CONTAINERS = {"Sequential", "ModuleList", "ModuleDict"}


def _kids(m: Any) -> list[tuple[str, Any]]:
    """A module's children, with containers inside it opened (ViT's encoder.layers: its blocks, not one "Sequential")."""
    out = []
    for n, c in m.named_children() if hasattr(m, "named_children") else []:
        if type(c).__name__ in CONTAINERS:
            out += [(f"{n}.{k}", g) for k, g in _kids(c)]
        else:
            out.append((n, c))
    return out


def _walk(name: str, m: Any, depth: int) -> Block:
    kind = type(m).__name__
    if kind in CONTAINERS:  # a stage (ResNet's layer1): its blocks, collapsed, under the stage's name
        inner = collapse([_walk(n, c, depth - 1) for n, c in _kids(m)])
        if len({b.kind for b in inner}) == 1:
            b = inner[0]
            return Block(name, b.kind, _params(m), sum(x.count for x in inner), b.children if depth > 1 else [])
        b = Block(name, kind, _params(m))
        b.children = inner
        return b
    b = Block(name, kind, _params(m))
    if depth > 0:
        b.children = collapse([_walk(n, c, depth - 1) for n, c in _kids(m)])
    return b


def collapse(blocks: list[Block]) -> list[Block]:
    """Consecutive blocks with the same signature become one, with a count.

    >>> [ (b.kind, b.count) for b in collapse([Block("0", "Layer", 10), Block("1", "Layer", 10), Block("2", "Norm", 2)]) ]
    [('Layer', 2), ('Norm', 1)]
    """
    out: list[Block] = []
    for b in blocks:
        if out and out[-1].signature == b.signature:
            out[-1].count += b.count
        else:
            out.append(b)
    return out


@dataclass
class Diagram:
    title: str
    blocks: list[Block]
    labels: dict[str, str] = field(default_factory=dict)
    direction: str = "right"  # or "down"
    per_row: int = 0  # with "right": start a new row after this many blocks (0: one row)

    def _label(self, b: Block) -> tuple[str, str]:
        main = self.labels.get(b.name, b.kind)
        sub = _human(b.params) if b.params else ""
        if b.count > 1:
            main += f" ×{b.count}"
        if b.name and not b.name[0].isdigit() and b.name not in self.labels and b.name.lower() != b.kind.lower():
            sub = f"{b.name}, {sub}" if sub else b.name  # the module's own name ("layer1", "encoder")
        return main, sub

    def _inner(self, b: Block) -> list[str]:
        """The block's parts, by kind: "BasicBlock ×2", not "BasicBlock → BasicBlock" when one has a downsample path."""
        out: list[list] = []
        for c in b.children:
            name = self.labels.get(c.name, c.kind)
            if out and out[-1][0] == name:
                out[-1][1] += c.count
            else:
                out.append([name, c.count])
        return [n + (f" ×{k}" if k > 1 else "") for n, k in out]

    def tikz(self) -> str:
        r"""TikZ code: \input it in a figure (needs \usepackage{tikz}); the text is set in the paper's font."""
        horizontal = self.direction == "right"
        step = "right" if horizontal else "below"
        lines = [
            "% Made by fig-check's diagram() from the model's modules; edit freely.",
            "% Needs \\usepackage{tikz} and \\usetikzlibrary{positioning} in the preamble.",
            "\\begin{tikzpicture}[",
            "  block/.style={draw, rounded corners=2pt, align=center, minimum height=2.2em, inner sep=3pt, font=\\small},",
            "  group/.style={draw, dashed, rounded corners=3pt, inner sep=5pt},",
            "  arrow/.style={-latex, thin},",
            f"  node distance={'0.45cm' if horizontal else '0.35cm'}]",
        ]
        prev = None
        for i, b in enumerate(self.blocks):
            main, sub = self._label(b)
            text = _tex(main) + (f"\\\\[-1pt]{{\\footnotesize {_tex(sub)}}}" if sub else "")
            new_row = horizontal and self.per_row and i and i % self.per_row == 0
            where = f", below=0.6cm of b{i - self.per_row}" if new_row else (f", {step}=of b{i - 1}" if prev is not None else "")
            if b.children:
                inner = " $\\to$ ".join(_tex(x) for x in self._inner(b))
                text += f"\\\\[-1pt]{{\\footnotesize {inner}}}"
            lines.append(f"\\node[block{where}] (b{i}) {{{text}}};")
            if prev is not None and new_row:  # down from the row's last block, across, down into the next row's first
                lines.append(f"\\draw[arrow] (b{i - 1}.south) -- ++(0,-0.3cm) -| (b{i}.north);")
            elif prev is not None:
                lines.append(f"\\draw[arrow] (b{i - 1}) -- (b{i});")
            prev = i
        lines.append("\\end{tikzpicture}")
        return "\n".join(lines) + "\n"

    def save_tikz(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.tikz(), encoding="utf-8")
        return p

    def svg(self) -> str:
        """A quick SVG of the same blocks (for a README or a slide; the TikZ is the paper's version)."""
        boxes = []
        x, y, gap = 10.0, 10.0, 26.0
        row_h = 0.0
        for i, b in enumerate(self.blocks):
            if self.direction == "right" and self.per_row and i and i % self.per_row == 0:
                x, y = 10.0, y + row_h + gap
                row_h = 0.0
            main, sub = self._label(b)
            inner = " → ".join(self._inner(b))
            w = max(len(main) * 7.2, len(sub) * 6.0, len(inner) * 5.6) + 22
            h = 40 + (14 if inner else 0)
            boxes.append((x, y, w, h, main, sub, inner))
            row_h = max(row_h, h)
            if self.direction == "right":
                x += w + gap
            else:
                y += h + gap
        width = (max(bx + bw for bx, _, bw, _, *_ in boxes) + 10) if boxes else 20
        height = (max(by + bh for _, by, _, bh, *_ in boxes) + 10) if boxes else 20
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" '
               'font-family="Times New Roman, Times, serif" font-size="13">',
               '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z"/></marker></defs>']  # fmt: skip  # noqa: E501 - one SVG element
        for i, (bx, by, bw, bh, main, sub, inner) in enumerate(boxes):
            out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh}" rx="4" fill="#fff" stroke="#333"/>')
            out.append(f'<text x="{bx + bw / 2:.1f}" y="{by + 17}" text-anchor="middle">{html.escape(main)}</text>')
            if sub:
                out.append(f'<text x="{bx + bw / 2:.1f}" y="{by + 32}" text-anchor="middle" font-size="10" fill="#555">{html.escape(sub)}</text>')
            if inner:
                out.append(f'<text x="{bx + bw / 2:.1f}" y="{by + 46}" text-anchor="middle" font-size="9.5" fill="#555">{html.escape(inner)}</text>')
            if i:
                px, py, pw, ph = boxes[i - 1][:4]
                if self.direction == "right" and by > py:  # to the next row
                    mid = py + ph + (by - py - ph) / 2
                    out.append(
                        f'<polyline points="{px + pw / 2:.1f},{py + ph:.1f} {px + pw / 2:.1f},{mid:.1f} {bx + bw / 2:.1f},{mid:.1f} {bx + bw / 2:.1f},{by - 2:.1f}" '  # noqa: E501 - one SVG element
                        'fill="none" stroke="#333" marker-end="url(#a)"/>'
                    )
                elif self.direction == "right":
                    out.append(
                        f'<line x1="{px + pw:.1f}" y1="{py + ph / 2:.1f}" x2="{bx - 2:.1f}" y2="{by + bh / 2:.1f}" stroke="#333" marker-end="url(#a)"/>'  # noqa: E501 - one SVG element
                    )
                else:
                    out.append(
                        f'<line x1="{px + pw / 2:.1f}" y1="{py + ph:.1f}" x2="{bx + bw / 2:.1f}" y2="{by - 2:.1f}" stroke="#333" marker-end="url(#a)"/>'  # noqa: E501 - one SVG element
                    )
        out.append("</svg>")
        return "\n".join(out) + "\n"


def _human(n: int) -> str:
    """1234567 -> '1.2M'.

    >>> _human(11689512), _human(4096), _human(512)
    ('11.7M', '4.1K', '512')
    """
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= size:
            return f"{n / size:.1f}{unit}"
    return str(n)


def _tex(s: str) -> str:
    return re.sub(r"([&%$#_{}])", r"\\\1", s).replace("×", "$\\times$").replace("~", "\\textasciitilde{}")


def diagram(model: Any, depth: int = 1, labels: dict[str, str] | None = None, direction: str = "right", skip: tuple[str, ...] = (),
            per_row: int = 0) -> Diagram:  # fmt: skip
    """The model's top-level blocks (opened `depth` levels: 1 shows each top block with its parts listed), repeated
    blocks collapsed. A top-level container whose children are the real blocks (nn.Sequential models) is opened.
    `skip` leaves out modules by class name (e.g. ("Dropout", "Identity"))."""
    if direction not in ("right", "down"):
        raise ValueError("direction is 'right' or 'down'")
    kids = list(model.named_children()) if hasattr(model, "named_children") else []
    if type(model).__name__ in CONTAINERS:  # an nn.Sequential model: its layers are the blocks
        kids = _kids(model)
    blocks = [_walk(n, c, depth) for n, c in kids if type(c).__name__ not in skip]
    for b in blocks:
        b.children = [c for c in b.children if c.kind not in skip]
    return Diagram(type(model).__name__, collapse(blocks), labels or {}, direction, per_row)
