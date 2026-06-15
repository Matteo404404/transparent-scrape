"""EU Transparency Register — download and parse."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from lxml import etree

from transparent_scrape.core.config import LOBBY_ACCRED_XML, LOBBY_ORG_XML
from transparent_scrape.core.http import download
from transparent_scrape.core.storage import save_json, update_manifest
from transparent_scrape.core.tags import tag_text

ORG_FILENAME = "lobby_organisations.xml"
ACCRED_FILENAME = "lobby_accredited.xml"


def fetch_lobby_register(raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    org_path = download(LOBBY_ORG_XML, raw_dir / ORG_FILENAME)
    accred_path = download(LOBBY_ACCRED_XML, raw_dir / ACCRED_FILENAME)
    return [org_path, accred_path]


def _text(el: etree._Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def _child_by_suffix(parent: etree._Element, suffix: str) -> etree._Element | None:
    for c in parent:
        if c.tag.endswith(suffix):
            return c
    return None


def _budget_max(ir: etree._Element) -> int | None:
    for costs in ir.iter():
        if not costs.tag.endswith("costs"):
            continue
        for mx in costs.iter():
            if mx.tag.endswith("max") and mx.text:
                try:
                    return int(mx.text.replace(",", "").strip())
                except ValueError:
                    pass
    return None


def parse_organizations(xml_path: Path) -> Iterator[dict]:
    parser = etree.XMLParser(recover=True, huge_tree=True)
    tree = etree.parse(str(xml_path), parser)
    for ir in tree.iter():
        if not ir.tag.endswith("interestRepresentative"):
            continue

        reg_id = _text(_child_by_suffix(ir, "identificationCode"))
        name_block = _child_by_suffix(ir, "name")
        name_el = _child_by_suffix(name_block, "originalName") if name_block is not None else None
        if name_el is None:
            for c in ir.iter():
                if c.tag.endswith("originalName"):
                    name_el = c
                    break
        name = _text(name_el)
        acronym = _text(_child_by_suffix(ir, "acronym"))
        category = _text(_child_by_suffix(ir, "registrationCategory"))
        country = ""
        for c in ir.iter():
            if c.tag.endswith("country") and c.text:
                country = c.text.strip()
                break

        goals = _text(_child_by_suffix(ir, "goals"))

        interests = []
        for block in ir.iter():
            if block.tag.endswith("interests"):
                for item in block:
                    if item.tag.endswith("interest"):
                        for nm in item:
                            if nm.tag.endswith("name") and nm.text:
                                interests.append(nm.text.strip())
        interests = interests[:20]

        ep_acc = 0
        for c in ir.iter():
            if c.tag.endswith("EPAccreditedNumber") and c.text:
                try:
                    ep_acc = int(float(c.text))
                except ValueError:
                    pass
                break

        legislative = ""
        for c in ir.iter():
            if c.tag.endswith("EULegislativeProposals"):
                legislative = _text(c)[:2000]
                break

        tags = tag_text(name, acronym, goals, legislative, " ".join(interests), category)

        yield {
            "register_id": reg_id,
            "name": name,
            "acronym": acronym,
            "category": category,
            "country": country,
            "goals": goals[:1500] if goals else "",
            "interests": interests[:15],
            "ep_accredited": ep_acc,
            "budget_max_eur": _budget_max(ir),
            "tags": tags,
            "register_url": (
                f"https://transparency-register.europa.eu/search-register-or-update/"
                f"organisation-detail_en?id={reg_id}"
                if reg_id
                else ""
            ),
        }


def load_organizations(xml_path: Path, limit: int | None = None) -> list[dict]:
    rows = []
    for row in parse_organizations(xml_path):
        rows.append(row)
        if limit and len(rows) >= limit:
            break
    return rows


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _child_text(node: etree._Element, name: str) -> str:
    for c in node:
        if _local(c.tag) == name and c.text:
            return c.text.strip()
    return ""


def load_accredited(xml_path: Path) -> list[dict]:
    rows = []
    parser = etree.XMLParser(recover=True, huge_tree=True)
    tree = etree.parse(str(xml_path), parser)
    for node in tree.iter():
        if _local(node.tag) != "accreditedPerson":
            continue
        reg_id = _child_text(node, "orgIdentificationCode")
        rows.append(
            {
                "register_id": reg_id,
                "first_name": _child_text(node, "firstName"),
                "last_name": _child_text(node, "lastName"),
                "organisation": _child_text(node, "orgName"),
                "accreditation_start": _child_text(node, "accreditationStartDate"),
                "accreditation_end": _child_text(node, "accreditationEndDate"),
            }
        )
    return rows


def aggregate_by_org(accredited: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in accredited:
        rid = row.get("register_id")
        if rid:
            counts[rid] = counts.get(rid, 0) + 1
    return counts


def parse_lobby_register(
    org_xml: Path,
    accred_xml: Path | None = None,
) -> tuple[dict, dict]:
    orgs = load_organizations(org_xml)
    accred_counts: dict[str, int] = {}
    accredited_rows: list[dict] = []
    if accred_xml and accred_xml.exists():
        accredited_rows = load_accredited(accred_xml)
        accred_counts = aggregate_by_org(accredited_rows)
        for org in orgs:
            org["accredited_persons"] = accred_counts.get(org["register_id"], 0)

    tag_counts = Counter()
    for org in orgs:
        for t in org.get("tags") or []:
            tag_counts[t] += 1

    org_payload = {
        "source": "lobby_register",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(orgs),
        "tag_counts": dict(tag_counts),
        "organizations": orgs,
    }
    accred_payload = {
        "source": "lobby_register",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(accredited_rows),
        "persons": accredited_rows,
        "counts_by_register_id": accred_counts,
    }
    return org_payload, accred_payload


def fetch_and_parse_lobby(data_root: Path) -> list[Path]:
    """Download to raw/, write parsed/lobby/*.json."""
    raw_dir = data_root / "raw"
    parsed_dir = data_root / "parsed" / "lobby"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    paths = fetch_lobby_register(raw_dir)
    org_xml, accred_xml = paths[0], paths[1]
    org_payload, accred_payload = parse_lobby_register(org_xml, accred_xml)

    org_path = save_json(parsed_dir / "organizations.json", org_payload)
    accred_path = save_json(parsed_dir / "accredited.json", accred_payload)
    update_manifest(
        data_root / "parsed",
        "lobby",
        {"organizations": len(org_payload["organizations"]), "accredited": accred_payload["total"]},
    )
    return [org_path, accred_path]


def parse_from_raw(raw_dir: Path, parsed_dir: Path) -> list[Path]:
    org_xml = raw_dir / ORG_FILENAME
    accred_xml = raw_dir / ACCRED_FILENAME
    if not org_xml.exists():
        raise FileNotFoundError(f"missing {org_xml}")
    parsed_dir.mkdir(parents=True, exist_ok=True)
    org_payload, accred_payload = parse_lobby_register(org_xml, accred_xml if accred_xml.exists() else None)
    org_path = save_json(parsed_dir / "organizations.json", org_payload)
    accred_path = save_json(parsed_dir / "accredited.json", accred_payload)
    return [org_path, accred_path]
