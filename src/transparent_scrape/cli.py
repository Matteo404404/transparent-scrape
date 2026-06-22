from __future__ import annotations

import argparse
import json
from pathlib import Path

from transparent_scrape.core.audit import audit_data_root, format_audit_report
from transparent_scrape.core.http import USER_AGENT, download, get_json, get_text
from transparent_scrape.core.pipeline import RunOptions, run_sources
from transparent_scrape.core.storage import save_json, save_text
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
from transparent_scrape.sources.registry import SOURCE_REGISTRY, list_sources


def _data_root(args: argparse.Namespace) -> Path:
    return Path(args.out)


def _cmd_wmm_show(args: argparse.Namespace) -> None:
    profile = wmm.load_wmm_profile(args.mep_id)
    print(f"{profile.name} income {profile.income_min}-{profile.income_max}")
    print(f"activities: {len(profile.activities)} meetings: {len(profile.meetings)}")
    for a in profile.activities[:5]:
        print(f"  {a.flow} {a.income_label} | {a.role[:60]}")
    for m in profile.meetings[:5]:
        print(f"  meets {m.iso_date} | {m.organization[:40]} | {m.subject[:50]}")


def _cmd_wmm_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = wmm.fetch_and_save(args.mep_id, root / "parsed" / "wmm", skip_existing=not args.force)
    print(f"wrote {path}")


def _cmd_wmm_batch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    stats = wmm.batch_fetch(
        root / "parsed",
        term=args.term,
        limit=args.limit,
        country=args.country,
        skip_existing=not args.force,
    )
    print(f"wmm batch done: {stats}")


def _cmd_ep_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = ep_api.fetch_and_save_roster(root / "parsed", args.term)
    print(f"wrote {path}")


def _cmd_ep_enrich(args: argparse.Namespace) -> None:
    root = _data_root(args)
    count = ep_api.enrich_batch(
        root / "parsed",
        term=args.term,
        limit=args.limit,
        skip_existing=not args.force,
        country_filter=args.country,
    )
    print(f"enriched {count} meps")


def _cmd_lobby_fetch(args: argparse.Namespace) -> None:
    paths = lobby_register.fetch_lobby_register(_data_root(args) / "raw")
    for p in paths:
        print(f"downloaded {p}")


def _cmd_lobby_parse(args: argparse.Namespace) -> None:
    root = _data_root(args)
    paths = lobby_register.parse_from_raw(root / "raw", root / "parsed" / "lobby")
    for p in paths:
        print(f"parsed {p}")


def _cmd_appf_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    years = [int(y) for y in args.years.split(",")] if args.years else [args.year]
    if args.parse:
        paths = appf.fetch_and_parse_years(years, root / "raw", root / "parsed")
        for path in paths:
            print(f"wrote {path}")
    else:
        for year in years:
            path = appf.fetch_parties_xlsx(year, root / "raw", url=args.url)
            print(f"downloaded {path}")


def _cmd_opensanctions_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = opensanctions.fetch_and_parse(root / "parsed", root / "raw", use_ftm=not args.csv)
    print(f"wrote {path}")


