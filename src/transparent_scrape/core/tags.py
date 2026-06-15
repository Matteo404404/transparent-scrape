"""Heuristic topic tags on lobby register text."""

from __future__ import annotations

import re

TAG_RULES: dict[str, list[str]] = {
    "israel_palestine": [
        r"\bisrael\b",
        r"\bpalestin",
        r"\bzion",
        r"\bknesset\b",
        r"\bhamas\b",
        r"\bgaza\b",
        r"\bwest bank\b",
        r"\bantisemit",
        r"\banti-semit",
        r"\bjewish\b",
        r"\bhebrew\b",
    ],
    "russia_energy": [
        r"\brussia\b",
        r"\brussian\b",
        r"\bgazprom\b",
        r"\brosneft\b",
        r"\bputin\b",
        r"\bnord\s*stream\b",
        r"\bukrain",
    ],
    "tobacco": [
        r"\btobacco\b",
        r"\bcigarette",
        r"\bphilip\s*morris\b",
        r"\bbritish\s*american\s*tobacco\b",
        r"\bpmi\b",
        r"\bvap(e|ing)\b",
        r"\bnicotine\b",
    ],
    "defense": [
        r"\bdefen[cs]e\b",
        r"\bmilitary\b",
        r"\barmament",
        r"\bweapon",
        r"\bnato\b",
        r"\bsecurity\s+policy\b",
    ],
    "big_tech": [
        r"\bgoogle\b",
        r"\bmeta\b",
        r"\bmicrosoft\b",
        r"\bapple\b",
        r"\bamazon\b",
        r"\bdigital\s+services\s+act\b",
        r"\bdma\b",
        r"\bartificial\s+intelligence\b",
    ],
    "finance": [
        r"\bbank(ing)?\b",
        r"\binsurance\b",
        r"\bfintech\b",
        r"\bcapital\s+market",
        r"\bprivate\s+equity\b",
    ],
    "agriculture": [
        r"\bfarmer",
        r"\bagricultur",
        r"\bcap\b",
        r"\bpesticide",
        r"\bfood\s+safety\b",
    ],
    "fossil_fuels": [
        r"\boil\b",
        r"\bgas\b",
        r"\bshell\b",
        r"\bbp\b",
        r"\bpipeline\b",
        r"\bfossil\b",
        r"\bcoal\b",
    ],
    "pharma": [
        r"\bpharma",
        r"\bmedicine\b",
        r"\bclinical\s+trial",
        r"\bhealthcare\b",
    ],
    "gambling": [
        r"\bgambl",
        r"\bbet(ting)?\b",
        r"\bcasino\b",
    ],
}

_COMPILED = {tag: [re.compile(p, re.I) for p in patterns] for tag, patterns in TAG_RULES.items()}


def tag_text(*chunks: str | None) -> list[str]:
    blob = " ".join(c for c in chunks if c).lower()
    if not blob.strip():
        return []
    hits = []
    for tag, patterns in _COMPILED.items():
        if any(p.search(blob) for p in patterns):
            hits.append(tag)
    return sorted(hits)
