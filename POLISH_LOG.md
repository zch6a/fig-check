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
### 2026-11-13 — polishing round 2

**Classes**: `IEEEtran`, `acmart`, `llncs`, `elsarticle` and `revtex4-2` were "not known" (article's widths, with a
note). Their widths depend on options, and the class files compute them in many steps, so they were measured: each
class compiled with pdflatex for its main options (38 runs), `\textwidth` and `\columnwidth` printed, and the table
holds those numbers. IEEEtran: 516/252 pt for 9–12pt, letter or A4, conference, journal, technote; `compsoc`,
`onecolumn`, `peerreview` and `draftcls` differ and are listed. **Found while measuring**: acmart reports one column
at `\begin{document}` and turns two columns on at `\maketitle`; measured there (sigconf 241.1 pt, not 506.3). An acmart
format not measured is not guessed. `--template ieee`, `acm`, `lncs` added. Geometry over IEEEtran checked against
pdflatex (505.89 / 246.94 pt). Tests: the 25 measured cases.

**pgfplots exporter** (`save_pgfplots`, `to_pgfplots`), the tikzplotlib successor in the plan: the fix for small text
that does not shrink the figure at all. The axes sit where matplotlib put them, as fractions of `\linewidth` (or a
width given); lines, markers, scatter, bars and rectangles, `fill_between`, error bars, text (data or axes
coordinates), labels, titles, limits, log scales, ticks with their labels, grids, legends (unlabelled plots marked
`forget plot` so entries stay matched). What it cannot export is returned and written as comments.

- Compiled with pdflatex and pgfplots 1.18 in a two-column paper, rendered and compared with the matplotlib figures.
  Two failures on the way: lengths in a macro (`0.67\fcw` is not a length when `\fcw` holds `252pt`: products written
  with `*` for pgfmath), and matplotlib's log tick labels (`$\mathdefault{10^{1}}$`, undefined in LaTeX: unwrapped).
  The rendered result matched the figures (an `imshow` in the sample had reset its axes' limits, as matplotlib does;
  the sample was at fault, not the export).
