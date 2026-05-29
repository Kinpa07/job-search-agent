from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str | None
    url: str
    source: str
    description: str | None
    discovered_at: datetime

    model_config = {"from_attributes": True}
