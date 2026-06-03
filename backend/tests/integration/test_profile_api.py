"""HTTP-layer tests for the profile endpoints — the wiring the service tests skip:
%PDF- sniffing (415), the ValueError→400 mapping, the 404 branches, and the
upload→confirm→get happy path with the LLM stubbed via a dependency override."""

from collections.abc import Iterator
from contextlib import contextmanager

import fitz  # pymupdf
import pytest
from httpx import AsyncClient

from app.dependencies import get_llm
from app.main import app
from tests.helpers.fakes import ToolCallingFake, tool_message

pytestmark = pytest.mark.integration


def _pdf_with_lines(lines: list[str]) -> bytes:
    """A minimal real PDF carrying a text layer, built with PyMuPDF itself."""
    doc = fitz.open()
    page = doc.new_page()
    y = 72.0
    for line in lines:
        page.insert_text((72, y), line)
        y += 14
    data: bytes = doc.tobytes()
    doc.close()
    return data


@contextmanager
def _override_llm(fake: ToolCallingFake) -> Iterator[None]:
    app.dependency_overrides[get_llm] = lambda: fake
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_llm, None)


async def test_upload_cv_rejects_non_pdf(api_client: AsyncClient) -> None:
    with _override_llm(ToolCallingFake(responses=[])):
        response = await api_client.post(
            "/api/v1/profile/upload-cv",
            files={"file": ("cv.txt", b"just plain text, no PDF header", "text/plain")},
        )
    assert response.status_code == 415


async def test_upload_cv_rejects_short_text(api_client: AsyncClient) -> None:
    # Valid PDF, but the text layer is below MIN_TEXT_LENGTH → extract_text raises
    # ValueError, which the endpoint maps to 400 (not a 500).
    short_pdf = _pdf_with_lines(["hi"])
    with _override_llm(ToolCallingFake(responses=[])):
        response = await api_client.post(
            "/api/v1/profile/upload-cv",
            files={"file": ("cv.pdf", short_pdf, "application/pdf")},
        )
    assert response.status_code == 400


async def test_get_profile_404_when_none_confirmed(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/profile")
    assert response.status_code == 404


async def test_get_draft_404_when_none(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/profile/draft")
    assert response.status_code == 404


async def test_confirm_404_when_no_draft(api_client: AsyncClient) -> None:
    with _override_llm(ToolCallingFake(responses=[])):
        response = await api_client.post(
            "/api/v1/profile/draft/confirm",
            json={"name": "Vesko", "email": "v@example.com"},
        )
    assert response.status_code == 404


async def test_upload_cv_without_email_yields_draft(api_client: AsyncClient) -> None:
    # The extraction schema is nullable for name/email, so a CV the LLM can't pull an
    # email from still produces a fixable draft (200) rather than a 500.
    fake = ToolCallingFake(responses=[tool_message("UserProfileData", {"name": "Vesko"})])
    pdf = _pdf_with_lines([f"Backend engineer summary line {i}" for i in range(6)])
    with _override_llm(fake):
        response = await api_client.post(
            "/api/v1/profile/upload-cv",
            files={"file": ("cv.pdf", pdf, "application/pdf")},
        )
    assert response.status_code == 200
    assert response.json()["email"] is None


async def test_upload_confirm_get_happy_path(api_client: AsyncClient) -> None:
    # One fake serves both LLM calls in order: the parse (upload) consumes the first
    # response, keyword extraction (confirm) consumes the second.
    fake = ToolCallingFake(
        responses=[
            tool_message("UserProfileData", {"name": "Vesko", "email": "v@example.com"}),
            tool_message("KeywordExtractorResult", {"keywords": ["Backend Engineer"]}),
        ]
    )
    long_pdf = _pdf_with_lines([f"Experienced backend engineer line {i}" for i in range(6)])

    with _override_llm(fake):
        upload = await api_client.post(
            "/api/v1/profile/upload-cv",
            files={"file": ("cv.pdf", long_pdf, "application/pdf")},
        )
        assert upload.status_code == 200
        assert upload.json()["name"] == "Vesko"  # draft returned for review

        confirm = await api_client.post(
            "/api/v1/profile/draft/confirm",
            json={
                "name": "Vesko",
                "email": "v@example.com",
                "experiences": [
                    {
                        "company": "Acme",
                        "title": "Backend Engineer",
                        "end_date": "Present",
                        "bullets": ["built APIs"],
                    }
                ],
            },
        )
        assert confirm.status_code == 200

    body = (await api_client.get("/api/v1/profile")).json()
    assert body["status"] == "confirmed"
    assert body["name"] == "Vesko"
    assert body["search_keywords"] == ["Backend Engineer"]
    # is_current round-trips through the confirm → GET path.
    assert body["experiences"][0]["is_current"] is True
    assert body["experiences"][0]["end_date"] is None
