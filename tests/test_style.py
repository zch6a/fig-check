"""paper_style and save_for_paper on real matplotlib figures (made here; nothing read from the network)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from fig_check import check_file, paper_style, save_for_paper  # noqa: E402
from fig_check.style import FONTS, embedded_fonts  # noqa: E402


def plot(**style):
    with plt.rc_context(style):
        fig, ax = plt.subplots()
        for k, c in enumerate(["#1f77b4", "#ff7f0e", "#7f7f7f"]):
            ax.plot([0, 1, 2, 3], [k, k + 1, k + 0.5, k + 2], color=c, marker="os^"[k], label=f"run {k}")
        ax.set_xlabel("training steps ($\\times$1000)")
        ax.set_ylabel("loss")
        ax.legend()
    return fig


@pytest.mark.parametrize("template", sorted(FONTS))
def test_made_at_the_column_width_text_prints_at_its_size(tmp_path, template):
    style = paper_style(template)
    with plt.rc_context(style):  # made and saved in the style: matplotlib picks fonts when it draws
        fig = plot()
        report = save_for_paper(fig, tmp_path / "f.pdf", template)
    plt.close(fig)
    assert report.scale == pytest.approx(1.0, abs=0.01)  # printed at its own size: nothing scaled
    want = FONTS[template].size - 2  # tick labels and legend, the smallest text
    assert report.smallest == pytest.approx(want, abs=0.15), str(report)
    assert report.worst != "error"
    # the file on disk is what was checked, at the width LaTeX gives it
    again = check_file(tmp_path / "f.pdf", style["figure.figsize"][0])
    assert again.smallest == pytest.approx(report.smallest, abs=0.01)


def test_the_same_figure_made_big_and_shrunk_has_small_text(tmp_path):
    fig = plot(**{"figure.figsize": (6.4, 4.8)})  # matplotlib's default size, 10 pt text
    with pytest.raises(ValueError, match="tight"):
        save_for_paper(fig, tmp_path / "f.pdf", "icml", bbox_inches="tight")
    fig.savefig(tmp_path / "big.pdf")
    plt.close(fig)
    shrunk = check_file(tmp_path / "big.pdf", 3.25)  # \includegraphics[width=\columnwidth]
    assert shrunk.smallest < 5.5 and shrunk.worst == "warning"


def test_fonts_are_embedded_as_truetype_and_named(tmp_path):
    with plt.rc_context(paper_style("neurips", "text", height=2.0)):
        fig = plot()
        report = save_for_paper(fig, tmp_path / "f.pdf", "neurips", "text")
    plt.close(fig)
    data = (tmp_path / "f.pdf").read_bytes()
    assert b"/Type3" not in data and b"/FontType 3" not in data
    fonts = embedded_fonts(data)
    assert fonts and any(f.rule == "typeface" and "fonts in the PDF" in f.message for f in report.findings)
    if not any(k in "".join(fonts).lower() for k in ("times", "nimbus", "termes", "stix")):
        assert any(f.rule == "typeface" and f.severity == "warning" for f in report.findings)  # DejaVu instead of Times


def test_style_values_and_errors():
    s = paper_style("acl", aspect=1.0, fontsize=8)
    w, h = s["figure.figsize"]
    assert w == h and s["font.size"] == 8 and s["xtick.labelsize"] == 7
    assert paper_style("ieee", font="times")["figure.figsize"][0] == pytest.approx(252 / 72.27, abs=1e-3)
    with pytest.raises(ValueError, match="font="):
        paper_style("ieee")
    with pytest.raises(ValueError):
        paper_style("nature")
