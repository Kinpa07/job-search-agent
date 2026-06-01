from typing import cast

import fitz  # pymupdf
import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.cv_parser.prompts import PROMPT
from app.agents.cv_parser.schemas import UserProfileData
from app.agents.cv_parser.state import CVParserState

logger = structlog.get_logger()

MIN_TEXT_LENGTH = 100


def extract_text(state: CVParserState) -> CVParserState:
    doc = fitz.open(stream=state.pdf_bytes, filetype="pdf")
    pages = [cast(str, page.get_text("text")) for page in doc]
    text = "\n".join(pages).strip()

    if len(text) < MIN_TEXT_LENGTH:
        raise ValueError(
            f"Extracted text too short ({len(text)} chars) — "
            "PDF may be scanned or image-based. "
            "Export your CV from a word processor that embeds a text layer."
        )

    logger.info("cv.extract_text.done", char_count=len(text))
    state.raw_text = text
    return state


def extract_structured(state: CVParserState, llm: BaseChatModel) -> CVParserState:
    result = llm.bind_tools([UserProfileData], tool_choice="UserProfileData").invoke(
        [SystemMessage(content=PROMPT), HumanMessage(content=state.raw_text)],
    )
    if not result.tool_calls:
        raise ValueError("LLM did not return any tool calls. Unable to extract profile data.")
    state.extracted_profile = result.tool_calls[0]["args"]
    logger.info("cv.extract_structured.done", extracted_profile=state.extracted_profile)
    return state