def _cmd_integrity_watch_status(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = integrity_watch.fetch_status(root / "parsed")
    print(f"wrote {path}")


def _cmd_howtheyvote_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = howtheyvote.fetch_and_parse(root / "parsed", root / "raw", force=args.force)
    print(f"wrote {path}")


def _cmd_parltrack_status(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = parltrack.fetch_dumps_status(root / "parsed")
    print(f"wrote {path}")


def _cmd_parltrack_meps(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = parltrack.fetch_meps_index(root / "parsed", root / "raw", force=args.force)
    print(f"wrote {path}")


def _cmd_epdb_status(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = epdb.fetch_status(root / "parsed")
    print(f"wrote {path}")


def _cmd_declarations_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    if args.mep_id:
        path = meps_declarations.fetch_mep_with_pdfs(
            args.mep_id,
            root / "parsed",
            root / "raw" / "declarations",
            term=args.term,
            skip_existing=not args.force,
            extract_pdf=not args.no_pdf,
        )
        print(f"wrote {path}")
    else:
        path = meps_declarations.fetch_batch(
            root / "parsed",
            root / "raw" / "declarations",
            term=args.term,
            limit=args.limit,
            skip_existing=not args.force,
            extract_pdf=not args.no_pdf,
        )
        print(f"wrote {path}")


def _cmd_declarations_refresh_pdfs(args: argparse.Namespace) -> None:
    root = _data_root(args)
    stats = meps_declarations.refresh_missing_pdfs(
        root / "parsed",
        root / "raw" / "declarations",
        skip_existing=not args.force,
        extract_pdf=not args.no_pdf,
        limit=args.limit,
    )
    print(f"conflict pdf refresh: {stats}")


def _cmd_ep_declarations_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    if args.mep_id:
        path = ep_declarations.fetch_financial_declarations(
            args.mep_id,
            root / "parsed",
            root / "raw",
            skip_existing=not args.force,
            extract_pdf=not args.no_pdf,
        )
        print(f"wrote {path}")
    else:
        count = ep_declarations.fetch_batch(
            root / "parsed",
            root / "raw",
            term=args.term,
            limit=args.limit,
            skip_existing=not args.force,
            extract_pdf=not args.no_pdf,
        )
        print(f"ep-declarations batch: {count} meps")


def _cmd_ec_meetings_fetch(args: argparse.Namespace) -> None:
    root = _data_root(args)
    path = ec_meetings.fetch_and_parse(args.dataset, root)
    print(f"wrote {path}")


def _cmd_get(args: argparse.Namespace) -> None:
    url = args.url
    out = Path(args.out) if args.out else None
    ua = args.user_agent or USER_AGENT

    if args.binary:
        dest = out or Path(url.rsplit("/", 1)[-1].split("?")[0] or "download.bin")
        download(url, dest, user_agent=ua)
        print(dest)
        return

    if args.json:
        data = get_json(url, rate_limit=False)
        if out:
            save_json(out, data)
            print(out)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    text = get_text(url, user_agent=ua)
    if out:
        save_text(out, text)
        print(out)
    else:
        print(text)


def _cmd_audit(args: argparse.Namespace) -> None:
    root = _data_root(args)
    report = audit_data_root(root, term=args.term)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_audit_report(report))


def _cmd_sources_list(args: argparse.Namespace) -> None:
    specs = list_sources(status=args.status, pack=args.pack)
    for spec in specs:
        license_bit = f" [{spec.license_note}]" if spec.license_note else ""
        print(f"{spec.id:18} {spec.status:6} {spec.title}{license_bit}")
        print(f"{'':18} cli: {spec.cli}")
        print(f"{'':18} parsed: {', '.join(spec.parsed_globs)}")
        if args.verbose:
            print()


def _cmd_postprocess(args: argparse.Namespace) -> None:
    """Incremental add-ons after bulk scrape. Skips sources already on disk."""
    root = _data_root(args)
    parsed = root / "parsed"
    raw = root / "raw"

    report = audit_data_root(root, term=args.term)
    gaps = report["gaps"]
    print("[tscrape] postprocess audit:")
    print(format_audit_report(report))
    print("")

    patched = ep_api.patch_appf_links(parsed)
    if patched:
        print(f"[tscrape] postprocess: patched appf links on {patched} meps (local, no API)")

    if args.enrich_mandates or gaps["mep_enrich_gaps"]:
        print("[tscrape] postprocess: enriching stale MEPs only...")
        count = ep_api.enrich_batch(
            parsed,
            term=args.term,
            only_stale=True,
            include_mandates=args.enrich_mandates,
        )
        print(f"[tscrape] postprocess: enriched {count} meps")
    else:
        print("[tscrape] postprocess: skip enrich (groups ok; use --enrich-mandates for mandate fields)")

    years = [int(y) for y in args.appf_years.split(",")]
    to_fetch = years if args.force else [y for y in years if not (parsed / "appf" / f"parties_{y}.json").exists()]
    if to_fetch:
        print(f"[tscrape] postprocess: APPF {to_fetch}...")
        from transparent_scrape.core.storage import load_json, save_json

        for year in to_fetch:
            appf.fetch_and_parse_parties(year, raw, url=None)
            data = load_json(raw / appf.PARTIES_JSON.format(year=year))
            save_json(parsed / "appf" / f"parties_{year}.json", data)
        print(f"[tscrape] postprocess: appf → {len(to_fetch)} new years")
    else:
        print("[tscrape] postprocess: skip appf (years already present)")

    os_path = parsed / "opensanctions" / "eu_meps.json"
    if args.force or not os_path.exists():
        print("[tscrape] postprocess: OpenSanctions eu_meps...")
        opensanctions.fetch_and_parse(parsed, raw)
    else:
        print("[tscrape] postprocess: skip opensanctions (already present)")

    iw_path = parsed / "integrity_watch" / "status.json"
    if args.force or not iw_path.exists():
        print("[tscrape] postprocess: Integrity Watch status...")
        integrity_watch.fetch_status(parsed)
    else:
        print("[tscrape] postprocess: skip integrity_watch (already present)")

    htv_path = parsed / "howtheyvote" / "voting_summary.json"
    if args.force or not htv_path.exists():
        print("[tscrape] postprocess: HowTheyVote roll-call summary...")
        try:
            howtheyvote.fetch_and_parse(parsed, raw, force=args.force)
        except Exception as exc:
            print(f"[tscrape] postprocess: howtheyvote skipped ({exc})")
    else:
        print("[tscrape] postprocess: skip howtheyvote (already present)")

    pt_path = parsed / "parltrack" / "meps_index.json"
    if args.force or not pt_path.exists():
        print("[tscrape] postprocess: Parltrack MEP index...")
        try:
            parltrack.fetch_dumps_status(parsed)
            parltrack.fetch_meps_index(parsed, raw, force=args.force)
        except Exception as exc:
            print(f"[tscrape] postprocess: parltrack skipped ({exc})")
    else:
        print("[tscrape] postprocess: skip parltrack (already present)")

    epdb_path = parsed / "epdb" / "status.json"
    if args.force or not epdb_path.exists():
        print("[tscrape] postprocess: EPDB API probe...")
        try:
            epdb.fetch_status(parsed)
        except Exception as exc:
            print(f"[tscrape] postprocess: epdb skipped ({exc})")
    else:
        print("[tscrape] postprocess: skip epdb (already present)")

    if args.conflict_pdfs:
        print("[tscrape] postprocess: conflict PDFs (missing text only, no API re-fetch)...")
        stats = meps_declarations.refresh_missing_pdfs(
            parsed,
            raw / "declarations",
            skip_existing=not args.force,
            extract_pdf=not args.no_pdf,
            limit=args.conflict_pdf_limit,
        )
        print(f"[tscrape] postprocess: conflict pdfs → {stats}")

    print("[tscrape] postprocess done.")


def _cmd_run(args: argparse.Namespace) -> None:
    root = _data_root(args)
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    opts = RunOptions(
        term=args.term,
        appf_year=args.year,
        appf_years=[int(y) for y in args.appf_years.split(",")] if args.appf_years else None,
        appf_url=args.url,
        ec_dataset=args.ec_dataset,
        skip_existing=not args.force,
        extract_pdf=not args.no_pdf,
        wmm_batch=args.wmm_batch,
        wmm_limit=args.wmm_limit,
        wmm_country=args.country,
        declarations_limit=args.declarations_limit,
        ep_declarations_limit=args.ep_declarations_limit,
        enrich_meps=args.enrich_meps,
    )
    results = run_sources(root, sources, options=opts)
    for r in results:
        for p in r.paths:
            print(f"{r.source}: {p}")
        if r.meta:
            print(f"{r.source} meta: {r.meta}")
    print("run done.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tscrape",
        description="Fetch and parse public datasets (generic core + bundled EU modules)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_get = sub.add_parser("get", help="fetch one URL to stdout or a file")
    p_get.add_argument("url")
    p_get.add_argument("--out", default=None, help="destination file path")
    p_get.add_argument("--json", action="store_true", help="parse response as JSON")
    p_get.add_argument("--binary", action="store_true", help="save raw bytes (PDF, csv.gz, etc.)")
    p_get.add_argument("--user-agent", default=None)
    p_get.set_defaults(func=_cmd_get)

    p_wmm = sub.add_parser("wmm", help="Where's My MEP")
    wmm_sub = p_wmm.add_subparsers(dest="wmm_cmd", required=True)
    p_show = wmm_sub.add_parser("show")
    p_show.add_argument("mep_id")
    p_show.set_defaults(func=_cmd_wmm_show)
    p_fetch = wmm_sub.add_parser("fetch")
    p_fetch.add_argument("mep_id")
    p_fetch.add_argument("--out", default="data")
    p_fetch.add_argument("--force", action="store_true")
    p_fetch.set_defaults(func=_cmd_wmm_fetch)
    p_batch = wmm_sub.add_parser("batch")
    p_batch.add_argument("--out", default="data")
    p_batch.add_argument("--term", type=int, default=10)
    p_batch.add_argument("--limit", type=int, default=None)
    p_batch.add_argument("--country", default=None)
    p_batch.add_argument("--force", action="store_true")
    p_batch.set_defaults(func=_cmd_wmm_batch)

    p_ep = sub.add_parser("ep", help="EP Open Data API")
    ep_sub = p_ep.add_subparsers(dest="ep_cmd", required=True)
    p_ep_fetch = ep_sub.add_parser("fetch")
    p_ep_fetch.add_argument("--out", default="data")
    p_ep_fetch.add_argument("--term", type=int, default=10)
    p_ep_fetch.set_defaults(func=_cmd_ep_fetch)
    p_ep_enrich = ep_sub.add_parser("enrich")
    p_ep_enrich.add_argument("--out", default="data")
    p_ep_enrich.add_argument("--term", type=int, default=10)
    p_ep_enrich.add_argument("--limit", type=int, default=None)
    p_ep_enrich.add_argument("--country", default=None)
    p_ep_enrich.add_argument("--force", action="store_true")
    p_ep_enrich.set_defaults(func=_cmd_ep_enrich)

    p_lobby = sub.add_parser("lobby", help="EU Transparency Register")
    lobby_sub = p_lobby.add_subparsers(dest="lobby_cmd", required=True)
    p_lf = lobby_sub.add_parser("fetch")
    p_lf.add_argument("--out", default="data")
    p_lf.set_defaults(func=_cmd_lobby_fetch)
    p_lp = lobby_sub.add_parser("parse")
    p_lp.add_argument("--out", default="data")
    p_lp.set_defaults(func=_cmd_lobby_parse)

    p_appf = sub.add_parser("appf", help="APPF europarty funding")
    appf_sub = p_appf.add_subparsers(dest="appf_cmd", required=True)
    p_af = appf_sub.add_parser("fetch")
    p_af.add_argument("--year", type=int, default=2024)
    p_af.add_argument("--years", default=None, help="comma-separated years, e.g. 2020,2021,2022,2023,2024")
    p_af.add_argument("--out", default="data")
    p_af.add_argument("--url", default=None)
    p_af.add_argument("--parse", action="store_true", default=True)
    p_af.add_argument("--no-parse", action="store_false", dest="parse")
    p_af.set_defaults(func=_cmd_appf_fetch)

    p_os = sub.add_parser("opensanctions", help="OpenSanctions eu_meps bulk")
    os_sub = p_os.add_subparsers(dest="os_cmd", required=True)
    p_osf = os_sub.add_parser("fetch")
    p_osf.add_argument("--out", default="data")
    p_osf.add_argument("--csv", action="store_true", help="use targets.simple.csv instead of ftm json")
    p_osf.set_defaults(func=_cmd_opensanctions_fetch)

    p_iw = sub.add_parser("integrity-watch", help="Integrity Watch EU datahub status")
    iw_sub = p_iw.add_subparsers(dest="iw_cmd", required=True)
    p_iws = iw_sub.add_parser("status")
    p_iws.add_argument("--out", default="data")
    p_iws.set_defaults(func=_cmd_integrity_watch_status)

    p_htv = sub.add_parser("howtheyvote", help="HowTheyVote.eu roll-call exports (ODbL)")
    htv_sub = p_htv.add_subparsers(dest="htv_cmd", required=True)
    p_htvf = htv_sub.add_parser("fetch")
    p_htvf.add_argument("--out", default="data")
    p_htvf.add_argument("--force", action="store_true")
    p_htvf.set_defaults(func=_cmd_howtheyvote_fetch)

    p_pt = sub.add_parser("parltrack", help="Parltrack dumps (ODbL)")
    pt_sub = p_pt.add_subparsers(dest="pt_cmd", required=True)
    p_pts = pt_sub.add_parser("status")
    p_pts.add_argument("--out", default="data")
    p_pts.set_defaults(func=_cmd_parltrack_status)
    p_ptm = pt_sub.add_parser("meps")
    p_ptm.add_argument("--out", default="data")
    p_ptm.add_argument("--force", action="store_true")
    p_ptm.set_defaults(func=_cmd_parltrack_meps)

    p_epdb = sub.add_parser("epdb", help="EPDB Council/EP vote API probe")
    epdb_sub = p_epdb.add_subparsers(dest="epdb_cmd", required=True)
    p_epdbs = epdb_sub.add_parser("status")
    p_epdbs.add_argument("--out", default="data")
    p_epdbs.set_defaults(func=_cmd_epdb_status)

    p_decl = sub.add_parser("declarations", help="MEP conflict-of-interest declarations")
    decl_sub = p_decl.add_subparsers(dest="decl_cmd", required=True)
    p_df = decl_sub.add_parser("fetch")
    p_df.add_argument("--out", default="data")
    p_df.add_argument("--term", type=int, default=10)
    p_df.add_argument("--mep-id", default=None)
    p_df.add_argument("--limit", type=int, default=None)
    p_df.add_argument("--force", action="store_true")
    p_df.add_argument("--no-pdf", action="store_true")
    p_df.set_defaults(func=_cmd_declarations_fetch)

    p_dfr = decl_sub.add_parser("refresh-pdfs", help="download conflict PDFs missing text only")
    p_dfr.add_argument("--out", default="data")
    p_dfr.add_argument("--limit", type=int, default=None, help="max PDF attempts this run")
    p_dfr.add_argument("--force", action="store_true", help="re-download even if PDF exists on disk")
    p_dfr.add_argument("--no-pdf", action="store_true")
    p_dfr.set_defaults(func=_cmd_declarations_refresh_pdfs)

    p_epd = sub.add_parser("ep-declarations", help="EP financial declaration PDFs")
    epd_sub = p_epd.add_subparsers(dest="epd_cmd", required=True)
    p_epdf = epd_sub.add_parser("fetch")
    p_epdf.add_argument("--out", default="data")
    p_epdf.add_argument("--term", type=int, default=10)
    p_epdf.add_argument("--mep-id", default=None)
    p_epdf.add_argument("--limit", type=int, default=None)
    p_epdf.add_argument("--force", action="store_true")
    p_epdf.add_argument("--no-pdf", action="store_true")
    p_epdf.set_defaults(func=_cmd_ep_declarations_fetch)

    p_ec = sub.add_parser("ec-meetings", help="Commission lobby meetings")
    ec_sub = p_ec.add_subparsers(dest="ec_cmd", required=True)
    p_ecf = ec_sub.add_parser("fetch")
    p_ecf.add_argument("--out", default="data")
    p_ecf.add_argument("--dataset", default="2429")
    p_ecf.set_defaults(func=_cmd_ec_meetings_fetch)

    p_run = sub.add_parser("run", help="run configured sources")
    p_run.add_argument("--out", default="data")
    p_run.add_argument(
        "--sources",
        default="ep,lobby,appf,ec_meetings,declarations,ep_declarations,wmm,opensanctions,integrity_watch",
    )
    p_run.add_argument("--term", type=int, default=10)
    p_run.add_argument("--year", type=int, default=2024, help="APPF year when --appf-years not set")
    p_run.add_argument(
        "--appf-years",
        default="2020,2021,2022,2023,2024",
        help="comma-separated APPF years (used when appf in --sources)",
    )
    p_run.add_argument("--url", default=None)
    p_run.add_argument("--ec-dataset", default="2429")
    p_run.add_argument("--force", action="store_true")
    p_run.add_argument("--no-pdf", action="store_true")
    p_run.add_argument("--wmm-batch", action="store_true", default=True)
    p_run.add_argument("--no-wmm-batch", action="store_false", dest="wmm_batch")
    p_run.add_argument("--wmm-limit", type=int, default=None)
    p_run.add_argument("--declarations-limit", type=int, default=None)
    p_run.add_argument("--ep-declarations-limit", type=int, default=None)
    p_run.add_argument("--country", default=None)
    p_run.add_argument("--enrich-meps", action="store_true")
    p_run.set_defaults(func=_cmd_run)

    p_pp = sub.add_parser(
        "postprocess",
        help="incremental add-ons after ep_declarations (skips existing data)",
    )
    p_pp.add_argument("--out", default="data")
    p_pp.add_argument("--term", type=int, default=10)
    p_pp.add_argument(
        "--appf-years",
        default="2020,2021,2022,2023",
        help="APPF years to fetch if missing (2024 skipped if already present)",
    )
    p_pp.add_argument("--force", action="store_true", help="re-fetch even if files exist")
    p_pp.add_argument(
        "--enrich-mandates",
        action="store_true",
        help="API backfill mandate_active on all MEPs (~741 calls, slow)",
    )
    p_pp.add_argument(
        "--conflict-pdfs",
        action="store_true",
        help="download conflict PDFs missing text only",
    )
    p_pp.add_argument(
        "--conflict-pdf-limit",
        type=int,
        default=None,
        help="max PDF attempts this run (default: all missing)",
    )
    p_pp.add_argument("--no-pdf", action="store_true")
    p_pp.set_defaults(func=_cmd_postprocess)

    p_audit = sub.add_parser("audit", help="show parsed data health for --out root")
    p_audit.add_argument("--out", default="data")
    p_audit.add_argument("--term", type=int, default=10)
    p_audit.add_argument("--json", action="store_true", help="also print full JSON report")
    p_audit.set_defaults(func=_cmd_audit)

    p_sources = sub.add_parser("sources", help="list built-in source modules")
    src_sub = p_sources.add_subparsers(dest="sources_cmd", required=True)
    p_src_list = src_sub.add_parser("list")
    p_src_list.add_argument(
        "--status",
        choices=("active", "probe", "heavy"),
        default=None,
        help="filter by module status",
    )
    p_src_list.add_argument(
        "--pack",
        default=None,
        help="filter bundled pack (default: all; built-in EU modules use pack=eu)",
    )
    p_src_list.add_argument("-v", "--verbose", action="store_true")
    p_src_list.set_defaults(func=_cmd_sources_list)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
