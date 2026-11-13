r"""A matplotlib figure as pgfplots code, so LaTeX draws it at the width it prints at, in the paper's own font and size:

>>> from fig_check.pgf import save_pgfplots                                   # doctest: +SKIP
>>> save_pgfplots(fig, "figures/loss.tex")                                    # doctest: +SKIP

and in the paper, with `\usepackage{pgfplots}` in the preamble: `\input{figures/loss.tex}`. The figure fills
`\linewidth` (or the width you give) with the axes where matplotlib put them; text is typeset by LaTeX, so it is never
shrunk with the figure.

Exported: lines (colour, width, dashes, markers), scatter points, bars and other rectangles, filled areas
(fill_between), error bars, text annotations, axis labels, titles, limits, log scales, ticks and their labels, grids,
legends. Not exported, and listed in the returned notes (and as comments in the code): images (imshow, pcolormesh),
colour bars, 3D axes, and anything else; save those as PDF and check them with fig-check.

It reads the figure through matplotlib's public methods (and one private attribute, the legend's location, with a
fallback); matplotlib is not imported here.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MARKERS = {"o": "*", ".": "*", "s": "square*", "^": "triangle*", "v": "triangle*", "D": "diamond*", "d": "diamond*",
           "x": "x", "+": "+", "*": "star", "p": "pentagon*", "h": "*", "|": "|", "_": "-"}  # fmt: skip
LEGEND = {1: "north east", 2: "north west", 3: "south west", 4: "south east", 5: "east", 6: "west", 7: "east", 8: "south", 9: "north",
          10: "center"}  # fmt: skip
SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
           "^": r"\textasciicircum{}", "$": r"\$"}  # fmt: skip


def tex_text(s: str) -> str:
    r"""matplotlib text as LaTeX: mathtext between unescaped $ kept, the rest escaped; the Unicode minus made ASCII.

    >>> tex_text("loss (%) of $\\alpha_1$ & co_2"), tex_text("−0.5")
    ('loss (\\%) of $\\alpha_1$ \\& co\\_2', '$-$0.5')
    """
    s = re.sub(r"\\mathdefault\{((?:[^{}]|\{[^{}]*\})*)\}", r"\1", s)  # matplotlib's tick labels: $\mathdefault{10^{2}}$
    s = s.replace("\u2212", "$-$") if "$" not in s else s.replace("\u2212", "-")
    parts = re.split(r"((?<!\\)\$.*?(?<!\\)\$)", s)
    return "".join(p if p.startswith("$") and p.endswith("$") and len(p) > 1 else "".join(SPECIAL.get(c, c) for c in p) for p in parts)


def _num(v: float) -> str:
    """A number as pgfplots reads it: up to 6 significant digits.

    >>> _num(0.1 + 0.2), _num(1e-7), _num(12345678.0), _num(float("nan"))
    ('0.3', '1e-07', '1.23457e+07', 'nan')
    """
    return "nan" if v != v else f"{v:.6g}"


@dataclass
class _Out:
    colours: dict[str, str] = field(default_factory=dict)  # hex -> name
    body: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def colour(self, rgba: Any) -> tuple[str, float]:
        """A colour's name (defined once) and its opacity."""
        r, g, b, *a = (float(x) for x in rgba)
        hx = f"{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"
        if hx not in self.colours:
            self.colours[hx] = f"fc{len(self.colours)}"
        return self.colours[hx], a[0] if a else 1.0


def _opacity(name: str, alpha: float, key: str = "opacity") -> str:
    return f"{name}, {key}={_num(alpha)}" if alpha < 0.999 else name


def _dash(style: Any) -> str:
    return {"--": "dashed", "dashed": "dashed", ":": "dotted", "dotted": "dotted", "-.": "dashdotted", "dashdot": "dashdotted"}.get(
        str(style), "solid"
    )


