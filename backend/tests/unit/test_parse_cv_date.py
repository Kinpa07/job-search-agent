from datetime import date

import pytest

from app.services.profile import parse_cv_date, split_end_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Mar 2021", date(2021, 3, 1)),       # month + year → day anchored to 1
        ("January 2018", date(2018, 1, 1)),
        ("2019", date(2019, 1, 1)),           # bare year → month/day anchored
        ("03/2020", date(2020, 3, 1)),
    ],
)
def test_parses_free_text_cv_dates(raw: str, expected: date) -> None:
    assert parse_cv_date(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "Present", "ongoing", "n/a", "to be decided"])
def test_unparseable_or_empty_returns_none(raw: str | None) -> None:
    # "Present"/empty/garbage must degrade to None rather than raising, so a single bad
    # date on a CV never breaks the whole parse.
    assert parse_cv_date(raw) is None


@pytest.mark.parametrize("raw", ["Present", "present", " Current ", "ongoing"])
def test_split_end_date_marks_ongoing(raw: str) -> None:
    # An ongoing marker → no date + is_current=True (case/whitespace insensitive).
    assert split_end_date(raw) == (None, True)


def test_split_end_date_parses_finished_role() -> None:
    # A real end date → parsed date + is_current=False.
    assert split_end_date("05/2026") == (date(2026, 5, 1), False)


@pytest.mark.parametrize("raw", [None, "", "to be decided"])
def test_split_end_date_missing_or_unparseable_is_not_current(raw: str | None) -> None:
    # Missing/unparseable end date → (None, False): "finished but undated", NOT "ongoing".
    # This is the guard against re-rendering a past role as current.
    assert split_end_date(raw) == (None, False)
