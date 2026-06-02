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


class Experience(BaseModel):
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    year: int | None = None


class UserProfileData(BaseModel):
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[Skill] = []
    experiences: list[Experience] = []
    educations: list[Education] = []
