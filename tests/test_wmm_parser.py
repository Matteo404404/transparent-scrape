from pathlib import Path

import pytest

from transparent_scrape.sources import appf, wmm


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def wmm_html() -> str:
    return (FIXTURES / "wmm_96761.html").read_text(encoding="utf-8")


def test_parse_voss_profile(wmm_html: str) -> None:
    profile = wmm.parse_wmm_profile("96761", wmm_html)
    assert profile.name and "VOSS" in profile.name.upper()
    assert profile.income_min == 39006
    assert profile.income_max == 42907
    assert len(profile.activities) == 31
    assert len(profile.meetings) == 8


def test_activity_income_and_flow(wmm_html: str) -> None:
    profile = wmm.parse_wmm_profile("96761", wmm_html)
    paid = [a for a in profile.activities if a.income_eur and a.income_eur > 0]
    assert paid
    assert paid[0].flow == "receives"
    assert paid[0].organization


def test_meeting_iso_date(wmm_html: str) -> None:
    profile = wmm.parse_wmm_profile("96761", wmm_html)
    assert profile.meetings[0].iso_date.count("-") == 2


def test_profile_to_dict(wmm_html: str) -> None:
    profile = wmm.parse_wmm_profile("96761", wmm_html)
    doc = wmm.profile_to_dict(profile)
    assert doc["mep_id"] == "96761"
    assert doc["meetings_count"] == 8
    assert doc["paid_activities_count"] >= 1
    assert doc["source"] == "wmm"


def test_parse_appf_parties_xlsx() -> None:
    path = FIXTURES / "appf_2024_parties.xlsx"
    payload = appf.parse_parties_xlsx(path, 2024)
    assert payload["financial_year"] == 2024
    assert len(payload["summary"]) >= 10
    epp = next(r for r in payload["summary"] if r["abbreviation"] == "EPP")
    assert epp["contributions_legal_persons_eur"] == 1483572.25
    assert "EPP" in payload["party_details"]
