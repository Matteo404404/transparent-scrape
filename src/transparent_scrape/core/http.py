from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from transparent_scrape.core.rate_limit import ep_limiter, web_limiter

DEFAULT_TIMEOUT = 120.0
USER_AGENT = "transparent-scrape/0.1 (EU transparency research)"


def download(url: str, dest: Path, retries: int = 3, *, user_agent: str = USER_AGENT) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    headers = {"User-Agent": user_agent}
    for attempt in range(retries):
        try:
            web_limiter.wait()
            with httpx.Client(follow_redirects=True, timeout=DEFAULT_TIMEOUT) as client:
                with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    with dest.open("wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                            f.write(chunk)
            return dest
        except Exception as exc:
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"download failed: {url}") from last_err


def get_text(url: str, retries: int = 3, *, user_agent: str = USER_AGENT) -> str:
    last_err: Exception | None = None
    headers = {"User-Agent": user_agent}
    for attempt in range(retries):
        try:
            web_limiter.wait()
            with httpx.Client(follow_redirects=True, timeout=DEFAULT_TIMEOUT) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"GET failed: {url}") from last_err


def get_json(
    url: str,
    headers: dict | None = None,
    retries: int = 3,
    *,
    rate_limit: bool = True,
) -> dict[str, Any]:
    h = {"Accept": "application/ld+json", "User-Agent": USER_AGENT, **(headers or {})}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            if rate_limit:
                ep_limiter.wait()
            with httpx.Client(follow_redirects=True, timeout=DEFAULT_TIMEOUT) as client:
                resp = client.get(url, headers=h)
                if resp.status_code == 204 or not resp.content.strip():
                    return {"data": []}
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            # no declarations for this MEP
            if exc.response.status_code in (404, 204):
                return {"data": []}
            last_err = exc
            time.sleep(2**attempt)
        except Exception as exc:
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"JSON GET failed: {url}") from last_err
