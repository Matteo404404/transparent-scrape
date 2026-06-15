"""EPDB (European Parliament Data Base) — Council + EP vote API probe."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from transparent_scrape.core.config import EPDB_API_BASE
from transparent_scrape.core.storage import save_json, update_manifest

PROBE_PATHS = (
    "/",
    "/v1/",
    "/api/",
    "/docs",
    "/openapi.json",
)


def probe_api() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    reachable = False
    for path in PROBE_PATHS:
        url = f"{EPDB_API_BASE.rstrip('/')}{path}"
        entry: dict[str, Any] = {"url": url, "ok": False}
        try:
            with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                resp = client.get(url, headers={"User-Agent": "transparent-scrape/0.1"})
                entry["status"] = resp.status_code
                entry["ok"] = resp.status_code < 400
                if entry["ok"]:
                    reachable = True
                entry["content_type"] = resp.headers.get("content-type", "")
                if "json" in entry["content_type"] and len(resp.content) < 50_000:
                    try:
                        entry["sample"] = resp.json()
                    except Exception:
                        entry["sample_text"] = resp.text[:500]
        except Exception as exc:
            entry["error"] = str(exc)
        results.append(entry)

    return {
        "source": "epdb",
        "api_base": EPDB_API_BASE,
        "site": "https://www.epdb.eu/",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reachable": reachable,
        "note": (
            "Council and EP vote aggregates; integrate when stable endpoints are documented."
            if reachable
            else "API not reachable from this environment — retry later or use manual export."
        ),
        "probes": results,
    }


def fetch_status(parsed_dir: Path) -> Path:
    payload = probe_api()
    out_dir = parsed_dir / "epdb"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = save_json(out_dir / "status.json", payload)
    update_manifest(parsed_dir, "epdb", {"reachable": payload["reachable"]})
    return path
