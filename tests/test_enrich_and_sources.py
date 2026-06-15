from pathlib import Path

import pytest

from transparent_scrape.core.europarty import link_mep_to_appf, political_group_to_appf_abbr
from transparent_scrape.sources import appf, ep_api, integrity_watch, meps_declarations, opensanctions

FIXTURES = Path(__file__).parent / "fixtures"


def test_political_group_to_appf_mapping() -> None:
    assert political_group_to_appf_abbr("PPE") == "EPP"
    assert political_group_to_appf_abbr("Renew") == "ALDE"
    assert political_group_to_appf_abbr("PfE") == "Patriots.eu"
    link = link_mep_to_appf("PPE")
    assert link["appf_abbreviation"] == "EPP"
    assert "People's Party" in (link["appf_party"] or "")


def test_extract_membership_historical_fallback() -> None:
    import json

    mep = json.loads((FIXTURES / "ep_mep_caspary_memberships.json").read_text())

    def fake_resolve(org: str) -> str:
        mapping = {"org/7018": "PPE", "org/6726": "CDU", "org/ep-10": "10"}
        return mapping.get(org, org)

    fields = ep_api.extract_membership_fields(mep, 10, fake_resolve)
    assert fields["political_group"] == "PPE"
    assert fields["national_party"] == "CDU"
    assert fields["mandate_active"] is False
    assert fields["mandate_ended"] == "2026-02-28"
    assert fields["membership_source"] == "historical"


def test_conflict_pdf_url_uses_data_host() -> None:
    import json

    payload = json.loads((FIXTURES / "meps_declarations_sample.json").read_text())
    doc = meps_declarations._parse_declaration(payload["data"][0])
    assert doc["pdf_url"] == (
        "https://data.europarl.europa.eu/distribution/doc/DCI-TEST-2026-01-01-000001_en.pdf"
    )
    candidates = meps_declarations.pdf_url_candidates(doc["doc_id"], doc["pdf_url"])
    assert candidates[0].startswith("https://data.europarl.europa.eu/")


def test_parse_opensanctions_ftm_fixture() -> None:
    payload = opensanctions.parse_entities_ftm_jsonl(FIXTURES / "opensanctions_eu_meps_sample.ftm.json")
    assert payload["linked_mep_count"] == 2
    assert payload["by_mep_id"]["96761"]["name"] == "Axel VOSS"
    assert "role.pep" in payload["by_mep_id"]["96761"]["topics"]


def test_integrity_watch_maintenance_detection() -> None:
    html = (FIXTURES / "integrity_watch_maintenance.html").read_text()
    status = integrity_watch.check_datahub_status(html)
    assert status["maintenance"] is True
    assert status["available"] is False


def test_needs_enrich_only_empty_group() -> None:
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        meps = Path(tmp) / "meps"
        meps.mkdir()
        complete = meps / "96761.json"
        complete.write_text(
            json.dumps({"identifier": "96761", "political_group": "PPE", "national_party": "CDU"}),
            encoding="utf-8",
        )
        incomplete = meps / "28219.json"
        incomplete.write_text(json.dumps({"identifier": "28219", "political_group": ""}), encoding="utf-8")

        assert ep_api.needs_enrich_update(complete) is False
        assert ep_api.needs_enrich_update(incomplete) is True
        assert ep_api.needs_enrich_update(complete, include_mandates=True) is True


def test_patch_appf_links_local() -> None:
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        parsed = Path(tmp)
        meps = parsed / "meps"
        meps.mkdir()
        path = meps / "96761.json"
        path.write_text(json.dumps({"identifier": "96761", "political_group": "PPE"}), encoding="utf-8")
        n = ep_api.patch_appf_links(parsed)
        assert n == 1
        data = json.loads(path.read_text())
        assert data["appf_abbreviation"] == "EPP"


def test_parse_legacy_appf_2021() -> None:
    import httpx

    dest = Path("/tmp/appf2021_test.xlsx")
    if not dest.exists():
        url = appf.PARTIES_XLSX_URLS[2021]
        dest.write_bytes(httpx.get(url, follow_redirects=True, timeout=60).content)
    payload = appf.parse_parties_xlsx(dest, 2021)
    assert payload["layout"] == "legacy_eupp"
    assert len(payload["summary"]) >= 8
    assert len(payload["party_details"]) >= 8


def test_appf_known_years() -> None:
    assert 2020 in appf.PARTIES_XLSX_URLS
    assert 2024 in appf.PARTIES_XLSX_URLS
    assert len(appf.DEFAULT_APPF_YEARS) == 5


@pytest.mark.live
def test_conflict_pdf_download_live() -> None:
    """One real DCI PDF from data.europarl (network)."""
    from transparent_scrape.core.http import download

    doc_id = "DCI-96761-2024-09-16-396831_de"
    url = f"https://data.europarl.europa.eu/distribution/doc/{doc_id}.pdf"
    dest = Path("/tmp") / f"{doc_id}.pdf"
    download(url, dest)
    assert dest.read_bytes()[:4] == b"%PDF"
