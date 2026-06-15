# Documentation index

**transparent-scrape** — modular ingestion for public transparency data.

## For users

| Document | Summary |
|----------|---------|
| [../README.md](../README.md) | Install, quick start, module overview |
| [MODULES.md](MODULES.md) | CLI reference per source |
| [SOURCES.md](SOURCES.md) | Official URLs, attribution, limits |
| [DATA_LAYOUT.md](DATA_LAYOUT.md) | `raw/` and `parsed/` conventions |

## For developers

| Document | Summary |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Core vs sources, pipeline, design boundaries |
| [EXTENDING.md](EXTENDING.md) | Add fetchers for new datasets |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | PR standards |

## Related projects

| Project | Role |
|---------|------|
| [eu-parl-observatory](https://github.com/Matteo404404/eu-parl-observatory) | Triangulation + static site over `parsed/` JSON |

## Principles

1. **Source-first** — every module documents where data comes from.
2. **Neutral output** — JSON facts, not editorial conclusions.
3. **Composable** — run one source or orchestrate many.
4. **Polite fetching** — rate limits and retries by default.
