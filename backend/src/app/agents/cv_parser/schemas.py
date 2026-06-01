from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    proficiency_level: str | None = None
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
