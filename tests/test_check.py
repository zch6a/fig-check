from __future__ import annotations

import json
from pathlib import Path

import pytest
from make import jpeg_header, pdf, png

from fig_check import cli
from fig_check.check import Limits, check_file
from fig_check.latex import TEMPLATES, detect, uses

FONT = b"/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >>"
RED_GREEN = b"0.84 0.15 0.16 RG 0 0 m 10 10 l S 0.17 0.63 0.17 RG 0 10 m 10 0 l S"


def write(tmp: Path, name: str, data: bytes | str) -> Path:
    p = tmp / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data.encode() if isinstance(data, str) else data)
    return p


def test_text_is_measured_at_the_printed_size(tmp_path: Path) -> None:
    f = write(tmp_path, "plot.pdf", pdf(b"BT /F1 10 Tf (a) Tj ET", width=432, height=288, resources=FONT))  # 6 in wide, 10 pt text
    at_size = check_file(f)
    assert at_size.smallest == 10 and at_size.worst == "ok"
    shrunk = check_file(f, width=3.25)  # in a 3.25 in column: 54% of its size, 5.4 pt
    assert shrunk.smallest is not None and round(shrunk.smallest, 1) == 5.4
    assert shrunk.findings[0].rule == "font" and shrunk.findings[0].severity == "warning"
    assert "10.0 pt in the file: printed at 54% of its size" in shrunk.findings[0].message
    assert check_file(f, width=2).findings[0].severity == "error"  # 3.3 pt


def test_raster_resolution_at_the_printed_size(tmp_path: Path) -> None:
    f = write(tmp_path, "photo.png", png(600, 300))  # no resolution stated: pdfLaTeX's 72 dpi, 8.33 in
    assert check_file(f, width=2.0).worst == "ok"  # 300 pixels per inch
    low = check_file(f, width=6.0)
    assert low.worst == "error" and "100 pixels per inch" in low.findings[0].message
    assert check_file(write(tmp_path, "scan.jpg", jpeg_header(1000, 500)), width=4.0).worst == "warning"  # 250 per inch


def test_images_inside_a_pdf_are_checked_too(tmp_path: Path) -> None:
    image = b"<< /Type /XObject /Subtype /Image /Width 200 /Height 100 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 0 >>\nstream\n\nendstream"
    f = write(
        tmp_path,
        "mixed.pdf",
        pdf(b"q 288 0 0 144 0 0 cm /Im Do Q", width=288, height=144, objects={10: image}, resources=b"/XObject << /Im 10 0 R >>"),
    )
    r = check_file(f, width=4.0)  # a 200-pixel image 4 in wide: 50 per inch
    assert r.worst == "error" and "embedded 200×100 image" in r.findings[0].message
    two = write(tmp_path, "two.pdf", pdf(b"q 288 0 0 144 0 0 cm /Im Do Q q 144 0 0 72 0 0 cm /Im Do Q", width=288, height=144, objects={10: image},
                                         resources=b"/XObject << /Im 10 0 R >>"))  # fmt: skip
    found = [f for f in check_file(two, width=4.0).findings if f.rule == "resolution"]
    assert len(found) == 1 and found[0].message.startswith("2 embedded images under 300 pixels per inch; the lowest")


def test_colours_that_collapse_with_colour_vision_deficiency(tmp_path: Path) -> None:
    clash = check_file(write(tmp_path, "rg.pdf", pdf(RED_GREEN)))
    colour = [f for f in clash.findings if f.rule == "colour"]
    assert clash.worst == "warning" and len(colour) == 1 and "deuteranopia" in colour[0].message
    safe = check_file(write(tmp_path, "ob.pdf", pdf(b"0.0 0.45 0.70 RG 0 0 m 10 10 l S 0.90 0.62 0.0 RG 0 10 m 10 0 l S")))  # blue and orange
    assert safe.worst == "ok"
    many = b"".join(b"%.3f %.3f 0.5 RG 0 0 m 1 1 l S " % (i / 40, 1 - i / 40) for i in range(40))
    cmap = check_file(write(tmp_path, "map.pdf", pdf(many)))
    assert cmap.worst == "ok" and any("colour map" in f.message for f in cmap.findings)


def test_unreadable_files_are_an_error_not_a_crash(tmp_path: Path) -> None:
    assert check_file(write(tmp_path, "bad.pdf", b"%PDF-1.4 garbage")).worst == "error"
    assert check_file(tmp_path / "missing.pdf").worst == "error"
    assert check_file(write(tmp_path, "f.eps", b"%!PS-Adobe-3.0 EPSF")).findings[0].severity == "info"


def test_limits_can_be_changed(tmp_path: Path) -> None:
    f = write(tmp_path, "plot.pdf", pdf(b"BT /F1 6 Tf (a) Tj ET", resources=FONT))
    assert check_file(f).worst == "warning"
    assert check_file(f, limits=Limits(font=5.5, font_error=4)).worst == "ok"