def _coords(xs: Any, ys: Any) -> str:
    pts = []
    for x, y in zip(xs, ys, strict=False):
        try:
            fx, fy = float(x), float(y)
        except (TypeError, ValueError):
            continue
        pts.append(f"({_num(fx)},{_num(fy)})")
    lines, cur = [], ""
    for p in pts:  # a few points per line, so the file diffs well
        if len(cur) + len(p) > 100:
            lines.append(cur)
            cur = ""
        cur += p + " "
    if cur:
        lines.append(cur)
    return "\n    ".join(x.rstrip() for x in lines)


def _line(out: _Out, line: Any, legend: str | None) -> bool:
    xs, ys = line.get_xdata(), line.get_ydata()
    if not line.get_visible() or len(xs) == 0:
        return False
    name, alpha = out.colour(_rgba(line.get_color()))
    opts = [_opacity(name, alpha)] if legend is not None else ["forget plot", _opacity(name, alpha)]
    style = line.get_linestyle()
    marker = str(line.get_marker())
    if style in ("None", "none", " ", ""):
        opts.append("only marks")
    else:
        opts += [_dash(style), f"line width={_num(line.get_linewidth())}pt"]
    if marker in MARKERS:
        mark = MARKERS[marker]
        face = line.get_markerfacecolor()
        hollow = isinstance(face, str) and face.lower() == "none"
        opts.append(f"mark={mark.rstrip('*') if hollow and mark.endswith('*') else mark}")
        opts.append(f"mark size={_num(line.get_markersize() / 2)}pt")
        if marker == "v":
            opts.append("mark options={solid, rotate=180}")
        else:
            opts.append("mark options={solid}")
    else:
        opts.append("no markers")
    out.body.append(f"\\addplot[{', '.join(opts)}] coordinates {{\n    {_coords(xs, ys)}\n}};")
    if legend is not None:
        out.body.append(f"\\addlegendentry{{{legend}}}")
    return True


def _rgba(c: Any) -> tuple[float, float, float, float]:
    """A matplotlib colour as RGBA floats, without importing matplotlib (#rrggbb, #rgb, names through to_rgba)."""
    if isinstance(c, str):
        s = c.strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", s):
            vals = [int(s[i : i + 2], 16) / 255 for i in range(1, len(s), 2)]
            return (vals[0], vals[1], vals[2], vals[3] if len(vals) > 3 else 1.0)
        try:
            from matplotlib.colors import to_rgba  # the figure is matplotlib's, so it is there

            r, g, b, a = to_rgba(s)
            return (r, g, b, a)
        except (ImportError, ValueError):
            return (0.0, 0.0, 0.0, 1.0)
    vals = [float(x) for x in c]
    return (vals[0], vals[1], vals[2], vals[3] if len(vals) > 3 else 1.0)


def _legend_entry(label: Any) -> str | None:
    s = str(label) if label is not None else ""
    return None if not s or s.startswith("_") else tex_text(s)


