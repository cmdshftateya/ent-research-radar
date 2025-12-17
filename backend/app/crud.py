from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Collaborator, Institution, Professor, Publication, ResearchTag


def upsert_institution(session: Session, name: str, website: Optional[str]) -> Institution:
    existing = session.scalar(select(Institution).where(Institution.name == name))
    if existing:
        if website and existing.website != website:
            existing.website = website
        return existing

    inst = Institution(name=name, website=website)
    session.add(inst)
    session.flush()
    return inst


def upsert_professor(
    session: Session,
    name: str,
    email: Optional[str],
    institution: Institution,
    profile_url: Optional[str] = None,
    h_index: Optional[int] = None,
    has_lab: bool = False,
) -> Professor:
    existing = session.scalar(
        select(Professor).where(
            Professor.name == name, Professor.institution_id == institution.id
        )
    )
    if existing:
        existing.email = email or existing.email
        existing.profile_url = profile_url or existing.profile_url
        if h_index is not None:
            existing.h_index = h_index
        existing.has_lab = existing.has_lab or has_lab
        return existing

    prof = Professor(
        name=name,
        email=email,
        institution=institution,
        profile_url=profile_url,
        h_index=h_index,
        has_lab=has_lab,
    )
    session.add(prof)
    session.flush()
    return prof


def set_professor_tags(session: Session, professor: Professor, tags: Iterable[str]) -> None:
    normalized = {tag.strip().lower() for tag in tags if tag.strip()}
    if not normalized:
        return

    tag_objects: List[ResearchTag] = []
    for tag_name in normalized:
        tag = session.scalar(select(ResearchTag).where(ResearchTag.name == tag_name))
        if not tag:
            tag = ResearchTag(name=tag_name)
            session.add(tag)
            session.flush()
        tag_objects.append(tag)

    professor.tags = tag_objects


def upsert_publications(
    session: Session, professor: Professor, publications: Iterable[dict]
) -> List[Publication]:
    saved = []
    for pub in publications:
        title = pub.get("title")
        if not title:
            continue
        existing = session.scalar(
            select(Publication).where(
                Publication.professor_id == professor.id, Publication.title == title
            )
        )
        co_authors = ", ".join(pub.get("co_authors", []))
        if existing:
            existing.published_on = pub.get("published_on", existing.published_on)
            existing.link = pub.get("link", existing.link)
            existing.co_authors = co_authors or existing.co_authors
            saved.append(existing)
            continue
        new_pub = Publication(
            professor=professor,
            title=title,
            published_on=pub.get("published_on"),
            link=pub.get("link"),
            co_authors=co_authors,
        )
        session.add(new_pub)
        saved.append(new_pub)
    return saved


def upsert_collaborators(
    session: Session, professor: Professor, collaborators: Iterable[dict]
) -> List[Collaborator]:
    saved = []
    for collaborator in collaborators:
        name = collaborator.get("name")
        if not name:
            continue
        existing = session.scalar(
            select(Collaborator).where(
                Collaborator.professor_id == professor.id, Collaborator.name == name
            )
        )
        if existing:
            existing.affiliation = collaborator.get("affiliation", existing.affiliation)
            saved.append(existing)
            continue
        new_c = Collaborator(
            professor=professor,
            name=name,
            affiliation=collaborator.get("affiliation"),
        )
        session.add(new_c)
        saved.append(new_c)
    return saved
