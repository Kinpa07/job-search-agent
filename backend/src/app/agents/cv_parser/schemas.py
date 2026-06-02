from pydantic import BaseModel, Field

from app.enums import ProficiencyLevel

PROFICIENCY_RUBRIC = """
familiar: Listed as a skill or mentioned incidentally, with limited evidence of hands-on use.

proficient: Demonstrated hands-on use in professional work or projects; appears in role 
responsibilities, accomplishments, or project descriptions.

expert: Strong evidence of deep expertise, such as technical ownership, leadership, 
architecture/design responsibility, mentoring, many years of experience, 
or explicit expert-level claims.
""".strip()


class Skill(BaseModel):
    name: str
    proficiency_level: ProficiencyLevel | None = Field(default=None, description=PROFICIENCY_RUBRIC)
    years: float | None = None
    confidence: float = 1.0
    category: str | None = Field(
        default=None,
        description="The section header this skill was listed under on the CV, verbatim "
        "(e.g. 'Cloud & Infrastructure'). Null if the CV lists skills without grouping.",
    )


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
    level: str | None = Field(
        default=None,
        description="Proficiency as written on the CV, verbatim (e.g. 'Native', 'Fluent (C1)').",
    )


class UserProfileData(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[Skill] = []
    experiences: list[Experience] = []
    educations: list[Education] = []
    projects: list[Project] = []
    certifications: list[Certification] = []
    languages: list[Language] = []
