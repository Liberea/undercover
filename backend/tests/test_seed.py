from fastapi.testclient import TestClient

from backend import seed
from backend.main import app


def test_seed_counts(tmp_path):
    assert seed.seed(tmp_path / "test.db") == {
        "claims": 25,
        "policies": 50,
        "customers": 49,
        "handlers": 3,
    }


def test_main_rebuilds_database(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    seed.main()
    assert capsys.readouterr().out == (
        "Seeded 25 claims, 50 policies, 49 customers, 3 handlers\n"
    )


def test_startup_seeds_missing_database(tmp_path, monkeypatch):
    path = tmp_path / "missing.db"
    monkeypatch.setenv("UNDERCOVER_DB", str(path))
    with TestClient(app) as client:
        assert len(client.get("/api/claims").json()) == 25
    assert path.exists()
