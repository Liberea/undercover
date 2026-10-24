import pytest
from fastapi.testclient import TestClient

from agent import api
from backend.main import app
from backend.seed import seed


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client for the API on a freshly seeded database, which the agent uses too."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("UNDERCOVER_DB", str(path))
    seed(path)
    monkeypatch.setattr(api, "backend", lambda: TestClient(app))
    return TestClient(app)
