"""to_pgfplots: matplotlib figures as pgfplots code. The code these tests check compiled with pdflatex and pgfplots 1.18
(and looked like the matplotlib figure) when this was written; the tests themselves need no TeX."""

from __future__ import annotations

import re

import pytest

from fig_check.pgf import save_pgfplots, tex_text, to_pgfplots

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


@pytest.fixture(autouse=True)
def _close() -> None:
    yield
    plt.close("all")


def test_lines_legend_labels_and_limits() -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([0, 1, 2], [1.0, 0.5, 0.25], label="ours")
    ax.plot([0, 1, 2], [1.0, 0.7, 0.5], "--", color="#e69f00", label="50% & $\\beta$")
    ax.plot([0, 2], [0.1, 0.1], color="grey")  # no label: not in the legend
    ax.plot([0, 1, 2], [0.9, 0.6, 0.3], "s", markerfacecolor="none", label="_hidden")
    ax.set(xlabel="step_k", ylabel="loss", title="Training", xlim=(0, 2), ylim=(0, 1.1))
    ax.grid(True)
    ax.legend(loc="upper right")
    code, notes = to_pgfplots(fig)
    assert notes == []
    assert "\\pgfmathsetlengthmacro{\\fcw}{\\linewidth}" in code and "\\pgfmathsetlengthmacro{\\fch}{0.666667*\\fcw}" in code
    assert "\\definecolor{fc0}{HTML}{1F77B4}" in code and "\\definecolor{fc1}{HTML}{E69F00}" in code
    assert "xlabel={step\\_k}" in code and "title={Training}" in code and "xmin=0" in code and "ymax=1.1" in code
    assert "xmajorgrids" in code and re.search(r"legend style=\{at=\{\(0\.[6-9]\d*,0\.[6-9]\d*\)\}, anchor=south west\}", code)
    assert re.findall(r"\\addlegendentry\{(.*)\}", code) == ["ours", "50\\% \\& $\\beta$"]
    plots = re.findall(r"\\addplot\[([^\]]*)\]", code)
    assert len(plots) == 4 and all(p.startswith("forget plot, ") for p in plots)  # the legend comes from its own entries
    assert plots[1].startswith("forget plot, fc1, dashed, line width=1.5pt")
    assert "mark=square," in plots[3] and "only marks" in plots[3]  # hollow
    images = re.findall(r"\\addlegendimage\{(.*)\}", code)
    assert len(images) == 2 and images[1].startswith("fc1, dashed")
    assert "(0,1) (1,0.5) (2,0.25)" in code


def test_bars_errors_scatter_text_and_log_scale() -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7, 3))
    a1.bar(["A", "B"], [3, 5], yerr=[0.3, 0.5], color=["#0072b2", "#009e73"])
    a2.scatter([1, 2], [10, 1000], s=36, label="runs")
    a2.fill_between([1, 2], [5, 50], [20, 2000], alpha=0.25)
    a2.set_yscale("log")
    a2.text(1.5, 100, "peak", ha="left")
    a2.text(0.5, 0.9, "(b)", transform=a2.transAxes)
    a2.legend(loc="upper left")
    code, notes = to_pgfplots(fig, width="\\textwidth")
    assert notes == []
    assert code.count("\\begin{axis}") == 2
    assert "\\fill[fc0] (axis cs:-0.4,0) rectangle (axis cs:0.4,3);" in code
    assert "xticklabels={{A},{B}}" in code
    assert len(re.findall(r"\\draw\[fc\d, line width=1.5pt\] \(axis cs:0,2.7\) -- \(axis cs:0,3.3\);", code)) == 1  # error bar
    assert "ymode=log" in code and re.search(r"legend style=\{at=\{\(0\.0\d*,0\.[6-9]\d*\)\}", code) and "\\addlegendentry{runs}" in code
    assert "mark size=3pt" in code  # s=36 points squared: a 6 pt marker
    assert "fill opacity=0.25" in code
    assert re.search(r"\\node\[anchor=west, fc\d\] at \(axis cs:1.5,100\) \{peak\};", code)
    assert "at (rel axis cs:0.5,0.9) {(b)};" in code
    assert "$10^{3}$" in code and "mathdefault" not in code


def test_what_is_not_exported_is_said() -> None:
    fig, (a1, a2) = plt.subplots(1, 2)
    im = a1.imshow([[0, 1], [1, 0]])
    fig.colorbar(im, ax=a1)
    a2.plot([0, 1])
    fig.suptitle("All")
    code, notes = to_pgfplots(fig)
    assert any("imshow" in n for n in notes) and "a colour bar" in notes and any("suptitle" in n for n in notes)
    assert "% not exported: a colour bar" in code
    assert code.count("\\begin{axis}") == 2  # the image's axes (empty) and the line's; not the colour bar


