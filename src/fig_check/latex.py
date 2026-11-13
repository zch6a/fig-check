r"""A LaTeX project's figures and the width each will print at: the venue's column and text width (from the style it
loads, or as you give them), \includegraphics's width, height and scale, \resizebox, and the line width inside figure,
figure*, wrapfigure, subfigure, subfloat and minipage."""

from __future__ import annotations

import math
import posixpath
import re
from dataclasses import dataclass, replace
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
    "ieee": Template("IEEEtran", 516 / IN, 252 / IN, "IEEEtran.cls"),
    "acm": Template("acmart sigconf", 506.295 / IN, 241.14749 / IN, "acmart.cls"),
    "lncs": Template("llncs", 347.12354 / IN, 347.12354 / IN, "llncs.cls"),
}
# classes whose widths depend on their options: (class, options it needs, name, \textwidth pt, \columnwidth pt), the
# first match wins. Each is what pdflatex printed for that class and those options (MiKTeX's IEEEtran.cls 1.8b,
# acmart.cls, llncs.cls, elsarticle.cls, revtex4-2.cls on 2026-11-13; acmart's after \maketitle, where it turns two
# columns on). IEEEtran's widths are the same for 9-12pt, letter or A4, conference, journal and technote.
CLASSES: list[tuple[str, frozenset[str], str, float, float]] = [
    (cls, frozenset(need.split()), name, text, column)
    for cls, need, name, text, column in [
        ("IEEEtran", "draftcls onecolumn", "IEEEtran, draft, one column", 469.75502, 469.75502),
        ("IEEEtran", "onecolumn", "IEEEtran, one column", 516.0, 516.0),
        ("IEEEtran", "peerreview", "IEEEtran, peer review", 516.0, 516.0),
        ("IEEEtran", "conference compsoc", "IEEEtran, Computer Society conference", 505.89, 243.91125),
        ("IEEEtran", "compsoc", "IEEEtran, Computer Society journal", 517.935, 252.94499),
        ("IEEEtran", "", "IEEEtran", 516.0, 252.0),
        ("acmart", "sigconf", "acmart sigconf", 506.295, 241.14749),
        ("acmart", "sigchi", "acmart sigchi", 506.295, 241.14749),
        ("acmart", "sigplan", "acmart sigplan", 505.89, 240.94499),
        ("acmart", "acmtog", "acmart acmtog", 510.295, 243.14749),
        ("acmart", "acmsmall", "acmart acmsmall", 395.8225, 395.8225),
        ("acmart", "acmlarge", "acmart acmlarge", 452.295, 452.295),
        ("acmart", "", "acmart manuscript", 430.00462, 430.00462),
        ("llncs", "", "llncs (Springer LNCS)", 347.12354, 347.12354),
        ("elsarticle", "5p", "elsarticle 5p", 522.0, 252.0),
        ("elsarticle", "3p twocolumn", "elsarticle 3p, two columns", 468.0, 222.0),
        ("elsarticle", "3p", "elsarticle 3p", 468.0, 468.0),
        ("elsarticle", "1p", "elsarticle 1p", 384.0, 384.0),
        ("elsarticle", "", "elsarticle preprint", 345.0, 345.0),
        ("revtex4-2", "preprint", "revtex4-2 preprint", 468.0, 468.0),
        ("revtex4-2", "twocolumn", "revtex4-2, two columns", 510.0, 246.0),
        ("revtex4-2", "reprint", "revtex4-2 reprint", 510.0, 246.0),
        ("revtex4-2", "", "revtex4-2", 510.0, 510.0),
    ]
]
# acmart formats not measured: their widths are not guessed
ACM_FORMATS = {"manuscript", "acmsmall", "acmlarge", "acmtog", "sigconf", "sigchi", "sigplan"}


def class_template(name: str, options: list[str]) -> Template | None:
    r"""The widths a known class sets for these options, or None.

    >>> class_template("IEEEtran", ["conference"]).column * IN, class_template("acmart", ["sigconf", "review"]).name
    (252.0, 'acmart sigconf')
    >>> class_template("acmart", ["acmengage"]) is None, class_template("memoir", []) is None
    (True, True)
    """
    opts = set(options)
    if name == "acmart" and any(o.startswith(("acm", "sig")) and o not in ACM_FORMATS for o in opts):
        return None
    for cls, need, label, text, column in CLASSES:
        if cls == name and need <= opts:
            return Template(label, text / IN, column / IN, f"{cls}.cls")
    return None


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


# paper widths and heights in inches: article.cls's paper options, and the same names in geometry
PAPERS = {
    "letterpaper": (8.5, 11.0),
    "a4paper": (210 / 25.4, 297 / 25.4),
    "a5paper": (148 / 25.4, 210 / 25.4),
    "b5paper": (176 / 25.4, 250 / 25.4),
    "legalpaper": (8.5, 14.0),
    "executivepaper": (7.25, 10.5),
}
# article.cls and report.cls (size10.clo, size11.clo, size12.clo, read on 2026-11-13): \textwidth is the smaller of
# \paperwidth - 2in and 345pt, 360pt, 390pt (twice that with twocolumn), rounded down to whole points; \columnsep 10pt
CLASS_WIDTH = {"10pt": 345.0, "11pt": 360.0, "12pt": 390.0}
ARTICLE_COLUMNSEP = 10 / IN
KNOWN_CLASSES = ("article", "report")
_NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)"


