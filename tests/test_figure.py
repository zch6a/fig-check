"""check_figure: a figure checked in memory, before it is saved (matplotlib's, or anything with savefig)."""

from __future__ import annotations

import io

import pytest
from make import pdf

from fig_check import check_figure
from fig_check.figure import printed_width

FONT = b"/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >>"


class Fake:
    """A figure 6 by 4 inches with 10 pt labels in red and green, as matplotlib's savefig would write it."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def savefig(self, file: io.BytesIO, **kwargs: object) -> None:
        self.calls.append(kwargs)
        content = b"BT /F1 10 Tf 40 20 Td (step) Tj ET 0.84 0.15 0.16 RG 50 40 m 400 180 l S 0.17 0.63 0.17 RG 50 60 m 400 160 l S"
        file.write(pdf(content, width=432, height=288, resources=FONT))


def test_a_figure_is_checked_at_the_width_it_prints_at() -> None:
    fig = Fake()
    r = check_figure(fig, width="column", template="icml", bbox_inches="tight")
    assert fig.calls == [{"format": "pdf", "bbox_inches": "tight"}]
    assert r.printed == pytest.approx(3.25) and r.smallest == pytest.approx(10 * 3.25 / 6)
    assert {f.rule for f in r.findings} == {"font", "colour"} and r.worst == "warning"
    assert str(r).startswith("figure: 3.25 in wide, at 54% of its size, smallest text 5.4 pt\n  warning: font:")
    assert check_figure(Fake()).smallest == 10.0  # at its own size


@pytest.mark.parametrize(("width", "inches"), [(3.0, 3.0), ("8cm", 8 / 2.54), ("text", 6.75), ("0.5\\linewidth", 1.625), ("columnwidth", 3.25)])
def test_widths(width: float | str, inches: float) -> None:
    assert printed_width(width, "icml") == pytest.approx(inches)


@pytest.mark.parametrize(("width", "template"), [("wide", "icml"), ("-3in", "icml"), ("column", "nature")])
def test_a_width_it_cannot_read_is_an_error(width: str, template: str) -> None:
    with pytest.raises(ValueError):
        printed_width(width, template)


def test_a_real_matplotlib_figure() -> None:
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([1, 2, 3], color="#d62728")
    ax.plot([3, 2, 1], color="#2ca02c")
    ax.set_xlabel("step")
    r = check_figure(fig, width="column", template="icml")
    assert r.smallest == pytest.approx(10 * 3.25 / 6, abs=0.05)  # matplotlib's 10 pt default, at 54%
    assert {f.rule for f in r.findings} == {"font", "colour"}
    small, ax = plt.subplots(figsize=(3.25, 2.2))
    ax.plot([1, 2, 3], "-o", color="#0072b2")
    ax.plot([3, 2, 1], "--s", color="#e69f00")
    ax.tick_params(labelsize=7)
    ax.set_xlabel("step", fontsize=8)
    with matplotlib.rc_context({"pdf.fonttype": 42}):  # TrueType fonts instead of Type 3
        assert check_figure(small, width="column", template="icml").worst == "ok"
    plt.close("all")
