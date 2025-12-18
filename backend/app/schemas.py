from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class PublicationOut(BaseModel):
    id: int
    title: str
    published_on: Optional[str] = None
    link: Optional[str] = None
    co_authors: List[str] = []
    abstract: Optional[str] = None

    class Config:
        from_attributes = True


class CollaboratorOut(BaseModel):
    id: int
    name: str
    affiliation: Optional[str] = None

    class Config:
        from_attributes = True


class ProfessorSummary(BaseModel):
    id: int
    name: str
    email: Optional[str]
    institution: str
    tags: List[str]
    has_recent_publication: bool = False

    class Config:
        from_attributes = True


class ProfessorDetail(BaseModel):
    id: int
    name: str
    email: Optional[str]
    institution: str
    profile_url: Optional[str]
    h_index: Optional[int]
    has_lab: bool
    biography: Optional[str]
    top_tags: List[str]
    has_recent_publication: bool = False
    publications: List[PublicationOut]
    collaborators: List[CollaboratorOut]
    last_refreshed_at: Optional[datetime]

    class Config:
        from_attributes = True


class UpdateEmailRequest(BaseModel):
    email: EmailStr
