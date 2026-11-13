r"""Checks the widths in tests/test_layout.py against pdflatex itself: each preamble and each class with its options is
compiled (a page that prints \the\textwidth and \the\columnwidth, after \maketitle for the classes, where acmart turns
two columns on), and the widths pdflatex prints are compared with the test tables and with fig-check's layout().

Needs a TeX distribution with pdflatex and the classes (IEEEtran, acmart, llncs, elsarticle, revtex4-2); CI has none,
so this is run by hand when the tables change: `uv run python scripts/latex_widths.py`. Nothing is fetched; TeX may
try to install a missing package, if the distribution is set to.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))
from fig_check.latex import IN, layout  # noqa: E402


def tables() -> tuple[list[tuple[str, float, float]], list[tuple[str, str, float, float]]]:
    """The LATEX and CLASSES tables, read from the test file without importing it."""
    tree = ast.parse((root / "tests" / "test_layout.py").read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("LATEX", "CLASSES"):
            found[node.targets[0].id] = ast.literal_eval(node.value)
    return found["LATEX"], found["CLASSES"]


def pdflatex(preamble: str, folder: str, n: int) -> tuple[float, float] | None:
    title = "\\title{T}\\author{A}" if "{acmart}" in preamble else ""  # acmart's columns begin at \maketitle
    start = "\\begin{document}\\maketitle" if title else "\\begin{document}"
    doc = f"{preamble}\n{title}{start}\n\\typeout{{FCW \\the\\textwidth\\space\\the\\columnwidth}}\nx\n\\end{{document}}\n"
    f = Path(folder) / f"c{n}.tex"
    f.write_text(doc, encoding="utf-8")
    r = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f.name], cwd=folder, capture_output=True, text=True, errors="replace"
    )
    m = re.search(r"FCW ([\d.]+)pt ([\d.]+)pt", r.stdout)
    return (float(m.group(1)), float(m.group(2))) if m else None


def main() -> int:
    latex, classes = tables()
    cases = [(pre, tw, cw) for pre, tw, cw in latex] + [(f"\\documentclass[{opts}]{{{cls}}}", tw, cw) for cls, opts, tw, cw in classes]
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        for i, (pre, tw, cw) in enumerate(cases):
            got = pdflatex(pre, d, i)
            t, _ = layout(pre + "\\begin{document}")
            ours = (t.text * IN, t.column * IN)
            ok = (
                got is not None
                and all(abs(a - b) < 0.02 for a, b in zip((tw, cw), got, strict=True))
                and all(abs(a - b) < 0.02 for a, b in zip((tw, cw), ours, strict=True))
            )
            bad += not ok
            shown = f"{got[0]:8.2f} {got[1]:8.2f}" if got else "  (pdflatex failed)"
            print(f"{'ok ' if ok else 'BAD'}  pdflatex {shown}  table {tw:8.2f} {cw:8.2f}  fig-check {ours[0]:8.2f} {ours[1]:8.2f}  {pre}")
    print(f"{len(cases)} cases, {bad} disagree")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
