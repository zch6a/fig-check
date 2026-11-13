<div align="center">

# fig-check

**A paper's figures as they will print.** Text measured at its printed size (the figure's own scale in the paper
applied), colours that people with colour vision deficiency cannot tell apart, and raster images too coarse for print,
for every figure of a LaTeX project at the width each one prints at.

<a href="https://github.com/zch6a/fig-check/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/zch6a/fig-check/actions/workflows/ci.yml/badge.svg"></a>
<img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
<img alt="No dependencies" src="https://img.shields.io/badge/dependencies-none-2ea44f">
<a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue"></a>

**English** · [简体中文](README.zh-CN.md)

</div>

---

A figure made 6 inches wide with 10 pt labels and printed in a 3.25-inch column has 5.4 pt labels. A red line and a
green line are the same line to about one man in twelve. A 640-pixel image stretched over the text width prints at
116 pixels per inch. None of this shows on screen, where you zoom; fig-check finds it before the reviewers do.

```bash
uvx --from git+https://github.com/zch6a/fig-check fig-check paper/
```

```
fig-check: main.tex: NeurIPS (detected): text 5.50 in, column 5.50 in
figures/loss.pdf  (main.tex:9, figure): 2.64 in wide, at 44% of its size, smallest text 4.4 pt
  error: font: text as small as 4.4 pt when printed; 2 of 2 pieces under 7 pt (it is 10.0 pt in the file: printed at 44% of its size)
  warning: colour: #d62629 and #2ba12b look alike with deuteranopia (ΔE 4.7); with typical vision ΔE 72. Tell them apart by more than hue: line style, markers, labels, lightness
figures/samples.png  (main.tex:14, figure): 5.50 in wide, at 62% of its size
  error: resolution: 640×320 pixels printed 5.50 in wide: 116 pixels per inch (under 300)
  note: a raster image: its text cannot be measured; make it a vector figure (PDF, SVG) if it can be
figures/method.pdf  (main.tex:19, figure): 3.30 in wide, smallest text 8.0 pt
fig-check: 3 figure(s), 2 with something to fix
```

That is the made-up project in [examples/paper](examples/paper). Exit status 0 when there is nothing to fix, 1 when
there is, 2 when it could not run; `--json` gives the reports.

## What it reads

- **A LaTeX project** (a folder, or its main `.tex`): every `\includegraphics`, following `\input` and `\include`, at
  the width it prints at: `width=`, `height=`, `scale=`, `\resizebox`, and the line width inside `figure` (the
  column), `figure*` (the text), `wrapfigure`, `subfigure` and `minipage`. The venue's widths come from the style the
  preamble loads; `--template` names it when it does not.
- **Single figures**: `fig-check plot.pdf --width 3.25in`.
- **Formats**: PDF (read with the standard library: text, colours, embedded images, form XObjects, compressed and
  object streams), PNG (decoded for its colours), JPEG (its size), SVG. EPS is noted, not read.

| Template | Text width | Column width | From |
|---|---|---|---|
| NeurIPS | 5.5 in | (one column) | `neurips_20xx.sty` |
| ICLR | 5.5 in | (one column) | `iclr20xx_conference.sty` |
| ICML | 6.75 in | 3.25 in | `icml20xx.sty` (`\columnsep` 0.25 in) |
| CVPR, ICCV | 6.875 in | 3.28 in | `cvpr.sty`, `iccv.sty` (`\columnsep` 0.3125 in) |
| ACL, EMNLP, NAACL | 16 cm | 7.7 cm | `acl.sty` (A4, 2.5 cm margins, `\columnsep` 0.6 cm) |
| AAAI | 7 in | 3.31 in | `aaai2x.sty` (`\columnsep` 0.375 in) |
| anything else | 345 pt | (one column) | LaTeX's `article` at 10 pt |

Each was read from the style file itself (2026-11-13).

## What it checks

- **Text size when printed**: every piece of text in the figure, at its drawn size times the figure's scale in the
  paper. Under 7 pt is a warning, under 5 pt an error (`--min-font`). Elsevier's rule of thumb is "a finished, printed
  size of 7 pt for normal text" and no smaller than 6 pt for sub- and superscripts.
- **Colour vision deficiency**: every pair of colours the figure draws with that is clearly different with typical
  vision (CIEDE2000 ΔE ≥ 15) but nearly the same with protanopia, deuteranopia or tritanopia (ΔE < 6), simulated
  with Machado, Oliveira and Fernandes's matrices (2009, severity 1). Greys are left out; a figure with many colours is
  taken as a colour map, with advice instead of pairs.
- **Resolution**: raster figures, and raster images inside PDFs, in pixels per printed inch. Under 300 is a warning,
  under 150 an error (`--min-dpi`). IEEE asks more than 300 dpi for colour and greyscale images; Elsevier 300 for
  halftones. A PNG with no stated resolution is taken at 72 dpi, as pdfLaTeX does.

The colour science is checked against its sources: CIEDE2000 against all 34 pairs of Sharma, Wu and Dalal's test
data; the simulation matrices against the authors' published table.

## Limits

- Widths from a style file the tool does not know, or set in the preamble (`\setlength{\textwidth}`, `geometry`),
  are not read yet: give `--template`, or check figures with `--width`.
- Paths a macro builds (`\iftoggle{hq}{a}{b}`) are counted, not followed.
- Text drawn as outlines (paths, not fonts) is not text to it; nor is text inside raster images.
- Colours are the ones paths and text are drawn in; gradients and patterns are not followed.

## Also in this toolkit

[submit-check](https://github.com/zch6a/submit-check) checks a submission against the venue's rules ·
[paper-proof](https://github.com/zch6a/paper-proof) checks references and numbers ·
[exp-tables](https://github.com/zch6a/exp-tables) makes results tables with significance ·
[gpu-budget](https://github.com/zch6a/gpu-budget) works out GPU memory, time and cost.

## License

MIT.
