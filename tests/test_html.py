from transparent_scrape.core.html import parse_html, text_of, xpath_all

SAMPLE = """
<html><body>
  <article class="listing"><h2>Studio</h2><span class="price">€650</span></article>
</body></html>
"""


def test_parse_listings_html():
    doc = parse_html(SAMPLE)
    cards = xpath_all(doc, "//article[@class='listing']")
    assert len(cards) == 1
    title = text_of(xpath_all(cards[0], ".//h2")[0])
    assert title == "Studio"
