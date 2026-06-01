from dataclasses import dataclass, field
from typing import Any


@dataclass
class CVParserState:
    pdf_bytes: bytes = field(default_factory=bytes)
    raw_text: str = ""
    extracted_profile: dict[str, Any] = field(default_factory=dict)
