import pytest

from app.adapters.base import JobFilters, title_allowed


@pytest.mark.parametrize(
    "title",
    [
        "Junior Python Developer",
        "Software Engineer",
        "Backend Developer (Junior)",
        "Graduate Developer",
        "SRE",
        "Site Reliability Engineer",
        "Leadership Development Program",
    ],
)
def test_allows_entry_level_and_neutral_titles(title: str) -> None:
    assert title_allowed(title, JobFilters()) is True


@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer",
        "Sr. Backend Developer",
        "Lead Data Scientist",
        "Tech Lead",
        "Staff Engineer",
        "Principal Engineer",
        "VP of Engineering",
        "Engineering Director",
    ],
)
def test_drops_senior_titles_when_entry_only(title: str) -> None:
    assert title_allowed(title, JobFilters(entry_level_only=True)) is False


def test_seniority_passes_when_entry_only_disabled() -> None:
    assert title_allowed("Senior Software Engineer", JobFilters(entry_level_only=False)) is True


@pytest.mark.parametrize(
    "title",
    [
        "Project Manager",
        "Product Designer",
        "Technical Recruiter",
        "Sales Representative",
        "Account Executive",
        "Scrum Master",
    ],
)
def test_drops_non_technical_titles_regardless_of_seniority(title: str) -> None:
    # Position exclusions apply even when seniority filtering is off.
    assert title_allowed(title, JobFilters(entry_level_only=False)) is False
