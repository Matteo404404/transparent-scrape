"""transparent-scrape — modular public transparency data ingestion."""

from transparent_scrape.core.pipeline import RunOptions, RunResult, run_sources

__version__ = "0.1.0"

__all__ = [
    "RunOptions",
    "RunResult",
    "run_sources",
    "__version__",
]
