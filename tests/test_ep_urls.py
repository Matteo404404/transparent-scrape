from transparent_scrape.sources.ep_api import _mep_web_urls


def test_mep_web_urls_include_name_slug():
    profile, decl = _mep_web_urls("88882", "NEGRESCU", "Victor", "Victor NEGRESCU")
    assert profile == "https://www.europarl.europa.eu/meps/en/88882/VICTOR_NEGRESCU"
    assert decl.endswith("/declarations")