def _axis(out: _Out, ax: Any, fig_w: float, fig_h: float) -> None:
    pos = ax.get_position()
    x0, y0, w, h = pos.x0, pos.y0, pos.width, pos.height
    opts = [
        f"at={{({_num(x0)}*\\fcw,{_num(y0)}*\\fch)}}", "anchor=south west", "scale only axis",
        f"width={_num(w)}*\\fcw", f"height={_num(h)}*\\fch",
    ]  # fmt: skip
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    opts += [f"xmin={_num(xmin)}", f"xmax={_num(xmax)}", f"ymin={_num(ymin)}", f"ymax={_num(ymax)}"]
    for a, scale in (("x", ax.get_xscale()), ("y", ax.get_yscale())):
        if scale == "log":
            opts.append(f"{a}mode=log")
        elif scale != "linear":
            out.notes.append(f"{scale} {a} scale: drawn linear")
    for a, label in (("x", ax.get_xlabel()), ("y", ax.get_ylabel())):
        if label:
            opts.append(f"{a}label={{{tex_text(label)}}}")
    title = ax.get_title()
    if title:
        opts.append(f"title={{{tex_text(title)}}}")
    for a, lo, hi, ticks, labels in (
        ("x", xmin, xmax, ax.get_xticks(), ax.get_xticklabels()),
        ("y", ymin, ymax, ax.get_yticks(), ax.get_yticklabels()),
    ):
        lo, hi = min(lo, hi), max(lo, hi)
        slack = 1e-9 * abs(hi - lo)  # matplotlib lists ticks just outside the limits too
        pairs = [(float(t), lab.get_text()) for t, lab in zip(ticks, labels, strict=False) if lo - slack <= float(t) <= hi + slack]
        if not pairs:
            opts.append(f"{a}tick=\\empty")
            continue
        opts.append(f"{a}tick={{{','.join(_num(t) for t, _ in pairs)}}}")
        if any(text for _, text in pairs):
            opts.append(f"{a}ticklabels={{{','.join('{' + tex_text(text) + '}' for _, text in pairs)}}}")
        else:
            opts.append(f"{a}ticklabels=\\empty")
    if ax.get_xgridlines() and any(g.get_visible() for g in ax.get_xgridlines()):
        opts.append("xmajorgrids")
    if ax.get_ygridlines() and any(g.get_visible() for g in ax.get_ygridlines()):
        opts.append("ymajorgrids")
    if xmin > xmax:
        opts.append("x dir=reverse")
    if ymin > ymax:
        opts.append("y dir=reverse")
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        loc = getattr(legend, "_loc", 1)
        opts.append(f"legend pos={LEGEND.get(loc, 'north east')}" if loc in (1, 2, 3, 4) else "legend pos=north east")
        opts.append("legend cell align=left")
    out.body.append("\\begin{axis}[\n  " + ",\n  ".join(opts) + "\n]")
    legend_labels = {t.get_text() for t in legend.get_texts()} if legend is not None else set()

    for patch in ax.patches:
        if not patch.get_visible() or type(patch).__name__ != "Rectangle":
            if patch.get_visible():
                out.notes.append(f"a {type(patch).__name__} patch")
            continue
        x, y = patch.get_x(), patch.get_y()
        pw, ph = patch.get_width(), patch.get_height()
        fill, fa = out.colour(patch.get_facecolor())
        out.body.append(
            f"\\fill[{_opacity(fill, fa, 'fill opacity')}] (axis cs:{_num(x)},{_num(y)}) rectangle (axis cs:{_num(x + pw)},{_num(y + ph)});"
        )
    for c in ax.collections:
        kind = type(c).__name__
        if not c.get_visible():
            continue
        if kind == "PathCollection":  # scatter
            offsets = c.get_offsets()
            if len(offsets) == 0:
                continue
            faces = c.get_facecolors()
            name, alpha = out.colour(faces[0] if len(faces) else (0, 0, 0, 1))
            if len(faces) > 1 and any(tuple(f) != tuple(faces[0]) for f in faces):
                out.notes.append("a scatter with a colour per point: drawn in its first colour")
            sizes = c.get_sizes()
            size = math.sqrt(float(sizes[0])) / 2 if len(sizes) else 3  # s is the marker's area in points squared
            label = _legend_entry(c.get_label()) if c.get_label() in legend_labels else None
            forget = "" if label is not None else "forget plot, "
            out.body.append(f"\\addplot[{forget}only marks, mark=*, {_opacity(name, alpha)}, mark size={_num(size)}pt] coordinates {{\n    "
                            f"{_coords(offsets[:, 0], offsets[:, 1])}\n}};")  # fmt: skip
            if label is not None:
                out.body.append(f"\\addlegendentry{{{label}}}")
        elif kind in ("PolyCollection", "FillBetweenPolyCollection"):  # fill_between
            faces = c.get_facecolors()
            name, alpha = out.colour(faces[0] if len(faces) else (0, 0, 0, 1))
            for path in c.get_paths():
                v = path.vertices
                out.body.append(
                    f"\\fill[{_opacity(name, alpha, 'fill opacity')}] " + " -- ".join(f"(axis cs:{_num(x)},{_num(y)})" for x, y in v) + " -- cycle;"
                )
        elif kind == "LineCollection":  # error bars, vlines, hlines
            colours = c.get_colors()
            widths = c.get_linewidths()
            for i, seg in enumerate(c.get_segments()):
                if len(seg) < 2:
                    continue
                name, alpha = out.colour(colours[i % len(colours)] if len(colours) else (0, 0, 0, 1))
                lw = widths[i % len(widths)] if len(widths) else 1
                out.body.append(
                    f"\\draw[{_opacity(name, alpha)}, line width={_num(lw)}pt] " + " -- ".join(f"(axis cs:{_num(x)},{_num(y)})" for x, y in seg) + ";"
                )
        else:
            out.notes.append(f"a {kind} (an image, mesh or contour): save it as PDF and check it with fig-check")
    for line in ax.get_lines():
        _line(out, line, _legend_entry(line.get_label()) if line.get_label() in legend_labels else None)
    for t in ax.texts:
        if not t.get_visible() or not t.get_text():
            continue
        x, y = t.get_position()
        cs = "axis cs" if t.get_transform() == ax.transData else "rel axis cs"
        if cs == "rel axis cs" and t.get_transform() != ax.transAxes:
            out.notes.append(f"text {t.get_text()!r} placed in figure coordinates")
            continue
        anchor = {"left": "west", "right": "east", "center": "center"}.get(t.get_horizontalalignment(), "center")
        name, _ = out.colour(_rgba(t.get_color()))
        out.body.append(f"\\node[anchor={anchor}, {name}] at ({cs}:{_num(x)},{_num(y)}) {{{tex_text(t.get_text())}}};")
    if ax.images:
        out.notes.append(f"{len(ax.images)} image(s) (imshow): save the figure as PDF at dpi=300 and check it with fig-check")
    out.body.append("\\end{axis}")


