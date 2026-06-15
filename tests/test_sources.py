from pathlib import Path

from transparent_scrape.core.tags import tag_text
from transparent_scrape.sources.lobby_register import load_accredited, parse_organizations

FIXTURES = Path(__file__).parent / "fixtures"


def test_tag_text_tobacco() -> None:
    tags = tag_text("European Tobacco Manufacturers Association", "goals", "cigarette regulation")
    assert "tobacco" in tags


def test_parse_ec_meetings_fixture() -> None:
    from transparent_scrape.sources.ec_meetings import index_by_register_id, parse_meetings_xml

    path = FIXTURES / "ec_meetings_2429.xml"
    meetings = parse_meetings_xml(path)
    assert len(meetings) == 1
    assert meetings[0]["entities"][0]["register_id"] == "123456789012-99"
    by_id = index_by_register_id(meetings)
    assert "123456789012-99" in by_id


def test_parse_meps_declaration_sample() -> None:
    from transparent_scrape.sources.meps_declarations import _parse_declaration

    import json

    payload = json.loads((FIXTURES / "meps_declarations_sample.json").read_text())
    doc = _parse_declaration(payload["data"][0])
    assert doc["doc_id"] == "DCI-TEST-2026-01-01-000001"
    assert "96761" in doc["person_ids"]
    assert doc["pdf_url"] and "data.europarl.europa.eu" in doc["pdf_url"]


def test_ep_declarations_parse_links() -> None:
    from transparent_scrape.sources.ep_declarations import parse_declaration_links

    html = (FIXTURES / "ep_declarations_96761.html").read_text()
    links = parse_declaration_links(html)
    assert len(links) >= 1
    assert any("DCI-TEST" in l["doc_id"] for l in links)


def test_pipeline_run_options_import() -> None:
    from transparent_scrape.core.pipeline import RunOptions, run_sources

    assert RunOptions(term=10).appf_year == 2024
    assert callable(run_sources)
