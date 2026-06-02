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


# Interchangeable role nouns (and language aliases) collapsed to one canonical token, so a
# keyword matches the variants job boards use freely ("Developer" ≈ "Engineer", "Golang" = "Go").
_KEYWORD_SYNONYMS = {
    "developer": "engineer",
    "dev": "engineer",
    "programmer": "engineer",
    "golang": "go",
}

# Split/hyphenated compounds collapsed to a single token so "Back End", "Back-end", and
# "Backend" all converge before matching.
_KEYWORD_COMPOUNDS = {
    "back end": "backend",
    "front end": "frontend",
    "full stack": "fullstack",
}


def _canonicalize(text: str) -> str:
    """Lowercase, neutralize hyphens, collapse known compounds, and map synonym tokens to a
    canonical form — so keyword matching is insensitive to word order, casing, and variants."""
    text = " ".join(text.lower().replace("-", " ").split())
    for split, joined in _KEYWORD_COMPOUNDS.items():
        text = text.replace(split, joined)
    for term, canon in _KEYWORD_SYNONYMS.items():
        text = re.sub(rf"(?<![a-z]){re.escape(term)}(?![a-z])", canon, text)
    return text


def _word_present(token: str, haystack: str) -> bool:
    """True if token appears in haystack on word edges (no adjacent letter), so "java" does
    not match "javascript" and "go" does not match "google"."""
    return re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", haystack) is not None


def keyword_matches(text: str, keywords: list[str]) -> bool:
    """True if ANY keyword matches text by token-set: every token of the keyword must appear
    as a whole word in text, in any order (titles reorder and interleave freely —
    "Backend Data Engineer" should match "Backend Engineer"). Centralizes adapter filtering."""
    haystack = _canonicalize(text)
    for keyword in keywords:
        tokens = _canonicalize(keyword).split()
        if tokens and all(_word_present(token, haystack) for token in tokens):
            return True
    return False


class JobSource(Protocol):
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]: ...

    def source_name(self) -> str: ...
