"""European Commission meetings with interest representatives."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lxml import etree

from transparent_scrape.core.config import EC_MEETINGS_BASE
from transparent_scrape.core.http import download
from transparent_scrape.core.storage import save_json, update_manifest

DATASETS = {
    "1419": "meetingscommissionrepresentatives1419",
    "1924": "meetingscommissionrepresentatives1924",
    "2429": "meetingscommissionrepresentatives2429",
    "dg": "meetingsdirectorgenerals",
}


def dataset_url(dataset: str) -> str:
    name = DATASETS.get(dataset, dataset)
    return f"{EC_MEETINGS_BASE}?name={name}"


def fetch_dataset(dataset: str, raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / f"ec_meetings_{dataset}.xml"
    return download(dataset_url(dataset), dest)


def _text(el: etree._Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _child(parent: etree._Element, tag: str) -> etree._Element | None:
    for c in parent:
        if c.tag.endswith(tag) or c.tag == tag:
            return c
    return None


def parse_meetings_xml(xml_path: Path) -> list[dict[str, Any]]:
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(str(xml_path), parser)
    root = tree.getroot()
    meetings = []
    for mnode in root.iter():
        if not mnode.tag.endswith("meeting"):
            continue
        entities = []
        ents = _child(mnode, "entities")
        if ents is not None:
            for en in ents:
                if not en.tag.endswith("entity"):
                    continue
                name_el = _child(en, "name")
                id_el = _child(en, "id")
                entities.append({"name": _text(name_el), "register_id": _text(id_el)})

        reps = []
        reps_el = _child(mnode, "representatives")
        if reps_el is not None:
            for r in reps_el:
                if not r.tag.endswith("representative"):
                    continue
                reps.append(
                    {
                        "name": _text(_child(r, "name")),
                        "title": _text(_child(r, "title")),
                    }
                )

        meetings.append(
            {
                "date": _text(_child(mnode, "date")),
                "cabinet": _text(_child(mnode, "cabinet")),
                "subject": _text(_child(mnode, "subject")),
                "location": _text(_child(mnode, "location")),
                "entities": entities,
                "representatives": reps,
            }
        )
    return meetings


def index_by_register_id(meetings: list[dict]) -> dict[str, list[dict]]:
    by_id: dict[str, list[dict]] = defaultdict(list)
    for m in meetings:
        for ent in m.get("entities") or []:
            rid = ent.get("register_id")
            if rid:
                by_id[rid].append(m)
    return dict(by_id)


def fetch_and_parse(dataset: str, data_root: Path) -> Path:
    raw_dir = data_root / "raw"
    parsed_dir = data_root / "parsed" / "ec_meetings"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    xml_path = fetch_dataset(dataset, raw_dir)
    meetings = parse_meetings_xml(xml_path)
    by_reg = index_by_register_id(meetings)

    payload = {
        "source": "ec_meetings",
        "dataset": dataset,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_meetings": len(meetings),
        "meetings": meetings,
        "by_register_id": by_reg,
    }
    path = save_json(parsed_dir / f"{dataset}.json", payload)
    update_manifest(
        data_root / "parsed",
        f"ec_meetings_{dataset}",
        {"meetings": len(meetings), "orgs_linked": len(by_reg)},
    )
    return path


def parse_from_raw(dataset: str, raw_dir: Path, parsed_dir: Path) -> Path:
    xml_path = raw_dir / f"ec_meetings_{dataset}.xml"
    if not xml_path.exists():
        raise FileNotFoundError(xml_path)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    meetings = parse_meetings_xml(xml_path)
    payload = {
        "source": "ec_meetings",
        "dataset": dataset,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_meetings": len(meetings),
        "meetings": meetings,
        "by_register_id": index_by_register_id(meetings),
    }
    return save_json(parsed_dir / f"{dataset}.json", payload)
