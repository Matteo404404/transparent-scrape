# Architecture

## Layers

```text
┌─────────────────────────────────────────────────────────────┐
│  CLI (tscrape)  +  Python API (run_sources, per-module)     │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  sources/          One module per institutional dataset      │
│  ep_api, lobby_register, wmm, declarations, ec_meetings, …  │
└────────────────────────────┬────────────────────────────────┘
                             │ uses
┌────────────────────────────▼────────────────────────────────┐
│  core/             Domain-agnostic building blocks         │
│  http, storage, rate_limit, pdf, tags, config, pipeline    │
└────────────────────────────┬────────────────────────────────┘
                             │ writes
┌────────────────────────────▼────────────────────────────────┐
│  {data_root}/raw/ + {data_root}/parsed/ + manifest.json    │
└─────────────────────────────────────────────────────────────┘
```

## Design boundaries

| In transparent-scrape | In downstream projects (e.g. observatory) |
|-----------------------|-------------------------------------------|
| Download public files | Merge curated YAML with scraped facts |
| Parse to JSON | Triangulate MEP ↔ org links |
| Rate-limit API calls | Analytics, rankings, UI copy |
| PDF text extraction | Evidence badges, journalism citations |
| Keyword tags on register text | Editorial briefings |

The scraper outputs **what the source says**. Interpretation lives downstream.

## Pipeline

`transparent_scrape.core.pipeline.run_sources(data_root, sources, options)` runs a comma-separated list:

```text
ep → lobby → appf → opensanctions → integrity_watch → ec_meetings
  → declarations → ep_declarations → wmm
```

Each step is independent. Failures should be handled inside the source module (retries, empty `data: []` on 404).

`postprocess` is a **second pass** for incremental work: APPF history, OpenSanctions, conflict PDF backfill, optional mandate enrichment.

## Core modules

| Module | Responsibility |
|--------|----------------|
| `core.http` | `download`, `get_text`, `get_json` with retries |
| `core.rate_limit` | `RateLimiter`, `ep_limiter`, `web_limiter` |
| `core.storage` | JSON read/write, `manifest.json` updates |
| `core.pdf` | PDF → plain text |
| `core.tags` | Regex keyword tags on free text |
| `core.config` | Canonical URLs + `data_layout()` paths |
| `core.europarty` | EP group ↔ APPF party mapping |
| `core.source` | `Source` protocol (for future plugin registry) |

## Data contract

- **Raw** files are immutable downloads (re-fetch overwrites).
- **Parsed** JSON includes `fetched_at` when written via `save_parsed`.
- **Manifest** records which pipeline step last touched each source.

Downstream code should read `parsed/` only, not scrape HTML at runtime.

## Extensibility roadmap

The package is EU-focused today but structured for more:

| Future domain | Likely module pattern |
|---------------|----------------------|
| National parliaments | `sources/{country}_register.py` |
| Company registries | `sources/opencorporates.py` (API wrapper) |
| Sanctions / PEP lists | Same pattern as `opensanctions.py` |
| Custom CSV/JSON dumps | `fetch` to `raw/`, `parse` to `parsed/` |

See [EXTENDING.md](EXTENDING.md).

## Testing

- **Unit tests** use fixtures in `tests/fixtures/` (no network).
- **`@pytest.mark.live`** optional integration tests against real endpoints.

## What not to add here

- Frontend assets
- SQL databases
- LLM summarisation of scraped content
- Non-public or authenticated sources without explicit user configuration