def test_templates_and_widths() -> None:
    assert detect(r"\usepackage{icml2025}").name == "ICML" and detect(r"\usepackage[review]{cvpr}").name == "CVPR/ICCV"
    t = TEMPLATES["acl"]
    us = uses(
        r"""\begin{figure}\centering\includegraphics[width=\columnwidth]{a}\end{figure}
\begin{figure*}\resizebox{\textwidth}{!}{\includegraphics{b}}\end{figure*}
\begin{figure}\includegraphics[scale=0.5]{c}\includegraphics[height=2cm]{d}\includegraphics{e}\end{figure}
\begin{wrapfigure}{r}{0.4\textwidth}\includegraphics[width=\linewidth]{f}\end{wrapfigure}""",
        t,
    )
    got = {u.path: (round(u.width, 3) if u.width else None, u.scale, round(u.height, 3) if u.height else None, u.where) for u in us}
    assert got == {"a": (round(t.column, 3), None, None, "figure"), "b": (round(t.text, 3), None, None, "figure*"), "c": (None, 0.5, None, "figure"),
                   "d": (None, None, round(2 / 2.54, 3), "figure"), "e": (None, None, None, "figure"),
                   "f": (round(0.4 * t.text, 3), None, None, "wrapfigure")}  # fmt: skip


def project(tmp: Path) -> Path:
    write(
        tmp,
        "paper/main.tex",
        r"""\documentclass{article}
\usepackage{icml2025}
\graphicspath{{figs/}}
\begin{document}
\input{sections/results}
\end{document}
""",
    )
    write(
        tmp,
        "paper/sections/results.tex",
        r"""% \includegraphics{commented-out}
\begin{figure}
\includegraphics[width=\linewidth]{loss}
\end{figure}
\begin{figure*}
\includegraphics[width=0.5\linewidth]{photo}
\includegraphics{missing}
\includegraphics{\iftoggle{hq}{figs/hq}{figs/small}}
\end{figure*}
\newcommand{\grid}[1]{\includegraphics{figs/grid_#1.png}}
""",
    )
    write(tmp, "paper/figs/loss.pdf", pdf(b"BT /F1 10 Tf (a) Tj ET " + RED_GREEN, width=432, height=288, resources=FONT))
    write(tmp, "paper/figs/photo.png", png(1200, 800, dpi=300))
    return tmp / "paper"


def test_a_whole_project(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([str(project(tmp_path))]) == 1
    out = capsys.readouterr().out
    assert "ICML (detected): text 6.75 in, column 3.25 in" in out
    assert "figs/loss.pdf  (main.tex:" in out and "smallest text 5.4 pt" in out and "deuteranopia" in out
    assert "figs/photo.png" in out and "missing  (main.tex:" in out and "not found in the project" in out
    assert "commented-out" not in out and "grid_#1" not in out
    assert "1 \\includegraphics whose path a macro builds" in out


def test_json_and_a_figure_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = write(tmp_path, "plot.pdf", pdf(b"BT /F1 10 Tf (a) Tj ET", width=432, height=288, resources=FONT))
    assert cli.main([str(f), "--width", "6in", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["projects"] == [] and data["limits"]["font"] == 7.0 and data["version"]
    fig = data["figures"][0]
    assert fig["worst"] == "ok" and fig["smallest"] == 10.0 and fig["printed"] == 6.0


def test_json_for_a_project_says_what_set_the_widths(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "main.tex", "\\documentclass{article}\\usepackage[margin=1in]{geometry}\\begin{document}\n"
          "\\includegraphics[width=0.5\\linewidth]{plot}\n\\begin{tikzpicture}\\end{tikzpicture}\n\\end{document}\n")  # fmt: skip
    write(tmp_path, "plot.pdf", pdf(b"BT /F1 10 Tf (a) Tj ET", width=432, height=288, resources=FONT))
    assert cli.main([str(tmp_path), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    how = "from the class options; the preamble sets: geometry margin=1in"
    assert data["projects"] == [{"main": "main.tex", "template": "article, 10pt letter (LaTeX's default)", "how": how,
                                 "text_width": 6.5, "column_width": 6.5}]  # fmt: skip
    assert data["figures"][0]["printed"] == 3.25 and data["figures"][0]["scale"] == 0.5417  # rounded
    assert "1 figure(s) drawn by LaTeX (TikZ, pgfplots)" in data["figures"][1]["findings"][0]["message"]


def test_errors_and_help(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([str(tmp_path / "nothing.pdf")]) == 2
    assert "no such file" in capsys.readouterr().err
    assert cli.main([str(tmp_path)]) == 2  # a folder with no main .tex
    with pytest.raises(SystemExit):
        cli.main(["x.pdf", "--width", "wide"])
    assert cli.main([]) == 2
    (tmp_path / "notes.txt").write_text("not a figure", encoding="utf-8")
    assert cli.main([str(tmp_path / "notes.txt")]) == 2
    assert "not a figure" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli.main(["x.pdf", "--width", "3"])
    assert "(inches: 3in)" in capsys.readouterr().err
