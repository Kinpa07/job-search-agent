# LLM Response Fixtures — "Record once, replay forever"

Cached real LLM API responses (JSON) used for **development iteration**, not unit tests.

- **Unit tests** never read these — they use `FakeMessagesListChatModel` with hardcoded
  responses (the `fake_llm` fixture in `tests/conftest.py`). Zero API cost, deterministic.
- **Dev iteration** uses `tests/helpers/llm_recorder.py::load_or_call()`. The first run makes
  one real API call and writes a `<fixture_name>.json` here; every later run replays from disk.

The rule (Standing Rule 6): if you are iterating on code *around* the LLM (response parsing,
persistence, endpoint wiring), replay a cached fixture. Only call the real API when you are
iterating on the *prompt itself* or verifying end-to-end.

Fixtures are committed so CI (Module 13+) can replay them without an API key.
Refresh a stale fixture by passing `force_refresh=True` to `load_or_call()`.
