# transparent-scrape

**Fetch, parse, store public datasets.** Generic Python toolkit + CLI (`tscrape`).

Downloads pages and APIs with retries and rate limits, keeps a predictable `raw/` + `parsed/` tree, exports JSON. No website, no database, no editorial layer.

**Bundled EU pack:** Parliament register, MEP data, etc. (used by [eu-parl-observatory](https://github.com/Matteo404404/eu-parl-observatory)).  
**Your project:** import `transparent_scrape.core.*`, add your own modules (housing, markets, news). EU code is optional.

Full guide for non-EU use: **[docs/GENERIC.md](docs/GENERIC.md)**.

---

## Install

```bash
git clone https://github.com/Matteo404404/transparent-scrape.git
cd transparent-scrape
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

```bash
pip install -e "../transparent-scrape"   # from another repo
```

Requires **Python 3.11+**.

---

## Quick start (any site)

```bash
# one URL → file
tscrape get "https://example.com/listings" --out data/raw/housing/page.html

# JSON API
tscrape get "https://api.example.com/prices" --json --out data/raw/market/prices.json
```

```python
from pathlib import Path
from transparent_scrape import base_paths
from transparent_scrape.core.http import get_text
from transparent_scrape.core.html import parse_html, xpath_all, text_of
from transparent_scrape.core.storage import save_parsed

paths = base_paths(Path("data"))
html = get_text("https://example.com/listings")
doc = parse_html(html)
# ... xpath your DOM, save_parsed(paths["parsed"], "housing/listings.json", {...})
```

Example module: [examples/scrape_listings.py](examples/scrape_listings.py).

---

## Quick start (EU pack)

```bash
tscrape run --out data --sources ep,lobby,appf,ec_meetings --no-pdf
tscrape sources list --pack eu
tscrape audit --out data
```

Point `--out` at another repo's `data/` folder:

```bash
export DATA_ROOT="/path/to/eu-parl-observatory/data"
tscrape postprocess --out "$DATA_ROOT" --conflict-pdfs
```

---

## Source modules (EU pack)

| Module | CLI | What it ingests |
|--------|-----|-----------------|
| `ep_api` | `tscrape ep fetch` | EP Open Data API v2 MEP roster + enrichment |
| `lobby_register` | `tscrape lobby fetch/parse` | EU Transparency Register XML |
| `wmm` | `tscrape wmm batch` | Where's My MEP profiles |
| `meps_declarations` | `tscrape declarations …` | Conflict-of-interest dossier API + PDFs |
| `ep_declarations` | `tscrape ep-declarations …` | Financial declaration PDFs |
| `ec_meetings` | `tscrape ec-meetings fetch` | Commission lobby meeting logs |
| `appf` | `tscrape appf fetch` | Europarty funding (APPF) |
| `opensanctions` | `tscrape opensanctions fetch` | OpenSanctions `eu_meps` bulk |
| `howtheyvote` | `tscrape howtheyvote fetch` | Roll-call rebellion stats (ODbL) |
| `parltrack` | `tscrape parltrack status`, `tscrape parltrack meps` | MEP index + dump freshness (ODbL) |
| `epdb` | `tscrape epdb status` | Council/EP vote API probe |
| `integrity_watch` | `tscrape integrity-watch status` | Integrity Watch datahub probe |

Full reference: [docs/MODULES.md](docs/MODULES.md).

---

## Core library

| Component | Use for |
|-----------|---------|
| `core.http` | Retrying downloads, JSON GET, custom User-Agent |
| `core.html` | Parse static HTML (lxml xpath) |
| `core.storage` | JSON IO, `parsed/manifest.json` |
| `core.rate_limit` | Polite scraping (`RateLimiter`) |
| `core.pdf` | PDF text via pdfplumber |
| `core.tags` | Keyword tagging on free text |
| `core.paths.base_paths` | `{root, raw, parsed}` only |

Add a source: [docs/EXTENDING.md](docs/EXTENDING.md) · [docs/GENERIC.md](docs/GENERIC.md).

---

## Output layout

```text
data/
  raw/              # bytes as fetched
  parsed/           # normalised JSON
    manifest.json
```

[docs/DATA_LAYOUT.md](docs/DATA_LAYOUT.md)

---

## What this package does **not** do

- Headless browser (JS-heavy SPAs need Playwright elsewhere)
- Criminal allegations or editorial scoring (EU observatory adds curation downstream)
- Guaranteed completeness or a production database

---

## Tests

```bash
pytest
pytest -m live   # optional network
```

---

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/GENERIC.md](docs/GENERIC.md) | Housing, markets, any domain |
| [docs/EXTENDING.md](docs/EXTENDING.md) | Add fetchers |
| [docs/MODULES.md](docs/MODULES.md) | EU module CLI |
| [docs/DATA_LAYOUT.md](docs/DATA_LAYOUT.md) | File naming |
| [docs/SOURCES.md](docs/SOURCES.md) | EU official URLs |

---

## License

MIT — see [LICENSE](LICENSE). Respect each publisher's terms and robots.txt.
