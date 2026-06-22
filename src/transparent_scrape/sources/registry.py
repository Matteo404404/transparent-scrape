"""Catalog of built-in source modules (CLI + parsed outputs)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    id: str
    title: str
    cli: str
    parsed_globs: tuple[str, ...]
    license_note: str | None = None
    status: str = "active"  # active | probe | heavy
    pack: str = "eu"  # bundled module pack (custom sources live in your repo)


SOURCE_REGISTRY: tuple[SourceSpec, ...] = (
    SourceSpec("ep", "EP Open Data API", "tscrape ep fetch", ("meps/term_*.json",)),
    SourceSpec(
        "lobby",
        "EU Transparency Register",
        "tscrape lobby fetch && tscrape lobby parse",
        ("lobby/organizations.json", "lobby/accredited.json"),
    ),
    SourceSpec(
        "wmm",
        "Where's My MEP",
        "tscrape wmm batch",
        ("wmm/*.json",),
        status="heavy",
    ),
    SourceSpec(
        "declarations",
        "Conflict-of-interest dossiers",
        "tscrape declarations fetch",
        ("declarations/conflicts/*.json",),
        status="heavy",
    ),
    SourceSpec(
        "ep_declarations",
        "Financial interest PDFs",
        "tscrape ep-declarations fetch",
        ("declarations/financial/*.json",),
        status="heavy",
    ),
    SourceSpec(
        "ec_meetings",
        "Commission lobby meetings",
        "tscrape ec-meetings fetch --dataset 2429",
        ("ec_meetings/2429.json",),
    ),
    SourceSpec(
        "appf",
        "Europarty funding (APPF)",
        "tscrape appf fetch --years 2020,2021,2022,2023,2024",
        ("appf/parties_*.json",),
    ),
    SourceSpec(
        "opensanctions",
        "OpenSanctions eu_meps",
        "tscrape opensanctions fetch",
        ("opensanctions/eu_meps.json",),
    ),
    SourceSpec(
        "howtheyvote",
        "HowTheyVote roll-call",
        "tscrape howtheyvote fetch",
        ("howtheyvote/voting_summary.json",),
        license_note="ODbL 1.0",
    ),
    SourceSpec(
        "parltrack",
        "Parltrack MEP index",
        "tscrape parltrack status && tscrape parltrack meps",
        ("parltrack/meps_index.json", "parltrack/dumps_status.json"),
        license_note="ODbL 1.0",
    ),
    SourceSpec(
        "epdb",
        "EPDB vote API",
        "tscrape epdb status",
        ("epdb/status.json",),
        status="probe",
    ),
    SourceSpec(
        "integrity_watch",
        "Integrity Watch datahub",
        "tscrape integrity-watch status",
        ("integrity_watch/status.json",),
        status="probe",
    ),
)


def list_sources(*, status: str | None = None, pack: str | None = None) -> list[SourceSpec]:
    out = list(SOURCE_REGISTRY)
    if status is not None:
        out = [s for s in out if s.status == status]
    if pack is not None:
        out = [s for s in out if s.pack == pack]
    return out
