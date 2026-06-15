from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def save_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def save_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_parsed(parsed_dir: Path, rel_path: str, data: Any) -> Path:
    """Write under parsed/ with standard envelope."""
    out = parsed_dir / rel_path
    if isinstance(data, dict) and "fetched_at" not in data:
        data = {**data, "fetched_at": datetime.now(timezone.utc).isoformat()}
    return save_json(out, data)


def load_manifest(parsed_dir: Path) -> dict[str, Any]:
    path = parsed_dir / "manifest.json"
    if path.exists():
        return load_json(path)
    return {"sources": {}, "fetched_at": None}


def update_manifest(parsed_dir: Path, source: str, meta: dict[str, Any]) -> Path:
    manifest = load_manifest(parsed_dir)
    manifest.setdefault("sources", {})[source] = {
        **meta,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return save_json(parsed_dir / "manifest.json", manifest)
