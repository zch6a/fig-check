# Contributing

```bash
uv sync
uv run pytest -q          # made-up figures only (tests/make.py writes them); no network
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## Where things are

| Module | What it does |
| --- | --- |
| `pdf.py` | a PDF read with the standard library: objects, streams, the page's content interpreted for text sizes, colours and images |
| `raster.py` | PNG (size, resolution, main colours) and JPEG (size, resolution) |
| `svg.py` | SVG sizes, text sizes and colours |
| `color.py` | sRGB to CIELAB, CIEDE2000, the colour vision deficiency simulation |
| `latex.py` | a project's figures and the widths they print at; the templates |
| `check.py` | the checks and their limits |
| `figure.py` | `check_figure`: a matplotlib figure checked in memory |
| `pgf.py` | `to_pgfplots` / `save_pgfplots`: a matplotlib figure as pgfplots code |
| `cli.py` | `fig-check` |

`examples/paper` is made by `scripts/example.py`; a test checks that the README shows what fig-check prints for it.

## Adding a template or a class

For a conference style: read `\textwidth` and `\columnsep` from the venue's own style file, add it to `TEMPLATES` and
`DETECT` in `latex.py` with the file named, and add a line to the README's table.

For a document class, whose widths depend on its options: compile it with pdflatex for each option set, add what
pdflatex prints to `CLASSES` in `latex.py` and to the `CLASSES` table in `tests/test_layout.py`, then run
`uv run python scripts/latex_widths.py` (needs TeX), which compiles every preamble and class in the tests again and
compares pdflatex's widths with the tables and with fig-check's.

The pgfplots exporter's tests check the code it writes; when you change what it writes, also compile a figure that
uses it with pdflatex and compare the page with the matplotlib figure.
