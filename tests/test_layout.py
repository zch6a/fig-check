"""The widths a preamble sets, against pdflatex's own: each row's \\textwidth and \\columnwidth (TeX points) are what
pdflatex printed for that preamble (MiKTeX, article.cls and geometry.sty as of 2026-11-13). The rows are fixed here, so
the tests need no TeX."""

from __future__ import annotations

import pytest

from fig_check.cli import main
from fig_check.latex import IN, TEMPLATES, layout

LATEX = [
    (r"\documentclass{article}", 345.00, 345.00),
    (r"\documentclass[11pt]{article}", 360.00, 360.00),
    (r"\documentclass[12pt,a4paper]{article}", 390.00, 390.00),
    (r"\documentclass[twocolumn]{article}", 469.00, 229.50),
    (r"\documentclass[11pt,twocolumn]{article}", 469.00, 229.50),
    (r"\documentclass[a4paper,twocolumn]{article}", 452.00, 221.00),
    (r"\documentclass[10pt]{report}", 345.00, 345.00),
    (r"\documentclass{article}\usepackage[margin=1in]{geometry}", 469.76, 469.76),
    (r"\documentclass{article}\usepackage{geometry}", 430.00, 430.00),
    (r"\documentclass[a4paper]{article}\usepackage[margin=2cm]{geometry}", 483.70, 483.70),
    (r"\documentclass{article}\usepackage[a4paper,left=3cm,right=2cm]{geometry}", 455.24, 455.24),
    (r"\documentclass{article}\usepackage[hmargin={1in,1.5in}]{geometry}", 433.62, 433.62),
    (r"\documentclass{article}\usepackage[textwidth=15cm]{geometry}", 426.79, 426.79),
    (r"\documentclass{article}\usepackage[text={6in,9in}]{geometry}", 433.62, 433.62),
    (r"\documentclass{article}\usepackage[left=1in]{geometry}", 449.88, 449.88),
    (r"\documentclass{article}\usepackage[margin=1in]{geometry}\geometry{left=2in}", 397.49, 397.49),
    (r"\documentclass{article}\usepackage[scale=0.8]{geometry}", 491.44, 491.44),
    (r"\documentclass{article}\usepackage[landscape,margin=1in]{geometry}", 650.43, 650.43),
    (r"\documentclass[twocolumn]{article}\usepackage[margin=0.75in,columnsep=0.25in]{geometry}", 505.89, 243.91),
    (r"\documentclass{article}\usepackage{amsmath,geometry}\geometry{margin=1.25in}", 433.62, 433.62),
    (r"\documentclass{article}\setlength{\textwidth}{6.5in}", 469.75, 469.75),
    (r"\documentclass{article}\addtolength{\textwidth}{2cm}", 401.91, 401.91),
    (r"\documentclass{article}\textwidth=16cm", 455.24, 455.24),
    (r"\documentclass{article}\setlength\textwidth{5in}", 361.35, 361.35),
    (r"\documentclass[twocolumn]{article}\setlength{\columnsep}{0.3in}", 469.00, 223.66),
    (r"\documentclass[twocolumn]{article}\usepackage[margin=1in]{geometry}", 469.76, 229.88),
    (r"\documentclass{article}\usepackage[right=2in]{geometry}", 377.61, 377.61),
    (r"\documentclass[twoside]{article}\usepackage[inner=1in]{geometry}", 468.31, 468.31),
    (r"\documentclass[landscape]{article}", 345.00, 345.00),
    (r"\documentclass[twoside]{article}\usepackage[outer=2in]{geometry}", 396.04, 396.04),
    (r"\documentclass[a4paper]{article}\usepackage[landscape]{geometry}", 591.53, 591.53),
    (r"\documentclass{article}\usepackage[papersize={6in,9in},margin=0.5in]{geometry}", 361.35, 361.35),
    (r"\documentclass{article}\usepackage[paperwidth=7in,paperheight=10in]{geometry}", 354.12, 354.12),
]


