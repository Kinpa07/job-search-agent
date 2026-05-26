from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RawJob:
    title: str
    company: str
    location: str | None
    url: str
    source: str
    description: str | None
    raw_html: str | None


@dataclass
class JobFilters:
    keywords: list[str] = field(default_factory=list)
    location: str | None = None
    remote_ok: bool = False
    entry_level_only: bool = True
    posted_within_days: int = 1


class JobSource(Protocol):
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]: ...

    def source_name(self) -> str: ...
