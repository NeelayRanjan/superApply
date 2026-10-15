"""Synthetic, hand-authored ATS shapes. No network access."""

import json
from pathlib import Path

BODY = "<p>Build reliable software. Required Python, SQL and AWS. 5+ years of experience. Remote within United States. Salary $150,000 - $200,000 per year. Visa sponsorship available.</p>"
SAMPLES = {
    "greenhouse": {
        "id": 1,
        "title": "Senior Software Engineer",
        "absolute_url": "https://example.test/apply/1",
        "location": {"name": "Remote, United States"},
        "departments": [{"name": "Engineering"}],
        "content": BODY,
        "first_published": "2026-01-01T00:00:00Z",
        "employment_type": "Full-time",
        "pay_input_ranges": {"min": 150000, "max": 200000, "currency": "USD"},
    },
    "lever": {
        "id": "1",
        "text": "Senior Software Engineer",
        "applyUrl": "https://example.test/apply/1",
        "categories": {
            "location": "United States",
            "department": "Engineering",
            "commitment": "Full-time",
        },
        "workplaceType": "remote",
        "description": BODY,
        "createdAt": 1767225600000,
        "salaryRange": {"min": 150000, "max": 200000, "currency": "USD"},
    },
    "ashby": {
        "id": "1",
        "title": "Senior Software Engineer",
        "applyUrl": "https://example.test/apply/1",
        "location": "United States",
        "isRemote": True,
        "department": "Engineering",
        "employmentType": "Full-time",
        "publishedAt": "2026-01-01T00:00:00Z",
        "descriptionHtml": BODY,
        "compensation": {"min": 150000, "max": 200000, "currency": "USD"},
    },
    "smartrecruiters": {
        "id": "1",
        "name": "Senior Software Engineer",
        "applyUrl": "https://example.test/apply/1",
        "location": {"country": "United States", "remote": True},
        "department": {"label": "Engineering"},
        "typeOfEmployment": {"label": "Full-time"},
        "releasedDate": "2026-01-01T00:00:00Z",
        "jobAd": {"sections": {"jobDescription": {"text": BODY}}},
        "compensation": {"min": 150000, "max": 200000, "currency": "USD"},
    },
    "workable": {
        "shortcode": "1",
        "title": "Senior Software Engineer",
        "url": "https://example.test/apply/1",
        "country": "United States",
        "telecommuting": True,
        "department": "Engineering",
        "employment_type": "Full-time",
        "published_on": "2026-01-01T00:00:00Z",
        "description": BODY,
        "salary": {"min": 150000, "max": 200000, "currency": "USD"},
    },
    "recruitee": {
        "id": 1,
        "title": "Senior Software Engineer",
        "careers_url": "https://example.test/apply/1",
        "location": "United States",
        "remote": True,
        "department": "Engineering",
        "employment_type_code": "Full-time",
        "published_at": "2026-01-01T00:00:00Z",
        "description": BODY,
        "salary": {"min": 150000, "max": 200000, "currency": "USD"},
    },
    "jsonld": {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "identifier": {"value": "1"},
        "title": "Senior Software Engineer",
        "url": "https://example.test/apply/1",
        "jobLocation": {"address": {"addressCountry": "United States"}},
        "jobLocationType": "TELECOMMUTE",
        "occupationalCategory": "Engineering",
        "employmentType": "Full-time",
        "datePosted": "2026-01-01T00:00:00Z",
        "description": BODY,
        "baseSalary": {"min": 150000, "max": 200000, "currency": "USD"},
    },
}
for platform, sample in SAMPLES.items():
    folder = Path("fixtures/cassettes") / platform
    folder.mkdir(parents=True, exist_ok=True)
    for name, n in [("board", 1), ("empty", 0), ("large", 500)]:
        items = []
        for i in range(n):
            item = dict(sample)
            key = (
                "shortcode"
                if platform == "workable"
                else "identifier"
                if platform == "jsonld"
                else "id"
            )
            item[key] = {"value": str(i + 1)} if key == "identifier" else str(i + 1)
            items.append(item)
        payload = (
            items
            if platform == "lever"
            else {"content": items, "totalFound": n}
            if platform == "smartrecruiters"
            else {"offers": items}
            if platform == "recruitee"
            else {"jobs": items}
        )
        if platform == "jsonld":
            payload = (
                '<html><script type="application/ld+json">' + json.dumps(items) + "</script></html>"
            )
        (folder / (name + ".json")).write_text(
            json.dumps(
                {
                    "synthetic": True,
                    "status": 200,
                    "headers": {
                        "etag": '"fixture-v1"',
                        "last-modified": "Thu, 01 Jan 2026 00:00:00 GMT",
                    },
                    "body": payload,
                }
            )
        )
    for status in [304, 429, 500]:
        (folder / f"{status}.json").write_text(
            json.dumps({"synthetic": True, "status": status, "headers": {}, "body": ""})
        )
    (folder / "malformed.json").write_text(
        json.dumps({"synthetic": True, "status": 200, "headers": {}, "body": "{invalid JSON"})
    )
Path("fixtures/README.md").write_text(
    "# Offline fixtures\n\nThese are synthetic examples authored from platform response shapes, not recordings from live boards. No company data is verified by these tests. Live verification is an explicit user operation after installation.\n"
)