# what pdflatex printed for these classes and options (acmart's after \maketitle, where its columns begin)
CLASSES = [
    ("IEEEtran", "", 516.0, 252.0),
    ("IEEEtran", "conference,a4paper", 516.0, 252.0),
    ("IEEEtran", "journal", 516.0, 252.0),
    ("IEEEtran", "onecolumn", 516.0, 516.0),
    ("IEEEtran", "draftcls,onecolumn", 469.75502, 469.75502),
    ("IEEEtran", "10pt,journal,compsoc", 517.935, 252.94499),
    ("IEEEtran", "conference,compsoc", 505.89, 243.91125),
    ("IEEEtran", "peerreview", 516.0, 516.0),
    ("acmart", "", 430.00462, 430.00462),
    ("acmart", "sigconf", 506.295, 241.14749),
    ("acmart", "sigconf,review", 506.295, 241.14749),
    ("acmart", "acmsmall", 395.8225, 395.8225),
    ("acmart", "acmlarge", 452.295, 452.295),
    ("acmart", "acmtog", 510.295, 243.14749),
    ("acmart", "sigplan", 505.89, 240.94499),
    ("llncs", "", 347.12354, 347.12354),
    ("elsarticle", "preprint", 345.0, 345.0),
    ("elsarticle", "1p", 384.0, 384.0),
    ("elsarticle", "3p", 468.0, 468.0),
    ("elsarticle", "3p,twocolumn", 468.0, 222.0),
    ("elsarticle", "5p", 522.0, 252.0),
    ("revtex4-2", "", 510.0, 510.0),
    ("revtex4-2", "aps,prl,twocolumn", 510.0, 246.0),
    ("revtex4-2", "aps,pra,reprint", 510.0, 246.0),
    ("revtex4-2", "aps,preprint", 468.0, 468.0),
]


@pytest.mark.parametrize(("cls", "options", "textwidth", "columnwidth"), CLASSES)
def test_a_class_s_widths_are_pdflatexs(cls: str, options: str, textwidth: float, columnwidth: float) -> None:
    t, how = layout(f"\\documentclass[{options}]{{{cls}}}\\begin{{document}}")
    assert (t.text * IN, t.column * IN, how) == (pytest.approx(textwidth, abs=0.01), pytest.approx(columnwidth, abs=0.01), "from the class")


def test_geometry_applies_over_a_class() -> None:
    t, how = layout(r"\documentclass[conference]{IEEEtran}\usepackage[margin=0.75in]{geometry}")
    assert round(t.text, 3) == 7.0 and round(t.column * IN, 2) == round((7 * IN - (516 - 2 * 252)) / 2, 2)
    assert how == "from the class; the preamble sets: geometry margin=0.75in"


@pytest.mark.parametrize(("preamble", "textwidth", "columnwidth"), LATEX)
def test_the_widths_are_pdflatexs(preamble: str, textwidth: float, columnwidth: float) -> None:
    t, _ = layout(preamble + "\\begin{document}")
    assert t.text * IN == pytest.approx(textwidth, abs=0.02)
    assert t.column * IN == pytest.approx(columnwidth, abs=0.02)


def test_a_style_s_widths_give_way_to_the_preamble_s() -> None:
    t, how = layout(r"\documentclass{article}\usepackage{icml2025}\setlength{\columnsep}{0.5in}")
    assert (t.name, t.text, t.column) == ("ICML", 6.75, 3.125)
    assert how == r"detected; the preamble sets: \setlength{\columnsep}{0.5in}"
    t, how = layout(r"\usepackage{neurips_2025}", TEMPLATES["acl"])
    assert (t, how) == (TEMPLATES["acl"], "given")


def test_settings_after_begin_document_and_in_macros_are_not_the_preamble_s() -> None:
    t, how = layout(r"\documentclass{article}\newcommand{\fw}{\includegraphics[width=\textwidth]{a}}\begin{document}\textwidth=2in")
    assert (t, how) == (TEMPLATES["article"], "from the class options")


def test_geometry_s_pass_option_keeps_the_class_s_layout() -> None:
    t, how = layout(r"\documentclass{article}\usepackage[pass]{geometry}")
    assert (t, how) == (TEMPLATES["article"], "from the class options")


def test_an_unknown_class_says_so() -> None:
    t, how = layout(r"\documentclass{memoir}")
    assert t == TEMPLATES["article"]
    assert "memoir (with these options) is not one fig-check knows" in how and "--template" in how
    t, how = layout(r"\documentclass[acmengage]{acmart}")
    assert t == TEMPLATES["article"] and "acmart" in how


def test_the_header_names_what_set_the_widths(tmp_path, capsys) -> None:  # noqa: ANN001
    (tmp_path / "main.tex").write_text(
        "\\documentclass[twocolumn]{article}\n\\usepackage[margin=0.75in]{geometry}\n\\begin{document}\nx\n\\end{document}\n", encoding="utf-8"
    )
    assert main([str(tmp_path)]) == 0
    first = capsys.readouterr().out.splitlines()[0]
    assert first == ("fig-check: main.tex: article, 10pt letter, two columns (from the class options; the preamble sets: geometry margin=0.75in): "
                     "text 7.00 in, column 3.43 in")  # fmt: skip
