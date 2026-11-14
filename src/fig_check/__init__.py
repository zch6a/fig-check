"""fig-check: a paper's figures as they will print."""

__version__ = "0.2.0"

from .check import Finding, Limits, Report, check_bytes, check_file  # noqa: E402
from .figure import check_figure  # noqa: E402
from .pgf import save_pgfplots, to_pgfplots  # noqa: E402
from .style import embedded_fonts, paper_style, save_for_paper  # noqa: E402

__all__ = [
    "Finding", "Limits", "Report", "check_bytes", "check_figure", "check_file", "embedded_fonts", "paper_style", "save_for_paper",
    "save_pgfplots", "to_pgfplots", "__version__",
]  # fmt: skip
