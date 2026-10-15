import json
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from firstlook.api import app
from firstlook.demo import populate
from firstlook.embed import clusters, index
from firstlook.match import rank
from firstlook.paths import ROOT


def test_tests_have_no_live_network_and_fixture_transports_are_required():
    with pytest.raises(AssertionError, match="fixture HTTP"):
        httpx.get("https://example.test")
    sock = socket.socket()
    with pytest.raises(AssertionError, match="external network"):
        sock.connect(("192.0.2.1", 443))
    sock.close()


def test_model_vectors_cached_once_and_local_clusters_work(db):
    populate(db, 8)
    calls = []

    class LocalEncoder:
        model = "fixture-encoder"
        note = "Local embeddings active"

        def encode(self, text):
            calls.append(text)
            return [1.0] + [0.0] * 383

    encoder = LocalEncoder()
    index(db, encoder)
    count = len(calls)
    assert count == db.execute("SELECT count(*) FROM job").fetchone()[0]
    index(db, encoder)
    assert len(calls) == count
    assert rank(db, encoder=encoder, include_filtered=True)
    assert clusters(db)
    db.execute("DELETE FROM job_embedding")
    db.commit()
    assert clusters(db)


def test_registry_review_lists_every_unverified_seed():
    rows = [
        json.loads(line) for line in (ROOT / "data/registry.seed.jsonl").read_text().splitlines()
    ]
    review = (ROOT / "REVIEW_REGISTRY.md").read_text()
    assert all(not row["verified"] and "| " + row["name"] + " |" in review for row in rows)
    assert "firstlook registry verify --all" in review


def test_complete_ui_api_workflow_without_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRSTLOOK_DB", str(tmp_path / "workflow.db"))
    client = TestClient(app)
    client.post("/api/demo")
    assert (
        client.post(
            "/api/chat", json={"message": "show strongest matches", "context": {"view": "Jobs"}}
        ).json()["mode"]
        == "local"
    )
    for entry in [
        dict(
            id="identity",
            kind="identity",
            title="Alex Example",
            organisation="alex@example.test",
            bullets=["San Francisco"],
        ),
        dict(
            id="role",
            title="Engineer",
            organisation="Example",
            dates="2023 - 2025",
            bullets=["Built Python services with SQL and AWS."],
        ),
    ]:
        assert client.put("/api/bank", json=entry).status_code == 200
    variant = client.post("/api/tailor/1", json={"template": "compact"}).json()
    assert variant["lines"] and variant["template"] == "compact"
    assert client.get("/api/jobs/1/gap").status_code == 200
    assert (
        client.post("/api/lines/" + str(variant["lines"][0]["id"]) + "/ai-suggest").status_code
        == 200
    )
    rendered = client.post("/api/variants/" + str(variant["id"]) + "/render").json()
    assert rendered["ready"]
    application = client.post(
        "/api/applications", json={"job_id": 1, "variant_id": variant["id"]}
    ).json()
    assert (
        client.put(
            "/api/applications/" + str(application["id"]) + "/metadata",
            json={"minutes": 15, "referral": True},
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/applications/" + str(application["id"]),
            json={"state": "screen", "notes": "manual outcome"},
        ).status_code
        == 200
    )
    assert client.get("/api/analytics").json()["overall"]["applications"] == 1
    assert client.get("/api/budget").json() == []
    assert client.post("/api/applications/confirm", json={"confirmed": False}).status_code == 400
