from __future__ import annotations

import pytest
from make import jpeg_header, pdf, png

from fig_check.pdf import PDFError, read_figure
from fig_check.raster import read_jpeg, read_png
from fig_check.svg import SVGError, read_svg

FONT = b"/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >>"


def sizes(data: bytes) -> list[float]:
    return [round(t.size, 3) for t in read_figure(data).texts]


def test_text_sizes_follow_tf_tm_and_cm() -> None:
    assert sizes(pdf(b"BT /F1 10 Tf (a) Tj ET", resources=FONT)) == [10]
    assert sizes(pdf(b"BT /F1 1 Tf 8 0 0 8 0 0 Tm (a) Tj ET", resources=FONT)) == [8]  # matplotlib's way
    assert sizes(pdf(b"q 0.5 0 0 0.5 0 0 cm BT /F1 12 Tf (a) Tj ET Q BT /F1 12 Tf (b) Tj ET", resources=FONT)) == [6, 12]
    assert sizes(pdf(b"BT /F1 10 Tf 0 1 -1 0 0 0 Tm (rotated) Tj ET", resources=FONT)) == [10]  # a rotated y-axis label
    assert sizes(pdf(b"BT /F1 10 Tf ( ) Tj [( )] TJ ET", resources=FONT)) == []  # spaces draw nothing


def test_type3_fonts_scale_by_their_font_matrix() -> None:
    t3 = b"/Font << /F1 << /Type /Font /Subtype /Type3 /FontMatrix [0.002 0 0 0.002 0 0] >> >>"
    assert sizes(pdf(b"BT /F1 5 Tf (a) Tj ET", resources=t3)) == [10]


def test_colours_of_fills_strokes_and_text() -> None:
    fig = read_figure(pdf(b"1 0 0 rg 0 0 10 10 re f 0 0 1 RG 0 0 m 10 10 l S 0 g BT /F1 9 Tf (t) Tj ET 0 1 1 0 k 0 0 5 5 re f", resources=FONT))
    assert fig.fills == [(1, 0, 0), (1.0, 0.0, 0.0)] and fig.strokes == [(0, 0, 1)] and fig.text_colours == [(0, 0, 0)]


def test_forms_images_compression_and_object_streams() -> None:
    form = (
        b"<< /Type /XObject /Subtype /Form /BBox [0 0 100 100] /Matrix [0.5 0 0 0.5 0 0] /Resources << "
        + FONT
        + b" >> /Length 23 >>\nstream\nBT /F1 10 Tf (a) Tj ET\nendstream"
    )
    image = b"<< /Type /XObject /Subtype /Image /Width 300 /Height 150 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 0 >>\nstream\n\nendstream"
    res = b"/XObject << /Fm 10 0 R /Im 11 0 R >>"
    content = b"/Fm Do q 72 0 0 36 0 0 cm /Im Do Q"
    for kwargs in ({}, {"compress": True}, {"objstm": True}):
        fig = read_figure(pdf(content, objects={10: form, 11: image}, resources=res, **kwargs))  # type: ignore[arg-type]
        assert [t.size for t in fig.texts] == [5]
        assert fig.images[0].pixels == (300, 150) and fig.images[0].size == (72, 36)


def test_a_form_that_draws_itself_stops() -> None:
    loop = b"<< /Type /XObject /Subtype /Form /BBox [0 0 1 1] /Resources << /XObject << /Fm 10 0 R >> >> /Length 6 >>\nstream\n/Fm Do\nendstream"
    fig = read_figure(pdf(b"/Fm Do", objects={10: loop}, resources=b"/XObject << /Fm 10 0 R >>"))
    assert any("within itself" in n for n in fig.notes)


def test_inline_images_and_the_page_size() -> None:
    fig = read_figure(pdf(b"q 144 0 0 72 0 0 cm BI /W 600 /H 300 /CS /G /BPC 8 ID \x00\x01\x02 EI Q", width=300, height=150))
    assert (fig.width, fig.height) == (300, 150) and fig.images[0].pixels == (600, 300) and fig.images[0].size == (144, 72)


def test_not_a_pdf_and_encrypted_are_refused() -> None:
    with pytest.raises(PDFError, match="not a PDF"):
        read_figure(b"hello")
    encrypted = pdf(b"").replace(b"/Root 1 0 R", b"/Root 1 0 R /Encrypt << /Filter /Standard >>")
    with pytest.raises(PDFError, match="encrypted"):
        read_figure(encrypted)


def test_png_and_jpeg() -> None:
    r = read_png(png(30, 10, [(214, 39, 40), (44, 160, 44), (255, 255, 255)], dpi=300))
    assert r.pixels == (30, 10) and r.dpi is not None and round(r.dpi[0]) == 300
    assert len(r.colours) == 2  # red and green; white left out
    assert read_png(png(8, 8)).dpi is None
    j = read_jpeg(jpeg_header(1200, 800, dpi=150))
    assert j.pixels == (1200, 800) and j.dpi == (150.0, 150.0)


def test_svg_sizes_colours_and_entities() -> None:
    svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="200pt" height="100pt" viewBox="0 0 400 200">
<style>.lbl { font-size: 16px; fill: #333333 }</style>
<g transform="scale(0.5)"><text font-size="20" x="0" y="20">big</text></g>
<text class="lbl" x="0" y="40">label</text>
<path d="M0 0L10 10" stroke="#d62728" fill="none"/><rect width="5" height="5" fill="rgb(44, 160, 44)"/></svg>"""
    fig = read_svg(svg)
    assert (fig.width, fig.height) == (200, 100)
    # viewBox 400 wide drawn 200 pt wide: half a point a unit; 20 units × 0.5 scale × 0.5 = 5 pt; 16 px × 0.5 = 8 pt
    assert sorted(round(t.size, 2) for t in fig.texts) == [5.0, 8.0]
    assert fig.strokes == [(214 / 255, 39 / 255, 40 / 255)] and fig.fills == [(44 / 255, 160 / 255, 44 / 255)]
    with pytest.raises(SVGError, match="entities"):
        read_svg(b'<!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">&x;</svg>')
