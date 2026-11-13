"""The checks, for one figure at the size it prints: the smallest text, the resolution of raster images, and colours
that people with colour vision deficiency cannot tell apart."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .color import RGB, Clash, clashes, hexed
from .pdf import PDFError, read_figure
from .raster import RasterError, read_jpeg, read_png
from .svg import SVGError, read_svg


@dataclass
class Limits:
    # Elsevier's rule of thumb: "a finished, printed size of 7 pt for normal text", "no smaller than 6 pt for subscript and
    # superscript characters"; IEEE: colour and greyscale images ">300dpi", Elsevier: "300 DPI for halftone images".
    # The error thresholds are this tool's judgement: text this small is hard to read at all, images this coarse blur.
    font: float = 7.0  # points: smaller printed text is a warning
    font_error: float = 5.0  # points: smaller is an error
    dpi: float = 300.0  # raster images below this many pixels per printed inch: a warning
    dpi_error: float = 150.0  # below this: an error
    colours: int = 24  # more distinct hues than this: a colour map, not categories


@dataclass
class Finding:
    rule: str  # font, resolution, colour, read
    severity: str  # error, warning, info
    message: str


@dataclass
class Report:
    figure: str
    where: str = ""  # e.g. "main.tex:120, figure"
    printed: float | None = None  # printed width, inches
    scale: float | None = None  # printed size over the figure's own size
    smallest: float | None = None  # the smallest printed text, points
    findings: list[Finding] = field(default_factory=list)

    @property
    def worst(self) -> str:
        sev = {f.severity for f in self.findings}
        return "error" if "error" in sev else "warning" if "warning" in sev else "ok"

    def __str__(self) -> str:
        """As fig-check prints it: a line for the figure, then its errors and warnings, then notes."""
        size = f"{self.printed:.2f} in wide" if self.printed is not None else "size unknown"
        scale = f", at {self.scale:.0%} of its size" if self.scale is not None and abs(self.scale - 1) > 0.005 else ""
        smallest = f", smallest text {self.smallest:.1f} pt" if self.smallest is not None else ""
        lines = [f"{self.figure}{f'  ({self.where})' if self.where else ''}: {size}{scale}{smallest}"]
        lines += [f"  {f.severity}: {f.rule}: {f.message}" for f in self.findings if f.severity != "info"]
        lines += [f"  note: {f.message}" for f in self.findings if f.severity == "info"]
        return "\n".join(lines)


def check_file(path: Path, width: float | None = None, height: float | None = None, scale: float | None = None,
               limits: Limits | None = None, name: str | None = None, where: str = "") -> Report:  # fmt: skip
    """One figure file, printed `width` inches wide (or `height` tall, or at `scale`; else at its own size)."""
    try:
        data = path.read_bytes()
    except OSError as e:
        return Report(name or path.as_posix(), where, findings=[Finding("read", "error", f"cannot be read ({e.strerror or e})")])
    return check_bytes(data, name or path.as_posix(), width, height, scale, limits, where, path.suffix)


def check_bytes(data: bytes, name: str, width: float | None = None, height: float | None = None, scale: float | None = None,
                limits: Limits | None = None, where: str = "", suffix: str = "") -> Report:  # fmt: skip
    """One figure's bytes (PDF, PNG, JPEG or SVG, told by their content; `suffix` ".svg" helps an SVG without a header)."""
    limits = limits or Limits()
    report = Report(name, where)
    kind = _kind(Path("figure" + suffix), data)
    try:
        if kind == "pdf":
            _vector(report, read_figure(data), width, height, scale, limits, "pdf")
        elif kind == "svg":
            _vector(report, read_svg(data), width, height, scale, limits, "svg")
        elif kind in ("png", "jpeg"):
            _raster(report, read_png(data) if kind == "png" else read_jpeg(data), width, height, scale, limits)
        elif kind == "eps":
            report.findings.append(Finding("read", "info", "EPS is not read: check the PDF that LaTeX makes of it (or convert it)"))
        else:
            report.findings.append(Finding("read", "info", "not a PDF, PNG, JPEG or SVG: not checked"))
    except (PDFError, RasterError, SVGError) as e:
        report.findings.append(Finding("read", "error", f"cannot be read: {e}"))
    return report


