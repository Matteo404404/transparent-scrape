# Official sources

Every module in transparent-scrape maps to a **public** endpoint. Always cite the original institution when reusing data.

Last reviewed: June 2026.

---

## EU Transparency Register

| Item | URL |
|------|-----|
| Organisations XML | https://transparency-register.europa.eu/odplastorganisationxml_en |
| Accredited persons XML | https://transparency-register.europa.eu/odplastaccreditedxml_en |
| Guidelines | https://transparency-register.europa.eu/guidance/guidelines_en |

Data is self-declared by registrants. Budget fields are ranges, not audited payments.

---

## European Parliament Open Data API v2

| Item | URL |
|------|-----|
| Base | `https://data.europarl.europa.eu/api/v2` |
| Docs | https://data.europarl.europa.eu/en/developer-corner/opendata-api |
| Conflict declarations | `/meps-declarations?person-id={id}&parliamentary-term=10` |
| Distribution docs (PDF) | `https://data.europarl.europa.eu/distribution/doc/{doc_id}_en.pdf` |

Rate limit observed in code: ~0.12 s between requests (500 / 5 min guideline).

---

## Where's My MEP

| Item | URL |
|------|-----|
| Site | https://www.whatsmymep.com |
| Profile pattern | `https://www.whatsmymep.com/meps/{id}` |

Third-party civic aggregator of EP declaration data. Not an EU institution.

---

## European Commission transparency meetings

| Item | URL |
|------|-----|
| Portal | https://ec.europa.eu/transparencyinitiative/meetings/ |
| XML export | `https://ec.europa.eu/transparency-initiative/meetings/data/meetings/dataxml` |

Dataset id `2429` is the default in this package.

---

## Authority for European Political Parties and Foundations (APPF)

Public XLSX/JSON exports per financial year (party contributions and donations).

---

## OpenSanctions

| Item | URL |
|------|-----|
| Project | https://www.opensanctions.org |
| EU MEPs export | `https://data.opensanctions.org/datasets/latest/eu_meps/` |

Used for PEP identifiers and citizenship enrichment. Presence in the dataset does not imply wrongdoing.

---

## Integrity Watch EU

| Item | URL |
|------|-----|
| Datahub | https://data.integritywatch.eu/ |

Status probe only until stable bulk access is implemented.

---

## Attribution and terms

- Raw files remain under the **terms of the publishing institution**.
- This project's MIT license applies to **code**, not to EU XML/PDF content.
- Set an honest User-Agent (`transparent-scrape/…`) and respect rate limits.
- Do not use this toolkit to circumvent access controls or bulk-scrape non-public systems.

---

## Ethical use

- Document **declared** ties and **public** records.
- Do not present keyword tags as findings of guilt or corruption.
- When building public tools, link back to the primary source URL for each fact.
