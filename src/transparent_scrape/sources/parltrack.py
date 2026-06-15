"""Parltrack bulk dumps (ODbL) — MEP index + dump freshness."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transparent_scrape.core.config import PARLTRACK_DUMPS_PAGE, PARLTRACK_MEPS_DUMP
from transparent_scrape.core.http import download, get_text
from transparent_scrape.core.storage import save_json, update_manifest

EP_ID_RE = re.compile(r"/meps/(?:en/)?(\d+)")


def _decompress_zst(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["zstd", "-dc", str(src)],
        capture_output=True,
        check=True,
    )
    dest.write_bytes(proc.stdout)


def parse_dumps_page(html: str) -> list[dict[str, Any]]:
    """Best-effort parse of parltrack dumps table rows."""
    rows: list[dict[str, Any]] = []
    for match in re.finditer(
        r"<tr>\s*<td>([^<]+)</td>\s*<td>[^<]*</td>\s*<td><a href=\"([^\"]+)\">",
        html,
        re.I | re.S,
    ):
        name = match.group(1).strip()
        href = match.group(2).strip()
        if not href.startswith("http"):
            href = f"https://parltrack.eu{href}" if href.startswith("/") else f"https://parltrack.eu/dumps/{href}"
        rows.append({"table": name, "url": href})
    return rows


def fetch_dumps_status(parsed_dir: Path) -> Path:
    html = get_text(PARLTRACK_DUMPS_PAGE)
    payload = {
        "source": "parltrack",
        "license": "ODbL-1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "Parltrack — https://parltrack.eu/",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "dumps": parse_dumps_page(html),
    }
    out_dir = parsed_dir / "parltrack"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = save_json(out_dir / "dumps_status.json", payload)
    update_manifest(parsed_dir, "parltrack_status", {"dump_tables": len(payload["dumps"])})
    return path


def _ep_id_from_mep(row: dict[str, Any]) -> str | None:
    meta = row.get("meta") or {}
    url = meta.get("url") or ""
    match = EP_ID_RE.search(str(url))
    if match:
        return match.group(1)
    user_id = row.get("UserID")
    return str(user_id) if user_id is not None else None


def fetch_meps_index(
    parsed_dir: Path,
    raw_dir: Path,
    *,
    force: bool = False,
    active_only: bool = True,
) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    zst_path = raw_dir / "parltrack" / "ep_meps.json.zst"
    json_path = raw_dir / "parltrack" / "ep_meps.json"
    if force or not zst_path.exists():
        download(PARLTRACK_MEPS_DUMP, zst_path)
    if force or not json_path.exists() or json_path.stat().st_mtime < zst_path.stat().st_mtime:
        _decompress_zst(zst_path, json_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    by_ep_id: dict[str, dict[str, Any]] = {}
    for row in data:
        ep_id = _ep_id_from_mep(row)
        if not ep_id:
            continue
        if active_only and row.get("active") is False:
            continue
        name = (row.get("Name") or {}).get("full") or ""
        by_ep_id[ep_id] = {
            "parltrack_user_id": row.get("UserID"),
            "name": name,
            "active": row.get("active"),
            "profile_url": f"https://parltrack.eu/meps/{ep_id}",
            "updated": (row.get("meta") or {}).get("updated"),
        }

    payload = {
        "source": "parltrack",
        "license": "ODbL-1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "Parltrack — https://parltrack.eu/",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "mep_count": len(by_ep_id),
        "by_ep_id": by_ep_id,
    }
    out_dir = parsed_dir / "parltrack"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = save_json(out_dir / "meps_index.json", payload)
    update_manifest(parsed_dir, "parltrack_meps", {"mep_count": len(by_ep_id)})
    return path
