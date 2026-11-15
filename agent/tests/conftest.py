import pytest
from fastapi.testclient import TestClient

from agent import api, harness
from backend.main import app
from backend.seed import seed


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    """Retry a failed model call at once, so the tests don't wait."""
    monkeypatch.setattr(harness, "RETRY_DELAY_SECONDS", 0)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client for the API on a freshly seeded database, which the agent uses too."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("UNDERCOVER_DB", str(path))
    seed(path)
    monkeypatch.setattr(api, "backend", lambda: TestClient(app))
    return TestClient(app)
