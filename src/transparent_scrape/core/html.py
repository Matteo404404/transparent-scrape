"""HTML parse helpers (lxml, no browser)."""

from __future__ import annotations

from lxml import html as lxml_html


def parse_html(text: str):
    return lxml_html.fromstring(text)


def xpath_all(doc, expr: str) -> list:
    return doc.xpath(expr)


def text_of(el) -> str:
    return " ".join((el.text_content() or "").split())
