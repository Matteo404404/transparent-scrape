# Contributing to transparent-scrape

Thanks for helping build a reusable transparency ingestion toolkit.

## What belongs in this repo

| Yes | No |
|-----|-----|
| Fetch + parse modules for **public** datasets | Site UI, charts, editorial merge logic |
| Core HTTP/storage/PDF utilities | Accusations or scoring of individuals |
| Tests with fixtures | Committed `data/raw` PDFs or XML dumps |
| Documentation with source URLs | Secrets or API keys |

Downstream projects (e.g. eu-parl-observatory) handle triangulation, curated YAML, and the public archive.

## Adding a source module

1. Create `src/transparent_scrape/sources/your_source.py`
2. Implement `fetch` / `parse` functions writing to `raw/` and `parsed/`
3. Register in `sources/__init__.py`, `core/pipeline.py`, and `cli.py`
4. Add tests with fixtures under `tests/fixtures/`
5. Document in `docs/MODULES.md` and `docs/SOURCES.md`

See [docs/EXTENDING.md](docs/EXTENDING.md).

## Code style

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

- Python 3.11+, type hints where helpful
- Rate-limit external APIs; set a descriptive User-Agent
- `skip_existing=True` by default for long-running fetches
- Plain log lines (`print("[tscrape] …")`), no banner noise

## Pull request checklist

- [ ] Primary source URL documented in `docs/SOURCES.md`
- [ ] Tests pass (`pytest`)
- [ ] No large binaries in the diff
- [ ] CLI help text updated if commands changed
- [ ] Neutral wording (facts from sources, not conclusions)

## Reporting bugs

Include: command run, `--out` path, error message, and whether the source endpoint was reachable. Do not attach full PDF caches.
