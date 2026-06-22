"""Generic raw/parsed layout (domain-agnostic)."""

from __future__ import annotations

from pathlib import Path


def base_paths(root: Path) -> dict[str, Path]:
    root = Path(root)
    return {"root": root, "raw": root / "raw", "parsed": root / "parsed"}


def raw_subdir(root: Path, *parts: str) -> Path:
    return Path(root) / "raw" / Path(*parts)


def parsed_subdir(root: Path, name: str) -> Path:
    return Path(root) / "parsed" / name
