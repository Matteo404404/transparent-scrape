"""HowTheyVote.eu roll-call exports (ODbL) — rebellion stats per MEP."""

from __future__ import annotations

import csv
import gzip
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transparent_scrape.core.config import (
    HTV_MEMBER_VOTES_URL,
    HTV_MEMBERS_URL,
    HTV_VOTES_URL,
)
from transparent_scrape.core.http import download
from transparent_scrape.core.storage import save_json, update_manifest

VALID_POSITIONS = frozenset({"FOR", "AGAINST", "ABSTENTION"})


def _download_gz(url: str, dest: Path, *, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return dest
    return download(url, dest)


def _group_majority_per_vote(member_votes_path: Path) -> dict[tuple[str, str], str]:
    """vote_id + group_code -> majority position (FOR/AGAINST/ABSTENTION)."""
    buckets: dict[tuple[str, str], Counter[str]] = {}
    with gzip.open(member_votes_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pos = (row.get("position") or "").strip().upper()
            if pos not in VALID_POSITIONS:
                continue
            key = (row.get("vote_id") or "", row.get("group_code") or "")
            if not key[0] or not key[1]:
                continue
            buckets.setdefault(key, Counter())[pos] += 1

    majority: dict[tuple[str, str], str] = {}
    for key, counts in buckets.items():
        if counts:
            majority[key] = counts.most_common(1)[0][0]
    return majority


def compute_rebellion_stats(member_votes_path: Path) -> dict[str, dict[str, Any]]:
    majority = _group_majority_per_vote(member_votes_path)
    stats: dict[str, dict[str, Any]] = {}

    with gzip.open(member_votes_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            mep_id = (row.get("member_id") or "").strip()
            vote_id = (row.get("vote_id") or "").strip()
            group = (row.get("group_code") or "").strip()
            pos = (row.get("position") or "").strip().upper()
            if not mep_id or not vote_id or not group:
                continue

            bucket = stats.setdefault(
                mep_id,
                {
                    "rcv_participated": 0,
                    "rebel_votes": 0,
                    "group_code": group,
                },
            )
            if pos in VALID_POSITIONS:
                bucket["rcv_participated"] += 1
                maj = majority.get((vote_id, group))
                if maj and pos != maj:
                    bucket["rebel_votes"] += 1
            bucket["group_code"] = group

    for row in stats.values():
        part = row["rcv_participated"] or 0
        rebels = row["rebel_votes"] or 0
        row["rebel_rate"] = round(rebels / part, 4) if part else None

    return stats


def _load_member_names(members_path: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    if not members_path.exists():
        return names
    with gzip.open(members_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            mid = (row.get("id") or "").strip()
            if not mid:
                continue
            first = (row.get("first_name") or "").strip()
            last = (row.get("last_name") or "").strip()
            names[mid] = f"{first} {last}".strip()
    return names


def _vote_count(votes_path: Path) -> int:
    if not votes_path.exists():
        return 0
    count = 0
    with gzip.open(votes_path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for _ in reader:
            count += 1
    return count


def fetch_and_parse(
    parsed_dir: Path,
    raw_dir: Path,
    *,
    force: bool = False,
) -> Path:
    raw_htv = raw_dir / "howtheyvote"
    member_votes = _download_gz(HTV_MEMBER_VOTES_URL, raw_htv / "member_votes.csv.gz", force=force)
    members = _download_gz(HTV_MEMBERS_URL, raw_htv / "members.csv.gz", force=force)
    votes = _download_gz(HTV_VOTES_URL, raw_htv / "votes.csv.gz", force=force)

    by_mep = compute_rebellion_stats(member_votes)
    names = _load_member_names(members)

    ranked = sorted(
        (
            {
                "mep_id": mid,
                "name": names.get(mid),
                **row,
            }
            for mid, row in by_mep.items()
        ),
        key=lambda r: (-(r.get("rebel_votes") or 0), -(r.get("rcv_participated") or 0)),
    )

    payload = {
        "source": "howtheyvote",
        "license": "ODbL-1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "HowTheyVote.eu — https://howtheyvote.eu/about",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "vote_count": _vote_count(votes),
        "mep_count": len(by_mep),
        "by_mep_id": by_mep,
        "top_rebels": ranked[:25],
    }

    out_dir = parsed_dir / "howtheyvote"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = save_json(out_dir / "voting_summary.json", payload)
    update_manifest(parsed_dir, "howtheyvote", {"mep_count": len(by_mep), "vote_count": payload["vote_count"]})
    return path
