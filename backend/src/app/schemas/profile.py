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


class ExperienceIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = []
    tech_stack: list[str] = []


class EducationIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    institution: str
    degree: str | None = None
    field: str | None = None
    year: int | None = None


class ProfileConfirmRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[SkillIn] = []
    experiences: list[ExperienceIn] = []
    educations: list[EducationIn] = []


class ProfilePatchRequest(BaseModel):
    # None means "field omitted — leave unchanged". A provided list replaces the
    # existing children wholesale (re-extraction of keywords is triggered server-side).
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[SkillIn] | None = None
    experiences: list[ExperienceIn] | None = None
    educations: list[EducationIn] | None = None


# --- Response side (serialized from confirmed ORM rows; no confidence) ---


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    proficiency_level: ProficiencyLevel | None = None
    years: float | None = None


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company: str
    title: str
    start_date: date | None = None
    end_date: date | None = None
    bullets: list[str] = []
    tech_stack: list[str] = []


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution: str
    degree: str | None = None
    field: str | None = None
    year: int | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    status: str
    search_keywords: list[str] = []
    skills: list[SkillOut] = []
    experiences: list[ExperienceOut] = []
    educations: list[EducationOut] = []
