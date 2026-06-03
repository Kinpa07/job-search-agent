from dataclasses import dataclass, field
from typing import Any


@dataclass
class CVParserState:
    pdf_bytes: bytes = field(default_factory=bytes)
    raw_text: str = ""
    # Deterministically captured from PDF link annotations in extract_text, then merged
    # into extracted_profile (the LLM never transcribes URLs).
    github_url: str | None = None
    linkedin_url: str | None = None
    extracted_profile: dict[str, Any] = field(default_factory=dict)
