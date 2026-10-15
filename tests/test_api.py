from fastapi.testclient import TestClient
from firstlook.api import app


def test_every_shell_panel_renders_from_fixture_corpus_and_profile_is_persisted(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("FIRSTLOOK_DB", str(tmp_path / "api.db"))
    client = TestClient(app)
    assert client.get("/api/jobs").json() == []
    assert client.post("/api/demo").status_code == 200
    jobs = client.get("/api/jobs").json()
    assert len(jobs) > 10
    assert client.post(f"/api/jobs/{jobs[0]['id']}/star").json()["starred"]
    assert client.get("/api/registry").json()
    profile = client.get("/api/profile").json()
    profile["titles"] = ["Platform Engineer"]
    assert client.put("/api/profile", json=profile).status_code == 200
    assert client.get("/api/profile").json()["titles"] == ["Platform Engineer"]
    assert client.put("/api/settings", json={"saved_searches": ["Python"]}).status_code == 200
    assert client.get("/api/settings").json()["saved_searches"] == ["Python"]
    assert client.put("/api/settings", json={"api_key": "not-a-real-key"}).status_code == 400
    assert client.post("/api/demo", headers={"Origin": "https://evil.example"}).status_code == 403
