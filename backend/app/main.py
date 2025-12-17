from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import crud
from .config import OFFLINE
from .db import Base, engine, get_session
from .models import Institution, Professor
from .schemas import ProfessorDetail, ProfessorSummary

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ENT Research Tool", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    with get_session() as session:
        yield session


@app.get("/health")
def health() -> dict:
    return {"ok": True, "offline": OFFLINE}


@app.get("/professors", response_model=list[ProfessorSummary])
def list_professors(db: Session = Depends(get_db)) -> list[ProfessorSummary]:
    professors = db.scalars(
        select(Professor).join(Institution).order_by(Institution.name, Professor.name)
    ).all()
    results: list[ProfessorSummary] = []
    for prof in professors:
        results.append(
            ProfessorSummary(
                id=prof.id,
                name=prof.name,
                email=prof.email,
                institution=prof.institution.name,
                tags=[t.name for t in prof.tags][:10],
            )
        )
    return results


@app.get("/professors/{professor_id}", response_model=ProfessorDetail)
def professor_detail(professor_id: int, db: Session = Depends(get_db)) -> ProfessorDetail:
    prof = db.get(Professor, professor_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Professor not found")
    return ProfessorDetail(
        id=prof.id,
        name=prof.name,
        email=prof.email,
        institution=prof.institution.name,
        profile_url=prof.profile_url,
        h_index=prof.h_index,
        has_lab=prof.has_lab,
        top_tags=[t.name for t in prof.tags][:10],
        publications=[
            {
                "id": pub.id,
                "title": pub.title,
                "published_on": pub.published_on,
                "link": pub.link,
                "co_authors": [c.strip() for c in pub.co_authors.split(",") if c.strip()],
            }
            for pub in sorted(prof.publications, key=lambda p: p.published_on or "", reverse=True)[:20]
        ],
        collaborators=[
            {"id": c.id, "name": c.name, "affiliation": c.affiliation}
            for c in prof.collaborators
        ],
        last_refreshed_at=prof.last_refreshed_at,
    )
