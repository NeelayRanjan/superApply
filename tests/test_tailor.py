import sqlite3

import pytest
import typst
from firstlook.bank import Entry, save
from firstlook.demo import populate
from firstlook.tailor import create, decide, draft_answer, get, parse_back, render, suggest


def setup_bank(db):
    populate(db, 1)
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
            id="role-1",
            title="Software Engineer",
            organisation="Example Company",
            dates="2022 - 2025",
            bullets=[
                "Built Python services, reducing latency by {latency}.",
                "Maintained SQL data pipelines.",
            ],
            metrics={"latency": "35%"},
            tags=["Python", "SQL"],
        ),
    )
    return db.execute("SELECT id FROM job LIMIT 1").fetchone()[0]


def compile_pdf(source, target):
    typst.compile(str(source), output=str(target))


def test_rephrasing_that_alters_locked_metric_is_rejected_line_without_provenance_blocks_export(
    db, tmp_path
):
    job = setup_bank(db)
    v = create(db, job)
    line = next(item for item in v["lines"] if "35%" in item["text"])
    with pytest.raises(ValueError, match="locked metric"):
        suggest(db, line["id"], line["text"].replace("35%", "45%"))
    db.execute("UPDATE variant_line SET bank_entry_id=NULL WHERE id=?", (line["id"],))
    db.commit()
    with pytest.raises(ValueError, match="bank_entry_id"):
        render(db, v["id"], tmp_path, compile_pdf)


def test_parse_back_recovers_all_identity_fields_from_rendered_pdf_and_cache_costs_zero(
    db, tmp_path
):
    job = setup_bank(db)
    v = create(db, job)
    assert create(db, job)["id"] == v["id"]
    assert db.execute("SELECT count(*) FROM llm_call").fetchone()[0] == 0
    line = v["lines"][0]
    suggest(db, line["id"], line["text"] + " Collaborated with the team.")
    with pytest.raises(ValueError, match="pending"):
        render(db, v["id"], tmp_path, compile_pdf)
    decide(db, line["id"], True)
    result = render(db, v["id"], tmp_path, compile_pdf)
    assert result["ready"]
    assert parse_back(
        tmp_path / f"resume-{v['id']}.pdf",
        [
            "Alex Example",
            "alex@example.test",
            "Software Engineer",
            "Example Company",
            "2022 - 2025",
        ],
    )
    assert not parse_back(tmp_path / f"resume-{v['id']}.pdf", ["fabricated person"])
    assert all(item["bank_entry_id"] for item in draft_answer(db, job, "Describe your Python work"))
    db.execute("UPDATE resume_variant SET used=1 WHERE id=?", (v["id"],))
    db.commit()
    with pytest.raises(ValueError, match="immutable"):
        suggest(db, line["id"], "changed")
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        db.execute("UPDATE variant_line SET text=? WHERE id=?", ("changed", line["id"]))


def test_no_typst_binary_degrades_to_source_and_layout_budget_is_enforced(
    db, tmp_path, monkeypatch
):
    job = setup_bank(db)
    v = create(db, job)
    monkeypatch.setattr("shutil.which", lambda _: None)
    import sys

    monkeypatch.setitem(sys.modules, "typst", None)
    result = render(db, v["id"], tmp_path)
    assert not result["ready"] and "not installed" in result["note"]
    line = v["lines"][0]
    suggest(db, line["id"], line["text"] + " word" * 1000)
    decide(db, line["id"], True)
    assert get(db, v["id"])["overflow"]
    with pytest.raises(ValueError, match="Layout budget"):
        render(db, v["id"], tmp_path)


def test_metrics_immutable_and_rejected_suggestion_keeps_original(db):
    job = setup_bank(db)
    v = create(db, job)
    line = v["lines"][0]
    suggest(db, line["id"], line["text"] + " Extra context.")
    result = decide(db, line["id"], False)
    assert (
        next(item for item in result["lines"] if item["id"] == line["id"])["text"] == line["text"]
    )
    with pytest.raises(ValueError, match="immutable"):
        save(db, Entry(id="role-1", title="Engineer", metrics={"latency": "100%"}))


def test_selection_order_template_and_export_readiness_invalidate(db, tmp_path):
    from firstlook.tailor import layout

    job = setup_bank(db)
    variant = create(db, job, "compact")
    original = variant["lines"]
    result = layout(
        db,
        variant["id"],
        [
            {"bank_entry_id": item["bank_entry_id"], "source_index": item["source_index"]}
            for item in reversed(original)
        ],
    )
    assert [item["text"] for item in result["lines"]] == [
        item["text"] for item in reversed(original)
    ]
    assert not result["ready"]
    assert render(db, variant["id"], tmp_path, compile_pdf)["ready"]
    with pytest.raises(ValueError, match="only once"):
        layout(db, variant["id"], [original[0], original[0]])
