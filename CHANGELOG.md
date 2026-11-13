# Changelog

## 0.1.0 — 2026-11-13

First release.

- `fig-check paper/`: every figure of a LaTeX project at the width it prints at (`width`, `height`, `scale`,
  `\resizebox`, `figure`/`figure*`/`wrapfigure`/`subfigure`/`minipage`), the venue's widths from its style file
  (NeurIPS, ICLR, ICML, CVPR/ICCV, ACL, AAAI); `fig-check plot.pdf --width 3.25in` for single figures.
- Checks: text size when printed; colour pairs that collapse with protanopia, deuteranopia or tritanopia (Machado et
  al. 2009, CIEDE2000); raster resolution, of raster figures and of images inside PDFs.
- Reads PDF, PNG, JPEG and SVG with the standard library only.
