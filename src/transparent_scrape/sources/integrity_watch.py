"""Integrity Watch EU datahub status (bulk export currently unavailable)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transparent_scrape.core.config import INTEGRITY_WATCH_DATAHUB
from transparent_scrape.core.http import get_text
from transparent_scrape.core.storage import save_json, update_manifest

MAINTENANCE_MARKERS = (
    "upgrading the integrity watch datahub",
    "revamping the iw eu datahub",
    "stay tuned for more info",
)


def check_datahub_status(html: str) -> dict[str, Any]:
    low = html.lower()
    maintenance = any(marker in low for marker in MAINTENANCE_MARKERS)
    return {
        "url": INTEGRITY_WATCH_DATAHUB,
        "available": not maintenance and len(html) > 200,
        "maintenance": maintenance,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Datahub offline; EC meetings and lobby register already covered via official sources."
            if maintenance
            else "Datahub reachable; manual export integration pending."
        ),
    }


def fetch_status(parsed_dir: Path) -> Path:
    html = get_text(INTEGRITY_WATCH_DATAHUB)
    status = check_datahub_status(html)
    out_dir = parsed_dir / "integrity_watch"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = save_json(out_dir / "status.json", status)
    update_manifest(parsed_dir, "integrity_watch", status)
    return path
