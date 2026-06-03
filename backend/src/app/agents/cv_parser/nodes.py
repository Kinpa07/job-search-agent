from typing import Any, cast
from urllib.parse import urlparse

import fitz  # pymupdf
import ftfy
import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.cv_parser.prompts import PROMPT
from app.agents.cv_parser.schemas import UserProfileData
from app.agents.cv_parser.state import CVParserState
from app.llm_cache import invoke_tool

logger = structlog.get_logger()

MIN_TEXT_LENGTH = 100


def _shortest_path(urls: list[str]) -> str | None:
    """Pick the profile link from same-domain candidates: the profile URL has the shortest
    path (github.com/user), so it sorts below project repo links (github.com/user/repo)."""
    if not urls:
        return None
    return min(urls, key=lambda u: len([seg for seg in urlparse(u).path.split("/") if seg]))


def _profile_links(doc: Any) -> tuple[str | None, str | None]:
    """Collect GitHub/LinkedIn URLs from the PDF's link annotations (not the text layer),
    classified by domain. These are the only links we capture automatically — portfolio and
    project URLs can't be told apart from a flat list, so the human adds those in review."""
    github: list[str] = []
    linkedin: list[str] = []
    for page in doc:
        for link in page.get_links():
            uri = link.get("uri")
            if not uri:
                continue
            host = uri.lower()
            if "github.com" in host:
                github.append(uri)
            elif "linkedin.com" in host:
                linkedin.append(uri)
    return _shortest_path(github), _shortest_path(linkedin)


def extract_text(state: CVParserState) -> CVParserState:
    with fitz.open(stream=state.pdf_bytes, filetype="pdf") as doc:
        pages = [cast(str, page.get_text("text")) for page in doc]
        # Repair mojibake from PDF glyph mis-decoding (â€" → —, DALLÂ·E → DALL·E) before the
        # LLM sees the text, so "copy verbatim" stays honest and every field comes out clean.
        text = ftfy.fix_text("\n".join(pages)).strip()

        if len(text) < MIN_TEXT_LENGTH:
            raise ValueError(
                f"Extracted text too short ({len(text)} chars) — "
                "PDF may be scanned or image-based. "
                "Export your CV from a word processor that embeds a text layer."
            )

        state.github_url, state.linkedin_url = _profile_links(doc)
    logger.info(
        "cv.extract_text.done",
        char_count=len(text),
        github_url=state.github_url,
        linkedin_url=state.linkedin_url,
    )
    state.raw_text = text
    return state


def extract_structured(state: CVParserState, llm: BaseChatModel) -> CVParserState:
    result = invoke_tool(
        llm, UserProfileData, [SystemMessage(content=PROMPT), HumanMessage(content=state.raw_text)]
    )
    if not result.tool_calls:
        raise ValueError("LLM did not return any tool calls. Unable to extract profile data.")
    profile = UserProfileData.model_validate(result.tool_calls[0]["args"]).model_dump()
    # Merge in the deterministically captured links — the LLM schema has no URL fields.
    profile["github_url"] = state.github_url
    profile["linkedin_url"] = state.linkedin_url
    state.extracted_profile = profile
    logger.info("cv.extract_structured.done", extracted_profile=state.extracted_profile)
    return state
