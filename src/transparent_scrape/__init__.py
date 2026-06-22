"""transparent-scrape — fetch, parse, store public datasets."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("transparent-scrape")
except PackageNotFoundError:
    __version__ = "0.3.0"

from transparent_scrape.core.paths import base_paths, parsed_subdir, raw_subdir
from transparent_scrape.core.pipeline import RunOptions, RunResult, run_sources

__all__ = [
    "RunOptions",
    "RunResult",
    "base_paths",
    "parsed_subdir",
    "raw_subdir",
    "run_sources",
    "__version__",
]
