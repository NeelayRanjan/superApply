import json

import httpx
import pytest
from firstlook.adapters import source
from firstlook.db import connect
from firstlook.ingest import crawl, ingest
from firstlook.ingest.http import PoliteClient
from firstlook.models import Company, RawPosting
from firstlook.paths import FIXTURES
from firstlook.registry import upsert
from hypothesis import given
from hypothesis import strategies as st

PLATFORMS = ["greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee", "jsonld"]


def company(platform="greenhouse"):
    return Company(
        id="test",
        name="Test",
        domain="example.test",
        platform=platform,
        token="https://example.test/careers" if platform == "jsonld" else "test",
    )


def cassette(platform, name="board"):
    return json.loads((FIXTURES / "cassettes" / platform / (name + ".json")).read_text())


def client(db, platform, name="board"):
    def handle(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        data = cassette(platform, name)
        kwargs = {"text": data["body"]} if isinstance(data["body"], str) else {"json": data["body"]}
        return httpx.Response(data["status"], headers=data["headers"], **kwargs)

    return PoliteClient(db, transport=httpx.MockTransport(handle), sleep=lambda _: None)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_each_adapter_parses_cassette_with_zero_unmatched_fields(db, platform):
    adapter = source(platform, client(db, platform))
    jobs = adapter.fetch(company(platform))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Software Engineer"
    assert job.description.startswith("Build reliable")
    assert job.remote and job.locations and job.department == "Engineering"
    assert job.employment_type == "Full-time" and job.posted_at and job.compensation
    assert job.external_id == "1" and job.apply_url.startswith("https://")
    assert adapter.detect("https://jobs.lever.co/a") == ("lever", "a")


@pytest.mark.parametrize("platform", PLATFORMS)
@pytest.mark.parametrize("name,count", [("empty", 0), ("large", 500), ("304", None)])
def test_empty_large_and_304_response_costs_no_parse(db, platform, name, count):
    c = client(db, platform, name)
    adapter = source(platform, c)
    if name == "304":
        adapter.parse = lambda _: pytest.fail("304 must not parse")
    result = adapter.fetch(company(platform))
    assert result is None if count is None else len(result) == count


@pytest.mark.parametrize("platform", PLATFORMS)
@pytest.mark.parametrize("name", ["429", "500", "malformed"])
def test_failures_never_look_like_empty_boards(db, platform, name):
    with pytest.raises((httpx.HTTPError, ValueError, KeyError, TypeError)):
        source(platform, client(db, platform, name)).fetch(company(platform))


def test_removed_posting_closed_after_two_successful_runs_failed_fetch_does_not_close(db):
    c = company()
    upsert(db, c)
    crawl(db, client(db, "greenhouse"))
    first = db.execute("SELECT first_seen FROM job").fetchone()[0]
    crawl(db, client(db, "greenhouse", "500"))
    assert db.execute("SELECT missing_count FROM job").fetchone()[0] == 0
    crawl(db, client(db, "greenhouse", "empty"))
    assert db.execute("SELECT closed_detected_at FROM job").fetchone()[0] is None
    crawl(db, client(db, "greenhouse", "empty"))
    assert db.execute("SELECT closed_detected_at FROM job").fetchone()[0]
    crawl(db, client(db, "greenhouse"))
    row = db.execute("SELECT * FROM job").fetchone()
    assert row["first_seen"] == first and row["closed_detected_at"] is None
    assert db.execute("SELECT count(*) FROM job").fetchone()[0] == 1


@given(st.lists(st.integers(min_value=1, max_value=20), unique=True, max_size=10))
def test_dedupe_is_idempotent_first_seen_never_changes_closed_job_reappears(ids):
    db = connect(":memory:")
    c = company()
    upsert(db, c)
    jobs = [
        RawPosting(
            external_id=str(i),
            title="Engineer",
            apply_url="https://example.test/a",
            description="Same role",
        )
        for i in ids
    ]
    ingest(db, c, jobs, "2026-01-01T00:00:00Z")
    ingest(db, c, jobs, "2026-01-02T00:00:00Z")
    assert db.execute("SELECT count(*) FROM job").fetchone()[0] == len(ids)
    assert all(r[0] == "2026-01-01T00:00:00Z" for r in db.execute("SELECT first_seen FROM job"))
    if ids:
        assert db.execute("SELECT count(*) FROM job WHERE duplicate_of IS NULL").fetchone()[0] == 1
    db.close()


def test_conditional_headers_backoff_and_cached_response(db):
    requests = []
    delays = []

    def handle(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200, headers={"etag": "v1", "last-modified": "yesterday"}, text="hello"
            )
        if len(requests) == 2:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(304)

    c = PoliteClient(db, transport=httpx.MockTransport(handle), sleep=delays.append)
    c.get("https://example.test/jobs")
    r = c.get("https://example.test/jobs")
    assert r.status_code == 304 and requests[-1].headers["If-None-Match"] == "v1"
    assert requests[-1].headers["If-Modified-Since"] == "yesterday"
    assert max(delays) >= 2 and c.bytes == 5
    assert c.cached_response(r.request.url).text == "hello"
    c.close()


def test_jsonld_respects_robots(db):
    c = PoliteClient(
        db,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, text="User-agent: *\nDisallow: /")
        ),
        sleep=lambda _: None,
    )
    with pytest.raises(ValueError, match="disallows"):
        source("jsonld", c).fetch(company("jsonld"))
