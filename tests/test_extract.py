import json

import pytest
from firstlook.extract import categories, extract, index_extract, set_tags
from firstlook.ingest import ingest
from firstlook.models import Company, RawPosting
from firstlook.paths import FIXTURES
from firstlook.registry import upsert


@pytest.mark.parametrize("case", json.loads((FIXTURES / "extraction.json").read_text()))
def test_golden_extraction_fixtures_pass(case):
    actual = extract(case["title"], case["description"])
    for key, value in case["expected"].items():
        assert actual[key] == value, (key, actual, case)


def test_categorisation_matches_labelled_fixture_accuracy_floor():
    cases = [
        ("ashby", 10, "", ["startup"]),
        ("greenhouse", 600, "", ["enterprise"]),
        ("greenhouse", 1, "We are a nonprofit", ["non-profit"]),
        ("lever", 10, "SaaS for business customers", ["startup", "SaaS", "B2B"]),
        ("greenhouse", 20, "municipal agency", ["public sector", "agency"]),
    ]
    correct = sum(
        set(expected) <= set(categories(platform, count, text, []))
        for platform, count, text, expected in cases
    )
    assert correct / len(cases) >= 0.9


def test_user_tag_survives_recrawl(db):
    c = Company(id="a", name="A", domain="a.test", platform="ashby", token="a")
    upsert(db, c)
    ingest(
        db,
        c,
        [
            RawPosting(
                external_id="1",
                title="Engineer",
                apply_url="https://a.test",
                description="Python",
                remote=True,
            )
        ],
    )
    index_extract(db)
    set_tags(db, "a", ["my custom category"])
    index_extract(db)
    assert json.loads(db.execute("SELECT tags FROM company").fetchone()[0]) == [
        "my custom category"
    ]
    assert (
        json.loads(db.execute("SELECT data FROM job_extract").fetchone()[0])["remote"] == "remote"
    )
