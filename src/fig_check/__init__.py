"""fig-check: a paper's figures as they will print."""

__version__ = "0.3.0"

from .check import Finding, Limits, Report, check_bytes, check_file  # noqa: E402
from .diagram import Diagram, diagram  # noqa: E402
from .figure import check_figure  # noqa: E402
from .pgf import save_pgfplots, to_pgfplots  # noqa: E402
from .style import embedded_fonts, paper_style, save_for_paper  # noqa: E402

__all__ = [
    "Diagram",
    "Finding",
    "Limits",
    "Report",
    "check_bytes",
    "check_figure",
    "diagram",
    "check_file",
    "embedded_fonts",
    "paper_style",
    "save_for_paper",
    "save_pgfplots",
    "to_pgfplots",
    "__version__",
]
