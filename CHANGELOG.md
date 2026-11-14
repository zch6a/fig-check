# Changelog

## 0.3.0 — 2026-11-14

- **`diagram(model)`**: a model's architecture as an editable TikZ figure (and SVG): its blocks in order, repeated
  blocks collapsed ("×N"), containers opened, each box with the class, name and parameter count; `labels`, `depth`,
  `direction`, `per_row`, `skip`. Any object with `named_children()`; torch is not a dependency. Checked on
  ResNet-18, `nn.TransformerEncoder` and ViT-B/16: compiles with pdflatex, and fig-check finds the figures fine.

## 0.2.1 — 2026-11-14

- The Claude Code plugin's manifest (`plugin/.claude-plugin/plugin.json`) says 0.2.1: it had stayed at an older
  version through the last release, so the marketplace showed the old one (found by `repro-score release`).
- A `CITATION.cff`, for GitHub's "Cite this repository".

## 0.2.0 — 2026-11-14

- **`paper_style(template, width="column", ...)`**: rcParams for a matplotlib figure made at the width it prints at,
  in the paper's typeface (Times for NeurIPS, ICLR, ICML, CVPR, ACL; Computer Modern for `article`, measured with
  pdflatex and each style file), text one point under the body size, ticks two under, constrained layout, TrueType
  fonts.
- **`save_for_paper(fig, path, template, width="column")`**: saves at exactly that width (TrueType fonts whatever the
  rcParams), refuses `bbox_inches="tight"`, checks the saved file at that width, names the fonts in the PDF and warns
  when the paper is in Times and the figure is not. `embedded_fonts(pdf_bytes)` lists a PDF's fonts.
- End to end: a figure from `paper_style("icml")` in a compiled ICML paper prints at 100%, smallest text 8 pt.

## 0.1.1 — 2026-11-14

- The agent skill's frontmatter is valid YAML again: its description held a `: `, which YAML reads as a new key, so
  the whole frontmatter failed to parse and the skill loaded without its description (`claude plugin validate`
  reported it). The values are quoted now.

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
