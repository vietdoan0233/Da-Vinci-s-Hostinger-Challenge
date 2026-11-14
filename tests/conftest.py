import pytest


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """No test reaches the real LLM or Bluesky; each gets a fresh cache and rate limit.
    Tests that need answers patch these again with their own stubs."""
    from app import main

    monkeypatch.delenv("OXYLABS_WEB_API_KEY", raising=False)
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache.db"))
    monkeypatch.setattr("app.llm.ask_json", lambda system, user: {"techniques": []})
    monkeypatch.setattr("app.bluesky.search", lambda q, around_ts=None: [])
    main._hits.clear()
