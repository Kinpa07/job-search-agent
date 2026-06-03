from typing import Any

from app.agents.cv_parser.nodes import _profile_links, _shortest_path


class _FakePage:
    """Stands in for a PyMuPDF page — only ``get_links()`` is exercised."""

    def __init__(self, links: list[dict[str, Any]]):
        self._links = links

    def get_links(self) -> list[dict[str, Any]]:
        return self._links


def test_shortest_path_prefers_profile_over_repo() -> None:
    # Profile URL (one path segment) wins over a deeper repo URL sharing the domain.
    urls = ["https://github.com/kinpa07/orderflow", "https://github.com/kinpa07"]
    assert _shortest_path(urls) == "https://github.com/kinpa07"


def test_shortest_path_empty_is_none() -> None:
    assert _shortest_path([]) is None


def test_profile_links_classifies_by_domain() -> None:
    doc = [
        _FakePage(
            [
                {"uri": "https://github.com/kinpa07/orderflow"},  # project repo
                {"uri": "https://github.com/kinpa07"},            # profile (should win)
                {"kind": 1},                                       # non-URI link, ignored
            ]
        ),
        _FakePage([{"uri": "https://www.linkedin.com/in/veselin-iliev/"}]),
    ]
    github, linkedin = _profile_links(doc)
    assert github == "https://github.com/kinpa07"
    assert linkedin == "https://www.linkedin.com/in/veselin-iliev/"


def test_profile_links_ignores_unrelated_domains() -> None:
    # A portfolio / project demo link is NOT auto-captured (can't be told apart reliably).
    doc = [_FakePage([{"uri": "https://veselin.dev"}, {"uri": "https://orderflow.demo"}])]
    assert _profile_links(doc) == (None, None)
