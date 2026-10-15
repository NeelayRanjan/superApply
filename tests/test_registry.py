import json

import httpx
import pytest
from firstlook.models import Company
from firstlook.paths import DATA
from firstlook.registry import allowed_url, companies, detect, discover, seed, verify


@pytest.mark.parametrize(
    "url,platform,token",
    [
        ("https://boards.greenhouse.io/acme", "greenhouse", "acme"),
        ("https://jobs.lever.co/acme", "lever", "acme"),
        ("https://jobs.ashbyhq.com/acme", "ashby", "acme"),
        ("https://careers.smartrecruiters.com/Acme", "smartrecruiters", "Acme"),
        ("https://apply.workable.com/acme", "workable", "acme"),
        ("https://acme.recruitee.com", "recruitee", "acme"),
    ],
)
def test_detection_returns_right_platform_for_every_cassette(url, platform, token):
    assert detect(url) == (platform, token)
    assert detect("https://acme.example/careers", '<a href="' + url + '">jobs</a>') == (
        platform,
        token,
    )


def test_seed_loads_validates_no_seeded_row_is_marked_verified(db):
    assert seed(db) >= 300
    seed(db)
    rows = companies(db)
    assert all(not c["verified"] for c in rows)
    assert len(rows) == len({c["id"] for c in rows})
    for line in (DATA / "registry.seed.jsonl").read_text().splitlines():
        Company.model_validate(json.loads(line))


def test_discovery_and_verification_are_explicit_and_mocked(db):
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json=[])
        if "api.lever.co" in str(r.url)
        else httpx.Response(200, text='<a href="https://jobs.lever.co/acme">Jobs</a>')
    )
    with httpx.Client(transport=transport) as client:
        company = discover(db, "https://acme.example/careers", client)
        assert not company.verified
        assert verify(db, client)[0]["verified"]
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as client:
        assert not verify(db, client)[0]["verified"]
    assert detect("https://a.example", '{"@type":"JobPosting"}') == ("jsonld", "https://a.example")
    assert detect("https://a.example") is None


def test_forbidden_sources_and_bad_urls_rejected():
    for url in [
        "https://linkedin.com/jobs",
        "https://www.indeed.com",
        "http://x.test",
        "file:///etc/passwd",
    ]:
        with pytest.raises(ValueError):
            allowed_url(url)
