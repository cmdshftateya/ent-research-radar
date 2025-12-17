"""
Lightweight ingestion orchestrator.

The scraping/parsing pieces are stubbed so we can wire the pipeline end-to-end
without hitting the network (per PRD note to ask before expensive work).
Fill in the `fetch_*` functions with real scraping/parsing when ready.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable, List

from . import crud
from .db import get_session
from .models import Professor

INSTITUTIONS = [
    {
        "name": "Northwestern University",
        "website": "https://www.oto-hns.northwestern.edu/faculty/a-z.html",
    },
    {
        "name": "University of Chicago",
        "website": "https://www.uchicagomedicine.org/conditions-services/ear-nose-throat/physicians",
    },
    {
        "name": "University of Illinois Chicago",
        "website": "https://chicago.medicine.uic.edu/otolaryngology/people/faculty/",
    },
    {
        "name": "Rush Medical School",
        "website": "https://www.rush.edu/locations/rush-otolaryngology-head-and-neck-surgery-chicago",
    },
]


def fetch_institution_roster(institution_name: str) -> List[dict]:
    """
    TODO: implement scraping/parsing for each institution page.
    Returns list of dicts: {"name": str, "email": str|None, "profile_url": str|None}.
    """
    # Placeholder: return empty list so pipeline runs without network.
    return []


def fetch_publications(professor: Professor) -> List[dict]:
    """
    TODO: call scholarly API (Semantic Scholar/Crossref/Google Scholar proxy) to populate.
    Each item: {"title": str, "published_on": str|None, "link": str|None, "co_authors": list[str]}.
    """
    return []


def derive_tags(publications: Iterable[dict]) -> List[str]:
    """
    TODO: NLP/keyword extraction to produce top 10 ENT research tags from publications.
    Placeholder returns empty list.
    """
    return []


def refresh_all() -> None:
    with get_session() as session:
        for inst_info in INSTITUTIONS:
            inst = crud.upsert_institution(session, inst_info["name"], inst_info["website"])
            roster = fetch_institution_roster(inst.name)
            for entry in roster:
                prof = crud.upsert_professor(
                    session,
                    name=entry.get("name", "").strip(),
                    email=entry.get("email"),
                    institution=inst,
                    profile_url=entry.get("profile_url"),
                )
                pubs = fetch_publications(prof)
                crud.upsert_publications(session, prof, pubs[:20])
                tags = derive_tags(pubs)
                crud.set_professor_tags(session, prof, tags[:10])
                prof.last_refreshed_at = dt.datetime.utcnow()


def seed_sample_data() -> None:
    """
    Insert a small sample payload to exercise the UI/API without scraping.
    """
    with get_session() as session:
        inst = crud.upsert_institution(session, "Sample University", "https://example.edu")
        prof = crud.upsert_professor(
            session,
            name="Dr. Jane Doe",
            email="jane.doe@example.edu",
            institution=inst,
            profile_url="https://example.edu/jane-doe",
            h_index=42,
            has_lab=True,
        )
        pubs = [
            {
                "title": "Advances in Otolaryngology",
                "published_on": "2023-11-01",
                "link": "https://doi.org/example1",
                "co_authors": ["A. Smith", "B. Chen"],
            },
            {
                "title": "Hearing Loss Interventions",
                "published_on": "2022-06-15",
                "link": "https://doi.org/example2",
                "co_authors": ["C. Patel"],
            },
        ]
        crud.upsert_publications(session, prof, pubs)
        crud.upsert_collaborators(
            session,
            prof,
            [{"name": "A. Smith", "affiliation": "Sample Lab"}, {"name": "B. Chen"}],
        )
        crud.set_professor_tags(session, prof, ["otology", "hearing loss", "cochlear implants"])
        prof.last_refreshed_at = dt.datetime.utcnow()
