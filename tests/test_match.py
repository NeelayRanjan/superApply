import json

import httpx
import pytest
from firstlook.demo import populate
from firstlook.embed import Encoder, bm25, index
from firstlook.ingest import crawl
from firstlook.ingest.http import PoliteClient
from firstlook.match import Profile, feedback, rank, require_targets, save_profile, train
from firstlook.models import Company
from firstlook.paths import FIXTURES
from firstlook.registry import upsert


def test_ranking_is_deterministic_fixed_corpus_profile_model_absent(db, tmp_path):
    populate(db)
    encoder = Encoder(tmp_path / "absent.onnx")
    first = rank(db, encoder=encoder, include_filtered=True)
    assert first == rank(db, encoder=encoder, include_filtered=True)
    assert first and all("Lexical mode" in r["mode"] for r in first)
    assert first[0]["matched"] and first[0]["extraction"]
    assert (
        bm25("python", ["python python", "cats"])[0] > bm25("python", ["python python", "cats"])[1]
    )
    assert bm25("x", []) == []
    assert "Lexical" in index(db, encoder)


def test_reranker_refuses_to_influence_ranking_below_50_labels(db):
    populate(db, 120)
    db.execute("UPDATE job SET duplicate_of=NULL")
    db.commit()
    original = rank(db, include_filtered=True)
    for row in original[:49]:
        feedback(db, row["id"], row["id"] % 2)
    assert not train(db)["active"]
    assert original == rank(db, include_filtered=True)
    for row in original[49:60]:
        feedback(db, row["id"], row["id"] % 2)
    assert train(db)["active"]


def test_hard_filters_and_exploration_are_explained(db):
    populate(db, 80)
    profile = Profile(
        titles=["Engineer"],
        locations=["Anywhere"],
        must_skills=["Python"],
        strong_threshold=0.99,
        possible_threshold=0.01,
        exploration_share=0.1,
    )
    jobs = rank(db, profile, include_filtered=True)
    assert any(j["exploration"] for j in jobs)
    profile.dealbreakers = ["Build"]
    assert any(j["dealbreakers"] for j in rank(db, profile, include_filtered=True))
    profile.compensation_floor_cents = 100000000
    assert not rank(db, profile)
    with pytest.raises(ValueError):
        feedback(db, 999999, 1)


def test_full_crawl_and_index_1000_company_fixture_corpus_issues_exactly_zero_llm_calls(db):
    with pytest.raises(ValueError, match="target"):
        require_targets(db)
    save_profile(db, Profile(titles=["Engineer"], locations=["United States"]))
    require_targets(db)
    for i in range(1000):
        upsert(
            db,
            Company(
                id=str(i),
                name=f"Fixture Company {i}",
                domain="example.test",
                platform="greenhouse",
                token=str(i),
            ),
        )
    payload = json.loads((FIXTURES / "cassettes/greenhouse/board.json").read_text())["body"]
    c = PoliteClient(
        db,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)),
        sleep=lambda _: None,
    )
    assert crawl(db, c)["new"] == 1000
    index(db)
    assert len(rank(db, include_filtered=True)) == 1000
    assert db.execute("SELECT count(*) FROM llm_call").fetchone()[0] == 0
