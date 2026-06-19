"""Data-root health check across all source modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from transparent_scrape.core.config import EP_TERM_DEFAULT
from transparent_scrape.core.storage import load_json, load_manifest
from transparent_scrape.sources import ep_api


def _glob_count(parsed: Path, pattern: str) -> int:
    if "*" not in pattern:
        return 1 if (parsed / pattern).exists() else 0
    parent = parsed / Path(pattern).parent
    if not parent.exists():
        return 0
    return len(list(parent.glob(Path(pattern).name)))


def _file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False}
    stat = path.stat()
    info: dict[str, Any] = {"present": True, "bytes": stat.st_size}
    try:
        data = load_json(path)
        if isinstance(data, dict):
            for key in ("vote_count", "mep_count", "reachable", "maintenance", "linked_mep_count"):
                if key in data:
                    info[key] = data[key]
    except (json.JSONDecodeError, OSError):
        pass
    return info


def conflict_pdf_stats(parsed_dir: Path) -> dict[str, int]:
    conflicts_dir = parsed_dir / "declarations" / "conflicts"
    rows = 0
    with_text = 0
    for path in conflicts_dir.glob("*.json"):
        if not path.stem.isdigit():
            continue
        for decl in load_json(path).get("declarations") or []:
            if not decl.get("pdf_url"):
                continue
            rows += 1
            if len((decl.get("pdf_text") or "").strip()) > 100:
                with_text += 1
    return {
        "rows": rows,
        "with_text": with_text,
        "missing_text": rows - with_text,
    }


def audit_data_root(data_root: Path, *, term: int = EP_TERM_DEFAULT) -> dict[str, Any]:
    parsed = data_root / "parsed"
    raw = data_root / "raw"
    gaps = ep_api.audit_gaps(parsed, term=term)
    conflicts = conflict_pdf_stats(parsed)

    lobby_orgs = parsed / "lobby" / "organizations.json"
    lobby_count = 0
    if lobby_orgs.exists():
        payload = load_json(lobby_orgs)
        orgs = payload.get("organizations") if isinstance(payload, dict) else payload
        lobby_count = len(orgs or [])

    wmm_count = _glob_count(parsed, "wmm/*.json")
    manifest = load_manifest(parsed)

    sources: dict[str, Any] = {
        "ep_roster": _file_info(parsed / "meps" / f"term_{term}.json"),
        "lobby": {
            **_file_info(lobby_orgs),
            "organizations": lobby_count if lobby_orgs.exists() else None,
        },
        "wmm_profiles": {"count": wmm_count},
        "conflicts": conflicts,
        "ec_meetings_2429": _file_info(parsed / "ec_meetings" / "2429.json"),
        "opensanctions": _file_info(parsed / "opensanctions" / "eu_meps.json"),
        "howtheyvote": _file_info(parsed / "howtheyvote" / "voting_summary.json"),
        "parltrack_meps": _file_info(parsed / "parltrack" / "meps_index.json"),
        "parltrack_status": _file_info(parsed / "parltrack" / "dumps_status.json"),
        "epdb": _file_info(parsed / "epdb" / "status.json"),
        "integrity_watch": _file_info(parsed / "integrity_watch" / "status.json"),
        "appf_years": {"present": bool(gaps["appf_have"]), "years": gaps["appf_have"]},
    }

    raw_pdfs = list((raw / "declarations").glob("DCI-*.pdf")) if (raw / "declarations").exists() else []

    return {
        "data_root": str(data_root.resolve()),
        "term": term,
        "gaps": gaps,
        "sources": sources,
        "raw_conflict_pdfs": len(raw_pdfs),
        "manifest_sources": list(manifest.get("sources", {}).keys()),
    }


def format_audit_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"data root: {report['data_root']}")
    lines.append(f"term: {report['term']}")
    lines.append("")

    gaps = report["gaps"]
    lines.append("postprocess gaps")
    lines.append(f"  mep enrich (no group): {gaps['mep_enrich_gaps']}")
    lines.append(f"  mep mandate backfill:  {gaps['mep_mandate_gaps']}")
    lines.append(f"  appf missing years:    {gaps['appf_missing'] or 'none'}")
    lines.append(f"  opensanctions needed:  {gaps['opensanctions']}")
    lines.append(f"  integrity_watch needed:{gaps['integrity_watch']}")
    lines.append("")

    c = report["sources"]["conflicts"]
    pct = (100.0 * c["with_text"] / c["rows"]) if c["rows"] else 100.0
    lines.append("conflict dossier PDFs")
    lines.append(f"  rows with pdf_url:     {c['rows']}")
    lines.append(f"  rows with text:        {c['with_text']} ({pct:.1f}%)")
    lines.append(f"  rows missing text:     {c['missing_text']}")
    lines.append(f"  raw pdfs on disk:      {report['raw_conflict_pdfs']}")
    lines.append("")

    lines.append("parsed sources")
    for key, info in report["sources"].items():
        if key == "conflicts":
            continue
        if "count" in info:
            lines.append(f"  {key}: {info['count']} files")
            continue
        if not info.get("present"):
            lines.append(f"  {key}: missing")
            continue
        extra = []
        if info.get("organizations") is not None:
            extra.append(f"{info['organizations']} orgs")
        if info.get("years") is not None:
            extra.append(f"years={info['years']}")
        if info.get("vote_count") is not None:
            extra.append(f"{info['vote_count']} votes")
        if info.get("reachable") is not None:
            extra.append(f"reachable={info['reachable']}")
        if info.get("maintenance") is not None:
            extra.append(f"maintenance={info['maintenance']}")
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"  {key}: ok{suffix}")

    if report["manifest_sources"]:
        lines.append("")
        lines.append(f"manifest keys: {', '.join(report['manifest_sources'])}")

    return "\n".join(lines)
