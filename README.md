# transparent-scrape

**Modular fetch-and-parse toolkit for public transparency data.**

Python library + CLI (`tscrape`) that downloads official EU institutional sources, normalises them to JSON, and writes a predictable `raw/` + `parsed/` tree. No website, no editorial merge, no accusations. Downstream projects (dashboards, archives, research pipelines) consume the JSON.

**Primary consumer today:** [eu-parl-observatory](https://github.com/Matteo404404/eu-parl-observatory) (EP transparency archive).

**Design goal:** EU institutions first, but the **core layer is domain-agnostic** (HTTP, rate limits, storage, PDF text, keyword tags). New sources are added as small modules under `sources/`.

---

## Why this exists

Public transparency data is scattered across XML dumps, JSON APIs, XLSX reports, and PDF declarations. This package:

1. **Fetches** with retries, rate limits, and a clear User-Agent
2. **Parses** into stable JSON schemas
3. **Separates** raw bytes from parsed facts (`data/raw/` vs `data/parsed/`)
4. **Composes** sources via `tscrape run --sources ep,lobby,…` or Python `run_sources()`

You bring interpretation and UI. This package brings reproducible ingestion.

---

## Install

```bash
git clone https://github.com/Matteo404404/transparent-scrape.git
cd transparent-scrape
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**As a dependency** (local path or git URL):

```bash
pip install -e "../transparent-scrape"
# or when published:
# pip install git+https://github.com/Matteo404404/transparent-scrape.git
```

Requires **Python 3.11+**.

---

## Quick start

```bash
# Fast refresh: roster, lobby register, APPF, EC meetings (no heavy PDFs)
tscrape run --out data --sources ep,lobby,appf,ec_meetings --no-pdf

# Single source
tscrape lobby fetch --out data
tscrape lobby parse --out data

# Conflict declarations (API metadata + optional PDF text)
tscrape declarations fetch --out data --limit 50
tscrape declarations refresh-pdfs --out data --limit 500

# Incremental add-ons after a bulk run
tscrape postprocess --out data --conflict-pdfs
```

Point `--out` at any directory (e.g. another repo's `data/` folder):

```bash
export DATA_ROOT="/path/to/eu-parl-observatory/data"
tscrape postprocess --out "$DATA_ROOT" --conflict-pdfs
```

---

## Source modules (EU)

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

**Inspect what you have:**

```bash
tscrape audit --out data
tscrape sources list
tscrape sources list --status probe
```

Full reference: [docs/MODULES.md](docs/MODULES.md).

---

## Reusable core (for your own projects)

Import primitives without EU-specific logic:

```python
from pathlib import Path
from transparent_scrape.core.http import download, get_json, get_text
from transparent_scrape.core.storage import save_json, save_parsed, update_manifest
from transparent_scrape.core.rate_limit import RateLimiter
from transparent_scrape.core.pdf import extract_pdf_text
from transparent_scrape.core.tags import tag_text, TAG_RULES
```

| Component | Use for |
|-----------|---------|
| `core.http` | Retrying downloads, JSON GET, custom User-Agent |
| `core.storage` | JSON IO, `parsed/manifest.json` bookkeeping |
| `core.rate_limit` | Polite scraping (`RateLimiter`) |
| `core.pdf` | PDF text extraction via pdfplumber |
| `core.tags` | Keyword tagging on free text (extend `TAG_RULES`) |
| `core.config.data_layout` | Standard `raw/` / `parsed/` paths |

How to add a new source: [docs/EXTENDING.md](docs/EXTENDING.md).

---

## Output layout

```text
data/
  raw/              # bytes as fetched (XML, PDF, XLSX, HTML)
  parsed/           # normalised JSON
    manifest.json   # last run metadata per source
```

Convention details: [docs/DATA_LAYOUT.md](docs/DATA_LAYOUT.md).

---

## What this package does **not** do

- No criminal allegations or editorial scoring
- No guaranteed completeness (sources are self-declared or API-limited)
- No production database (filesystem JSON only)
- Outside income is often **bands**, not exact euros (EP rules + WMM)

Source URLs and attribution: [docs/SOURCES.md](docs/SOURCES.md).

---

## Tests

```bash
pytest
pytest -m live   # optional network integration
```

---

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/README.md](docs/README.md) | Index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layers, pipeline, boundaries |
| [docs/MODULES.md](docs/MODULES.md) | Per-source CLI and outputs |
| [docs/SOURCES.md](docs/SOURCES.md) | Official URLs and terms |
| [docs/DATA_LAYOUT.md](docs/DATA_LAYOUT.md) | File naming conventions |
| [docs/EXTENDING.md](docs/EXTENDING.md) | Add new fetchers |
| [CONTRIBUTING.md](CONTRIBUTING.md) | PR guidelines |

---

## License

MIT — see [LICENSE](LICENSE). Institutional data remains subject to the original publishers' terms; always attribute the source register or API.
