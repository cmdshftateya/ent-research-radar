"""
Publication enrichment helpers using Semantic Scholar.

If ENT_OFFLINE=true, returns an empty list to avoid network calls.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List

import httpx

from .config import HTTP_TIMEOUT, OFFLINE, USER_AGENT
from .models import Professor


BASE_URL = "https://api.semanticscholar.org/graph/v1"
HEADERS = {"User-Agent": USER_AGENT}


def fetch_publications(professor: Professor, limit: int = 20) -> List[dict]:
    if OFFLINE:
        return []
    author_id = lookup_author_id(professor)
    if not author_id:
        return []
    params = {
        "limit": limit,
        "fields": "title,abstract,year,publicationDate,url,authors,externalIds",
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
                "published_on": _published_on(item),
                "link": item.get("url") or _first_doi(item),
                "co_authors": _co_authors(item, professor.name),
                "abstract": item.get("abstract"),
            }
        )
    results.sort(key=lambda p: p.get("published_on") or "", reverse=True)
    return results[:limit]


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


ENT_KEYWORDS = {
    "otology": "otology",
    "neurotology": "neurotology",
    "hearing loss": "hearing loss",
    "hearing": "hearing",
    "cochlear implant": "cochlear implants",
    "cochlear implants": "cochlear implants",
    "tinnitus": "tinnitus",
    "vertigo": "vertigo",
    "balance": "balance",
    "audiology": "audiology",
    "pediatric": "pediatric otolaryngology",
    "otolaryngology": "otolaryngology",
    "sinus": "sinusitis",
    "rhinology": "rhinology",
    "nasal": "nasal disorders",
    "sleep apnea": "sleep apnea",
    "sleep": "sleep medicine",
    "laryngology": "laryngology",
    "voice": "voice",
    "airway": "airway",
    "head and neck": "head and neck",
    "oncology": "oncology",
    "thyroid": "thyroid",
    "parathyroid": "parathyroid",
    "skull base": "skull base",
    "facial plastic": "facial plastics",
    "reconstructive": "reconstructive surgery",
    "allergy": "allergy",
}


def derive_tags(publications: Iterable[dict], biography: str | None = None) -> List[str]:
    """
    Derive ENT-focused tags from biography text only.
    Publication titles often produce noisy tags, so they are ignored by design.
    """
    if not biography:
        return []

    combined = biography.lower()
    counts = Counter()
    for phrase, canonical in ENT_KEYWORDS.items():
        hits = re.findall(rf"\b{re.escape(phrase)}\b", combined)
        if hits:
            counts[canonical] += len(hits)

    if counts:
        return [t for t, _ in counts.most_common(10)]

    tokens = normalize_terms(biography)
    counts = Counter(tokens)
    return [t for t, _ in counts.most_common(10)]


def normalize_terms(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", text).lower()
    words = [w for w in cleaned.split() if len(w) > 3]
    stop = {
        "with",
        "from",
        "this",
        "that",
        "into",
        "using",
        "study",
        "case",
        "role",
        "professor",
        "assistant",
        "associate",
        "doctor",
        "clinical",
        "medicine",
        "department",
    }
    return [w for w in words if w not in stop]


def _first_doi(item: dict) -> str | None:
    ids = item.get("externalIds") or {}
    doi = ids.get("DOI")
    if doi:
        return f"https://doi.org/{doi}"
    return None


def _published_on(item: dict) -> str | None:
    if item.get("year"):
        return str(item["year"])
    for key in ("publicationDate", "date"):
        if item.get(key):
            return str(item[key])
    return None


def _co_authors(item: dict, professor_name: str | None) -> list[str]:
    names = [a.get("name") for a in item.get("authors", []) if a.get("name")]
    if professor_name and not any(_names_match(n, professor_name) for n in names):
        names.insert(0, professor_name)
    return names


def _names_match(a: str, b: str) -> bool:
    return _clean_name(a) == _clean_name(b)


def _clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).replace(".", "").strip().lower()
