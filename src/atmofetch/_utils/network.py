from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0

_OGIMET_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:143.0) Gecko/20100101 Firefox/143.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl,en-US;q=0.7,en;q=0.3",
    "Referer": "https://ogimet.com/resynops.phtml.en",
    "Cookie": "cookieconsent_status=dismiss; ogimet_serverid=huracan|aNaPt|aNaPj",
}


def check_internet() -> bool:
    try:
        httpx.head("https://www.google.com", timeout=5)
        return True
    except httpx.HTTPError:
        return False


def download(url: str, dest: Path | str | None = None, *, timeout: float = _TIMEOUT) -> bytes:
    logger.info("Downloading %s", url)
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    if dest is not None:
        Path(dest).write_bytes(resp.content)
    return resp.content


def fetch_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = _TIMEOUT,
) -> str:
    logger.info("Fetching %s", url)
    resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def fetch_ogimet(url: str, *, timeout: float = _TIMEOUT) -> str:
    return fetch_text(url, headers=_OGIMET_HEADERS, timeout=timeout)
