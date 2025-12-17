from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    professors: Mapped[List["Professor"]] = relationship(back_populates="institution")


class Professor(Base):
    __tablename__ = "professors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    h_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_lab: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    institution: Mapped[Institution] = relationship(back_populates="professors")
    tags: Mapped[List["ResearchTag"]] = relationship(
        secondary="professor_tags", back_populates="professors"
    )
    publications: Mapped[List["Publication"]] = relationship(back_populates="professor")
    collaborators: Mapped[List["Collaborator"]] = relationship(back_populates="professor")


class ResearchTag(Base):
    __tablename__ = "research_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    professors: Mapped[List[Professor]] = relationship(
        secondary="professor_tags", back_populates="tags"
    )


class ProfessorTag(Base):
    __tablename__ = "professor_tags"
    __table_args__ = (UniqueConstraint("professor_id", "tag_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("professors.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("research_tags.id"), nullable=False)


class Publication(Base):
    __tablename__ = "publications"
    __table_args__ = (UniqueConstraint("professor_id", "title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("professors.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    published_on: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    co_authors: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    professor: Mapped[Professor] = relationship(back_populates="publications")


class Collaborator(Base):
    __tablename__ = "collaborators"
    __table_args__ = (UniqueConstraint("professor_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("professors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    affiliation: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    professor: Mapped[Professor] = relationship(back_populates="collaborators")
