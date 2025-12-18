"""
Utilities to fetch a short biography/intro paragraph for a professor.

Respects ENT_OFFLINE flag to avoid network calls when scraping is disabled.
"""

from __future__ import annotations

from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .config import HTTP_TIMEOUT, OFFLINE, USER_AGENT

HEADERS = {"User-Agent": USER_AGENT}


def fetch_professor_bio(profile_url: str | None) -> Optional[str]:
    if OFFLINE or not profile_url:
        return None
    try:
        with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(profile_url)
            resp.raise_for_status()
    except Exception:
        return None

    return extract_bio(resp.text)


def extract_bio(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")

    content_paras = soup.select(
        "main p, article p, .field-name-body p, .provider-bio p, .bio p, .pane-node-body p"
    )
    for p in content_paras:
        text = p.get_text(" ", strip=True)
        if len(text.split()) >= 12:
            return text

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip() or None

    return None
