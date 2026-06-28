from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transparent_scrape.core.config import EP_API, EP_TERM_DEFAULT
from transparent_scrape.core.http import get_json
from transparent_scrape.core.storage import load_json, save_json, save_parsed, update_manifest


_ORG_CACHE: dict[str, str] = {}


def _normalize_email(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        value = value[0] if value else ""
    if not isinstance(value, str):
        value = str(value)
    return value.replace("mailto:", "").strip()


def _resolve_org(org_ref: str) -> str:
    if not org_ref:
        return ""
    if org_ref in _ORG_CACHE:
        return _ORG_CACHE[org_ref]
    oid = org_ref.split("/")[-1]
    url = f"{EP_API}/corporate-bodies/{oid}"
    try:
        data = get_json(url)
        items = data.get("data") or []
        label = items[0].get("label", oid) if items else oid
    except Exception:
        label = oid
    _ORG_CACHE[org_ref] = label
    time.sleep(0.05)
    return label


def fetch_meps_term(term: int = EP_TERM_DEFAULT, page_size: int = 100) -> list[dict]:
    meps: list[dict] = []
    offset = 0
    while True:
        url = f"{EP_API}/meps?parliamentary-term={term}&limit={page_size}&offset={offset}"
        payload = get_json(url)
        batch = payload.get("data") or []
        if not batch:
            break
        meps.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
        time.sleep(0.1)
    return meps


def fetch_and_save_roster(parsed_dir: Path, term: int = EP_TERM_DEFAULT) -> Path:
    meps_dir = parsed_dir / "meps"
    meps_dir.mkdir(parents=True, exist_ok=True)
    rows = fetch_meps_term(term)
    roster = []
    for row in rows:
        pid = row.get("identifier") or (row.get("id") or "").split("/")[-1]
        roster.append(
            {
                "identifier": pid,
                "label": row.get("label", ""),
                "family_name": row.get("familyName", ""),
                "given_name": row.get("givenName", ""),
            }
        )
    payload = {
        "source": "ep_api",
        "parliamentary_term": term,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(roster),
        "meps": roster,
    }
    path = save_json(meps_dir / f"term_{term}.json", payload)
    update_manifest(parsed_dir, "ep_roster", {"term": term, "count": len(roster), "path": str(path)})
    return path


def _membership_end(membership: dict) -> str | None:
    return (membership.get("memberDuring") or {}).get("endDate")


def _is_term_institution(org: str, term: int) -> bool:
    return f"org/ep-{term}" in str(org)


def _pick_latest_label(
    rows: list[tuple[str | None, str | None, str]],
) -> str:
    if not rows:
        return ""

    def sort_key(item: tuple[str | None, str | None, str]) -> tuple[str, str]:
        end, start, _ = item
        return (end or "9999-12-31", start or "")

    return sorted(rows, key=sort_key, reverse=True)[0][2]


def extract_membership_fields(
    mep: dict,
    term: int,
    resolve_org: Any,
) -> dict[str, Any]:
    active_group = ""
    active_party = ""
    active_country = ""
    active_committees: list[str] = []
    historical_groups: list[tuple[str | None, str | None, str]] = []
    historical_parties: list[tuple[str | None, str | None, str]] = []
    mandate_active = False
    mandate_ended: str | None = None

    for membership in mep.get("hasMembership") or []:
        cls = membership.get("membershipClassification", "") or ""
        org = membership.get("organization", "")
        if not org:
            continue

        end = _membership_end(membership)
        start = (membership.get("memberDuring") or {}).get("startDate")
        label = resolve_org(org)
        is_active = not end

        if _is_term_institution(org, term):
            if is_active:
                mandate_active = True
            elif end:
                mandate_ended = end

        if "EU_POLITICAL_GROUP" in cls:
            if is_active:
                active_group = label
            else:
                historical_groups.append((end, start, label))
        elif "NATIONAL_POLITICAL_GROUP" in cls:
            if is_active:
                active_party = label
            else:
                historical_parties.append((end, start, label))
        elif "MEMBERSHIP_COUNTRY" in cls or "COUNTRY" in cls:
            if is_active:
                active_country = label
        elif "COMMITTEE" in cls and is_active:
            active_committees.append(label)

    political_group = active_group or _pick_latest_label(historical_groups)
    national_party = active_party or _pick_latest_label(historical_parties)
    membership_source = "active"
    if not active_group and historical_groups:
        membership_source = "historical"
    if not active_party and historical_parties and membership_source == "active":
        membership_source = "historical"

    return {
        "political_group": political_group,
        "national_party": national_party,
        "country": active_country,
        "committees": active_committees[:8],
        "mandate_active": mandate_active,
        "mandate_ended": mandate_ended,
        "membership_source": membership_source,
    }


def _mep_web_slug(family_name: str, given_name: str, label: str) -> str:
    """EP site URLs need /{id}/{GIVEN_FAMILY}/ not /{id}/ alone."""
    if given_name and family_name:
        return f"{given_name}_{family_name}".upper().replace(" ", "_").replace("-", "_")
    if label:
        return label.upper().replace(" ", "_").replace("-", "_")
    return ""


def _mep_web_urls(person_id: str, family_name: str, given_name: str, label: str) -> tuple[str, str]:
    slug = _mep_web_slug(family_name, given_name, label)
    if slug:
        base = f"https://www.europarl.europa.eu/meps/en/{person_id}/{slug}"
    else:
        base = f"https://www.europarl.europa.eu/meps/en/{person_id}"
    return base, f"{base}/declarations"


def enrich_mep(person_id: str, term: int = EP_TERM_DEFAULT) -> dict[str, Any]:
    url = f"{EP_API}/meps/{person_id}?parliamentary-term={term}"
    payload = get_json(url)
    items = payload.get("data") or []
    if not items:
        return {}
    mep = items[0]
    fields = extract_membership_fields(mep, term, _resolve_org)

    from transparent_scrape.core.europarty import link_mep_to_appf

    appf_link = link_mep_to_appf(fields["political_group"])

    return {
        "identifier": mep.get("identifier") or person_id,
        "label": mep.get("label", ""),
        "family_name": mep.get("familyName", ""),
        "given_name": mep.get("givenName", ""),
        "email": _normalize_email(mep.get("hasEmail")),
        "political_group": fields["political_group"],
        "national_party": fields["national_party"],
        "country": fields["country"],
        "committees": fields["committees"],
        "mandate_active": fields["mandate_active"],
        "mandate_ended": fields["mandate_ended"],
        "membership_source": fields["membership_source"],
        "appf_abbreviation": appf_link["appf_abbreviation"],
        "appf_party": appf_link["appf_party"],
        "profile_url": _mep_web_urls(
            person_id,
            mep.get("familyName", "") or "",
            mep.get("givenName", "") or "",
            mep.get("label", "") or "",
        )[0],
        "declarations_url": _mep_web_urls(
            person_id,
            mep.get("familyName", "") or "",
            mep.get("givenName", "") or "",
            mep.get("label", "") or "",
        )[1],
    }


def enrich_and_save(
    person_id: str,
    parsed_dir: Path,
    *,
    term: int = EP_TERM_DEFAULT,
    skip_existing: bool = False,
) -> Path | None:
    out = parsed_dir / "meps" / f"{person_id}.json"
    if skip_existing and out.exists():
        return out
    detail = enrich_mep(person_id, term)
    if not detail:
        return None
    detail["source"] = "ep_api"
    detail["parliamentary_term"] = term
    detail["fetched_at"] = datetime.now(timezone.utc).isoformat()
    save_json(out, detail)
    return out


def needs_enrich_update(path: Path, *, include_mandates: bool = False) -> bool:
    """True if MEP needs an API re-fetch (empty group, or optional mandate backfill)."""
    if not path.exists():
        return True
    data = load_json(path)
    if not data.get("political_group"):
        return True
    if include_mandates and "mandate_active" not in data:
        return True
    return False


def patch_appf_links(parsed_dir: Path) -> int:
    """Add appf_* fields locally from political_group (no API calls)."""
    from transparent_scrape.core.europarty import link_mep_to_appf

    meps_dir = parsed_dir / "meps"
    updated = 0
    for path in meps_dir.glob("*.json"):
        if not path.stem.isdigit():
            continue
        data = load_json(path)
        group = data.get("political_group") or ""
        if not group:
            continue
        link = link_mep_to_appf(group)
        if (
            data.get("appf_abbreviation") == link["appf_abbreviation"]
            and data.get("appf_party") == link["appf_party"]
        ):
            continue
        data["appf_abbreviation"] = link["appf_abbreviation"]
        data["appf_party"] = link["appf_party"]
        save_json(path, data)
        updated += 1
    return updated


def audit_gaps(parsed_dir: Path, *, term: int = EP_TERM_DEFAULT) -> dict[str, Any]:
    """Summarize what postprocess still needs to fetch."""
    meps_dir = parsed_dir / "meps"
    need_enrich = sum(
        1 for p in meps_dir.glob("*.json") if p.stem.isdigit() and needs_enrich_update(p)
    )
    need_mandates = sum(
        1
        for p in meps_dir.glob("*.json")
        if p.stem.isdigit() and needs_enrich_update(p, include_mandates=True)
    )
    appf_have = {int(p.stem.split("_")[1]) for p in (parsed_dir / "appf").glob("parties_*.json")}
    appf_missing = sorted(set(range(2020, 2025)) - appf_have)

    conflict_pdfs_missing = 0
    conflicts_dir = parsed_dir / "declarations" / "conflicts"
    for path in conflicts_dir.glob("*.json"):
        if not path.stem.isdigit():
            continue
        for decl in load_json(path).get("declarations") or []:
            if decl.get("pdf_url") and len((decl.get("pdf_text") or "").strip()) <= 100:
                conflict_pdfs_missing += 1

    return {
        "mep_enrich_gaps": need_enrich,
        "mep_mandate_gaps": need_mandates,
        "appf_have": sorted(appf_have),
        "appf_missing": appf_missing,
        "opensanctions": not (parsed_dir / "opensanctions" / "eu_meps.json").exists(),
        "integrity_watch": not (parsed_dir / "integrity_watch" / "status.json").exists(),
        "conflict_pdfs_missing": conflict_pdfs_missing,
        "term": term,
    }


def enrich_batch(
    parsed_dir: Path,
    *,
    term: int = EP_TERM_DEFAULT,
    limit: int | None = None,
    skip_existing: bool = True,
    only_stale: bool = False,
    include_mandates: bool = False,
    country_filter: str | None = None,
) -> int:
    roster_path = parsed_dir / "meps" / f"term_{term}.json"
    if not roster_path.exists():
        fetch_and_save_roster(parsed_dir, term)
    roster_data = load_json(roster_path)
    meps = roster_data.get("meps") or []
    if limit:
        meps = meps[:limit]

    done = 0
    skipped = 0
    errors: list[dict] = []
    for i, row in enumerate(meps):
        pid = row["identifier"]
        out_path = parsed_dir / "meps" / f"{pid}.json"
        if only_stale:
            if not needs_enrich_update(out_path, include_mandates=include_mandates):
                skipped += 1
                continue
        elif skip_existing and out_path.exists():
            skipped += 1
            continue
        try:
            detail = enrich_mep(pid, term)
        except Exception as exc:
            errors.append({"mep_id": pid, "error": str(exc)})
            print(f"ep enrich fail {pid}: {exc}")
            continue
        if not detail:
            continue
        if country_filter:
            c = (detail.get("country") or "").lower()
            want = country_filter.lower()
            if want == "de" and c not in ("germany", "de", "deu"):
                continue
            elif want != "de" and want not in c:
                continue
        detail["source"] = "ep_api"
        detail["parliamentary_term"] = term
        detail["fetched_at"] = datetime.now(timezone.utc).isoformat()
        save_json(parsed_dir / "meps" / f"{pid}.json", detail)
        done += 1
        print(f"ep enrich {done}: {pid}")
        if (i + 1) % 20 == 0:
            print(f"enriched {i + 1}/{len(meps)} meps")
        time.sleep(0.15)

    if skipped:
        print(f"ep enrich skipped {skipped} up-to-date meps")
    if errors:
        save_json(parsed_dir / "meps" / "_enrich_errors.json", {"errors": errors})
    update_manifest(parsed_dir, "ep_enriched", {"term": term, "count": done, "errors": len(errors)})
    return done


def fetch_enriched_meps(
    term: int = EP_TERM_DEFAULT,
    limit: int | None = None,
) -> list[dict]:
    """Legacy helper: fetch roster + enrich in memory."""
    base = fetch_meps_term(term)
    if limit:
        base = base[:limit]
    out = []
    for i, row in enumerate(base):
        pid = row.get("identifier") or (row.get("id") or "").split("/")[-1]
        detail = enrich_mep(pid, term)
        if not detail:
            detail = {
                "identifier": pid,
                "label": row.get("label", ""),
                "family_name": row.get("familyName", ""),
                "given_name": row.get("givenName", ""),
            }
        out.append(detail)
        if (i + 1) % 20 == 0:
            print(f"enriched {i + 1}/{len(base)} meps")
        time.sleep(0.15)
    return out
