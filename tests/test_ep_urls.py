from transparent_scrape.sources.ep_api import _mep_web_urls


def test_mep_web_urls_profile_id_only():
    profile, decl = _mep_web_urls("88882", "NEGRESCU", "Victor", "Victor NEGRESCU")
    assert profile == "https://www.europarl.europa.eu/meps/en/88882"
    assert decl == "https://www.europarl.europa.eu/meps/en/88882/VICTOR_NEGRESCU/declarations"


def test_mep_web_urls_ascii_slug():
    _, decl = _mep_web_urls("22418", "GARCÍA", "Esther", "Esther HERRANZ GARCÍA")
    assert decl.endswith("/ESTHER_HERRANZ_GARCIA/declarations")
