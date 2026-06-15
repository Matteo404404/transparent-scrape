# Source modules

One Python file per public dataset. Each module should:

1. Download to `raw/` (or call a JSON API)
2. Parse to `parsed/`
3. Update `manifest.json`
4. Document its URL in `docs/SOURCES.md`

| Module | Institution |
|--------|-------------|
| `ep_api.py` | European Parliament Open Data |
| `lobby_register.py` | EU Transparency Register |
| `wmm.py` | Where's My MEP |
| `meps_declarations.py` | EP conflict-of-interest declarations |
| `ep_declarations.py` | EP financial interest PDFs |
| `ec_meetings.py` | European Commission meeting logs |
| `appf.py` | Europarty funding (APPF) |
| `opensanctions.py` | OpenSanctions eu_meps |
| `integrity_watch.py` | Integrity Watch EU |

Add new files here and register in `__init__.py`. See [../docs/EXTENDING.md](../docs/EXTENDING.md).
