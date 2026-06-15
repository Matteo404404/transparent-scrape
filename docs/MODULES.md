# Source modules reference

CLI entry point: `tscrape`. Default data root: `data/` (override with `--out`).

---

## `ep_api` — European Parliament Open Data

| | |
|--|--|
| **CLI** | `tscrape ep fetch`, `tscrape ep enrich` |
| **API** | `https://data.europarl.europa.eu/api/v2` |
| **Raw** | (API only; optional profile HTML in other modules) |
| **Parsed** | `parsed/meps/term_{n}.json`, `parsed/meps/{id}.json` |

Fetches term roster, then optional per-MEP enrichment (group, country, committees, mandate).

---

## `lobby_register` — EU Transparency Register

| | |
|--|--|
| **CLI** | `tscrape lobby fetch`, `tscrape lobby parse` |
| **URLs** | Daily XML exports (organisations + accredited persons) |
| **Raw** | `raw/lobby_organisations.xml`, `raw/lobby_accredited.xml` |
| **Parsed** | `parsed/lobby/organizations.json`, `parsed/lobby/accredited.json` |

Applies `core.tags` keyword classification on declared goals/interests.

---

## `wmm` — Where's My MEP

| | |
|--|--|
| **CLI** | `tscrape wmm fetch <id>`, `tscrape wmm batch`, `tscrape wmm show <id>` |
| **Site** | https://www.whatsmymep.com |
| **Parsed** | `parsed/wmm/{mep_id}.json` |

Outside activities, meetings, income bands. Rate-limited (~1 req/s).

---

## `meps_declarations` — Conflict-of-interest dossiers

| | |
|--|--|
| **CLI** | `tscrape declarations fetch`, `tscrape declarations refresh-pdfs` |
| **API** | `/meps-declarations?person-id=…` |
| **Raw** | `raw/declarations/DCI-*.pdf` |
| **Parsed** | `parsed/declarations/conflicts/{mep_id}.json` |

`refresh-pdfs` downloads PDFs for rows missing text only (no API re-fetch).

---

## `ep_declarations` — Financial interest PDFs

| | |
|--|--|
| **CLI** | `tscrape ep-declarations fetch` |
| **Raw** | `raw/declarations/financial/{mep_id}/*.pdf` |
| **Parsed** | `parsed/declarations/financial/{mep_id}.json` |

Largest disk footprint (~1.4 GB for full term). Use `--no-pdf` to skip in `tscrape run`.

---

## `ec_meetings` — Commission transparency meetings

| | |
|--|--|
| **CLI** | `tscrape ec-meetings fetch --dataset 2429` |
| **Raw** | `raw/ec_meetings_{dataset}.xml` |
| **Parsed** | `parsed/ec_meetings/{dataset}.json` |

Dataset `2429` is the standard lobby meeting log. Additional dataset IDs can be added.

---

## `appf` — Europarty funding

| | |
|--|--|
| **CLI** | `tscrape appf fetch --year 2024`, `--years 2020,2021,…` |
| **Raw** | `raw/appf_parties_{year}.xlsx` (+ JSON sidecar) |
| **Parsed** | `parsed/appf/parties_{year}.json` |

Party-level contributions and donations, not per-MEP.

---

## `opensanctions` — PEP bulk enrichment

| | |
|--|--|
| **CLI** | `tscrape opensanctions fetch` |
| **URL** | OpenSanctions `eu_meps` dataset export |
| **Parsed** | `parsed/opensanctions/eu_meps.json` |

Index by MEP id for citizenship/topic enrichment. Not an accusation source.

---

## `integrity_watch` — Integrity Watch EU probe

| | |
|--|--|
| **CLI** | `tscrape integrity-watch status` |
| **Parsed** | `parsed/integrity_watch/status.json` |

Checks datahub availability; full ingest when API is stable.

---

## Orchestration

### `tscrape run`

```bash
tscrape run --out data \
  --sources ep,lobby,appf,ec_meetings \
  --term 10 \
  --no-pdf
```

### `tscrape postprocess`

Incremental backfill after a heavy run:

```bash
tscrape postprocess --out data \
  --appf-years 2020,2021,2022,2023,2024 \
  --conflict-pdfs \
  --conflict-pdf-limit 500
```

Flags: `--enrich-mandates`, `--force`, `--no-pdf`.

---

## Python API

```python
from pathlib import Path
from transparent_scrape.core.pipeline import RunOptions, run_sources

run_sources(
    Path("data"),
    ["ep", "lobby", "appf"],
    options=RunOptions(term=10, extract_pdf=False),
)
```

Individual modules are importable, e.g. `from transparent_scrape.sources import lobby_register`.
