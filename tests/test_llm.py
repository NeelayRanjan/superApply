import json

import httpx
from firstlook.chat import chat
from firstlook.demo import populate
from firstlook.llm import Client, estimate


def provider(monkeypatch):
    monkeypatch.setenv("FIRSTLOOK_API_KEY", "test-key-not-a-secret")
    monkeypatch.setenv("FIRSTLOOK_PROVIDER_URL", "https://provider.example/v1")
    monkeypatch.setenv("FIRSTLOOK_MODEL", "fixture")
    monkeypatch.delenv("FIRSTLOOK_LOCAL_URL", raising=False)


def test_every_llm_path_writes_ledger_row_cache_hit_zero_tokens_and_ceiling_degrades(
    db, monkeypatch
):
    provider(monkeypatch)
    populate(db, 1)
    job = db.execute("SELECT id FROM job").fetchone()[0]
    calls = []

    def handle(request):
        calls.append(request)
        assert (
            db.execute("SELECT status FROM llm_call ORDER BY id DESC").fetchone()[0] == "reserved"
        )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "A sourced suggestion"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 12},
            },
        )

    client = Client(db, transport=httpx.MockTransport(handle))
    assert client.call("tailor", job, "hello")["tokens"] == 0
    db.execute("UPDATE job SET touched=1")
    db.commit()
    assert client.call("tailor", job, "hello")["tokens"] == 22
    assert client.call("tailor", job, "hello")["tokens"] == 0
    assert len(calls) == 1
    db.execute("INSERT INTO setting(key,value) VALUES('daily_tokens','0')")
    db.commit()
    result = client.call("chat", job, "different")
    assert result["tokens"] == 0 and "ceiling" in result["note"] and len(calls) == 1
    assert db.execute("SELECT status FROM llm_call").fetchone()[0] == "complete"


def test_no_provider_chat_and_tailor_degrade_with_visible_note(db, monkeypatch):
    for key in [
        "FIRSTLOOK_API_KEY",
        "FIRSTLOOK_LOCAL_URL",
        "FIRSTLOOK_PROVIDER_URL",
        "FIRSTLOOK_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)
    populate(db, 1)
    assert "Local tools" in chat(db, "help", {})["message"]
    result = chat(db, "ask what is this role?", {"job_id": 1, "view": "Jobs"})
    assert "No provider" in result["message"]
    assert db.execute("SELECT count(*) FROM llm_call").fetchone()[0] == 0
    assert estimate("crawl", 1000)["predicted_tokens"] == 0
    assert estimate("tailor", 26)["requires_yes"]


def test_local_provider_first_and_failed_requests_keep_reservations(db, monkeypatch):
    provider(monkeypatch)
    monkeypatch.setenv("FIRSTLOOK_LOCAL_URL", "http://127.0.0.1:11434/v1")
    populate(db, 1)
    db.execute("UPDATE job SET starred=1")
    db.commit()

    def handle(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "local-model"}]})
        assert "authorization" not in request.headers
        return httpx.Response(500)

    client = Client(db, transport=httpx.MockTransport(handle))
    assert client.resolve()[1] == "local-model"
    assert "reservation retained" in client.call("chat", 1, "test")["note"]
    assert db.execute("SELECT status FROM llm_call").fetchone()[0] == "failed_usage_unknown"
    assert "test-key" not in json.dumps([tuple(r) for r in db.execute("SELECT * FROM llm_call")])


def test_agent_loop_uses_same_budget_run_and_cannot_submit(db, monkeypatch):
    provider(monkeypatch)
    populate(db, 1)
    db.execute("INSERT INTO setting(key,value) VALUES('run_tokens','20000')")
    db.execute("INSERT INTO setting(key,value) VALUES('daily_tokens','40000')")
    db.commit()
    messages = [
        json.dumps({"tool": "explain_match", "arguments": {"id": 999}}),
        json.dumps({"answer": "Your Python experience fits this role."}),
    ]

    def handle(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": messages.pop(0)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    result = chat(
        db, "ask explain the role", {"view": "Jobs", "job_id": 1}, httpx.MockTransport(handle)
    )
    assert "Python" in result["message"]
    assert db.execute("SELECT count(DISTINCT run_id) FROM llm_call").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM llm_call").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM application").fetchone()[0] == 0
