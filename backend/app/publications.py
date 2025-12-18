"""
Publication enrichment helpers using OpenAlex (primary) with Semantic Scholar fallback.

If ENT_OFFLINE=true, returns an empty list to avoid network calls.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Iterable, List, Sequence

import httpx

from .config import HTTP_TIMEOUT, OFFLINE, USER_AGENT
from .models import Professor


SEMANTIC_BASE_URL = "https://api.semanticscholar.org/graph/v1"
OPENALEX_BASE_URL = "https://api.openalex.org"
HEADERS = {"User-Agent": USER_AGENT}
OPENALEX_MAILTO = os.getenv("ENT_OPENALEX_MAILTO", "bodaateya@gmail.com")

INSTITUTION_ALIASES = {
    "northwestern university": [
        "northwestern",
        "northwestern university",
        "northwestern medicine",
        "feinberg",
    ],
    "university of chicago": [
        "university of chicago",
        "uchicago",
        "u chicago",
        "uchicago medicine",
    ],
    "university of illinois chicago": [
        "university of illinois chicago",
        "uic",
        "illinois at chicago",
        "illinois chicago",
    ],
    "rush medical school": [
        "rush medical school",
        "rush university",
        "rush university medical center",
        "rush medical college",
    ],
}

INSTITUTION_OPENALEX_IDS = {
    "northwestern university": "https://openalex.org/I111979921",
    "university of chicago": "https://openalex.org/I40347166",
    "university of illinois chicago": "https://openalex.org/I39422238",
    "rush medical school": "https://openalex.org/I1285301757",  # Rush University Medical Center
}

def fetch_publications(professor: Professor, limit: int = 20) -> List[dict]:
    """
    Try OpenAlex first (name + institution disambiguation). Fall back to Semantic Scholar if
    OpenAlex fails to return any results.
    """
    if OFFLINE:
        return []

    cleaned_name = normalize_professor_name(professor.name)
    name_options = name_variants(cleaned_name)
    if not name_options:
        return []

    pubs = _fetch_from_openalex(professor, name_options, limit)
    if pubs:
        return pubs[:limit]

    pubs = _fetch_from_semantic_scholar(professor, name_options[0], limit)
    return pubs[:limit]


def _fetch_from_openalex(professor: Professor, name_options: Sequence[str], limit: int) -> List[dict]:
    institution = professor.institution.name if professor.institution else None
    try:
        with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT) as client:
            author_id = _resolve_openalex_author(client, name_options, institution)
            if author_id:
                pubs = _fetch_openalex_works(client, author_id, institution, professor.name, limit)
                if pubs:
                    return pubs
            # Fallback: text search by name + institution without an author id.
            return _search_openalex_works(client, name_options, institution, professor.name, limit)
    except Exception:
        return []


def _resolve_openalex_author(
    client: httpx.Client, name_options: Sequence[str], institution: str | None
) -> str | None:
    best: dict | None = None
    best_score = 0.0
    inst_filter = _institution_filter(institution, for_authors=True)

    for name in name_options:
        params = {
            "search": name,
            "per-page": 5,
            "select": "id,display_name,works_count,cited_by_count,last_known_institutions,affiliations,x_concepts",
            "mailto": OPENALEX_MAILTO,
        }
        if inst_filter:
            params["filter"] = inst_filter
        resp = client.get(f"{OPENALEX_BASE_URL}/authors", params=params)
        resp.raise_for_status()
        data = resp.json()
        for candidate in data.get("results", []):
            score = _score_author_candidate(candidate, name, institution)
            if score > best_score:
                best_score = score
                best = candidate
        if best_score >= 5:
            break  # confident enough
    return best.get("id") if best else None


def _score_author_candidate(candidate: dict, target_name: str, institution: str | None) -> float:
    score = 0.0
    candidate_name = normalize_professor_name(candidate.get("display_name") or "")
    score += _name_similarity_score(candidate_name, target_name)

    if institution:
        aliases = _institution_aliases(institution)
        inst_hits = 0
        last_known = (candidate.get("last_known_institution") or {}).get("display_name", "")
        if _institution_matches(last_known, aliases):
            inst_hits += 1
        for aff in candidate.get("affiliations") or []:
            inst = (aff.get("institution") or {}).get("display_name", "")
            if _institution_matches(inst, aliases):
                inst_hits += 1
                break
        score += 2 * min(inst_hits, 1)

    score += _concept_score(candidate.get("x_concepts") or [])

    works_count = candidate.get("works_count") or 0
    cited_by = candidate.get("cited_by_count") or 0
    if works_count > 10:
        score += 0.5
    if cited_by > 200:
        score += 0.5
    return score


def _fetch_openalex_works(
    client: httpx.Client,
    author_id: str,
    institution: str | None,
    professor_name: str,
    limit: int,
) -> List[dict]:
    filters = [f"authorships.author.id:{author_id}"]
    inst_filter = _institution_filter(institution, for_authors=False)
    if inst_filter:
        filters.append(inst_filter)

    params = {
        "filter": ",".join(filters),
        "sort": "publication_year:desc",
        "per-page": min(limit, 25),
        "select": "id,doi,display_name,authorships,publication_year,primary_location,publication_date,abstract_inverted_index",
        "mailto": OPENALEX_MAILTO,
    }
    resp = client.get(f"{OPENALEX_BASE_URL}/works", params=params)
    resp.raise_for_status()
    data = resp.json()
    pubs = [_map_openalex_work(item, professor_name) for item in data.get("results", [])]
    pubs = _filter_ent_publications(pubs)
    return _dedupe_publications(pubs)


def _search_openalex_works(
    client: httpx.Client,
    name_options: Sequence[str],
    institution: str | None,
    professor_name: str,
    limit: int,
) -> List[dict]:
    inst_filter = _institution_filter(institution, for_authors=False)
    for name in name_options:
        params = {
            "search": name,
            "sort": "publication_year:desc",
            "per-page": min(limit, 25),
            "select": "id,doi,display_name,authorships,publication_year,primary_location,publication_date,abstract_inverted_index",
            "mailto": OPENALEX_MAILTO,
        }
        if inst_filter:
            params["filter"] = inst_filter
        resp = client.get(f"{OPENALEX_BASE_URL}/works", params=params)
        resp.raise_for_status()
        data = resp.json()
        pubs = [_map_openalex_work(item, professor_name) for item in data.get("results", [])]
        pubs = _filter_ent_publications(pubs)
        if pubs:
            return _dedupe_publications(pubs)
    return []


def _map_openalex_work(item: dict, professor_name: str) -> dict:
    return {
        "title": item.get("display_name"),
        "published_on": _openalex_published_on(item),
        "link": _openalex_link(item),
        "co_authors": _openalex_coauthors(item, professor_name),
        "abstract": _openalex_abstract(item),
    }


def _openalex_published_on(item: dict) -> str | None:
    if item.get("publication_date"):
        return item["publication_date"]
    if item.get("publication_year"):
        return str(item["publication_year"])
    return None


def _openalex_link(item: dict) -> str | None:
    doi = item.get("doi")
    if doi:
        return f"https://doi.org/{doi.split('doi.org/')[-1]}"
    primary = item.get("primary_location") or {}
    if primary.get("landing_page_url"):
        return primary["landing_page_url"]
    if item.get("id"):
        return f"https://openalex.org/{item['id'].split('/')[-1]}"
    return None


def _openalex_coauthors(item: dict, professor_name: str) -> list[str]:
    names = []
    for auth in item.get("authorships") or []:
        author = auth.get("author") or {}
        name = author.get("display_name")
        if name:
            names.append(name)
    if professor_name and not any(_names_match(n, professor_name) for n in names):
        names.insert(0, professor_name)
    return names


def _openalex_abstract(item: dict) -> str | None:
    inverted = item.get("abstract_inverted_index") or {}
    if not inverted:
        return None
    # Convert inverted index to readable abstract.
    tokens = []
    for word, positions in inverted.items():
        for pos in positions:
            tokens.append((pos, word))
    tokens.sort(key=lambda t: t[0])
    return " ".join(word for _, word in tokens)


def _dedupe_publications(pubs: Iterable[dict]) -> List[dict]:
    seen = set()
    unique: List[dict] = []
    for pub in pubs:
        title = (pub.get("title") or "").strip().lower()
        if not title or title in seen:
            continue
        seen.add(title)
        unique.append(pub)
    unique.sort(key=lambda p: p.get("published_on") or "", reverse=True)
    return unique


def _fetch_from_semantic_scholar(professor: Professor, cleaned_name: str, limit: int) -> List[dict]:
    author_id = _lookup_semantic_author_id(professor, cleaned_name)
    if not author_id:
        return []
    params = {
        "limit": limit,
        "fields": "title,abstract,year,publicationDate,url,authors,externalIds",
    }
    try:
        with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT) as client:
            resp = client.get(f"{SEMANTIC_BASE_URL}/author/{author_id}/papers", params=params)
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
    return results


def _lookup_semantic_author_id(professor: Professor, cleaned_name: str) -> str | None:
    query = f"{cleaned_name} {professor.institution.name}"
    params = {
        "query": query,
        "limit": 1,
        "fields": "authorId,name,affiliations",
    }
    try:
        with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT) as client:
            resp = client.get(f"{SEMANTIC_BASE_URL}/author/search", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None
    if not data.get("data"):
        return None
    return data["data"][0].get("authorId")


def normalize_professor_name(name: str) -> str:
    """
    Remove credentials, specialties, and extra whitespace to improve matching.
    """
    cleaned = re.sub(r"\s+", " ", name.replace("\n", " ")).strip()
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)  # drop parentheses like (ENT)
    cleaned = re.split(r"\b(otolaryngology|ent|pediatric|pediatrics)\b", cleaned, flags=re.I)[0]
    credential_tokens = (
        "md",
        "do",
        "phd",
        "mph",
        "ms",
        "msn",
        "mscr",
        "mspa",
        "msp",
        "aud",
        "np",
        "aprn",
        "pa",
        "pa-c",
        "rn",
        "bsn",
        "fnp",
        "anp",
        "cnp",
        "acnp",
        "agnp",
        "facs",
        "ccc-slp",
        "faap",
        "cnm",
        "dnp",
        "mba",
    )
    cleaned = re.sub(
        r",?\s*\b(" + "|".join(credential_tokens) + r")\b\.?", "",
        cleaned,
        flags=re.I,
    )
    cleaned = cleaned.replace(",", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def name_variants(cleaned_name: str) -> List[str]:
    parts = cleaned_name.split()
    variants = {cleaned_name}
    if len(parts) >= 2:
        variants.add(f"{parts[0]} {parts[-1]}")
        variants.add(f"{parts[-1]}, {parts[0]}")
    return [v for v in variants if v]


def _institution_filter(institution: str | None, *, for_authors: bool) -> str | None:
    if not institution:
        return None
    inst_id = _institution_id(institution)
    if not inst_id:
        return None
    field = "last_known_institutions.id" if for_authors else "institutions.id"
    return f"{field}:{inst_id}"


def _institution_aliases(institution: str) -> List[str]:
    key = _institution_key(institution)
    return INSTITUTION_ALIASES.get(key, [key])


def _institution_id(institution: str) -> str | None:
    key = _institution_key(institution)
    if key in INSTITUTION_OPENALEX_IDS:
        return INSTITUTION_OPENALEX_IDS[key]
    return None


def _institution_key(name: str) -> str:
    normalized = name.lower().strip()
    for key, aliases in INSTITUTION_ALIASES.items():
        if normalized == key or normalized in aliases:
            return key
    return normalized


def _institution_matches(candidate: str, aliases: Sequence[str]) -> bool:
    candidate_norm = candidate.lower()
    return any(alias in candidate_norm for alias in aliases)


def _name_similarity_score(candidate: str, target: str) -> float:
    cand_parts = candidate.split()
    target_parts = target.split()
    if not cand_parts or not target_parts:
        return 0.0
    if _names_match(candidate, target):
        return 4.0
    if cand_parts[-1] == target_parts[-1]:
        if cand_parts[0][0:1] == target_parts[0][0:1]:
            return 3.0
        return 2.0
    return 0.5 if cand_parts[0] == target_parts[0] else 0.0


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
ENT_KEYWORD_TERMS = {k.lower() for k in ENT_KEYWORDS.keys()}

# Concepts that should be present for ENT faculty; used to disambiguate OpenAlex authors.
ENT_CONCEPT_TERMS = {
    "otolaryngology",
    "otorhinolaryngology",
    "head and neck surgery",
    "audiology",
    "hearing",
    "neurosciences",
    "neurology",
    "oncology",
    "laryngology",
    "sinusitis",
    "sleep medicine",
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


def _concept_score(concepts: Sequence[dict]) -> float:
    """
    Favor authors whose OpenAlex primary concepts include ENT-adjacent areas.
    """
    if not concepts:
        return 0.0
    names = {c.get("display_name", "").lower() for c in concepts if c.get("display_name")}
    hits = sum(1 for name in names if any(term in name for term in ENT_CONCEPT_TERMS))
    if hits >= 2:
        return 2.5
    if hits == 1:
        return 1.5
    return -1.0  # penalize clearly non-ENT concept clusters


def _filter_ent_publications(pubs: Iterable[dict]) -> List[dict]:
    """
    Prefer publications that appear ENT-related; fall back to the full list if none match.
    """
    pubs = list(pubs)
    filtered = []
    for pub in pubs:
        text = " ".join(
            [
                (pub.get("title") or "").lower(),
                (pub.get("abstract") or "").lower(),
            ]
        )
        if any(term in text for term in ENT_KEYWORD_TERMS):
            filtered.append(pub)
    return filtered or pubs


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
    return normalize_professor_name(a).lower() == normalize_professor_name(b).lower()
