from datetime import date

from pydantic import BaseModel, ConfigDict

from app.enums import ProficiencyLevel

# --- Request side (user-submitted corrections) ---
# Dates arrive as free-text strings ("Mar 2021", "Present") — persist_confirmed parses
# them to real dates. extra="ignore" lets the draft's confidence field pass through
# harmlessly when the frontend submits the edited draft back.


class SkillIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    proficiency_level: ProficiencyLevel | None = None
    years: float | None = None
    category: str | None = None


class ExperienceIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str
    title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = []
    tech_stack: list[str] = []


class EducationIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    institution: str
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ProjectIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    bullets: list[str] = []
    tech_stack: list[str] = []
    url: str | None = None  # human-entered in review; the parser never emits it
    year: int | None = None


class CertificationIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    issuer: str | None = None
    year: int | None = None


class LanguageIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    level: str | None = None


class ProfileConfirmRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    # github/linkedin arrive pre-filled from deterministic link capture; portfolio is user-added.
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    summary: str | None = None
    skills: list[SkillIn] = []
    experiences: list[ExperienceIn] = []
    educations: list[EducationIn] = []
    projects: list[ProjectIn] = []
    certifications: list[CertificationIn] = []
    languages: list[LanguageIn] = []


class ProfilePatchRequest(BaseModel):
    # None means "field omitted — leave unchanged". A provided list replaces the
    # existing children wholesale (re-extraction of keywords is triggered server-side).
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    summary: str | None = None
    skills: list[SkillIn] | None = None
    experiences: list[ExperienceIn] | None = None
    educations: list[EducationIn] | None = None
    projects: list[ProjectIn] | None = None
    certifications: list[CertificationIn] | None = None
    languages: list[LanguageIn] | None = None


# --- Response side (serialized from confirmed ORM rows; no confidence) ---


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    proficiency_level: ProficiencyLevel | None = None
    years: float | None = None
    category: str | None = None


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company: str
    title: str
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    bullets: list[str] = []
    tech_stack: list[str] = []


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution: str
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    bullets: list[str] = []
    tech_stack: list[str] = []
    url: str | None = None
    year: int | None = None


class CertificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    issuer: str | None = None
    year: int | None = None


class LanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    level: str | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    summary: str | None = None
    status: str
    search_keywords: list[str] = []
    skills: list[SkillOut] = []
    experiences: list[ExperienceOut] = []
    educations: list[EducationOut] = []
    projects: list[ProjectOut] = []
    certifications: list[CertificationOut] = []
    languages: list[LanguageOut] = []
