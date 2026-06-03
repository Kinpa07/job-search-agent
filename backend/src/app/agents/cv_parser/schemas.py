from pydantic import BaseModel, Field

from app.enums import ProficiencyLevel


class Skill(BaseModel):
    name: str
    proficiency_level: ProficiencyLevel | None = None
    years: float | None = None
    confidence: float = 1.0
    category: str | None = None


class Experience(BaseModel):
    company: str
    title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class Project(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    year: int | None = None


class Certification(BaseModel):
    name: str
    issuer: str | None = None
    year: int | None = None


class Language(BaseModel):
    name: str
    level: str | None = None


class UserProfileData(BaseModel):
    # Nullable at extraction time: a CV with no parseable name/email should still produce a
    # draft the user can fix in review, not a 500. ProfileConfirmRequest keeps them required.
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[Skill] = []
    experiences: list[Experience] = []
    educations: list[Education] = []
    projects: list[Project] = []
    certifications: list[Certification] = []
    languages: list[Language] = []
