"""EP MEP financial interest declaration PDFs from profile page."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from transparent_scrape.core.config import EP_PDF_BASE, EP_TERM_DEFAULT
from transparent_scrape.core.http import download
from transparent_scrape.core.pdf import extract_pdf_text
from transparent_scrape.core.storage import load_json, save_json, update_manifest

PDF_LINK_RE = re.compile(
    r'href="([^"]+\.pdf[^"]*)"',
    re.I,
)


def _name_slug(label: str) -> str:
    # "Axel VOSS" -> "AXEL_VOSS"
    parts = re.sub(r"[^a-zA-Z0-9\s-]", "", label).upper().split()
    return "_".join(parts) if parts else "UNKNOWN"


def declarations_url(mep_id: str, label: str | None = None) -> str:
    if label:
        return f"https://www.europarl.europa.eu/meps/en/{mep_id}/{_name_slug(label)}/declarations"
    return f"https://www.europarl.europa.eu/meps/en/{mep_id}/declarations"


def _normalize_pdf_url(href: str) -> str:
    if href.startswith("http"):
        return href
    return urljoin(EP_PDF_BASE + "/", href.lstrip("/"))


def parse_declaration_links(html: str) -> list[dict[str, str]]:
    links = []
    seen = set()
    for href in PDF_LINK_RE.findall(html):
        url = _normalize_pdf_url(href)
        if url in seen:
            continue
        seen.add(url)
        doc_id = url.split("/")[-1].replace("_en.pdf", "").replace(".pdf", "")
        links.append({"doc_id": doc_id, "pdf_url": url})
    return links


def _heuristic_gifts(text: str) -> list[dict[str, Any]]:
    """Best-effort gift/hospitality rows from PDF text."""
    gifts = []
    for line in text.splitlines():
        low = line.lower()
        if any(k in low for k in ("gift", "hospitality", "sponsor", "donation")):
            amount_m = re.search(r"€\s*([\d,]+(?:\.\d+)?)", line)
            gifts.append(
                {
                    "line": line.strip()[:300],
                    "amount_eur": amount_m.group(1).replace(",", "") if amount_m else None,
                }
            )
    return gifts[:50]


def _fetch_declarations_html(url: str) -> tuple[str, int | None]:
    """Return (html, http_status). Empty html on 404."""
    import httpx

    from transparent_scrape.core.http import USER_AGENT
    from transparent_scrape.core.rate_limit import web_limiter

    web_limiter.wait()
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        resp = client.get(url, headers={"User-Agent": USER_AGENT})
        if resp.status_code == 404:
            return "", 404
        resp.raise_for_status()
        return resp.text, resp.status_code


def fetch_financial_declarations(
    mep_id: str,
    parsed_dir: Path,
    raw_dir: Path,
    *,
    skip_existing: bool = True,
    extract_pdf: bool = True,
    label: str | None = None,
) -> Path:
    html_path = raw_dir / "ep_profiles" / f"{mep_id}_declarations.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)

    if not label:
        meta_path = parsed_dir / "meps" / f"{mep_id}.json"
        if meta_path.exists():
            label = load_json(meta_path).get("label")

    url = declarations_url(mep_id, label)
    http_status: int | None = None

    if skip_existing and html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        if not html.strip() and label:
            html, http_status = _fetch_declarations_html(url)
            if html:
                html_path.write_text(html, encoding="utf-8")
    else:
        html, http_status = _fetch_declarations_html(url)
        if not html and label:
            # fallback old URL pattern
            fallback = declarations_url(mep_id, None)
            html, http_status = _fetch_declarations_html(fallback)
            if html:
                url = fallback
        if html:
            html_path.write_text(html, encoding="utf-8")

    pdf_links = parse_declaration_links(html)
    declarations = []
    pdf_raw = raw_dir / "declarations" / "financial"
    pdf_raw.mkdir(parents=True, exist_ok=True)

    for link in pdf_links:
        doc_id = link["doc_id"]
        dest = pdf_raw / f"{doc_id}.pdf"
        entry: dict[str, Any] = dict(link)
        if extract_pdf:
            if not (skip_existing and dest.exists()):
                try:
                    download(link["pdf_url"], dest)
                except Exception as exc:
                    entry["pdf_error"] = str(exc)
            if dest.exists():
                extracted = extract_pdf_text(dest)
                entry["pdf_path"] = str(dest)
                entry["pdf_pages"] = extracted.get("pages")
                entry["pdf_text"] = extracted.get("text") or ""
                entry["pdf_error"] = extracted.get("error")
                entry["gifts_hospitality_heuristic"] = _heuristic_gifts(entry["pdf_text"])
        declarations.append(entry)

    out_dir = parsed_dir / "declarations" / "financial"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "ep_declarations",
        "mep_id": mep_id,
        "declarations_url": url,
        "http_status": http_status,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "pdf_count": len(declarations),
        "declarations": declarations,
    }
    return save_json(out_dir / f"{mep_id}.json", payload)


def fetch_batch(
    parsed_dir: Path,
    raw_dir: Path,
    *,
    term: int = EP_TERM_DEFAULT,
    limit: int | None = None,
    skip_existing: bool = True,
    extract_pdf: bool = True,
) -> int:
    from transparent_scrape.sources import ep_api

    roster_path = parsed_dir / "meps" / f"term_{term}.json"
    if not roster_path.exists():
        ep_api.fetch_and_save_roster(parsed_dir, term)
    roster = load_json(roster_path).get("meps") or []
    done = 0
    errors: list[dict] = []
    for row in roster:
        if limit and done >= limit:
            break
        pid = row["identifier"]
        out = parsed_dir / "declarations" / "financial" / f"{pid}.json"
        if skip_existing and out.exists():
            existing = load_json(out)
            # retry empty 404 stubs from broken URL era
            if existing.get("pdf_count", 0) > 0 or existing.get("http_status") not in (404, None):
                done += 1
                continue
        try:
            fetch_financial_declarations(
                pid, parsed_dir, raw_dir, skip_existing=False, extract_pdf=extract_pdf
            )
        except Exception as exc:
            errors.append({"mep_id": pid, "error": str(exc)})
            print(f"ep-declarations fail {pid}: {exc}")
            save_json(
                out,
                {
                    "source": "ep_declarations",
                    "mep_id": pid,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "pdf_count": 0,
                    "declarations": [],
                    "error": str(exc),
                },
            )
        done += 1
        print(f"ep-declarations {done}: {pid}")
        if done % 20 == 0:
            print(f"ep-declarations: {done} meps")
        time.sleep(1.0)

    if errors:
        save_json(parsed_dir / "declarations" / "financial/_errors.json", {"errors": errors})
    update_manifest(parsed_dir, "ep_declarations", {"mep_count": done, "errors": len(errors)})
    return done
