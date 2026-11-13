# Security

## What it does

- **Nothing over the network.** It reads the files you give it and the project's own files; nothing is sent.
- **Reads, never runs.** LaTeX is read as text (no TeX is run); PDFs are parsed, not rendered; SVGs are parsed
  without DTDs or external entities (a file that declares entities is refused).
- **A hostile file cannot run it long or far**: PDFs over 200 MB and images over 100 million pixels are refused;
  decompressed streams are capped; the PDF interpreter stops after three million operators; nested drawings have a
  depth cap and cycle detection; encrypted PDFs are refused.
- **Writes nothing but what you ask for**: `check_figure` saves the figure to memory; `save_pgfplots` writes the one
  file you name. Text from the figure goes into that file escaped for LaTeX, except maths between `$...$`, which is
  passed through as your figure has it.
- **Inside the project only**: `\input`, `\include` and `\includegraphics` are followed only to files inside the
  project folder.

## Reporting a vulnerability

Please open a private security advisory on GitHub (Security → Report a vulnerability) rather than a public issue.
