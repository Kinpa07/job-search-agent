import re
from dataclasses import dataclass, field
from typing import Protocol

from app.config import settings


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
    location: str | None = field(default_factory=lambda: settings.default_location)
    remote_ok: bool = field(default_factory=lambda: settings.default_remote_ok)
    entry_level_only: bool = field(default_factory=lambda: settings.default_entry_level_only)
    posted_within_days: int = field(default_factory=lambda: settings.default_posted_within_days)


_SENIORITY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in settings.seniority_terms) + r")\b",
    re.IGNORECASE,
)
_EXCLUDE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in settings.exclude_title_terms) + r")\b",
    re.IGNORECASE,
)


def title_allowed(title: str, filters: JobFilters) -> bool:
    """Best-effort title filter: drop non-technical roles always, and
    senior-level roles when ``entry_level_only`` is set. No seniority signal
    means the job passes."""
    if _EXCLUDE_RE.search(title):
        return False
    return not (filters.entry_level_only and _SENIORITY_RE.search(title))


class JobSource(Protocol):
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]: ...

    def source_name(self) -> str: ...
