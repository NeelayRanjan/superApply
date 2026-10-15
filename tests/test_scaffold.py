from fastapi.testclient import TestClient
from firstlook.api import app


def test_health_and_idempotent_migration(db):
    assert TestClient(app).get("/api/health").json()["status"] == "ok"
    assert db.execute("PRAGMA user_version").fetchone()[0] >= 1
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