def _kind(path: Path, data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8"):
        return "jpeg"
    if data.startswith(b"%!PS"):
        return "eps"
    head = data[:2048].lstrip()
    if path.suffix.lower() == ".svg" or head.startswith(b"<?xml") and b"<svg" in data[:4096] or head.startswith(b"<svg"):
        return "svg"
    return ""


def _scale(native_w: float, native_h: float, width: float | None, height: float | None, scale: float | None) -> tuple[float, bool]:
    """(printed over natural size, whether a size was given); natural sizes in points."""
    if width is not None and native_w > 0:
        return width * 72 / native_w, True
    if height is not None and native_h > 0:
        return height * 72 / native_h, True
    if scale is not None:
        return scale, True
    return 1.0, False


def _vector(report: Report, fig: object, width: float | None, height: float | None, scale: float | None, limits: Limits, kind: str) -> None:
    w, h = fig.width, fig.height  # type: ignore[attr-defined]
    s, given = _scale(w, h, width, height, scale)
    report.scale = s
    report.printed = w * s / 72
    if not given:
        report.findings.append(Finding("read", "info", f"no printed size given: checked at its own size, {w / 72:.2f} in wide"))
    sizes = [t.size * s for t in fig.texts]  # type: ignore[attr-defined]
    if sizes:
        report.smallest = min(sizes)
        small = [x for x in sizes if x < limits.font]
        if small:
            sev = "error" if report.smallest < limits.font_error else "warning"
            own = min(t.size for t in fig.texts)  # type: ignore[attr-defined]
            fix = f" (it is {own:.1f} pt in the file: printed at {s:.0%} of its size)" if abs(s - 1) > 0.05 else ""
            report.findings.append(Finding("font", sev, f"text as small as {report.smallest:.1f} pt when printed; {len(small)} of {len(sizes)} "
                                                       f"pieces under {limits.font:g} pt{fix}"))  # fmt: skip
    low: list[tuple[float, str]] = []  # embedded images under the limit: one finding for them all, the worst named
    for img in getattr(fig, "images", []):
        pw, ph = img.size[0] * s / 72, img.size[1] * s / 72
        if pw < 0.25 or ph < 0.25:
            continue  # an icon or a marker
        dpi = min(img.pixels[0] / pw, img.pixels[1] / ph)
        if dpi < limits.dpi:
            low.append((dpi, f"{img.pixels[0]}×{img.pixels[1]} image printed {pw:.2f} in wide"))
    if low:
        low.sort()
        dpi, what = low[0]
        many = f"{len(low)} embedded images under {limits.dpi:g} pixels per inch; the lowest, a " if len(low) > 1 else "an embedded "
        sev = "error" if dpi < limits.dpi_error else "warning"
        report.findings.append(
            Finding("resolution", sev, f"{many}{what}: {dpi:.0f} pixels per inch" + ("" if len(low) > 1 else f" (under {limits.dpi:g})"))
        )
    _colours(report, list(fig.fills) + list(fig.strokes), limits)  # type: ignore[attr-defined]
    for note in getattr(fig, "notes", []):
        report.findings.append(Finding("read", "info", note))


def _raster(report: Report, r: object, width: float | None, height: float | None, scale: float | None, limits: Limits) -> None:
    px, py = r.pixels  # type: ignore[attr-defined]
    if px <= 0 or py <= 0:
        report.findings.append(Finding("read", "error", f"cannot be read: an image of {px}×{py} pixels"))
        return
    dpi_stated = r.dpi  # type: ignore[attr-defined]
    if dpi_stated and (dpi_stated[0] <= 0 or dpi_stated[1] <= 0):
        dpi_stated = None  # a stated resolution of 0 is no resolution: pdfLaTeX's 72 dpi
    # pdfLaTeX's natural size for an image without a stated resolution: 72 pixels an inch
    nat_w = px / (dpi_stated[0] if dpi_stated else 72) * 72
    nat_h = py / (dpi_stated[1] if dpi_stated else 72) * 72
    s, given = _scale(nat_w, nat_h, width, height, scale)
    report.scale = s
    report.printed = nat_w * s / 72
    if not given:
        assumed = "" if dpi_stated else " (no resolution stated: 72 dpi, as pdfLaTeX takes it)"
        report.findings.append(Finding("read", "info", f"no printed size given: at its natural size, {report.printed:.2f} in wide{assumed}"))
    dpi = min(px / report.printed, py / (nat_h * s / 72))
    _dpi_finding(report, dpi, limits, f"{px}×{py} pixels printed {report.printed:.2f} in wide")
    report.findings.append(Finding("font", "info", "a raster image: its text cannot be measured; make it a vector figure (PDF, SVG) if it can be"))
    _colours(report, r.colours, limits)  # type: ignore[attr-defined]


def _dpi_finding(report: Report, dpi: float, limits: Limits, what: str) -> None:
    if dpi < limits.dpi:
        sev = "error" if dpi < limits.dpi_error else "warning"
        report.findings.append(Finding("resolution", sev, f"{what}: {dpi:.0f} pixels per inch (under {limits.dpi:g})"))


def _colours(report: Report, used: Sequence[RGB], limits: Limits) -> None:
    found = clashes(used)
    distinct = {hexed(c) for c in used}
    if len(distinct) > limits.colours:
        advice = "a perceptually uniform map that reads in greyscale and with colour vision deficiency (viridis, cividis) is safe"
        report.findings.append(Finding("colour", "info", f"{len(distinct)} colours: a colour map, not categories; {advice}"))
        return
    pairs: dict[tuple[str, str], list[Clash]] = {}
    for c in found:
        pairs.setdefault((hexed(c.a), hexed(c.b)), []).append(c)
    for (a, b), cs in pairs.items():
        kinds = ", ".join(f"{c.kind} (ΔE {c.seen:.1f})" for c in cs)
        report.findings.append(Finding("colour", "warning", f"{a} and {b} look alike with {kinds}; with typical vision ΔE {cs[0].normal:.0f}. "
                                                             "Tell them apart by more than hue: line style, markers, labels, lightness"))  # fmt: skip
