from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transparent_scrape.core.storage import update_manifest
from transparent_scrape.sources import (
    appf,
    ec_meetings,
    ep_api,
    ep_declarations,
    epdb,
    howtheyvote,
    integrity_watch,
    lobby_register,
    meps_declarations,
    opensanctions,
    parltrack,
    wmm,
)


@dataclass
class RunOptions:
    term: int = 10
    appf_year: int = 2024
    appf_years: list[int] | None = None
    appf_url: str | None = None
    ec_dataset: str = "2429"
    skip_existing: bool = True
    extract_pdf: bool = True
    wmm_batch: bool = True
    wmm_limit: int | None = None
    wmm_country: str | None = None
    declarations_limit: int | None = None
    ep_declarations_limit: int | None = None
    enrich_meps: bool = False


@dataclass
class RunResult:
    source: str
    paths: list[Path] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def run_sources(
    data_root: Path,
    sources: list[str],
    *,
    options: RunOptions | None = None,
) -> list[RunResult]:
    opts = options or RunOptions()
    data_root.mkdir(parents=True, exist_ok=True)
    raw_dir = data_root / "raw"
    parsed_dir = data_root / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    results: list[RunResult] = []

    if "ep" in sources:
        print(f"[tscrape] ep: fetching MEP roster term {opts.term}...")
        roster = ep_api.fetch_and_save_roster(parsed_dir, opts.term)
        print(f"[tscrape] ep: roster saved → {roster}")
        results.append(RunResult("ep", [roster], {"term": opts.term}))
        if opts.enrich_meps:
            print("[tscrape] ep: enriching MEP metadata (prints every 20)...")
            count = ep_api.enrich_batch(parsed_dir, term=opts.term, skip_existing=opts.skip_existing)
            print(f"[tscrape] ep: enriched {count} meps")
            results.append(RunResult("ep_enrich", [], {"count": count}))

    if "lobby" in sources:
        print("[tscrape] lobby: downloading + parsing register XML (can take a few min)...")
        paths = lobby_register.fetch_and_parse_lobby(data_root)
        print(f"[tscrape] lobby: done → {', '.join(p.name for p in paths)}")
        results.append(RunResult("lobby", paths, {}))

    if "appf" in sources:
        years = opts.appf_years or [opts.appf_year]
        print(f"[tscrape] appf: fetching parties {years}...")
        raw_dir.mkdir(parents=True, exist_ok=True)
        paths = appf.fetch_and_parse_years(years, raw_dir, parsed_dir)
        print(f"[tscrape] appf: done → {len(paths)} years")
        results.append(RunResult("appf", paths, {"years": years}))

    if "opensanctions" in sources:
        print("[tscrape] opensanctions: downloading eu_meps bulk...")
        path = opensanctions.fetch_and_parse(parsed_dir, raw_dir)
        print(f"[tscrape] opensanctions: done → {path.name}")
        results.append(RunResult("opensanctions", [path], {}))

    if "integrity_watch" in sources:
        print("[tscrape] integrity_watch: checking datahub status...")
        path = integrity_watch.fetch_status(parsed_dir)
        print(f"[tscrape] integrity_watch: done → {path.name}")
        results.append(RunResult("integrity_watch", [path], {}))

    if "howtheyvote" in sources:
        print("[tscrape] howtheyvote: downloading roll-call CSV + rebellion stats...")
        path = howtheyvote.fetch_and_parse(parsed_dir, raw_dir, force=not opts.skip_existing)
        print(f"[tscrape] howtheyvote: done → {path.name}")
        results.append(RunResult("howtheyvote", [path], {}))

    if "parltrack" in sources:
        print("[tscrape] parltrack: dumps status + MEP index...")
        paths = [
            parltrack.fetch_dumps_status(parsed_dir),
            parltrack.fetch_meps_index(parsed_dir, raw_dir, force=not opts.skip_existing),
        ]
        print(f"[tscrape] parltrack: done → {', '.join(p.name for p in paths)}")
        results.append(RunResult("parltrack", paths, {}))

    if "epdb" in sources:
        print("[tscrape] epdb: probing Council/EP vote API...")
        path = epdb.fetch_status(parsed_dir)
        print(f"[tscrape] epdb: done → {path.name}")
        results.append(RunResult("epdb", [path], {}))

    if "ec_meetings" in sources:
        print(f"[tscrape] ec_meetings: dataset {opts.ec_dataset}...")
        path = ec_meetings.fetch_and_parse(opts.ec_dataset, data_root)
        print(f"[tscrape] ec_meetings: done → {path.name}")
        results.append(RunResult("ec_meetings", [path], {"dataset": opts.ec_dataset}))

    if "declarations" in sources:
        print("[tscrape] declarations: conflict-of-interest API + PDFs (prints every 20 meps)...")
        decl_raw = raw_dir / "declarations"
        path = meps_declarations.fetch_batch(
            parsed_dir,
            decl_raw,
            term=opts.term,
            limit=opts.declarations_limit,
            skip_existing=opts.skip_existing,
            extract_pdf=opts.extract_pdf,
        )
        print(f"[tscrape] declarations: done → {path.name}")
        results.append(RunResult("declarations", [path], {}))

    if "ep_declarations" in sources:
        print("[tscrape] ep_declarations: financial PDFs from EP pages (prints every 20 meps)...")
        count = ep_declarations.fetch_batch(
            parsed_dir,
            raw_dir,
            term=opts.term,
            limit=opts.ep_declarations_limit,
            skip_existing=opts.skip_existing,
            extract_pdf=opts.extract_pdf,
        )
        print(f"[tscrape] ep_declarations: done, {count} meps")
        results.append(RunResult("ep_declarations", [], {"count": count}))

    if "wmm" in sources and opts.wmm_batch:
        print("[tscrape] wmm: batch fetch (prints every 10 meps, ~1 req/s)...")
        stats = wmm.batch_fetch(
            parsed_dir,
            term=opts.term,
            limit=opts.wmm_limit,
            country=opts.wmm_country,
            skip_existing=opts.skip_existing,
        )
        print(f"[tscrape] wmm: done → {stats}")
        results.append(RunResult("wmm", [], stats))

    print("[tscrape] writing manifest...")
    update_manifest(
        parsed_dir,
        "run",
        {
            "sources": sources,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    print("[tscrape] all sources finished.")
    return results
