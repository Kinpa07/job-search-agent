import pytest

from app.adapters.base import keyword_matches


# --- Token-set: real LinkedIn titles that the old contiguous-substring match missed ---
# Every one of these is a genuine "Backend Engineer" role written with the words reordered,
# interleaved, hyphenated, or qualified in parentheses.
@pytest.mark.parametrize(
    "title",
    [
        "Backend Engineer",
        "Backend Data Engineer",  # word inserted between
        "Backend Software Engineer",
        "Software Engineer Backend",  # reordered
        "Python Backend Developer",  # developer→engineer + interleaved
        "Back End Developer",  # split compound + synonym
        "Back-end Developer I AI-Driven Workflows",  # hyphen + trailing noise
        "Associate Developer (Java-Backend)",  # qualifier in parens
        "Backend engineer (Go) - Payments Experience",
    ],
)
def test_backend_engineer_matches_real_title_variants(title: str) -> None:
    assert keyword_matches(title, ["Backend Engineer"]) is True


@pytest.mark.parametrize(
    "title",
    [
        "Frontend Engineer",
        "Golang Developer",  # no 'backend' token present
        "Data Scientist",
        "Product Manager",
    ],
)
def test_backend_engineer_rejects_unrelated_titles(title: str) -> None:
    assert keyword_matches(title, ["Backend Engineer"]) is False


def test_token_set_is_order_independent() -> None:
    assert keyword_matches("Software Engineer Backend", ["Backend Engineer"]) is True


# --- Letter-boundary: kills the substring false positives ---
def test_java_does_not_match_javascript() -> None:
    assert keyword_matches("Senior JavaScript Developer", ["Java"]) is False


def test_go_does_not_match_google() -> None:
    assert keyword_matches("Google Cloud Engineer", ["Go"]) is False


def test_go_matches_standalone_go_token() -> None:
    assert keyword_matches("Backend Engineer (Go)", ["Go"]) is True


def test_react_still_matches_space_separated_compound() -> None:
    # Space/paren boundaries are fine — only *letter* adjacency is blocked.
    assert keyword_matches("React Native Developer", ["React"]) is True


# --- Synonyms: developer ≈ engineer, golang = go ---
def test_developer_matches_engineer_keyword() -> None:
    assert keyword_matches("Backend Developer", ["Backend Engineer"]) is True


def test_golang_and_go_are_interchangeable() -> None:
    assert keyword_matches("Golang Developer", ["Go"]) is True
    assert keyword_matches("Backend Engineer (Go)", ["Golang"]) is True


# --- Compounds: back end / back-end / backend converge ---
@pytest.mark.parametrize("title", ["Backend Developer", "Back End Developer", "Back-end Developer"])
def test_backend_compound_variants_all_match(title: str) -> None:
    assert keyword_matches(title, ["Backend Engineer"]) is True


# --- Distinct tech matches against tags (single-token keywords) ---
def test_distinct_tech_matches_tag() -> None:
    assert keyword_matches("fastapi", ["FastAPI"]) is True


# --- Documented strictness: letter-fused tech compounds do NOT match (intentional tradeoff) ---
def test_dotnet_does_not_match_aspdotnet() -> None:
    # ".NET" ↛ "ASP.NET" and "SQL" ↛ "PostgreSQL" are accepted recall losses; the candidate
    # carries the specific term as its own keyword, and false positives hurt more on titles.
    assert keyword_matches("ASP.NET Developer", [".NET"]) is False
    assert keyword_matches("PostgreSQL Engineer", ["SQL"]) is False


# --- Guards ---
def test_empty_keywords_never_match() -> None:
    assert keyword_matches("Backend Engineer", []) is False


def test_any_keyword_in_the_set_can_match() -> None:
    assert keyword_matches("Data Scientist", ["Backend Engineer", "Data Scientist"]) is True
