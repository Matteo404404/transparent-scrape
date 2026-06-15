from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class Source(Protocol):
    name: str

    def fetch(self, out_dir: Path, **kwargs: Any) -> Path | list[Path]: ...


@dataclass
class RunResult:
    source: str
    paths: list[Path] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
