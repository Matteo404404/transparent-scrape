#!/usr/bin/env python3
"""Minimal listing scrape pattern (swap URL + xpath for your site)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from transparent_scrape.core.html import parse_html, text_of, xpath_all
from transparent_scrape.core.storage import save_json

# ponytail: fixture HTML for self-check; real run needs LIST_URL + live network
SAMPLE_HTML = """
<html><body>
  <article class="listing"><h2>Flat A</h2><span class="price">€900</span></article>
  <article class="listing"><h2>Flat B</h2><span class="price">€1200</span></article>
</body></html>
"""


def parse_listings(html: str, source_url: str) -> list[dict]:
    doc = parse_html(html)
    rows = []
    for card in xpath_all(doc, "//article[@class='listing']"):
        title_el = xpath_all(card, ".//h2")
        price_el = xpath_all(card, ".//*[@class='price']")
        rows.append(
            {
                "title": text_of(title_el[0]) if title_el else "",
                "price": text_of(price_el[0]) if price_el else "",
                "source_url": source_url,
            }
        )
    return rows


def demo() -> None:
    rows = parse_listings(SAMPLE_HTML, "https://example.com/rentals")
    assert len(rows) == 2
    assert rows[0]["title"] == "Flat A"
    assert rows[0]["price"] == "€900"


def main() -> None:
    demo()
    out_dir = Path("data/parsed/housing")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_url": "fixture",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "records": parse_listings(SAMPLE_HTML, "https://example.com/rentals"),
    }
    path = out_dir / "listings_fixture.json"
    save_json(path, payload)
    print(f"wrote {path} ({len(payload['records'])} rows)")


if __name__ == "__main__":
    main()
