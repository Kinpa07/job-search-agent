from datetime import date

import pytest

from app.services.profile import parse_cv_date


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