def length(expr: str, paper: float, text: float, column: float) -> float | None:
    r"""A length in a preamble, in inches: `6.5in`, `5.5 true in`, `-2cm`, `0.8\paperwidth`, `\textwidth`.

    >>> length("5.5 true in", 8.5, 5, 5), length("0.5\\paperwidth", 8.5, 5, 5), length("-72.27pt", 8.5, 5, 5)
    (5.5, 4.25, -1.0)
    """
    e = re.sub(r"\s+|true", "", expr)
    m = re.fullmatch(rf"({_NUMBER})?\\(paperwidth|textwidth|columnwidth|linewidth|hsize)", e)
    if m:
        base = {"paperwidth": paper, "textwidth": text, "hsize": text}.get(m.group(2), column)
        return (float(m.group(1)) if m.group(1) not in (None, "+", "-") else -1.0 if m.group(1) == "-" else 1.0) * base
    m = re.fullmatch(rf"({_NUMBER})(in|cm|mm|pt|bp|pc)", e)
    return float(m.group(1)) * UNITS_IN[m.group(2)] if m else None


def _options(text: str) -> list[tuple[str, str]]:
    """key=value options split at top-level commas: `margin=1in, text={6in,9in}, a4paper`."""
    out, depth, cur = [], 0, ""
    for c in text + ",":
        if c == "," and depth == 0:
            k, _, v = cur.partition("=")
            if k.strip():
                out.append((k.strip(), v.strip()))
            cur = ""
            continue
        depth += (c == "{") - (c == "}")
        cur += c
    return out


def _first(value: str) -> str:
    """The first of `{a,b}` (geometry's width,height pairs), or the value."""
    v = value.strip()
    if v.startswith("{") and v.endswith("}"):
        v = v[1:-1]
    return v.split(",")[0].strip()


def _pair(value: str) -> tuple[str, str]:
    """`{a,b}` as (a, b); a single value for both."""
    v = value.strip()
    if v.startswith("{") and v.endswith("}"):
        v = v[1:-1]
    parts = [x.strip() for x in v.split(",")]
    return (parts[0], parts[1] if len(parts) > 1 else parts[0])