- Labels are escaped for LaTeX outside `$...$`; maths is passed through (the user's own figure).
- Writes only the file it is given. Tests check the code's structure with real matplotlib figures (no TeX needed).

**Docs**: README (both languages: the classes in the widths table, a pgfplots section), CHANGELOG, the skill.

Tests: 158 (+2 skipped doctests of examples needing a figure). ruff, ruff format, mypy clean.

Next: polishing round 3 (a social card; a look at real papers' figures again with the new widths; review pass).
### 2026-11-13 — polishing round 3

**An independent review** (a separate reviewer given the code, not my conclusions) of rounds 1–2, each finding
reproduced against pdflatex or by compiling the exported code. All fixed except two, below.

`layout()`, each fix checked against pdflatex (the table is now 51 preambles, all within 0.01 pt):

- `\advance\textwidth 2cm` was read as an assignment (57 pt instead of 402): handled as an addition.
- Repeated `\geometry` calls: pdflatex showed that when both margins are set a width is over-specified and dropped,
  whatever the order; the reviewer's suggested "later call wins" was wrong for one order, and pdflatex decided it.
- `columnsep=0pt` was ignored (`or` on a zero): `is not None`.
- `16,5cm` (TeX takes a decimal comma) now read; `\dimexpr` and other macros are named in the header as "not read"
  instead of silently ignored, as is geometry's `includemp`.
- `bindingoffset`, `hmarginratio`/`centering` with one margin, `\PassOptionsToPackage{...}{geometry}`, `fullpage`
  (and `[cm]`), geometry's ISO A0–A6 and B0–B6 papers (and the class's paper option read by geometry, but not by
  article itself) — all matched with pdflatex.
- A setting that would leave no text width is refused and named.

`to_pgfplots`, each fix compiled with pdflatex and the page compared with the matplotlib figure:

- Categorical and date data were raw strings (a "Dimension too large" stop, or empty plots): `get_xydata()`, matplotlib's
  own unit conversion. Masked values and NaN gaps break the line (`unbounded coords=jump`), NaN bars are skipped.
- Legends: built from matplotlib's legend itself (its handles, texts and order, `\addlegendimage` for each), so
  `ax.legend(["a","b"])`, bar entries and mixed scatter/line legends are right; placed where matplotlib put it (its
  bounding box), "best" included, instead of a fixed corner.
- `\mathregular` (undefined in LaTeX) becomes `\mathrm`; ≥, µ, Greek letters and dashes become LaTeX that pdflatex's
  default fonts set.
- Inverted axes (min/max kept ordered, `dir=reverse`), line `alpha`, hollow circles (`mark=` was empty), `twinx`
  (axis lines left/right), rotated tick labels, pgfplots' own tick scaling turned off (it added ×10⁴ to date axes),
  matplotlib's scale factor (1e7) drawn after the axis where pgfplots does not clip it, annotation arrows noted.
- `check_figure`: numpy floats, widths of 0 or less, the template always checked, `format=` refused.

Not done: AAAI-26's style name (the reviewer thought `aaai2026.sty`; not verified, so detection is unchanged), and
an error bar's legend symbol is a line, not its marker.

**Real papers again** (SegNet: IEEEtran compsoc journal; LIME: an old ACM class; GPT-3, Adam, LoRA, EfficientNet;
fetched to the scratchpad, deleted after): IEEEtran's Computer Society widths applied (7.17/3.50 in). **Found**:
EfficientNet loads its style as `\usepackage[accepted]{sty/icml2019}`, a folder in the name, and got article's
widths: styles are matched by their file name now (ICML, 3.25 in column). LIME's `sig-alternate` is named as not
known. Adam's source has no figures, and fig-check says so.

**Social card**: `scripts/social-card.html`, rendered with headless Chrome (no network, its own profile, deleted
after) to `docs/social-preview.png`, with fig-check's own output on the example. Setting it as the repository's
social preview is a repository setting for its owner.

Tests: 184 (51 preambles and 25 class cases from pdflatex; 17 for the exporter). ruff, ruff format, mypy clean.

Next: polishing round 4 (an end-to-end check: a paper with exported pgfplots figures compiled and checked by
fig-check itself; CLI and JSON output review; packaging check of the wheel).
### 2026-11-13 — polishing round 4

**CLI and JSON, tried on the awkward cases** (no arguments, a missing file, an empty folder, a text file, `--width 3`,
`--json`, a figure with no width):

- A text file given by mistake was "1 figure(s), 0 with something to fix", exit status 0: now an error (exit 2), "not a
  figure (PDF, PNG, JPEG or SVG), nor a LaTeX project".
- `--width 3` now suggests `3in`.
- `--json` was a bare list of figures, without the widths they were checked at or how those were found: now
  `{"version", "limits", "projects": [{"main", "template", "how", "text_width", "column_width"}], "figures": [...]}`
  (before 0.1.0, so no one's parser breaks), with numbers rounded to 4 decimals (it printed `2.6399999999999997`).
- A project's TikZ and pgfplots figures are counted in a note (their text is the paper's own).

**End to end** (local, with pdflatex; CI has no TeX): one 6 × 4 in matplotlib figure in a two-column paper, included
as a PDF at the column width and exported with `save_pgfplots`; each compiled paper checked by fig-check at its own
size. As a PDF: 5.3 pt text, all 16 pieces under 7 pt. As pgfplots: 10 pt. This also checked the PDF reader on
pdflatex's own output (the included figure as a form XObject, scaled). The README gives the result.

**Packaging**: wheel and sdist built and listed. The wheel has the package only (no tests, docs or examples); the sdist
has the tests and the example, so its tests run. Installed into a clean Python 3.10 environment: `fig-check --version`,
the example project, and `import fig_check` without matplotlib loaded all work. Added: `py.typed` (the API has types),
classifiers (Matplotlib, Visualization, LaTeX, Typed), a description naming the matplotlib and pgfplots parts.

Tests: 186. ruff, ruff format, mypy clean.

Next: polishing round 5 (a last review of everything against the "polish" definition; docs read through end to end;
then v0.1.0).