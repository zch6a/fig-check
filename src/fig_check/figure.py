"""Checking a matplotlib figure before it is saved, at the width it will print at:

>>> import matplotlib.pyplot as plt                                         # doctest: +SKIP
>>> from fig_check import check_figure                                      # doctest: +SKIP
>>> fig, ax = plt.subplots(figsize=(6, 4))                                  # doctest: +SKIP
>>> ax.plot([1, 2, 3], label="ours"); ax.set_xlabel("step")                 # doctest: +SKIP
>>> print(check_figure(fig, width="column", template="icml"))               # doctest: +SKIP

The figure is saved to memory as a PDF (what LaTeX would include) and checked like a file: the smallest text when
printed, colours that collapse with colour vision deficiency, and the resolution of images in it (imshow). Nothing is
written to disk. matplotlib is not a dependency: anything with a `savefig(file, format="pdf")` method will do.
"""

from __future__ import annotations

import io
from typing import Any

from .check import Limits, Report, check_bytes
from .latex import TEMPLATES, dimension


def printed_width(width: float | str | None, template: str = "article") -> float | None:
    r"""Inches, from a number of inches, a TeX length (`"3.25in"`, `"8cm"`, `"0.48\linewidth"`), or `"column"` and
    `"text"` for the template's column and text width.

    >>> printed_width("column", "icml"), printed_width("text", "icml"), printed_width("0.5\\textwidth", "neurips")
    (3.25, 6.75, 2.75)
    """
    if width is None or isinstance(width, (int, float)):
        return None if width is None else float(width)
    if template not in TEMPLATES:
        raise ValueError(f"template {template!r}: one of {', '.join(sorted(TEMPLATES))}")
    t = TEMPLATES[template]
    named = {"column": t.column, "columnwidth": t.column, "text": t.text, "textwidth": t.text}
    if width.strip() in named:
        return named[width.strip()]
    inches = dimension(width, t.column, t)
    if inches is None or inches <= 0:
        raise ValueError(f"width {width!r}: inches, a length like 3.25in or 0.48\\linewidth, or 'column' or 'text'")
    return inches


def check_figure(fig: Any, width: float | str | None = None, *, template: str = "article", limits: Limits | None = None,
                 name: str = "figure", **savefig: Any) -> Report:  # fmt: skip
    r"""A matplotlib figure checked as it will print `width` wide (inches, `"3.25in"`, `"column"`, `"text"`,
    `"0.48\linewidth"`; the line width is the template's column), or at its own size when `width` is None.

    `template` is a venue (neurips, iclr, icml, cvpr, acl, aaai, article) for the named widths; other keyword
    arguments go to `savefig` (`bbox_inches="tight"` if that is how you will save it). `print()` the report to read
    it; `report.worst` is "ok", "warning" or "error".
    """
    inches = printed_width(width, template)
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", **savefig)
    return check_bytes(buf.getvalue(), name, inches, limits=limits)
