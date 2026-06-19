from pathlib import Path

from transparent_scrape.core.audit import audit_data_root, conflict_pdf_stats, format_audit_report
from transparent_scrape.sources.registry import SOURCE_REGISTRY, list_sources


def test_source_registry_has_odbl_modules() -> None:
    ids = {s.id for s in SOURCE_REGISTRY}
    assert {"howtheyvote", "parltrack", "epdb"}.issubset(ids)
    assert list_sources(status="probe")
    assert any(s.id == "howtheyvote" and s.license_note == "ODbL 1.0" for s in SOURCE_REGISTRY)


def test_conflict_pdf_stats_empty_dir(tmp_path: Path) -> None:
    import json

    parsed = tmp_path / "parsed"
    conflicts = parsed / "declarations" / "conflicts"
    conflicts.mkdir(parents=True)
    payload = {"declarations": [{"pdf_url": "http://x/a.pdf", "pdf_text": "x" * 120}]}
    (conflicts / "123.json").write_text(json.dumps(payload), encoding="utf-8")
    stats = conflict_pdf_stats(parsed)
    assert stats == {"rows": 1, "with_text": 1, "missing_text": 0}


def test_audit_data_root_minimal(tmp_path: Path) -> None:
    parsed = tmp_path / "parsed"
    (parsed / "meps").mkdir(parents=True)
    (parsed / "meps" / "term_10.json").write_text('{"meps":[]}', encoding="utf-8")
    report = audit_data_root(tmp_path, term=10)
    text = format_audit_report(report)
    assert "term: 10" in text
    assert "conflict dossier PDFs" in text
    assert report["sources"]["ep_roster"]["present"] is True
