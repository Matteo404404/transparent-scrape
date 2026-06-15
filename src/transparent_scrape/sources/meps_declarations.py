"""MEP per-dossier conflict-of-interest declarations (EP API + PDF)."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from transparent_scrape.core.config import EP_API, EP_DATA_BASE, EP_PDF_BASE, EP_TERM_DEFAULT
from transparent_scrape.core.http import download, get_json
from transparent_scrape.core.pdf import extract_pdf_text
from transparent_scrape.core.storage import load_json, save_json, update_manifest


def _pdf_url_from_doc(doc: dict) -> str | None:
    for expr in doc.get("is_realized_by") or []:
        for emb in expr.get("is_embodied_by") or []:
            rel = emb.get("is_exemplified_by")
            if not rel:
                continue
            rel = str(rel).lstrip("/")
            is_pdf = "pdf" in str(emb.get("format", "")).lower() or rel.endswith(".pdf")
            if not is_pdf:
                continue
            if rel.startswith("distribution/doc/"):
                return urljoin(EP_DATA_BASE + "/", rel)
            return urljoin(EP_PDF_BASE + "/", rel)
    return None


def pdf_url_candidates(doc_id: str, primary_url: str | None = None) -> list[str]:
    """Try data.europarl first, then legacy www host."""
    candidates: list[str] = []
    if primary_url:
        candidates.append(primary_url)
        if "www.europarl.europa.eu/distribution/" in primary_url:
            candidates.append(primary_url.replace("www.europarl.europa.eu", "data.europarl.europa.eu"))
    stem = doc_id
    for lang in ("en", "de", "fr"):
        candidates.append(f"{EP_DATA_BASE}/distribution/doc/{stem}_{lang}.pdf")
        if not stem.endswith(f"_{lang}"):
            candidates.append(f"{EP_DATA_BASE}/distribution/doc/{stem}.pdf")
    # dedupe, keep order
    seen: set[str] = set()
    out: list[str] = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _doc_id(doc: dict) -> str:
    ident = doc.get("identifier") or doc.get("id", "")
    if isinstance(ident, str) and ident.startswith("DCI-"):
        return ident
    raw = doc.get("id", "")
    return raw.split("/")[-1] if "/" in raw else str(raw)


def _person_ids(doc: dict) -> list[str]:
    ids: list[str] = []
    for part in doc.get("workHadParticipation") or []:
        for p in part.get("had_participant_person") or []:
            pid = p.split("/")[-1] if isinstance(p, str) else str(p)
            if pid.isdigit():
                ids.append(pid)
    return ids


def _parse_declaration(doc: dict) -> dict[str, Any]:
    title = ""
    titles = doc.get("title_dcterms") or doc.get("title") or {}
    if isinstance(titles, dict):
        title = titles.get("en") or next(iter(titles.values()), "")
    elif isinstance(titles, str):
        title = titles

    capacity = ""
    role = ""
    for part in doc.get("workHadParticipation") or []:
        role = part.get("participation_role", "")
        cap = part.get("inCapacityOf") or {}
        capacity = cap.get("capacityRole", "") if isinstance(cap, dict) else ""

    return {
        "doc_id": _doc_id(doc),
        "document_date": doc.get("document_date"),
        "title": title,
        "awareness_of_conflict": doc.get("awarenessOfConflict"),
        "refers_to": doc.get("refers_to") or [],
        "participation_role": role,
        "capacity_role": capacity,
        "person_ids": _person_ids(doc),
        "pdf_url": _pdf_url_from_doc(doc),
        "work_type": doc.get("work_type"),
    }


def fetch_declarations_for_mep(
    person_id: str,
    *,
    term: int = EP_TERM_DEFAULT,
    limit: int = 50,
) -> list[dict]:
    url = (
        f"{EP_API}/meps-declarations?person-id={person_id}"
        f"&parliamentary-term={term}&limit={limit}"
    )
    payload = get_json(url)
    return [_parse_declaration(d) for d in payload.get("data") or []]


def fetch_all_declarations(term: int = EP_TERM_DEFAULT, *, max_offset: int = 9999) -> list[dict]:
    all_docs: list[dict] = []
    offset = 0
    page_size = 50
    while offset <= max_offset:
        url = f"{EP_API}/meps-declarations?parliamentary-term={term}&limit={page_size}&offset={offset}"
        payload = get_json(url)
        batch = payload.get("data") or []
        if not batch:
            break
        all_docs.extend(_parse_declaration(d) for d in batch)
        if len(batch) < page_size:
            break
        offset += page_size
        time.sleep(0.12)
    return all_docs


def download_pdf(
    decl: dict,
    raw_dir: Path,
    *,
    skip_existing: bool = True,
    extract: bool = True,
) -> dict[str, Any]:
    pdf_url = decl.get("pdf_url")
    doc_id = decl.get("doc_id", "unknown")
    result = {"pdf_path": None, "pdf_text": None, "pdf_pages": 0, "pdf_error": None, "pdf_url_used": None}
    dest = raw_dir / f"{doc_id}.pdf"

    if skip_existing and dest.exists() and dest.stat().st_size > 100:
        result["pdf_path"] = str(dest)
        result["pdf_url_used"] = pdf_url
    else:
        last_err: str | None = None
        for candidate in pdf_url_candidates(doc_id, pdf_url):
            try:
                download(candidate, dest)
                if dest.exists() and dest.read_bytes()[:4] == b"%PDF":
                    result["pdf_path"] = str(dest)
                    result["pdf_url_used"] = candidate
                    break
                dest.unlink(missing_ok=True)
                last_err = f"not a pdf: {candidate}"
            except Exception as exc:
                last_err = str(exc)
        if not result["pdf_path"]:
            result["pdf_error"] = last_err or "no pdf url"
            return result

    if extract and dest.exists():
        extracted = extract_pdf_text(dest)
        result["pdf_text"] = extracted.get("text") or ""
        result["pdf_pages"] = extracted.get("pages") or 0
        if extracted.get("error"):
            result["pdf_error"] = extracted["error"]
    return result


def fetch_mep_with_pdfs(
    person_id: str,
    parsed_dir: Path,
    raw_dir: Path,
    *,
    term: int = EP_TERM_DEFAULT,
    skip_existing: bool = True,
    extract_pdf: bool = True,
) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    decls = fetch_declarations_for_mep(person_id, term=term)
    enriched = []
    for d in decls:
        row = dict(d)
        if extract_pdf:
            row.update(download_pdf(d, raw_dir, skip_existing=skip_existing))
        enriched.append(row)

    out_dir = parsed_dir / "declarations" / "conflicts"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "meps_declarations",
        "mep_id": person_id,
        "parliamentary_term": term,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "declarations": enriched,
    }
    path = save_json(out_dir / f"{person_id}.json", payload)
    return path


def fetch_batch(
    parsed_dir: Path,
    raw_dir: Path,
    *,
    term: int = EP_TERM_DEFAULT,
    limit: int | None = None,
    skip_existing: bool = True,
    extract_pdf: bool = True,
) -> Path:
    from transparent_scrape.sources import ep_api

    roster_path = parsed_dir / "meps" / f"term_{term}.json"
    if not roster_path.exists():
        ep_api.fetch_and_save_roster(parsed_dir, term)
    roster = load_json(roster_path).get("meps") or []

    all_flat: list[dict] = []
    done = 0
    errors: list[dict] = []
    for row in roster:
        if limit and done >= limit:
            break
        pid = row["identifier"]
        per_path = parsed_dir / "declarations" / "conflicts" / f"{pid}.json"
        if skip_existing and per_path.exists():
            existing = load_json(per_path)
            all_flat.extend(existing.get("declarations") or [])
            done += 1
            continue
        try:
            fetch_mep_with_pdfs(
                pid, parsed_dir, raw_dir, term=term, skip_existing=skip_existing, extract_pdf=extract_pdf
            )
        except Exception as exc:
            errors.append({"mep_id": pid, "error": str(exc)})
            print(f"declarations fail {pid}: {exc}")
            # save empty record so we don't retry forever
            out_dir = parsed_dir / "declarations" / "conflicts"
            out_dir.mkdir(parents=True, exist_ok=True)
            save_json(
                out_dir / f"{pid}.json",
                {
                    "source": "meps_declarations",
                    "mep_id": pid,
                    "parliamentary_term": term,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "declarations": [],
                    "error": str(exc),
                },
            )
        if per_path.exists():
            all_flat.extend(load_json(per_path).get("declarations") or [])
        done += 1
        print(f"declarations {done}: {pid}")
        if done % 20 == 0:
            print(f"declarations: {done} meps")
        time.sleep(0.15)

    if errors:
        save_json(parsed_dir / "declarations" / "_errors.json", {"errors": errors})

    bulk = {
        "source": "meps_declarations",
        "parliamentary_term": term,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_flat),
        "declarations": all_flat,
    }
    out = save_json(parsed_dir / "declarations" / "conflicts.json", bulk)
    update_manifest(
        parsed_dir,
        "meps_declarations",
        {"mep_count": done, "declaration_count": len(all_flat)},
    )
    return out


def refresh_missing_pdfs(
    parsed_dir: Path,
    raw_dir: Path,
    *,
    skip_existing: bool = True,
    extract_pdf: bool = True,
    limit: int | None = None,
) -> dict[str, int]:
    """Download conflict PDFs only where metadata exists but pdf_text is empty."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    conflicts_dir = parsed_dir / "declarations" / "conflicts"
    stats = {
        "files_touched": 0,
        "pdfs_downloaded": 0,
        "pdfs_failed": 0,
        "pdfs_skipped": 0,
        "pdfs_attempted": 0,
    }

    paths = sorted(p for p in conflicts_dir.glob("*.json") if p.stem.isdigit())
    total_meps = len(paths)
    total_missing = 0
    for path in paths:
        for decl in load_json(path).get("declarations") or []:
            if decl.get("pdf_url") and len((decl.get("pdf_text") or "").strip()) <= 100:
                total_missing += 1

    print(
        f"conflict pdfs: {total_missing} rows missing text across {total_meps} mep files "
        f"(metadata already complete)"
    )

    for idx, path in enumerate(paths, start=1):
        data = load_json(path)
        decls = data.get("declarations") or []
        changed = False
        for decl in decls:
            if limit is not None and stats["pdfs_attempted"] >= limit:
                break
            if not decl.get("pdf_url"):
                continue
            text = (decl.get("pdf_text") or "").strip()
            if len(text) > 100:
                stats["pdfs_skipped"] += 1
                continue
            stats["pdfs_attempted"] += 1
            extra = download_pdf(
                decl,
                raw_dir,
                skip_existing=skip_existing,
                extract=extract_pdf,
            )
            decl.update(extra)
            if extra.get("pdf_url_used"):
                decl["pdf_url"] = extra["pdf_url_used"]
            changed = True
            if extra.get("pdf_text") and len(extra["pdf_text"]) > 100:
                stats["pdfs_downloaded"] += 1
            else:
                stats["pdfs_failed"] += 1
            done = stats["pdfs_attempted"]
            if done % 25 == 0:
                print(
                    f"conflict pdfs: {done}/{total_missing} attempted "
                    f"({stats['pdfs_downloaded']} ok, {stats['pdfs_failed']} fail, "
                    f"{stats['pdfs_skipped']} skipped) · mep file {idx}/{total_meps}"
                )

        if changed:
            save_json(path, data)
            stats["files_touched"] += 1
            time.sleep(0.02)

        if limit is not None and stats["pdfs_attempted"] >= limit:
            break

    print(
        f"conflict pdfs done: {stats['pdfs_downloaded']} ok, "
        f"{stats['pdfs_failed']} fail, {stats['pdfs_skipped']} already had text, "
        f"{stats['pdfs_attempted']} attempted this run"
    )

    update_manifest(
        parsed_dir,
        "meps_declarations_pdfs",
        stats,
    )
    return stats