def to_pgfplots(fig: Any, width: str = r"\linewidth", height: str | None = None) -> tuple[str, list[str]]:
    r"""The figure as a tikzpicture (pgfplots), `width` wide (a TeX length; `\linewidth` by default) and `height` tall
    (default: the figure's own proportions); and notes on what was not exported.
    """
    fig.canvas.draw()  # tick labels are set when the figure is drawn
    fig_w, fig_h = (float(v) for v in fig.get_size_inches())
    out = _Out()
    for ax in fig.axes:
        if getattr(ax, "name", "rectilinear") != "rectilinear":
            out.notes.append(f"a {ax.name} axes")
            continue
        if ax.get_label() == "<colorbar>":
            out.notes.append("a colour bar")
            continue
        if not ax.get_visible():
            continue
        _axis(out, ax, fig_w, fig_h)
    if fig.texts or getattr(fig, "_suptitle", None) is not None:
        out.notes.append("figure-level text (suptitle, fig.text)")
    h = height or f"{_num(fig_h / fig_w)}*\\fcw"
    head = [
        "% made by fig-check's to_pgfplots from a matplotlib figure; needs \\usepackage{pgfplots} (and \\pgfplotsset{compat=1.18})",
        *[f"% not exported: {n}" for n in dict.fromkeys(out.notes)],
        *[f"\\definecolor{{{name}}}{{HTML}}{{{hx}}}" for hx, name in out.colours.items()],
        "\\begin{tikzpicture}",
        f"\\pgfmathsetlengthmacro{{\\fcw}}{{{width}}}",
        f"\\pgfmathsetlengthmacro{{\\fch}}{{{h}}}",
    ]
    code = "\n".join(head + out.body + ["\\end{tikzpicture}"]) + "\n"
    return code, list(dict.fromkeys(out.notes))


def save_pgfplots(fig: Any, path: str | Path, width: str = r"\linewidth", height: str | None = None) -> list[str]:
    """Writes the figure's pgfplots code to `path` (for `\\input`); returns the notes on what was not exported."""
    code, notes = to_pgfplots(fig, width, height)
    Path(path).write_text(code, encoding="utf-8", newline="\n")
    return notes
