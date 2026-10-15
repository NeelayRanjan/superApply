import pytest
from firstlook.apply import Driver
from firstlook.match import get_profile, save_profile
from firstlook.paths import FIXTURES
from firstlook.tailor import create, render
from firstlook.track import applications, queue, transition
from playwright.sync_api import Error
from test_tailor import compile_pdf, setup_bank


def prepared(db, tmp_path):
    job = setup_bank(db)
    profile = get_profile(db)
    profile.contact = {"name": "Alex Example", "email": "alex@example.test"}
    profile.needs_sponsorship = True  # Must never infer the legal answer from this preference.
    save_profile(db, profile)
    v = create(db, job)
    render(db, v["id"], tmp_path, compile_pdf)
    return queue(db, job, v["id"])


@pytest.mark.parametrize("platform", ["greenhouse", "lever", "ashby"])
def test_no_code_path_submits_without_explicit_confirm_eeo_work_authorization_never_inferred_receipt_every_submission(
    db, tmp_path, platform
):
    app = prepared(db, tmp_path)
    driver = Driver()
    try:
        preview = driver.preview(db, app["id"], fixture=FIXTURES / "forms" / f"{platform}.html")
        assert preview["available"] and preview["can_confirm"]
        assert all(f["value"] == "Decline to answer" for f in preview["fields"] if f["sensitive"])
        assert db.execute("SELECT count(*) FROM application_field").fetchone()[0] == 0
        page = driver.sessions[preview["token"]]["page"]
        assert page.locator("#result").inner_text() == ""
        with pytest.raises(ValueError, match="confirmation"):
            driver.confirm(db, preview["token"], False)
        receipt = driver.confirm(db, preview["token"], True)
        assert receipt["state"] == "applied" and receipt["confirmation"] == "confirmed"
        assert db.execute("SELECT count(*) FROM application_field").fetchone()[0] == len(
            preview["fields"]
        )
        with pytest.raises(ValueError, match="already confirmed"):
            driver.confirm(db, preview["token"], True)
        assert applications(db)[0]["state"] == "applied"
        transition(db, app["id"], "screen", "Recruiter call", "Recruiter")
        assert applications(db)[0]["response_at"]
    finally:
        driver.close()


def test_required_essay_and_changed_form_block_submission(db, tmp_path):
    app = prepared(db, tmp_path)
    driver = Driver()
    try:
        preview = driver.preview(db, app["id"], fixture=FIXTURES / "forms/essay.html")
        assert preview["unedited_essays"] and preview["missing"]
        with pytest.raises(ValueError, match="unedited essays"):
            driver.confirm(db, preview["token"], True)
        preview = driver.preview(
            db,
            app["id"],
            answers={"why_role": "My own edited answer."},
            fixture=FIXTURES / "forms/essay.html",
        )
        assert preview["can_confirm"]
        with pytest.raises(ValueError, match="individual"):
            driver.batch_confirm(db, [preview["token"]], True)
        driver.sessions[preview["token"]]["page"].locator("[name=email]").fill(
            "changed@example.test"
        )
        with pytest.raises(ValueError, match="form changed"):
            driver.confirm(db, preview["token"], True)
    finally:
        driver.close()


def test_missing_playwright_browsers_working_manual_path(db, tmp_path, monkeypatch):
    app = prepared(db, tmp_path)
    driver = Driver()

    class Missing:
        def start(self):
            raise Error("Executable does not exist")

    monkeypatch.setattr("firstlook.apply.sync_playwright", lambda: Missing())
    result = driver.preview(db, app["id"])
    assert not result["available"] and "manually" in result["message"]
    assert applications(db)


def test_simple_batch_confirm_requires_every_diff(db, tmp_path):
    app = prepared(db, tmp_path)
    driver = Driver()
    try:
        preview = driver.preview(db, app["id"], fixture=FIXTURES / "forms/lever.html")
        with pytest.raises(ValueError, match="Duplicate"):
            driver.batch_confirm(db, [preview["token"], preview["token"]], True)
        assert driver.batch_confirm(db, [preview["token"]], True)[0]["confirmation"] == "confirmed"
    finally:
        driver.close()
