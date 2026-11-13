# Changelog

## 0.1.0 — 2026-11-13

First release.

**Checking a paper's figures**

- `fig-check paper/`: every figure of a LaTeX project at the width it prints at (`width`, `height`, `scale`,
  `\resizebox`, `figure`/`figure*`/`wrapfigure`/`subfigure`/`minipage`); `fig-check plot.pdf --width 3.25in` for
  single figures. PDF, PNG, JPEG and SVG read with the standard library only.
- Checks: text size when printed; colour pairs that collapse with protanopia, deuteranopia or tritanopia (Machado et
  al. 2009, CIEDE2000, checked against the published tables); raster resolution, of raster figures and of images
  inside PDFs.
- The widths it checks at: the venue's style file (NeurIPS, ICLR, ICML, CVPR/ICCV, ACL, AAAI); the `IEEEtran`,
  `acmart`, `llncs`, `elsarticle` and `revtex4-2` classes for their options; `article`'s class options; then the
  preamble's `geometry`, `fullpage`, `\setlength`, `\addtolength` and `\advance` — as pdflatex sets them, checked
  for 51 preambles and 25 class option sets (`scripts/latex_widths.py` checks again with your TeX). Settings it
  cannot read are named in the first line of the output.
- `--json`: the widths used and how they were found, and each figure's findings.

**matplotlib**

- `check_figure(fig, width="column", template="icml")`: a figure checked in memory before it is saved.
- `save_pgfplots(fig, "fig.tex")`: a figure as pgfplots code that LaTeX draws at its printed width in the paper's own
  font (lines, markers, scatter, bars, areas, error bars, text, log and date axes, legends, twin axes); what it cannot
  export is listed.

Also `check_file`, `check_bytes` and `to_pgfplots`; the package is typed and has no dependencies.