def layout(tex: str, template: Template | None = None) -> tuple[Template, str]:
    r"""The widths the paper is set at, and how they were found: the template given, or the style the preamble loads, or
    LaTeX's article/report widths for the class options; then the preamble's own settings, in order: geometry's options
    (\usepackage[...]{geometry}, \geometry{...}), \setlength, \addtolength or an assignment of \textwidth and
    \columnsep.

    >>> t, how = layout(r"\documentclass[11pt,twocolumn]{article}")
    >>> t.name, round(t.text * IN), round(t.column * IN, 1), how
    ('article, 11pt letter, two columns', 469, 229.5, 'from the class options')
    >>> t, how = layout(r"\documentclass{article}\usepackage[margin=1in]{geometry}")
    >>> round(t.text, 2), how
    (6.5, 'from the class options; the preamble sets: geometry margin=1in')
    >>> t, how = layout(r"\documentclass{article}\usepackage{icml2025}\setlength{\textwidth}{7in}")
    >>> t.name, round(t.text, 2), round(t.column, 3)
    ('ICML', 7.0, 3.375)
    """
    pre = tex.split("\\begin{document}")[0]
    cls = re.search(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}", pre)
    class_options = [k for k, _ in _options(cls.group(1) or "")] if cls else []
    class_name = cls.group(2).strip() if cls else "article"
    paper = PAPERS["letterpaper"]
    for o in class_options:
        if o in PAPERS:
            paper = PAPERS[o]
    landscape = "landscape" in class_options
    paper_w = paper[landscape]
    how: list[str] = []
    if template is not None:
        how.append("given")
    else:
        template = detect(tex)
        known = class_template(class_name, class_options)
        if template is not TEMPLATES["article"]:
            how.append("detected")
        elif known is not None:
            template = known
            how.append("from the class")
        else:
            size = next((o for o in class_options if o in CLASS_WIDTH), "10pt")
            paper_name = next((o for o in class_options if o in PAPERS), "letterpaper")
            two = "twocolumn" in class_options
            width = min(paper_w * IN - 2 * IN, CLASS_WIDTH[size] * (2 if two else 1))
            text = math.floor(width + 1e-9) / IN
            if (size, paper_name, two, landscape) != ("10pt", "letterpaper", False, False):
                template = Template(
                    f"article, {size} {paper_name.removesuffix('paper')}{' landscape' if landscape else ''}{', two columns' if two else ''}",
                    text,
                    (text - ARTICLE_COLUMNSEP) / 2 if two else text,
                    "article.cls, size1x.clo",
                )
            how.append("from the class options")
            if class_name not in KNOWN_CLASSES:
                how[-1] = f"the class {class_name} (with these options) is not one fig-check knows: LaTeX's article widths, give --template if wrong"
    two_column = template.column < template.text - 1e-6
    sep = template.text - 2 * template.column if two_column else ARTICLE_COLUMNSEP
    text = template.text
    set_by: list[str] = []
    geo: dict[str, str] = {}  # geometry's options so far: each \geometry adds to them
    events: list[tuple[int, str, str, str]] = []
    for m in re.finditer(r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{([^{}]*)\}", pre):
        if "geometry" in [x.strip() for x in m.group(2).split(",")]:  # it sets the layout when loaded, options or not
            events.append((m.start(), "geometry", m.group(1) or "", ""))
    for m in re.finditer(r"\\geometry\s*\{", pre):
        body, _ = _braced(pre, m.end() - 1)
        events.append((m.start(), "geometry", body, ""))
    for m in re.finditer(r"\\(setlength|addtolength)\s*\{?\s*\\(textwidth|columnsep)\s*\}?\s*\{([^{}]*)\}", pre):
        events.append((m.start(), m.group(1), m.group(2), m.group(3)))
    for m in re.finditer(rf"\\(textwidth|columnsep)(?![A-Za-z])\s*=?\s*((?:{_NUMBER})\s*(?:true\s*)?(?:in|cm|mm|pt|bp|pc)(?![A-Za-z]))", pre):
        events.append((m.start(), "setlength", m.group(1), m.group(2)))
    for _, kind, what, value in sorted(events):
        column = (text - sep) / 2 if two_column else text
        if kind == "geometry":
            opts = _options(what)
            keys = dict(opts)
            if "pass" in keys:  # geometry keeps the class's layout
                continue
            for k, v in opts:
                if k in PAPERS or (k == "paper" and v in PAPERS):
                    paper = PAPERS[k if k in PAPERS else v]
                elif k == "landscape":
                    landscape = v in ("", "true")
                elif k == "portrait":
                    landscape = v not in ("", "true")
                elif k == "paperwidth":
                    paper = (length(v, paper_w, text, column) or paper[0], paper[1])
                elif k in ("papersize", "layoutsize"):
                    w, h = _pair(v)
                    paper = (length(w, paper_w, text, column) or paper[0], length(h, paper_w, text, column) or paper[1])
            paper_w = paper[landscape]
            if "twocolumn" in keys:
                two_column = keys["twocolumn"] in ("", "true")
            if "onecolumn" in keys:
                two_column = keys["onecolumn"] not in ("", "true")
            if "columnsep" in keys:
                sep = length(keys["columnsep"], paper_w, text, column) or sep
            for k, v in opts:
                if k == "margin":
                    geo["left"] = geo["right"] = _first(v)
                elif k == "hmargin":
                    geo["left"], geo["right"] = _pair(v)
                elif k in ("left", "lmargin", "inner"):
                    geo["left"] = v
                elif k in ("right", "rmargin", "outer"):
                    geo["right"] = v
                elif k in ("width", "textwidth", "text", "total", "body"):
                    geo["body"] = _first(v)
                elif k in ("hscale", "scale") and re.fullmatch(_NUMBER, _first(v)):
                    geo["body"] = _first(v) + "\\paperwidth"
                elif k == "reset":
                    geo.clear()
            given = length(geo["body"], paper_w, text, column) if "body" in geo else None
            lw = length(geo["left"], paper_w, text, column) if "left" in geo else None
            rw = length(geo["right"], paper_w, text, column) if "right" in geo else None
            if given is not None:
                text = given
            elif lw is not None or rw is not None:
                # one margin alone: the other is the first share of the margins around geometry's default body (0.7
                # of the paper's width), split 1:1, or 2:3 with twoside (as pdflatex lays it out)
                other = 0.3 * paper_w * (2 / 5 if "twoside" in class_options or "twoside" in keys else 1 / 2)
                text = paper_w - (lw if lw is not None else other) - (rw if rw is not None else other)
            else:  # geometry's default body
                text = 0.7 * paper_w
            set_by.append("geometry " + ", ".join(f"{k}={v}" if v else k for k, v in opts) if opts else "geometry (its defaults)")
        else:
            amount = length(value, paper_w, text, column)
            if amount is None:
                continue
            if what == "textwidth":
                text = text + amount if kind == "addtolength" else amount
            else:
                sep = sep + amount if kind == "addtolength" else amount
            set_by.append(f"\\{kind}{{\\{what}}}{{{value.strip()}}}")
    if set_by:
        how.append("the preamble sets: " + "; ".join(set_by))
        template = replace(template, text=text, column=(text - sep) / 2 if two_column else text)
    return template, "; ".join(how)


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
