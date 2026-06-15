"""Map EP political groups to APPF europarty abbreviations."""

from __future__ import annotations

# APPF sheet abbreviations (2024 parties file)
APPF_PARTIES: dict[str, str] = {
    "EPP": "European People's Party",
    "PES": "Party of European Socialists",
    "ALDE": "Alliance of Liberals and Democrats for Europe Party",
    "EDP": "European Democratic Party",
    "EGP": "European Green Party",
    "EFA": "European Free Alliance",
    "Patriots.eu": "Patriots.eu",
    "EL": "Party of the European Left",
    "ECRP": "European Conservatives and Reformists Party",
    "ECPP": "European Christian Political Party",
    "ELA": "European Left Alliance for the People and the Plan",
    "ESN": "Europe of Sovereign Nations",
}

# Labels from EP corporate-bodies API (short) -> APPF abbreviation
EP_GROUP_TO_APPF: dict[str, str] = {
    "PPE": "EPP",
    "EPP": "EPP",
    "S&D": "PES",
    "PES": "PES",
    "Renew": "ALDE",
    "RE": "ALDE",
    "ALDE": "ALDE",
    "Greens/EFA": "EGP",
    "Verts/ALE": "EGP",
    "EGP": "EGP",
    "EFA": "EFA",
    "ECR": "ECRP",
    "ECRP": "ECRP",
    "The Left": "EL",
    "GUE/NGL": "EL",
    "EL": "EL",
    "PfE": "Patriots.eu",
    "Patriots for Europe": "Patriots.eu",
    "Patriots.eu": "Patriots.eu",
    "ESN": "ESN",
    "ID": "Patriots.eu",  # legacy ID group; APPF uses Patriots.eu from 2024
    "NI": "",
    "Non-attached": "",
}


def political_group_to_appf_abbr(political_group: str) -> str | None:
    """Return APPF abbreviation for an EP API political group label."""
    if not political_group:
        return None
    key = political_group.strip()
    if key in EP_GROUP_TO_APPF:
        abbr = EP_GROUP_TO_APPF[key]
        return abbr or None
    for label, abbr in EP_GROUP_TO_APPF.items():
        if label.lower() in key.lower():
            return abbr or None
    return None


def appf_abbr_to_party_name(abbr: str) -> str | None:
    return APPF_PARTIES.get(abbr)


def link_mep_to_appf(political_group: str) -> dict[str, str | None]:
    abbr = political_group_to_appf_abbr(political_group)
    return {
        "appf_abbreviation": abbr,
        "appf_party": appf_abbr_to_party_name(abbr) if abbr else None,
    }
