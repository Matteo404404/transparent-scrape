# Extending transparent-scrape

Add new public datasets as small modules. The pattern is always: **fetch → raw → parse → parsed → manifest**.

## Minimal module template

```python
"""My registry — download and parse."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from transparent_scrape.core.http import download, get_json
from transparent_scrape.core.storage import save_json, update_manifest

SOURCE_URL = "https://example.org/export.json"


def fetch_raw(raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    return download(SOURCE_URL, raw_dir / "example_export.json")


def parse(raw_path: Path, parsed_dir: Path) -> Path:
    import json

    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    out = {
        "source_url": SOURCE_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "records": payload.get("items") or [],
    }
    path = parsed_dir / "example" / "records.json"
    save_json(path, out)
    update_manifest(parsed_dir, "example", {"record_count": len(out["records"])})
    return path


def fetch_and_parse(data_root: Path) -> Path:
    raw = fetch_raw(data_root / "raw")
    return parse(raw, data_root / "parsed")
```

## Integration checklist

1. **Module file** — `src/transparent_scrape/sources/your_source.py`
2. **Export** — add to `sources/__init__.py` `__all__`
3. **Pipeline** — optional block in `core/pipeline.py` `run_sources()` if it should run with `tscrape run`
4. **CLI** — subcommand in `cli.py` for manual runs
5. **Config** — canonical URLs in `core/config.py` if shared
6. **Tests** — fixture JSON/XML in `tests/fixtures/`, test parse output shape
7. **Docs** — `docs/MODULES.md` + `docs/SOURCES.md`

## Use core primitives

| Need | Import |
|------|--------|
| File download | `core.http.download` |
| JSON API | `core.http.get_json` (pass `rate_limit=False` for non-EP APIs) |
| HTML page | `core.http.get_text` |
| Polite delay | `core.rate_limit.RateLimiter` or reuse `web_limiter` |
| PDF text | `core.pdf.extract_pdf_text` |
| Keyword tags | `core.tags.tag_text`, extend `TAG_RULES` |
| Paths | `core.config.data_layout` |

## Source protocol (future)

`core.source.Source` is a `Protocol` with `name` and `fetch(out_dir)`. New modules can implement it; pipeline registration will evolve toward a plugin list.

## Non-EU datasets

Same layout works for housing listings, market APIs, national registers, CKAN portals, etc.

**Start here:** [GENERIC.md](GENERIC.md) (CLI `tscrape get`, `core/html`, example in `examples/`).

Keep modules **focused**: one site section or one API export per file. Fetch → raw → parse → parsed → manifest.

## What reviewers expect

- Public URL documented in `docs/SOURCES.md`
- No hardcoded secrets
- `skip_existing` respected for expensive runs
- Tests without network by default
- Neutral docstrings (fetch/parse, not "expose corruption")

## Downstream consumption

Projects like eu-parl-observatory read `parsed/` only. Do not import observatory code from this package. Optional exporters belong in the downstream repo (`euparl.exporters`).
