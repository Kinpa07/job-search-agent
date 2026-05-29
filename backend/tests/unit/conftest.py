from collections.abc import Callable
from typing import Any

import httpx
import pytest

ResponseHandler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def patch_httpx(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[str, ResponseHandler], None]:
    """Route an adapter module's ``httpx.AsyncClient`` through a MockTransport
    so its HTTP calls hit ``handler`` instead of the network."""
    real_client = httpx.AsyncClient

    def install(module_path: str, handler: ResponseHandler) -> None:
        def fake_client(**kwargs: Any) -> httpx.AsyncClient:
            return real_client(transport=httpx.MockTransport(handler), **kwargs)

        monkeypatch.setattr(f"{module_path}.httpx.AsyncClient", fake_client)

    return install


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Replace an adapter module's ``sleep`` with a no-op so politeness delays
    don't slow the tests."""

    async def _instant(*args: Any, **kwargs: Any) -> None:
        return None

    def install(module_path: str) -> None:
        monkeypatch.setattr(f"{module_path}.sleep", _instant)

    return install
