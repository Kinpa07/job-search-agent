from datetime import datetime

from pydantic import BaseModel, Field


class SourceCount(BaseModel):
    job_count: int
    new_count: int


class PollStatusResponse(BaseModel):
    completed_at: datetime | None
    counts: dict[str, SourceCount]
    errors: dict[str, str] = Field(default_factory=dict)
