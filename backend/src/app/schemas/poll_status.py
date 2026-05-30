from datetime import datetime

from pydantic import BaseModel


class SourceCount(BaseModel):
    job_count: int
    new_count: int


class PollStatusResponse(BaseModel):
    completed_at: datetime | None
    counts: dict[str, SourceCount]
