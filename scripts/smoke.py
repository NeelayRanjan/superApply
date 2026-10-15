"""End-to-end offline smoke run in a disposable database, with actual PDF/browser checks."""

import json
import os
import socket
import tempfile
from pathlib import Path

import httpx
from firstlook.analytics import report
from firstlook.apply import Driver
from firstlook.bank import Entry, save
from firstlook.db import connect
from firstlook.embed import index
from firstlook.ingest import crawl
from firstlook.ingest.http import PoliteClient
from firstlook.match import Profile, rank, save_profile
from firstlook.models import Company
from firstlook.paths import FIXTURES
from firstlook.registry import upsert
from firstlook.tailor import create, render
from firstlook.track import queue


def blocked(*args, **kwargs):
    raise RuntimeError("Smoke test attempted a real network request")


socket.socket.connect = blocked
httpx.HTTPTransport.handle_request = blocked
for key in [
    "FIRSTLOOK_API_KEY",
    "FIRSTLOOK_LOCAL_URL",
    "FIRSTLOOK_PROVIDER_URL",
    "FIRSTLOOK_MODEL",
]:
    os.environ.pop(key, None)
with tempfile.TemporaryDirectory(prefix="firstlook-smoke-") as folder:
    root = Path(folder)
    db = connect(root / "smoke.db")
    save_profile(
        db,
        Profile(
            titles=["Software Engineer"],
            locations=["United States"],
            must_skills=["Python", "SQL", "AWS"],
            contact={"name": "Alex Example", "email": "alex@example.test"},
        ),
    )
    for i in range(1000):
        upsert(
            db,
            Company(
                id=f"fixture-{i}",
                name=f"Fixture Company {i}",
                domain="example.test",
                platform="greenhouse",
                token=f"fixture-{i}",
                tags=["SaaS"],
            ),
        )
    payload = json.loads((FIXTURES / "cassettes/greenhouse/board.json").read_text())["body"]
    client = PoliteClient(
        db,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        sleep=lambda _: None,
    )
    result = crawl(db, client)
    assert result["new"] == 1000
    print(f"Crawl: {result['new']} postings from 1,000 synthetic companies")
    print("Index:", index(db))
    matches = rank(db)
    assert matches
    print("Matching:", len(matches), "explained opportunities")
    save(
        db,
        Entry(
            id="identity",
            kind="identity",
            title="Alex Example",
            organisation="alex@example.test",
            bullets=["San Francisco, CA"],
        ),
    )
    save(
        db,
        Entry(
            id="role",
            title="Software Engineer",
            organisation="Example Company",
            dates="2022 - 2025",
            bullets=[
                "Built Python services and reduced latency by {latency}.",
                "Maintained SQL data pipelines.",
                "Deployed AWS infrastructure.",
            ],
            metrics={"latency": "35%"},
        ),
    )
    variant = create(db, matches[0]["id"])
    variant = render(db, variant["id"], root / "exports")
    assert variant["ready"], variant["note"]
    print("Resume:", variant["note"])
    application = queue(db, matches[0]["id"], variant["id"])
    driver = Driver()
    try:
        preview = driver.preview(db, application["id"], fixture=FIXTURES / "forms/greenhouse.html")
        assert preview["can_confirm"], preview
        receipt = driver.confirm(db, preview["token"], explicit_confirm=True)
        assert receipt["confirmation"] == "confirmed"
        print("Application: explicitly confirmed local fixture; receipt and screenshot recorded")
    finally:
        driver.close()
    # Synthetic history yields rates while keeping the actual browser receipt above.
    for i in range(24):
        db.execute(
            "INSERT INTO application(job_id,variant_id,state,applied_at,response_at,minutes) VALUES(?,?,'applied','2026-01-02T00:00:00Z',?,10)",
            (matches[0]["id"], variant["id"], "2026-01-09T00:00:00Z" if i % 2 == 0 else None),
        )
    db.commit()
    print("Analytics:", json.dumps(report(db)["tables"], indent=2))
    assert db.execute("SELECT count(*) FROM llm_call").fetchone()[0] == 0
    print("PASS — zero LLM calls throughout crawl, index, match, tailoring, apply and analytics.")
    db.close()
