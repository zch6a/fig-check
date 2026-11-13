"""Writes examples/paper: a made-up NeurIPS-style project with three figures, one of each kind of problem and one fine.
The README's output is fig-check run on it (a test checks they agree)."""

from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "tests"))
from make import pdf, png  # noqa: E402

FONT = b"/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >>"

out = root / "examples" / "paper"
(out / "figures").mkdir(parents=True, exist_ok=True)
(out / "main.tex").write_text(
    r"""\documentclass{article}
\usepackage[final]{neurips_2025}
\usepackage{graphicx}
\graphicspath{{figures/}}
\begin{document}
% A made-up paper, for fig-check's example: three figures as a paper might have them.
\begin{figure}
  \centering
  \includegraphics[width=0.48\linewidth]{loss}
  \caption{Training loss: drawn 6 inches wide with 10 pt labels, printed at less than half that size, in red and green.}
\end{figure}
\begin{figure}
  \centering
  \includegraphics[width=\linewidth]{samples}
  \caption{Samples: a 640-pixel-wide image stretched over the text width.}
\end{figure}
\begin{figure}
  \centering
  \includegraphics[width=0.6\linewidth]{method}
  \caption{The method: drawn at the size it prints, in blue and orange.}
\end{figure}
\end{document}
""",
    encoding="utf-8",
    newline="\n",
)

loss = (b"BT /F1 10 Tf 40 20 Td (step) Tj ET BT /F1 10 Tf 0 1 -1 0 15 100 Tm (loss) Tj ET "
        b"0.84 0.15 0.16 RG 2 w 50 40 m 200 150 l 400 180 l S 0.17 0.63 0.17 RG 50 60 m 200 120 l 400 160 l S")  # fmt: skip
(out / "figures" / "loss.pdf").write_bytes(pdf(loss, width=432, height=288, resources=FONT))
(out / "figures" / "samples.png").write_bytes(png(640, 320, [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]))
method = (b"BT /F1 8 Tf 20 20 Td (encoder) Tj ET BT /F1 8 Tf 150 20 Td (decoder) Tj ET "
          b"0.0 0.45 0.70 rg 20 40 100 60 re f 0.90 0.62 0.0 rg 150 40 100 60 re f")  # fmt: skip
(out / "figures" / "method.pdf").write_bytes(pdf(method, width=237.6, height=120, resources=FONT))
print(f"wrote {out.relative_to(root).as_posix()}")
