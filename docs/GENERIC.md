# Generic scraping (any domain)

Use **transparent-scrape** as a small library: HTTP + rate limits + `raw/`/`parsed/` layout. EU Parliament modules are one bundled pack under `sources/`, not the whole package.

**eu-parl-observatory** is just a consumer. Your housing, market, or news project can `pip install` this repo and never touch EU code.

---

## Layout (always the same)

```text
my-project/data/
  raw/       # bytes as fetched (html, pdf, csv, json)
  parsed/    # your normalised JSON + manifest.json
```

```python
from pathlib import Path
from transparent_scrape import base_paths
from transparent_scrape.core.storage import save_parsed, update_manifest

paths = base_paths(Path("data"))
paths["raw"].mkdir(parents=True, exist_ok=True)
paths["parsed"].mkdir(parents=True, exist_ok=True)
```

---

## One-off fetch (CLI)

```bash
# HTML page → file
tscrape get "https://example.com/listings" --out data/raw/housing/page.html

# JSON API
tscrape get "https://api.example.com/v1/prices" --json --out data/raw/market/prices.json

# Binary (PDF, gzip dump)
tscrape get "https://example.com/report.pdf" --binary --out data/raw/report.pdf
```

Respect robots.txt and site terms yourself. The package only adds retries, User-Agent, and polite delays.

---

## HTML listing page (library)

No browser, no Playwright. Static HTML + lxml:

```python
from datetime import datetime, timezone
from pathlib import Path

from transparent_scrape.core.html import parse_html, text_of, xpath_all
from transparent_scrape.core.http import get_text
from transparent_scrape.core.storage import save_parsed, update_manifest

LIST_URL = "https://example.com/rentals?page=1"
# ponytail: xpath selectors are site-specific; swap expr for your DOM


def scrape_page(url: str) -> list[dict]:
    html = get_text(url)
    doc = parse_html(html)
    rows = []
    for card in xpath_all(doc, "//article[@class='listing']"):
        title = text_of(xpath_all(card, ".//h2")[0]) if xpath_all(card, ".//h2") else ""
        price = text_of(xpath_all(card, ".//*[@class='price']")[0]) if xpath_all(card, ".//*[@class='price']") else ""
        rows.append({"title": title, "price": price, "source_url": url})
    return rows


def run(data_root: Path) -> Path:
    records = scrape_page(LIST_URL)
    out = save_parsed(
        data_root / "parsed",
        "housing/listings_page1.json",
        {
            "source_url": LIST_URL,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "records": records,
        },
    )
    update_manifest(data_root / "parsed", "housing_listings", {"record_count": len(records)})
    return out
```

Runnable sketch: [examples/scrape_listings.py](../examples/scrape_listings.py).

---

## Where to put your module

| Option | When |
|--------|------|
| **Your repo** (`my_scraper/sources/housing.py`) | Normal case. Import `transparent_scrape.core.*`. |
| **This repo** (`sources/your_source.py`) | Only if you want to share it upstream (PR). |

Checklist (same as EU modules): fetch → raw → parse → parsed → `update_manifest`. See [EXTENDING.md](EXTENDING.md).

Do **not** import eu-parl-observatory from here. Downstream reads `parsed/` only.

---

## Core imports

```python
from transparent_scrape.core.http import download, get_json, get_text
from transparent_scrape.core.html import parse_html, xpath_all, text_of
from transparent_scrape.core.rate_limit import RateLimiter
from transparent_scrape.core.storage import save_json, save_parsed, update_manifest
from transparent_scrape.core.pdf import extract_pdf_text
from transparent_scrape.core.tags import tag_text, TAG_RULES
```

---

## Bundled EU pack

```bash
tscrape sources list --pack eu
tscrape run --out data --sources ep,lobby   # EU only when you ask for it
```

` tscrape audit` reports EU-shaped paths if present; ignore sections that do not apply to your project.

---

## What we deliberately skip

- **Headless browser** (Playwright/Selenium): add only when a site is JS-only.
- **Plugin registry / YAML config**: one Python module per source is enough until you have many.
- **Database**: filesystem JSON until size forces Postgres/SQLite.

Add those when a profiler or a broken site proves you need them.
