r"""Matplotlib figures made at the width they print at, in the paper's font: no scaling in LaTeX, so 9 pt text prints at
9 pt.

>>> import matplotlib.pyplot as plt                                   # doctest: +SKIP
>>> from fig_check import paper_style, save_for_paper                 # doctest: +SKIP
>>> with plt.rc_context(paper_style("icml")):                         # doctest: +SKIP
...     fig, ax = plt.subplots()                                      # 3.25 in wide: ICML's column
...     ax.plot([1, 2, 3], label="ours"); ax.legend()
...     report = save_for_paper(fig, "figures/loss.pdf", "icml")      # saved at 3.25 in, then checked
>>> print(report)                                                     # doctest: +SKIP

Then `\includegraphics{figures/loss.pdf}` with no width (or `width=\columnwidth`, the same) prints it at its size.
matplotlib is not a dependency: `paper_style` returns a plain dict of rcParams.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .check import Finding, Limits, Report, check_bytes
from .figure import printed_width


@dataclass(frozen=True)
class Font:
    family: str  # "times" or "computer modern"
    size: float  # the body text's size, points
    source: str


# Each template's body font, as pdflatex sets it with the style file (\f@family and \f@size printed after
# \begin{document}, MiKTeX, 2026-11-14): neurips_2025.sty (\renewcommand{\rmdefault}{ptm}), icml2025.sty
# (\RequirePackage{times}), iclr2025_conference.sty with the template's \usepackage{...,times}: ptm at 10 pt;
# acl.sty with the template's \documentclass[11pt]{article} and \usepackage{times}: ptm at 10.95 pt; article.cls: cmr at
# 10 pt. cvpr.sty could not be compiled here (it needs silence.sty); it loads \RequirePackage{times} and its template is
# \documentclass[10pt,twocolumn,letterpaper]{article}. AAAI, IEEEtran, acmart and llncs were not measured: give `font=`.
FONTS = {
    "neurips": Font("times", 10.0, "neurips_2025.sty"),
    "iclr": Font("times", 10.0, "iclr2025_conference.sty + times"),
    "icml": Font("times", 10.0, "icml2025.sty"),
    "cvpr": Font("times", 10.0, "cvpr.sty (read, not compiled)"),
    "acl": Font("times", 10.95, "acl.sty, 11pt"),
    "article": Font("computer modern", 10.0, "article.cls"),
}
SERIF = {
    # what matplotlib finds first: the font itself, then metric clones (Nimbus Roman and TeX Gyre Termes are Times's)
    "times": ["Times New Roman", "Times", "Nimbus Roman", "Nimbus Roman No9 L", "TeX Gyre Termes", "STIXGeneral", "DejaVu Serif"],
    "computer modern": ["CMU Serif", "Latin Modern Roman", "cmr10", "DejaVu Serif"],
}
MATH = {"times": "stix", "computer modern": "cm"}
GOLDEN = 0.618


def paper_style(template: str = "article", width: float | str = "column", *, height: float | None = None, aspect: float = GOLDEN,
                font: str | None = None, fontsize: float | None = None) -> dict[str, Any]:  # fmt: skip
    r"""rcParams for a figure `width` wide (`"column"`, `"text"`, inches, `"0.48\linewidth"`; see `printed_width`) and
    `height` tall (or `aspect` times the width), in the template's font: text one point under the body size (a
    caption's), tick labels and legend two under, thin lines, fonts embedded as TrueType (no Type 3 fonts, which some
    venues reject).

    >>> s = paper_style("icml"); s["figure.figsize"], s["font.size"], s["font.serif"][0], s["pdf.fonttype"]
    ((3.25, 2.0085), 9.0, 'Times New Roman', 42)
    >>> paper_style("article", "text", height=2)["figure.figsize"], paper_style("article")["mathtext.fontset"]
    ((4.7738, 2), 'cm')
    """
    inches = printed_width(width, template)
    assert inches is not None
    f = FONTS.get(template)
    family = font or (f.family if f else None)
    if family not in SERIF:
        raise ValueError(f"no measured font for template {template!r}: pass font='times' or font='computer modern'")
    body = fontsize if fontsize is not None else (f.size - 1 if f else 9.0)
    small = max(body - 1, 5.0)
    return {
        "figure.figsize": (round(inches, 4), height if height is not None else round(inches * aspect, 4)),
        "figure.dpi": 150,
        "savefig.dpi": 300,  # images (imshow) are rasterised at this
        "savefig.bbox": None,  # "tight" would change the width the figure was made for
        "font.family": "serif",
        "font.serif": SERIF[family],
        "mathtext.fontset": MATH[family],
        "axes.formatter.use_mathtext": True,  # cmr10 has no minus sign of its own
        "font.size": float(round(body, 2)),
        "axes.labelsize": float(round(body, 2)),
        "axes.titlesize": float(round(body, 2)),
        "xtick.labelsize": float(round(small, 2)),
        "ytick.labelsize": float(round(small, 2)),
        "legend.fontsize": float(round(small, 2)),
        "lines.linewidth": 1.0,
        "lines.markersize": 3.5,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "grid.linewidth": 0.4,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.constrained_layout.use": True,  # labels kept inside the width, without bbox_inches="tight"
    }


def save_for_paper(fig: Any, path: str | Path, template: str = "article", width: float | str = "column", *,
                   height: float | None = None, limits: Limits | None = None, **savefig: Any) -> Report:  # fmt: skip
    r"""Save `fig` at exactly the width it prints at (its height kept, or `height`), then check the saved figure at that
    width (text size, colours, images) and return the report. The format follows the file's extension (PDF for LaTeX;
    PNG and SVG are checked too). `bbox_inches="tight"` is refused: it changes the width, and LaTeX would scale the
    figure back, text included.

    Call it inside the same `plt.rc_context(paper_style(...))` the figure was made in: matplotlib picks the fonts when
    it draws, at saving.

    The report names the fonts the PDF uses, and warns when the paper is in Times and the figure is not (matplotlib
    falls back to DejaVu when no Times font is installed).
    """
    if savefig.get("bbox_inches") == "tight":
        raise ValueError('bbox_inches="tight" changes the width: use paper_style (constrained layout) instead')
    inches = printed_width(width, template)
    assert inches is not None
    w, h = fig.get_size_inches()
    fig.set_size_inches(inches, height if height is not None else h * inches / w)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    fmt = path.suffix.lstrip(".").lower() or "pdf"
    try:  # fonts embedded as TrueType whatever the rcParams in force when saving (Type 3 is matplotlib's default)
        import matplotlib

        with matplotlib.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42}):
            fig.savefig(buf, format=fmt, **savefig)
    except ImportError:  # not matplotlib: anything with savefig()
        fig.savefig(buf, format=fmt, **savefig)
    data = buf.getvalue()
    path.write_bytes(data)
    report = check_bytes(data, path.name, inches, limits=limits)
    if fmt == "pdf":
        fonts = embedded_fonts(data)
        wanted = FONTS.get(template)
        if fonts:
            report.findings.append(Finding("typeface", "info", "fonts in the PDF: " + ", ".join(fonts)))
        if wanted and fonts and wanted.family == "times" and not any(_times(x) for x in fonts):
            msg = "the paper is set in Times, the figure is not: install a Times font for matplotlib (Nimbus Roman, TeX Gyre Termes)"
            report.findings.append(Finding("typeface", "warning", msg))
    return report


def _times(name: str) -> bool:
    return any(k in name.lower().replace(" ", "") for k in ("times", "nimbusroman", "termes", "stix"))


def embedded_fonts(pdf: bytes) -> list[str]:
    r"""The base names of the fonts a PDF uses (subset prefixes removed).

    >>> embedded_fonts(b"<< /Type /Font /BaseFont /ABCDEF+TimesNewRomanPSMT >> << /BaseFont /DejaVuSans >>")
    ['DejaVuSans', 'TimesNewRomanPSMT']
    """
    import re

    names = {re.sub(r"^[A-Z]{6}\+", "", m.decode("latin-1")) for m in re.findall(rb"/BaseFont\s*/([^\s/<>\[\]()]+)", pdf)}
    return sorted(names)
