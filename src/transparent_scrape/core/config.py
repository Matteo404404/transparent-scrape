from __future__ import annotations

from pathlib import Path

EP_API = "https://data.europarl.europa.eu/api/v2"
EP_TERM_DEFAULT = 10

LOBBY_ORG_XML = "https://transparency-register.europa.eu/odplastorganisationxml_en"
LOBBY_ACCRED_XML = "https://transparency-register.europa.eu/odplastaccreditedxml_en"
LOBBY_NS = {"tr": "http://intragate.ec.europa.eu/transparencyregister/odp"}

EC_MEETINGS_BASE = (
    "https://ec.europa.eu/transparency-initiative/meetings/data/meetings/dataxml"
)

EP_PDF_BASE = "https://www.europarl.europa.eu"
EP_DATA_BASE = "https://data.europarl.europa.eu"

OPENSANCTIONS_EU_MEPS_CSV = (
    "https://data.opensanctions.org/datasets/latest/eu_meps/targets.simple.csv"
)
INTEGRITY_WATCH_DATAHUB = "https://data.integritywatch.eu/"

HTV_MEMBER_VOTES_URL = (
    "https://github.com/HowTheyVote/data/releases/latest/download/member_votes.csv.gz"
)
HTV_MEMBERS_URL = "https://github.com/HowTheyVote/data/releases/latest/download/members.csv.gz"
HTV_VOTES_URL = "https://github.com/HowTheyVote/data/releases/latest/download/votes.csv.gz"

PARLTRACK_DUMPS_PAGE = "https://parltrack.eu/dumps"
PARLTRACK_MEPS_DUMP = "https://parltrack.eu/dumps/ep_meps.json.zst"

EPDB_API_BASE = "https://api.epdb.eu"


def data_layout(root: Path) -> dict[str, Path]:
    """Standard data/raw and data/parsed paths under root."""
    return {
        "root": root,
        "raw": root / "raw",
        "parsed": root / "parsed",
        "raw_declarations": root / "raw" / "declarations",
        "raw_ep_profiles": root / "raw" / "ep_profiles",
        "parsed_meps": root / "parsed" / "meps",
        "parsed_wmm": root / "parsed" / "wmm",
        "parsed_lobby": root / "parsed" / "lobby",
        "parsed_appf": root / "parsed" / "appf",
        "parsed_ec": root / "parsed" / "ec_meetings",
        "parsed_declarations": root / "parsed" / "declarations",
        "parsed_howtheyvote": root / "parsed" / "howtheyvote",
        "parsed_parltrack": root / "parsed" / "parltrack",
        "parsed_epdb": root / "parsed" / "epdb",
    }
