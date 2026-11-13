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
