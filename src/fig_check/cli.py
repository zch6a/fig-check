"""fig-check: a paper's figures as they will print.

fig-check paper/                     every figure in a LaTeX project, at the width it prints at
fig-check paper/main.tex             the same, from this main file
fig-check plot.pdf --width 3.25in    single figures (PDF, PNG, JPEG, SVG) at a printed width

It checks the smallest text when printed, the resolution of raster images, and colours that people with colour
vision deficiency (protanopia, deuteranopia, tritanopia) cannot tell apart.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .check import Limits, Report, check_file
from .latex import TEMPLATES, dimension, expand, find, graphicspath, layout, main_file, uses

FIGURES = {".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"}


def _width(text: str) -> float:
    w = dimension(text, 0, TEMPLATES["article"])
    if w is None or w <= 0:
        hint = f" (inches: {text.strip()}in)" if text.strip().replace(".", "", 1).isdigit() else ""
        raise argparse.ArgumentTypeError(f"a width like 3.25in, 8cm or 240pt, not {text!r}{hint}")
    return w


def _rounded(value: object) -> object:
    """JSON without float noise: 2.6399999999999997 as 2.64 (4 decimals)."""
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rounded(v) for v in value]
    return value


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="fig-check", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="exit status: 0 nothing to fix, 1 warnings or errors found, 2 it could not run")  # fmt: skip
    ap.add_argument("paths", nargs="*", type=Path, help="a LaTeX project folder or main .tex file, or figure files")
    ap.add_argument("--width", type=_width, help="the printed width of figure files given directly (default: their own size)")
    ap.add_argument("--template", choices=sorted(TEMPLATES),
                    help="the venue's widths, when the preamble does not tell (its \\setlength and geometry still apply)")  # fmt: skip
    ap.add_argument("--min-font", type=float, default=Limits.font, metavar="PT", help=f"warn below this printed size (default {Limits.font:g} pt)")
    ap.add_argument("--min-dpi", type=float, default=Limits.dpi, metavar="DPI", help=f"warn below this resolution (default {Limits.dpi:g})")
    ap.add_argument("--json", action="store_true", help="the reports as JSON")
    ap.add_argument("--version", action="version", version=f"fig-check {__version__}")
    args = ap.parse_args(argv)
    if not args.paths:
        ap.print_help()
        return 2
    limits = Limits(font=args.min_font, dpi=args.min_dpi, font_error=min(Limits.font_error, args.min_font),
                    dpi_error=min(Limits.dpi_error, args.min_dpi))  # fmt: skip
    reports: list[Report] = []
    projects: list[dict[str, object]] = []
    try:
        for path in args.paths:
            if path.is_dir() or path.suffix.lower() == ".tex":
                project, rs = _project(path, limits, args.template)
                projects.append(project)
                reports += rs
            elif path.suffix.lower() in FIGURES or path.is_file():
                if not path.is_file():
                    raise ValueError(f"{path.as_posix()}: no such file")
                r = check_file(path, args.width, limits=limits)
                if any(f.message.startswith("not a PDF, PNG, JPEG or SVG") for f in r.findings):
                    raise ValueError(f"{path.as_posix()}: not a figure (PDF, PNG, JPEG or SVG), nor a LaTeX project")
                reports.append(r)
            else:
                raise ValueError(f"{path.as_posix()}: no such file or folder")
    except ValueError as e:
        print(f"fig-check: {e}", file=sys.stderr)
        return 2
    if args.json:
        out = {"version": __version__, "limits": asdict(limits), "projects": projects,
               "figures": [{**asdict(r), "worst": r.worst} for r in reports]}  # fmt: skip
        print(json.dumps(_rounded(out), indent=2, ensure_ascii=False))
    else:
        for p in projects:
            print(f"fig-check: {p['main']}: {p['template']} ({p['how']}): text {p['text_width']:.2f} in, column {p['column_width']:.2f} in")
        for r in reports:
            _print(r)
        bad = sum(1 for r in reports if r.worst != "ok")
        print(f"fig-check: {len(reports)} figure(s), {bad} with something to fix" if reports else "fig-check: no figures found")
    return 1 if any(r.worst != "ok" for r in reports) else 0


def _project(path: Path, limits: Limits, template_name: str | None) -> tuple[dict[str, object], list[Report]]:
    root = path if path.is_dir() else path.parent
    main = path if path.is_file() else main_file(root)
    if main is None or not main.is_file():
        raise ValueError(f"{path.as_posix()}: no main .tex file (one with \\documentclass and \\begin{{document}})")
    tex = expand(main, root)
    template, how = layout(tex, TEMPLATES[template_name] if template_name else None)
    dirs = graphicspath(tex)
    reports = []
    seen: set[tuple[str, float | None]] = set()
    macro_paths = 0
    for u in uses(tex, template):
        if "#" in u.path:
            continue  # inside a macro's definition (#1 is its argument): checked where the macro is used, if a file is named there
        if "\\" in u.path:
            macro_paths += 1  # a path a macro builds (\iftoggle{hq}{a}{b}, \figdir/x): not followed
            continue
        f = find(u.path, root, main, dirs)
        where = f"{main.name}:{u.line}, {u.where}"
        if f is None:
            reports.append(Report(u.path, where, findings=[_missing()]))
            continue
        key = (f.as_posix(), u.width)
        if key in seen:
            continue
        seen.add(key)
        reports.append(check_file(f, u.width, u.height, u.scale, limits, f.relative_to(root.resolve()).as_posix(), where))
    if macro_paths:
        reports.append(Report("(paths built by macros)", main.name, findings=[_macro_note(macro_paths)]))
    drawn = len(re.findall(r"\\begin\s*\{tikzpicture\}", tex)) + len(re.findall(r"\\includestandalone\b", tex))
    if drawn:
        reports.append(Report("(TikZ and pgfplots figures)", main.name, findings=[_drawn_note(drawn)]))
    name = main.relative_to(root).as_posix() if main.is_relative_to(root) else main.name
    project = {"main": name, "template": template.name, "how": how, "text_width": template.text, "column_width": template.column}
    return project, reports


def _drawn_note(n: int):  # noqa: ANN202
    from .check import Finding

    return Finding("read", "info", f"{n} figure(s) drawn by LaTeX (TikZ, pgfplots): their text is set in the paper's font; not checked")


def _missing():  # noqa: ANN202
    from .check import Finding

    return Finding("read", "error", "not found in the project")


def _macro_note(n: int):  # noqa: ANN202
    from .check import Finding

    return Finding(
        "read", "info", f"{n} \\includegraphics whose path a macro builds (\\iftoggle, \\figdir...): not followed; check those files directly"
    )


def _print(r: Report) -> None:
    print(r)


if __name__ == "__main__":
    raise SystemExit(main())
