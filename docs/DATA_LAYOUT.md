# Data layout conventions

`--out` (default `data/`) is the root. Any downstream project can point here (e.g. `eu-parl-observatory/data/`).

## Directory tree

```text
{data_root}/
  raw/                          # bytes exactly as downloaded
    lobby_organisations.xml
    lobby_accredited.xml
    ec_meetings_2429.xml
    appf_parties_2024.xlsx
    opensanctions_eu_meps.ftm.json
    ep_profiles/                # optional HTML snapshots
    declarations/
      DCI-*.pdf                 # conflict-of-interest PDFs
      financial/{mep_id}/*.pdf  # financial interest PDFs

  parsed/                       # normalised JSON
    manifest.json               # pipeline bookkeeping
    meps/
      term_10.json
      {mep_id}.json
    wmm/{mep_id}.json
    lobby/
      organizations.json
      accredited.json
    appf/parties_{year}.json
    ec_meetings/{dataset}.json
    declarations/
      conflicts/{mep_id}.json
      financial/{mep_id}.json
    opensanctions/eu_meps.json
    integrity_watch/status.json
```

## Raw vs parsed

| Layer | Purpose | Git |
|-------|---------|-----|
| `raw/` | Audit trail, re-parse without re-download | **Never commit** (see `.gitignore`) |
| `parsed/` | Stable input for analytics / sites | Regenerate locally; optional commit in downstream repos |

## Parsed JSON envelope

When using `save_parsed()`, dicts get a `fetched_at` ISO timestamp if missing.

`manifest.json` shape:

```json
{
  "fetched_at": "2026-06-12T12:00:00+00:00",
  "sources": {
    "run": {
      "sources": ["ep", "lobby"],
      "completed_at": "...",
      "updated_at": "..."
    }
  }
}
```

## Path helper

```python
from pathlib import Path
from transparent_scrape.core.config import data_layout

paths = data_layout(Path("/my/project/data"))
paths["parsed_lobby"]  # → .../parsed/lobby
```

## Disk expectations (EU full stack)

| Content | Approximate size |
|---------|------------------|
| Financial PDFs | ~1.4 GB |
| Conflict PDFs (complete) | ~875 MB |
| Parsed JSON (with excerpts) | ~100–150 MB |
| Lobby XML raw | ~110 MB |

Use `tscrape run --no-pdf` for register-only refreshes without PDF weight.

## Conflict PDF ingest semantics

A declaration row is considered **text-ingested** when extracted PDF text length > 100 characters (matches `refresh_missing_pdfs` logic). Short or failed extractions keep metadata but no excerpt.

Downstream audit: `python -m euparl.cli audit` in eu-parl-observatory.