def test_saving_writes_only_the_named_file(tmp_path) -> None:  # noqa: ANN001
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1])
    assert save_pgfplots(fig, tmp_path / "f.tex", width="3.25in") == []
    assert [p.name for p in tmp_path.iterdir()] == ["f.tex"]
    assert "\\pgfmathsetlengthmacro{\\fcw}{3.25in}" in (tmp_path / "f.tex").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("text", "tex"),
    [("a_b", "a\\_b"), ("$a_b$", "$a_b$"), ("100%", "100\\%"), ("#1 & {x}", "\\#1 \\& \\{x\\}"), ("cost \\$5", "cost \\textbackslash{}\\$5"),
     ("$\\mathdefault{10^{2}}$", "$10^{2}$"), ("\u22121", "$-$1"), ("$\u22121$", "$-1$")],
)  # fmt: skip
def test_text_is_escaped_outside_maths(text: str, tex: str) -> None:
    assert tex_text(text) == tex


def test_categories_dates_and_gaps() -> None:
    import datetime

    fig, (a1, a2) = plt.subplots(1, 2)
    a1.plot(["10", "2", "300"], [1, 2, 3])  # categories, not numbers
    a2.plot([datetime.date(2024, 1, d) for d in (1, 2, 3)], [1.0, float("nan"), 3.0])
    code, _ = to_pgfplots(fig)
    assert "(0,1) (1,2) (2,3)" in code and "xticklabels={{10},{2},{300}}" in code
    assert re.search(r"\(19723,1\) \(19724,nan\) \(19725,3\)", code) and "unbounded coords=jump" in code


def test_nan_bars_inverted_axes_alpha_and_hollow_circles() -> None:
    fig, ax = plt.subplots()
    ax.bar([1, 2, 3], [1, float("nan"), 3])
    ax.plot([1, 3], [1, 3], "o", markerfacecolor="none", alpha=0.5)
    ax.invert_xaxis()
    code, _ = to_pgfplots(fig)
    assert "nan" not in code.split("\\begin{axis}")[1].split("\\addplot")[0]  # no NaN rectangle
    assert code.count("rectangle") == 2
    assert re.search(r"xmin=0\.\d+,\s*xmax=3\.\d+", code) and "x dir=reverse" in code
    assert "opacity=0.5" in code and "mark=o," in code


def test_legends_from_labels_bars_and_order() -> None:
    fig, (a1, a2) = plt.subplots(1, 2)
    a1.plot([0, 1])
    a1.plot([1, 0])
    a1.legend(["a", "b"])
    a2.scatter([1], [1], label="points")
    a2.bar([1], [2], label="bars")
    a2.plot([0, 1], label="line")
    a2.legend()
    code, _ = to_pgfplots(fig)
    assert re.findall(r"\\addlegendentry\{(.*)\}", code) == ["a", "b", "points", "line", "bars"]  # the legend's own order
    images = re.findall(r"\\addlegendimage\{(.*)\}", code)
    assert images[2].startswith("only marks") and images[3].startswith("fc") and images[4].startswith("area legend")


def test_twin_axes_offsets_and_mathregular() -> None:
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1e7, 2e7])
    ax.set_xlabel(r"time ($\mathregular{s}$), ≥ 5 µs")
    twin = ax.twinx()
    twin.plot([1, 2], [0, 1], color="C1")
    ax.annotate("max", xy=(2, 2e7), xytext=(1.5, 1.8e7), arrowprops={"arrowstyle": "->"})
    code, notes = to_pgfplots(fig)
    assert "axis y line*=left" in code and "axis y line*=right, axis x line=none" in code.replace(",\n  ", ", ")
    assert "after end axis/.append code={\\node[anchor=south west] at (rel axis cs:0,1) {1e7};}" in code  # not clipped
    assert "xlabel={time ($\\mathrm{s}$), $\\geq$ 5 $\\mu$s}" in code
    assert any("arrow" in n for n in notes)


def test_a_width_check_figure_cannot_use_is_an_error() -> None:
    import numpy as np

    from fig_check import check_figure
    from fig_check.figure import printed_width

    assert printed_width(np.float32(3.25), "icml") == 3.25
    for bad in (0, -1.0):
        with pytest.raises(ValueError):
            printed_width(bad, "icml")
    with pytest.raises(ValueError):
        printed_width(3.0, "nature")
    fig, _ = plt.subplots()
    with pytest.raises(ValueError):
        check_figure(fig, format="png")
