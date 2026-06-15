"""OpenSanctions eu_meps bulk dataset (PEP metadata, Wikidata links)."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transparent_scrape.core.config import OPENSANCTIONS_EU_MEPS_CSV
from transparent_scrape.core.http import download
from transparent_scrape.core.storage import save_json, update_manifest

MEP_ID_RE = re.compile(r"/meps/en/(\d+)")


def _mep_id_from_source_url(url: str) -> str | None:
    match = MEP_ID_RE.search(url or "")
    return match.group(1) if match else None


def parse_targets_csv(path: Path) -> dict[str, Any]:
    by_mep_id: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source_url = row.get("sourceUrl") or row.get("source_url") or ""
            # targets.simple.csv has no sourceUrl column; use identifiers if present
            mep_id = None
            if source_url:
                mep_id = _mep_id_from_source_url(source_url)
            if not mep_id:
                for ident in (row.get("identifiers") or "").split(";"):
                    ident = ident.strip()
                    if ident.isdigit() and len(ident) >= 5:
                        mep_id = ident
                        break
            entry = {
                "opensanctions_id": row.get("id"),
                "name": row.get("name"),
                "countries": [c.strip() for c in (row.get("countries") or "").split(";") if c.strip()],
                "birth_date": row.get("birth_date") or None,
                "aliases": [a.strip() for a in (row.get("aliases") or "").split(";") if a.strip()],
                "dataset": row.get("dataset"),
                "last_seen": row.get("last_seen"),
            }
            rows.append(entry)
            if mep_id:
                by_mep_id[mep_id] = entry

    return {
        "source": "opensanctions",
        "dataset": "eu_meps",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "csv_path": str(path),
        "total_rows": len(rows),
        "linked_mep_count": len(by_mep_id),
        "by_mep_id": by_mep_id,
        "rows": rows,
    }


def parse_entities_ftm_jsonl(path: Path) -> dict[str, Any]:
    """Parse entities.ftm.json (newline-delimited JSON) with sourceUrl on Person rows."""
    import json

    by_mep_id: dict[str, dict[str, Any]] = {}
    person_count = 0

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("schema") != "Person":
                continue
            person_count += 1
            props = obj.get("properties") or {}
            source_urls = props.get("sourceUrl") or []
            mep_id = None
            for url in source_urls:
                mep_id = _mep_id_from_source_url(url)
                if mep_id:
                    break
            entry = {
                "opensanctions_id": obj.get("id"),
                "name": (props.get("name") or [""])[0],
                "first_name": (props.get("firstName") or [""])[0] or None,
                "last_name": (props.get("lastName") or [""])[0] or None,
                "citizenship": props.get("citizenship") or [],
                "source_url": source_urls[0] if source_urls else None,
                "topics": props.get("topics") or [],
            }
            if mep_id:
                by_mep_id[mep_id] = entry

    return {
        "source": "opensanctions",
        "dataset": "eu_meps",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ftm_path": str(path),
        "person_count": person_count,
        "linked_mep_count": len(by_mep_id),
        "by_mep_id": by_mep_id,
    }


def fetch_and_parse(parsed_dir: Path, raw_dir: Path, *, use_ftm: bool = True) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir = parsed_dir / "opensanctions"
    out_dir.mkdir(parents=True, exist_ok=True)

    if use_ftm:
        dest = raw_dir / "opensanctions_eu_meps.ftm.json"
        url = OPENSANCTIONS_EU_MEPS_CSV.replace("targets.simple.csv", "entities.ftm.json")
        download(url, dest)
        payload = parse_entities_ftm_jsonl(dest)
        out = save_json(out_dir / "eu_meps.json", payload)
    else:
        dest = raw_dir / "opensanctions_eu_meps.csv"
        download(OPENSANCTIONS_EU_MEPS_CSV, dest)
        payload = parse_targets_csv(dest)
        out = save_json(out_dir / "eu_meps.json", payload)

    update_manifest(
        parsed_dir,
        "opensanctions",
        {"linked_mep_count": payload.get("linked_mep_count", 0)},
    )
    return out
