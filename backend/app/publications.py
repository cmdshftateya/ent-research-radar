"""
Publication enrichment helpers using Semantic Scholar.

If ENT_OFFLINE=true, returns an empty list to avoid network calls.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List

import httpx

from .config import HTTP_TIMEOUT, OFFLINE, SEMANTIC_SCHOLAR_API_KEY, USER_AGENT
from .models import Professor


BASE_URL = "https://api.semanticscholar.org/graph/v1"
HEADERS = {"User-Agent": USER_AGENT}
if SEMANTIC_SCHOLAR_API_KEY:
    HEADERS["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY


def fetch_publications(professor: Professor) -> List[dict]:
    if OFFLINE:
        return []
    author_id = lookup_author_id(professor)
    if not author_id:
        return []
    params = {
        "limit": 20,
        "fields": "title,year,url,authors,journal,publicationTypes,externalIds",
    }
    try:
        with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT) as client:
            resp = client.get(f"{BASE_URL}/author/{author_id}/papers", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    results = []
    for item in data.get("data", []):
        results.append(
            {
                "title": item.get("title"),
                "published_on": str(item.get("year")) if item.get("year") else None,
                "link": item.get("url") or _first_doi(item),
                "co_authors": [a.get("name") for a in item.get("authors", []) if a.get("name")],
            }
        )
    return results


def lookup_author_id(professor: Professor) -> str | None:
    params = {
        "query": f"{professor.name} {professor.institution.name}",
        "limit": 1,
        "fields": "authorId,name,affiliations",
    }
    try:
        with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT) as client:
            resp = client.get(f"{BASE_URL}/author/search", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None
    if not data.get("data"):
        return None
    return data["data"][0].get("authorId")


def derive_tags(publications: Iterable[dict]) -> List[str]:
    tokens = []
    for pub in publications:
        title = pub.get("title") or ""
        tokens.extend(normalize_terms(title))
    counts = Counter(tokens)
    return [t for t, _ in counts.most_common(10)]


def normalize_terms(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", text).lower()
    words = [w for w in cleaned.split() if len(w) > 3]
    stop = {"with", "from", "this", "that", "into", "using", "study", "case", "role"}
    return [w for w in words if w not in stop]


def _first_doi(item: dict) -> str | None:
    ids = item.get("externalIds") or {}
    doi = ids.get("DOI")
    if doi:
        return f"https://doi.org/{doi}"
    return None
