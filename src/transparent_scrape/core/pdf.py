from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any

import pdfplumber

# EP declaration PDFs often have broken font metadata; text still extracts fine.
logging.getLogger("pdfminer").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*FontBBox.*")


def extract_pdf_text(path: Path) -> dict[str, Any]:
    """Extract text from a PDF file. Returns empty text on failure."""
    try:
        pages_text: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                pages_text.append(t)
        full = "\n\n".join(pages_text).strip()
        return {"pages": len(pages_text), "text": full, "error": None}
    except Exception as exc:
        return {"pages": 0, "text": "", "error": str(exc)}
