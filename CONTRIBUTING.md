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
| `cli.py` | `fig-check` |

`examples/paper` is made by `scripts/example.py`; a test checks that the README shows what fig-check prints for it.

## Adding a template

Read `\textwidth` and `\columnsep` from the venue's own style file, add it to `TEMPLATES` and `DETECT` in
`latex.py` with the file named, and add a line to the README's table.
