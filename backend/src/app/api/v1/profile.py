from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cv_parser.graph import build_graph
from app.agents.cv_parser.state import CVParserState
from app.database import get_session
from app.dependencies import get_llm
from app.models.profile import UserProfile
from app.repositories.profile import UserProfileRepository
from app.schemas.profile import ProfileConfirmRequest, ProfilePatchRequest, ProfileResponse
from app.services.profile import persist_confirmed, update_profile

logger = structlog.get_logger()

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/upload-cv")
async def upload_cv(
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
    llm: BaseChatModel = Depends(get_llm),
) -> dict[str, Any]:
    """Parse an uploaded CV PDF into a draft profile and return it for review."""
    pdf_bytes = await file.read()
    # Content sniffing: a real PDF starts with the "%PDF-" signature. This beats
    # trusting the (spoofable) content-type or filename extension.
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=415,
            detail="File is not a valid PDF. Export your CV as a PDF and try again.",
        )

    graph = build_graph(llm)
    try:
        result = graph.invoke(CVParserState(pdf_bytes=pdf_bytes))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    extracted: dict[str, Any] = result["extracted_profile"]
    repo = UserProfileRepository(session)
    profile = await repo.create_draft(UserProfile(draft_data=extracted))
    logger.info("profile.draft_created", profile_id=profile.id)
    return extracted


@router.get("/draft")
async def get_draft(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Return the current paused-state draft profile for review."""
    repo = UserProfileRepository(session)
    profile = await repo.get_draft()
    if profile is None or profile.draft_data is None:
        raise HTTPException(status_code=404, detail="No draft profile awaiting review.")
    return profile.draft_data


@router.get("")
async def get_profile(session: AsyncSession = Depends(get_session)) -> ProfileResponse:
    """Return the confirmed profile; 404 if none has been confirmed yet."""
    repo = UserProfileRepository(session)
    profile = await repo.get_confirmed()
    if profile is None:
        raise HTTPException(status_code=404, detail="No confirmed profile yet.")
    return ProfileResponse.model_validate(profile)


@router.post("/draft/confirm")
async def confirm_draft(
    data: ProfileConfirmRequest,
    session: AsyncSession = Depends(get_session),
    llm: BaseChatModel = Depends(get_llm),
) -> ProfileResponse:
    """Persist the user-corrected draft as a confirmed profile and extract keywords."""
    repo = UserProfileRepository(session)
    draft = await repo.get_draft()
    if draft is None:
        raise HTTPException(status_code=404, detail="No draft profile awaiting review.")

    profile = await persist_confirmed(repo, llm, draft, data)
    logger.info("profile.confirmed", profile_id=profile.id)
    return ProfileResponse.model_validate(profile)


@router.patch("")
async def patch_profile(
    data: ProfilePatchRequest,
    session: AsyncSession = Depends(get_session),
    llm: BaseChatModel = Depends(get_llm),
) -> ProfileResponse:
    """Update the confirmed profile with new data from the user and re-extract keywords."""
    repo = UserProfileRepository(session)
    confirmed = await repo.get_confirmed()
    if confirmed is None:
        raise HTTPException(status_code=404, detail="No confirmed profile to update.")

    updated = await update_profile(repo, llm, data, confirmed)
    logger.info("profile.updated", profile_id=updated.id)
    return ProfileResponse.model_validate(updated)
