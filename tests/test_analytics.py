import json

import pytest
from firstlook.analytics import export_csv, extra_samples, report, summary, survival, wilson
from firstlook.demo import populate
from firstlook.paths import FIXTURES


def history(db):
    populate(db, 1)
    job = db.execute("SELECT id FROM job").fetchone()[0]
    variants = {
        v: db.execute(
            "INSERT INTO resume_variant(job_id,cache_key) VALUES(?,?)", (job, v)
        ).lastrowid
        for v in ["A", "B"]
    }
    # first_seen is immutable: create an independent fixture with its intended timestamp.
    db.execute(
        "INSERT INTO job(company_id,external_id,title,apply_url,locations,description,content_hash,first_seen,last_seen) VALUES('demo-0','history','Engineer','https://example.test','[]','Python','history','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')"
    )
    job = db.execute("SELECT id FROM job WHERE external_id='history'").fetchone()[0]
    for row in json.loads((FIXTURES / "history/applications.json").read_text()):
        day = 1 + row["delay_days"]
        applied = f"2026-01-{day:02d}T00:00:00Z"
        response = f"2026-01-{day + 7:02d}T00:00:00Z" if row["response"] else None
        db.execute(
            "INSERT INTO application(job_id,variant_id,state,applied_at,response_at,minutes) VALUES(?,?,?,?,?,?)",
            (
                job,
                variants[row["variant"]],
                "screen" if response else "applied",
                applied,
                response,
                row["minutes"],
            ),
        )
    db.commit()


def test_every_metric_matches_hand_computed_synthetic_history_zero_llm(db):
    history(db)
    result = report(db, "2026-02-01T00:00:00Z")
    assert result["overall"]["applications"] == 120 and result["overall"]["responses"] == 45
    assert result["overall"]["rate"] == 0.375
    variants = result["tables"]["variant"]
    assert variants[0]["rate"] == 0.5 and variants[1]["rate"] == 0.25
    assert variants[0]["responses_per_hour"] == 3 and variants[1]["responses_per_hour"] == 0.75
    assert result["overall"]["responses_per_hour"] == 1.5
    assert result["tables"]["lead_time"][0]["rate"] == 0.5
    assert result["survival"][-1]["survival"] == pytest.approx(0.625)
    assert "applications,responses" in export_csv(result, "overall")
    assert "segment" in export_csv(result, "variant")
    assert "survival" in export_csv(result, "survival")
    assert export_csv(result, "unknown") == ""
    assert db.execute("SELECT count(*) FROM llm_call").fetchone()[0] == 0


def test_segment_under_gate_displays_counts_only_and_wilson_reference():
    result = summary([{"response_at": "yes", "minutes": 10}] * 11)
    assert result["applications"] == 11 and result["responses"] == 11
    assert (
        result["rate"] is None
        and result["low"] is None
        and result["high"] is None
        and result["responses_per_hour"] is None
    )
    low, high = wilson(5, 10)
    assert low == pytest.approx(0.236593, abs=1e-6)
    assert high == pytest.approx(0.763407, abs=1e-6)
    assert wilson(0, 0) == (0, 1)
    assert extra_samples(0.5, 0.5, 12, 12) is None
    assert extra_samples(0.5, 0.25, 12, 12) > 0


def test_survival_curve_matches_reference_implementation_to_tolerance():
    # At day 1: one of four responds. Day 2: one of remaining three responds,
    # one censored; day 3: last responds. S = 3/4, 1/2, 0.
    curve = survival([1, 2, 2, 3], [True, True, False, True])
    assert [r["survival"] for r in curve] == pytest.approx([1, 0.75, 0.5, 0])
    assert [r["at_risk"] for r in curve] == [4, 4, 3, 1]
    with pytest.raises(ValueError):
        survival([1], [])
    with pytest.raises(ValueError):
        survival([-1], [True])
