---
name: fig-check
description: Check a paper's figures with fig-check before submission: text size at the size it prints (the figure's scale in the LaTeX paper applied), colour pairs that people with protanopia, deuteranopia or tritanopia cannot tell apart, and raster images too coarse for print, for every figure of a LaTeX project (NeurIPS, ICLR, ICML, CVPR/ICCV, ACL, AAAI templates detected) or single PDF/PNG/JPEG/SVG files. Use when the user asks whether their figures are readable, colour-blind friendly or high enough resolution, or to check a paper's figures before submitting.
license: MIT
compatibility: Needs Python 3.10+ and uv. Runs fig-check with uvx from GitHub (git+https://github.com/zch6a/fig-check) unless installed. Reads local files only; no network.
metadata:
  homepage: https://github.com/zch6a/fig-check
---

# Checking a paper's figures with fig-check

```bash
uvx --from git+https://github.com/zch6a/fig-check fig-check paper/                     # a LaTeX project
uvx --from git+https://github.com/zch6a/fig-check fig-check plot.pdf --width 3.25in    # one figure at a printed width
```

- Read back the first line: the template it detected and the widths it used. If the venue is wrong or "article", ask
  the user for it and pass `--template` (neurips, iclr, icml, cvpr, acl, aaai).
- For each finding, say what to change in the figure's source, not only that it is wrong:
  - small text: the figure is printed at N% of its size; make it at the printed width (e.g. matplotlib
    `figsize=(3.25, 2.2)`) with 7–9 pt fonts, rather than shrinking a large one;
  - colours: tell the series apart by more than hue (line style, markers, direct labels, lightness), or use a
    colour-blind-safe palette (Okabe–Ito; matplotlib's `tableau-colorblind10` style);
  - resolution: export at the printed size × 300 dpi, or as a vector file (PDF/SVG) for plots.
- Exit status 1 means there is something to fix; `--json` gives the reports. A note about paths built by macros means
  those figures were not checked: run it on those files directly with `--width`.
