# Polish log

### 2026-11-13 — development

**Why it exists**: figures are drawn on screen, at their own size, and printed at another, in a column; small labels,
red–green pairs and stretched raster images go unseen until the PDF is printed or a reviewer complains. No tool checks
a whole LaTeX project's figures at the size each one prints at. (submit-check checks the submission's rules, not its
figures; the tikzplotlib successor in the plan comes later, as its own piece.)

**What it does**: reads a LaTeX project (every `\includegraphics`, through `\input`/`\include`, with `width`,
`height`, `scale`, `\resizebox` and the line width in `figure`, `figure*`, `wrapfigure`, `subfigure`, `minipage`),
the venue's widths from the style file the preamble loads, and checks each figure: text size when printed, colour
pairs that collapse with colour vision deficiency, raster resolution (of raster figures and of images inside PDFs).

**A PDF reader with the standard library**: objects, Flate/ASCIIHex/ASCII85 streams, object streams; the page's
content interpreted (graphics state, text matrices, Type 3 font matrices, colour spaces, path painting, form XObjects
with their matrices, images and inline images), with caps against hostile files. PNG decoded (filters) for its main
colours, JPEG read for its size, SVG with transforms and simple style rules.

**Checked against sources** (read on 2026-11-13):

- CIEDE2000 against all 34 pairs of Sharma, Wu and Dalal's published test data (a test each).
- Machado, Oliveira and Fernandes's simulation matrices against the authors' table, digit for digit. Their page does
  not say linear or gamma RGB; the docstring now says linear is this tool's reading (an earlier wording claimed the
  paper said so: corrected).
- The template widths from the style files themselves: `neurips_2020.sty` (bundled in a paper's source), ICLR's
  master template, `icml2025.sty`, `cvpr.sty` and `iccv.sty`, ACL's `acl.sty` (geometry margins), `aaai25.sty`.
  NeurIPS's, ICML's and AAAI's own pages answered 404/500; their style files came from a paper's source and from
  template copies on GitHub (the same files).
- The default limits: Elsevier's "7 pt for normal text" (6 for sub- and superscripts) and IEEE's ">300dpi" for colour
  and greyscale images. The error limits (5 pt, 150 dpi) are the tool's own, and the README says so.

**Tried on three real papers' sources** (ControlNet, DDPM, Segment Anything; fetched to the scratchpad, deleted
after, with older fetched sources there):

1. Paths built by macros (`\iftoggle{hqfigures}{a}{b}`, 13 in DDPM) were "not found" errors: counted in one note.
2. `figs/sa1b_examples/#3.jpg` inside a `\newcommand` was "not found": macro parameters are skipped.
3. One figure with 38 low-resolution embedded images gave 38 warnings: one finding naming the worst.
4. Segment Anything loads its style as `\usepackage{iccv, times, epsfig, ...}`, which detection missed (it matched
   a lone package): every package of every list is matched now; its teaser is then checked at 6.81 in, not 4.73.

The findings looked right: ControlNet's figures drawn large and printed at 13–32% (5.5 pt labels), matplotlib's
default green against red (deuteranopia) and orange (protanopia, ΔE 1.3) in Segment Anything's plots.

`examples/paper` is a made-up project written by `scripts/example.py`; a test checks the README's output against it,
and CI checks that the generator reproduces the committed files.

Tests: 66 (with doctests). ruff, mypy clean.

First CI run failed on every job, two causes: the `.gitignore` line keeping fetched papers' PDFs out (`*.pdf`) also
kept the example's PDFs out, so the README test found them missing (now `!/examples/**/*.pdf`); and the regenerated
PNG's bytes differ with zlib's version, so CI compares PNGs by their decompressed image (`scripts/same_png.py`) and
the rest byte for byte. Also: one commit went in with `ruff format --check` failing; fixed in the next. CI green.

Next: polishing round 1 (widths set in the preamble, `\setlength{\textwidth}` and `geometry`; a matplotlib API to
check a figure before saving it; then the pgfplots exporter).

### 2026-11-13 — polishing round 1

**Widths set in the preamble** (the gap the first version's README named): `layout()` works out the text and column
width as LaTeX does, in order: the template given, or the style the preamble loads, or `article`'s widths from the
class options; then the preamble's `geometry` options (package options and `\geometry{}`, which add to each other),
`\setlength`/`\addtolength`/assignments of `\textwidth` and `\columnsep`. The header says what set them.

- Read from the files themselves (MiKTeX's `article.cls`, `size10/11/12.clo`, `geometry.sty`): `\textwidth` is the
  smaller of `\paperwidth`−2in and 345/360/390 pt (twice that with `twocolumn`), rounded down to whole points;
  `\columnsep` 10 pt; geometry lays the page out when loaded, options or not (0.7 of the paper's width by default),
  reads the class options, and with one margin alone gives the other the first share of the default margins (1:1,
  2:3 with `twoside`).
- **Found by checking against pdflatex**: the first version took `\documentclass[twocolumn]{article}` as one 345 pt
  column; LaTeX sets 469 pt text and 229.5 pt columns. Fixed with the rest.
- Checked against pdflatex itself: 33 preambles compiled, each one's `\textwidth` and `\columnwidth` printed; all
  agree to 0.01 pt. Two disagreed on the first try (one margin alone, `landscape` as a geometry option) and one on
  the second (`twoside`); fixed from geometry's source. The widths pdflatex printed are the test table, so the tests
  need no TeX.
- A class it does not know (revtex, IEEEtran...) is said, with `--template` suggested; geometry's `pass` is honoured;
  settings after `\begin{document}` or inside macro definitions are not the preamble's.

**A matplotlib API**: `check_figure(fig, width="column", template="icml")` saves the figure to memory as a PDF and
checks it like a file (nothing written to disk; matplotlib is not a dependency, anything with `savefig` will do).
Widths as inches, TeX lengths, or the template's "column" and "text"; other keyword arguments go to `savefig`.
`check_file`, `check_bytes`, `Report` and `Limits` are exported; a report prints as the command prints it (the CLI
uses the same `__str__`).

- Tried on real matplotlib figures (3.10/3.11, Type 3 and TrueType fonts): a 6×4 in figure at ICML's column width has
  5.4 pt labels and matplotlib's default red–green pair (ΔE 4.6 with deuteranopia); a 3.25 in one with 7–8 pt labels,
  markers and Okabe–Ito colours passes; an `imshow` image is rasterised at the figure's dpi (100 pixels per inch at
  that size), so the README says to pass `dpi=300`. The README's sample output is that run's.
- matplotlib is in the dev group so CI runs the real-figure test; the lock's sources are pypi.org.

**Docs**: README (both languages), CHANGELOG, the skill. **Code**: one `Report.__str__` replaces the CLI's printer;
`check_bytes` split from `check_file`. ruff now formats README code blocks: done.

Tests: 117 (33 from pdflatex's widths, 10 for `check_figure`). ruff, ruff format, mypy clean.

Next: polishing round 2 (the pgfplots exporter for matplotlib, the tikzplotlib successor; IEEEtran and acmart widths;
a social card).