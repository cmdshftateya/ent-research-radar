"""
Lightweight ingestion orchestrator.

Scraping/parsing is implemented in a conservative/offline-friendly way. If
ENT_OFFLINE=true, no network calls are made and only sample data is inserted.
When ready to scrape live, unset ENT_OFFLINE and set SEMANTIC_SCHOLAR_API_KEY
for publication enrichment.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable, List, Optional

from . import crud
from .config import OFFLINE
from .db import Base, engine, get_session
from .models import Institution, Professor
from .scrapers import fetch_institution_roster
from .bio import fetch_professor_bio
from .publications import fetch_publications, derive_tags

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


def refresh_all() -> None:
    Base.metadata.create_all(bind=engine)
    with get_session() as session:
        if OFFLINE:
            seed_sample_data(session)
            return
        for inst_info in INSTITUTIONS:
            inst = crud.upsert_institution(session, inst_info["name"], inst_info["website"])
            roster = fetch_institution_roster(inst)
            for entry in roster:
                prof = crud.upsert_professor(
                    session,
                    name=entry.get("name", "").strip(),
                    email=entry.get("email"),
                    institution=inst,
                    profile_url=entry.get("profile_url"),
                )
                if entry.get("profile_url") and not prof.biography:
                    prof.biography = fetch_professor_bio(entry.get("profile_url"))

                pubs = fetch_publications(prof, limit=20)
                crud.upsert_publications(session, prof, pubs[:20])
                tags = derive_tags(pubs, biography=prof.biography)
                crud.set_professor_tags(session, prof, tags[:10])
                prof.last_refreshed_at = dt.datetime.utcnow()


def seed_sample_data(session=None) -> None:
    """
    Insert a small sample payload to exercise the UI/API without scraping.
    """
    if session is None:
        with get_session() as session:
            _seed(session)
    else:
        _seed(session)


def _seed(session):
    inst = crud.upsert_institution(session, "Sample University", "https://example.edu")
    prof = crud.upsert_professor(
        session,
        name="Dr. Jane Doe",
        email="jane.doe@example.edu",
        institution=inst,
        profile_url="https://example.edu/jane-doe",
        h_index=42,
        has_lab=True,
        biography="Dr. Jane Doe leads translational research on hearing loss and cochlear implant outcomes, mentoring residents and collaborating across neurology and speech pathology.",
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
