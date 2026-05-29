import re
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


SENIORITY_TERMS = (
    "senior",
    "sr",
    "lead",
    "principal",
    "staff",
    "head of",
    "director",
    "vp",
    "vice president",
)

EXCLUDE_TITLE_TERMS = (
    "manager",
    "designer",
    "recruiter",
    "sales",
    "account executive",
    "marketing",
    "human resources",
    "accountant",
    "customer success",
    "scrum master",
)

_SENIORITY_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in SENIORITY_TERMS) + r")\b",
    re.IGNORECASE,
)
_EXCLUDE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in EXCLUDE_TITLE_TERMS) + r")\b",
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
