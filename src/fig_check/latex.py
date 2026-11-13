r"""A LaTeX project's figures and the width each will print at: the venue's column and text width (from the style it
loads, or as you give them), \includegraphics's width, height and scale, \resizebox, and the line width inside figure,
figure*, wrapfigure, subfigure, subfloat and minipage."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

IN = 72.27  # TeX points per inch (pt); PDF points are bp, 72 per inch
UNITS_IN = {"in": 1.0, "cm": 1 / 2.54, "mm": 1 / 25.4, "pt": 1 / 72.27, "bp": 1 / 72, "pc": 12 / 72.27, "em": 10 / 72.27, "ex": 4.3 / 72.27}


@dataclass(frozen=True)
class Template:
    name: str
    text: float  # \textwidth, inches
    column: float  # \columnwidth, inches (the text width for one-column styles)
    source: str


# column and text widths as each style file sets them (read from the files on 2026-11-13):
# neurips_2020.sty: textwidth=5.5in; iclr2025_conference.sty: \textwidth 5.5 true in;
# icml2025.sty: \textwidth 6.75in, \columnsep 0.25in; cvpr.sty and iccv.sty (cvpr-org/author-kit): \textwidth 6.875in,
# \columnsep 0.3125in; acl.sty (acl-org/acl-style-files): a4paper, margin=2.5cm, \columnsep 0.6cm;
# aaai25.sty: \textwidth 7.0in, \columnsep 0.375in; article.cls with size10.clo on letter paper: \textwidth 345pt
TEMPLATES = {
    "neurips": Template("NeurIPS", 5.5, 5.5, "neurips_20xx.sty"),
    "iclr": Template("ICLR", 5.5, 5.5, "iclr20xx_conference.sty"),
    "icml": Template("ICML", 6.75, (6.75 - 0.25) / 2, "icml20xx.sty"),
    "cvpr": Template("CVPR/ICCV", 6.875, (6.875 - 0.3125) / 2, "cvpr.sty, iccv.sty"),
    "acl": Template("ACL/EMNLP/NAACL", 16 / 2.54, (16 - 0.6) / 2 / 2.54, "acl.sty"),
    "aaai": Template("AAAI", 7.0, (7.0 - 0.375) / 2, "aaai2x.sty"),
    "article": Template("article, 10pt letter (LaTeX's default)", 345 / IN, 345 / IN, "article.cls, size10.clo"),
}
# a style file's name, among the packages \usepackage loads (one or a list: \usepackage{iccv, times})
DETECT = [
    (r"neurips_\d{4}", "neurips"),
    (r"iclr\d{4}_conference", "iclr"),
    (r"icml\d{4}", "icml"),
    (r"cvpr|iccv|wacv", "cvpr"),
    (r"acl|acl\d{4}|emnlp\d{4}|naacl\d{4}", "acl"),
    (r"aaai\d{2}", "aaai"),
]


def detect(tex: str) -> Template:
    r"""The template the preamble loads, or LaTeX's default article.

    >>> detect(r"\documentclass{article}\usepackage[final]{neurips_2024}").name
    'NeurIPS'
    >>> detect(r"\documentclass[twocolumn]{article}").name
    "article, 10pt letter (LaTeX's default)"
    >>> detect(r"\usepackage{iccv, times, epsfig}").name
    'CVPR/ICCV'
    """
    packages = [p.strip() for m in re.finditer(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^{}]*)\}", tex) for p in m.group(1).split(",")]
    for pattern, key in DETECT:
        if any(re.fullmatch(pattern, p) for p in packages):
            return TEMPLATES[key]
    return TEMPLATES["article"]


@dataclass
class Use:
    path: str  # as \includegraphics names it
    line: int
    width: float | None  # inches it prints at; None: its natural size (or decided by height/scale, below)
    height: float | None = None  # inches, when only the height is given
    scale: float | None = None
    where: str = ""  # figure, figure*, subfigure...


def dimension(expr: str, line: float, template: Template) -> float | None:
    r"""A TeX dimension in inches: `3.25in`, `0.48\linewidth`, `.9\textwidth`, `\columnwidth`, `8cm`.

    >>> t = TEMPLATES["icml"]
    >>> dimension("0.5\\linewidth", 3.25, t), dimension("\\textwidth", 3.25, t), dimension("72.27pt", 3.25, t)
    (1.625, 6.75, 1.0)
    """
    e = expr.strip().replace(" ", "")
    m = re.fullmatch(r"([+-]?(?:\d+\.?\d*|\.\d+))?\\(linewidth|columnwidth|textwidth|hsize|paperwidth)", e)
    if m:
        factor = float(m.group(1)) if m.group(1) else 1.0
        base = {"linewidth": line, "hsize": line, "columnwidth": template.column, "textwidth": template.text, "paperwidth": 8.5}[m.group(2)]
        return factor * base
    m = re.fullmatch(r"([+-]?(?:\d+\.?\d*|\.\d+))(in|cm|mm|pt|bp|pc|em|ex)", e)
    if m:
        return float(m.group(1)) * UNITS_IN[m.group(2)]
    return None


def _braced(tex: str, start: int) -> tuple[str, int]:
    depth, i = 0, start
    while i < len(tex):
        c = tex[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return tex[start + 1 : i], i + 1
        i += 1
    return tex[start + 1 :], len(tex)


def strip_comments(tex: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", tex)


def expand(path: Path, root: Path, depth: int = 0, seen: set[Path] | None = None) -> str:
    r"""The file with its \input and \include files in place (each once), comments stripped; line breaks kept."""
    seen = set() if seen is None else seen
    seen.add(path.resolve())
    try:
        tex = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""

    def inline(m: re.Match[str]) -> str:
        name = m.group(1).strip()
        for c in (root / name, root / (name + ".tex"), path.parent / name, path.parent / (name + ".tex")):
            if c.is_file() and c.resolve() not in seen and depth < 8 and c.resolve().is_relative_to(root.resolve()):
                return expand(c, root, depth + 1, seen)
        return ""

    return re.sub(r"\\(?:input|include|subfile)\s*\{([^{}]+)\}", inline, tex)


ENVS = ("figure*", "figure", "wrapfigure", "subfigure", "minipage", "table*", "table")


def uses(tex: str, template: Template) -> list[Use]:
    r"""Every \includegraphics with the width it prints at, in order.

    >>> t = TEMPLATES["icml"]
    >>> [(u.path, round(u.width, 3), u.where) for u in uses(r"\begin{figure*}\includegraphics[width=0.5\linewidth]{a}\end{figure*}"
    ...     r"\begin{figure}\begin{subfigure}{0.48\linewidth}\includegraphics[width=\linewidth]{b}\end{subfigure}\end{figure}", t)]
    [('a', 3.375, 'figure*'), ('b', 1.56, 'subfigure')]
    """
    out: list[Use] = []
    stack: list[tuple[str, float]] = [("body", template.text)]
    token = re.compile(r"\\begin\{(" + "|".join(re.escape(e) for e in ENVS) + r")\}|\\end\{(" + "|".join(re.escape(e) for e in ENVS) + r")\}"
                       r"|\\includegraphics\*?|\\resizebox\*?|\\subfloat")  # fmt: skip
    pending_width: float | None = None
    pending_until = -1
    pos = 0
    while True:
        m = token.search(tex, pos)
        if not m:
            break
        pos = m.end()
        line = stack[-1][1]
        if m.group(1):
            env = m.group(1)
            if env == "figure*" or env == "table*":
                width = template.text
            elif env in ("figure", "table"):
                width = template.column
            else:  # wrapfigure{r}{w}, subfigure{w}, minipage[pos]{w}
                rest = tex[pos:]
                args = re.match(r"\s*(?:\[[^\]]*\]\s*)*(?:\{[^{}]*\}\s*)?" if env == "wrapfigure" else r"\s*(?:\[[^\]]*\]\s*)*", rest)
                start = pos + (args.end() if args else 0)
                width = line
                if start < len(tex) and tex[start] == "{":
                    arg, _ = _braced(tex, start)
                    width = dimension(arg, line, template) or line
            stack.append((env, width))
        elif m.group(2):
            if len(stack) > 1 and stack[-1][0] == m.group(2):
                stack.pop()
        elif m.group(0).startswith("\\resizebox"):
            if pos < len(tex) and tex[pos:].lstrip().startswith("{"):
                start = tex.index("{", pos)
                arg, end = _braced(tex, start)
                pending_width = dimension(arg, line, template)
                pending_until = end + 400
        elif m.group(0) == "\\subfloat":
            pass  # its graphics take the surrounding line width, or their own width option
        else:
            opts = ""
            head = re.match(r"\s*(\[([^\]]*)\])?\s*\{", tex[pos:])
            if not head:
                continue
            opts = head.group(2) or ""
            path, end = _braced(tex, pos + head.end() - 1)
            kv = dict((k.strip(), v.strip()) for k, _, v in (p.partition("=") for p in opts.split(",")) if k.strip())
            given = dimension(kv["width"], line, template) if "width" in kv else None
            height = dimension(kv["height"], line, template) if "height" in kv and "width" not in kv else None
            scale = float(kv["scale"]) if re.fullmatch(r"\d*\.?\d+", kv.get("scale", "")) else None
            if given is None and pending_width is not None and m.start() <= pending_until:
                given = pending_width
            pending_width = None
            out.append(Use(path.strip(), tex.count("\n", 0, m.start()) + 1, given, height, scale, stack[-1][0]))
            pos = end
    return out


def graphicspath(tex: str) -> list[str]:
    m = re.search(r"\\graphicspath\s*\{((?:\{[^{}]*\}\s*)*)\}", tex)
    return [p for p in re.findall(r"\{([^{}]*)\}", m.group(1))] if m else []


EXTENSIONS = ["", ".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"]


def find(path: str, root: Path, main: Path, dirs: list[str]) -> Path | None:
    """The file an \\includegraphics path names (pdfLaTeX's extension order, inside the project only)."""
    base = main.parent
    for d in ["", *dirs]:
        for ext in EXTENSIONS:
            c = (base / d / (path + ext)).resolve()
            if c.is_file() and c.is_relative_to(root.resolve()):
                return c
    return None


def main_file(root: Path) -> Path | None:
    r"""The project's main file: a .tex with \documentclass and \begin{document} (main.tex, paper.tex, ms.tex first)."""
    found = []
    for p in sorted(root.rglob("*.tex")):
        try:
            head = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if re.search(r"(?m)^[^%\n]*\\documentclass", head) and "\\begin{document}" in head:
            found.append(p)
    found.sort(key=lambda p: (p.name.lower() not in ("main.tex", "paper.tex", "ms.tex"), len(p.relative_to(root).parts)))
    return found[0] if found else None


def posix(p: str) -> str:
    return posixpath.normpath(p.replace("\\", "/"))
