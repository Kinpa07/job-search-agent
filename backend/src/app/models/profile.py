from datetime import date
from typing import Any, Literal

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import ProficiencyLevel


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    # name/email are nullable while status="draft" — the draft lives in draft_data
    # and these columns are only populated when the profile is confirmed.
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))
    # github_url/linkedin_url are auto-captured by domain from PDF link annotations;
    # portfolio_url is human-entered in review (project links can't be told apart).
    github_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[Literal["draft", "confirmed"]] = mapped_column(String(20), default="draft")
    # Raw extracted profile (incl. per-skill confidence) while status="draft"; NULL once confirmed.
    # none_as_null=True so `draft_data = None` writes SQL NULL, not the JSON `null` literal.
    draft_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    search_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[date] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[date] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    skills: Mapped[list["Skill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    educations: Mapped[list["Education"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    languages: Mapped[list["Language"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    name: Mapped[str] = mapped_column(String(255))
    proficiency_level: Mapped[ProficiencyLevel | None] = mapped_column(String(50))
    years: Mapped[float | None]
    # Free-form section label from the CV ("Cloud & Infrastructure"); presentational only,
    # used to regroup skills when re-rendering the CV. Never feeds matching.
    category: Mapped[str | None] = mapped_column(String(255))

    profile: Mapped["UserProfile"] = relationship(back_populates="skills")


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    company: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    # True when the CV marks the role ongoing ("Present"). Distinguishes "still here"
    # (is_current=True, end_date NULL) from "finished but end date missing/unparseable"
    # (is_current=False, end_date NULL) — so re-rendering never shows a past job as current.
    is_current: Mapped[bool] = mapped_column(default=False)
    bullets: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    tech_stack: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    profile: Mapped["UserProfile"] = relationship(back_populates="experiences")


class Education(Base):
    __tablename__ = "educations"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    institution: Mapped[str] = mapped_column(String(255))
    degree: Mapped[str | None] = mapped_column(String(255))
    field: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    # Date range like Experience so the rendered CV can show "2021 - 2026" (or "- Present"
    # when ongoing); a bare graduation year couldn't reproduce that.
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    # In-progress degree marked "Present"; same semantics as Experience.is_current.
    is_current: Mapped[bool] = mapped_column(default=False)

    profile: Mapped["UserProfile"] = relationship(back_populates="educations")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    name: Mapped[str] = mapped_column(String(255))
    bullets: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    tech_stack: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    # url is human-entered in review, never LLM-transcribed.
    url: Mapped[str | None] = mapped_column(String(500))
    year: Mapped[int | None]

    profile: Mapped["UserProfile"] = relationship(back_populates="projects")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    name: Mapped[str] = mapped_column(String(255))
    issuer: Mapped[str | None] = mapped_column(String(255))
    year: Mapped[int | None]

    profile: Mapped["UserProfile"] = relationship(back_populates="certifications")


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    name: Mapped[str] = mapped_column(String(255))
    level: Mapped[str | None] = mapped_column(String(100))

    profile: Mapped["UserProfile"] = relationship(back_populates="languages")
