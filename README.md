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
  preamble loads, or from the class options (`11pt`, `a4paper`, `twocolumn`) as LaTeX's `article` sets them; then
  from the preamble's own `geometry` options, `\setlength{\textwidth}` or `\columnsep`. `--template` names the venue
  when the preamble does not.
- **Single figures**: `fig-check plot.pdf --width 3.25in`.
- **A matplotlib figure, before it is saved** (below).
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
| IEEE (`IEEEtran`) | 516 pt | 252 pt | the class; `compsoc`, `onecolumn`, `peerreview`, `draftcls` too |
| ACM (`acmart`) | 506.3 pt | 241.1 pt | `sigconf`; `sigplan`, `acmtog`, `acmsmall`, `acmlarge`, `manuscript` too |
| Springer LNCS (`llncs`) | 347.1 pt | (one column) | the class |
| Elsevier (`elsarticle`), APS (`revtex4-2`) | by option | by option | `preprint`, `1p`, `3p`, `5p`; `preprint`, `twocolumn`, `reprint` |
| anything else | 345 pt | (one column) | LaTeX's `article` at 10 pt, letter paper |

Each style's widths were read from the style file itself; each class's are what pdflatex sets with that class and
those options (MiKTeX's class files, 2026-11-13; `acmart`'s after `\maketitle`, where its two columns begin). Widths from `article`'s class options and from `geometry` are
worked out as `article.cls`, `size1x.clo` and `geometry.sty` do; for 33 preambles (paper sizes, margins, one margin
alone, `twoside`, `landscape`, two columns, `\setlength`, `\addtolength`) they agree with the widths pdflatex prints,
to 0.01 pt, and the tests hold those widths.

### In Python: a matplotlib figure

```python
from fig_check import check_figure

fig, ax = plt.subplots(figsize=(6, 4))
...
report = check_figure(fig, width="column", template="icml")  # or width=3.25, "8cm", "0.48\\linewidth", "text"
print(report)  # as the command prints it
assert report.worst != "error"  # "ok", "warning" or "error"
```

```
figure: 3.25 in wide, at 54% of its size, smallest text 5.4 pt
  warning: font: text as small as 5.4 pt when printed; 21 of 21 pieces under 7 pt (it is 10.0 pt in the file: printed at 54% of its size)
  warning: colour: #d62728 and #2ca02c look alike with deuteranopia (ΔE 4.6); with typical vision ΔE 72. Tell them apart by more than hue: line style, markers, labels, lightness
```

The figure is saved to memory as a PDF and checked like a file; nothing is written to disk. Other keyword arguments
go to `savefig` (`bbox_inches="tight"`, `dpi=300` for `imshow` images, which matplotlib rasterises at the figure's
dpi). matplotlib is not a dependency: anything with `savefig(file, format="pdf")` will do. `check_file` and
`check_bytes` check files and bytes the same way.

### Or let LaTeX draw it: pgfplots

The surest fix for small text is not to shrink the figure at all. `save_pgfplots` writes a matplotlib figure as
pgfplots code, which LaTeX draws at the width it prints at, with the paper's own font at the paper's own size:

```python
from fig_check import save_pgfplots

notes = save_pgfplots(fig, "figures/loss.tex")  # width=r"\linewidth" by default; "3.25in", r"\textwidth"...
```

```latex
\usepackage{pgfplots}\pgfplotsset{compat=1.18}   % in the preamble
\begin{figure}\centering\input{figures/loss.tex}\caption{...}\end{figure}
```

The axes sit where matplotlib put them. Exported: lines (colour, width, dashes, markers), scatter points, bars and
other rectangles, `fill_between`, error bars, text, axis labels, titles, limits, log scales, ticks and their labels,
grids, legends. Labels are escaped for LaTeX, with `$...$` maths kept. What is not exported (images, colour bars, 3D
axes, figure-level text) is returned in `notes` and written as comments at the top of the file: for those, save a PDF
and check it. It fills the role tikzplotlib did, for the parts of a figure papers mostly have; the code it writes was
compiled with pdflatex and compared with the matplotlib figure.

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

- Widths from a style file or class the tool does not know (memoir, an acmart format not measured...) are not
  read: it says so and uses `article`'s; give `--template`, or check figures with `--width`. Widths set in a macro, or by
  arithmetic beyond `\setlength` and `\addtolength`, are not followed.
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
