"""Application assistance. Submission is possible only through confirm()."""

import hashlib
import json
import re
import secrets
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from playwright.sync_api import Error, sync_playwright

from firstlook.ingest import now
from firstlook.match import get_profile
from firstlook.paths import DATA
from firstlook.track import transition

SENSITIVE = {
    "work_authorization": r"work.?auth|authorized|eligible.*work",
    "sponsorship": r"sponsor",
    "eeo": r"gender|race|ethnic|eeo",
    "veteran": r"veteran",
    "disability": r"disab",
}
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="firstlook-browser")


class Driver:
    def __init__(self):
        self.runtime = None
        self.browser = None
        self.sessions: dict[str, dict] = {}

    def close(self):
        if self.browser:
            self.browser.close()
        if self.runtime:
            self.runtime.stop()
        self.browser = None
        self.runtime = None
        self.sessions.clear()

    def preview(
        self,
        db: sqlite3.Connection,
        application_id: int,
        answers: dict | None = None,
        fixture: Path | None = None,
    ) -> dict:
        answers = answers or {}
        for previous in self.sessions.values():
            if previous["application_id"] == application_id and not previous["used"]:
                previous["used"] = True
                previous["context"].close()
        row = db.execute(
            """SELECT a.*,j.apply_url,c.platform FROM application a JOIN job j ON j.id=a.job_id JOIN company c ON c.id=j.company_id WHERE a.id=?""",
            (application_id,),
        ).fetchone()
        if not row:
            raise ValueError("Application not found")
        if row["state"] != "saved":
            raise ValueError("This application has already left the review queue")
        variant = db.execute(
            "SELECT * FROM resume_variant WHERE id=?", (row["variant_id"],)
        ).fetchone()
        if (
            not variant
            or not variant["ready"]
            or not variant["pdf_path"]
            or not Path(variant["pdf_path"]).exists()
        ):
            return {
                "available": False,
                "message": "Choose a parse-back verified resume variant before opening the form.",
                "fields": [],
            }
        try:
            if self.runtime is None:
                self.runtime = sync_playwright().start()
            if self.browser is None:
                self.browser = self.runtime.chromium.launch(headless=fixture is not None)
        except Error:
            self.close()
            return {
                "available": False,
                "message": "Playwright browser unavailable. Open the original listing, review your verified PDF and apply manually. The tracker still works.",
                "fields": [],
            }
        context = self.browser.new_context()
        page = context.new_page()
        if fixture:

            def intercept(route):
                if route.request.url == "http://127.0.0.1:8766/form":
                    route.fulfill(status=200, content_type="text/html", body=fixture.read_text())
                else:
                    route.abort()

            page.route("**/*", intercept)
            page.goto("http://127.0.0.1:8766/form")
        else:
            from firstlook.registry import allowed_url

            page.goto(allowed_url(row["apply_url"]), wait_until="domcontentloaded")
        profile = get_profile(db)
        map_path = DATA / "formmaps" / f"{row['platform']}.json"
        mapping = json.loads(map_path.read_text()) if map_path.exists() else {}
        fields = []
        controls = page.locator(
            "input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea"
        )
        for i in range(controls.count()):
            element = controls.nth(i)
            if not element.is_visible() or element.is_disabled():
                continue
            name = element.get_attribute("name") or element.get_attribute("id") or f"field-{i}"
            label = (
                element.evaluate(
                    '(el)=>el.labels?.[0]?.innerText || el.getAttribute("aria-label") || el.name || el.id'
                )
                or name
            )
            tag = element.evaluate("(el)=>el.tagName.toLowerCase()")
            kind = element.get_attribute("type") or tag
            sensitive = next(
                (
                    key
                    for key, pattern in SENSITIVE.items()
                    if re.search(pattern, name + " " + label, re.I)
                ),
                None,
            )
            essay = tag == "textarea" and not re.search(r"address|url|link", name, re.I)
            value = str(answers.get(name, ""))
            if sensitive:
                value = profile.explicit_answers.get(sensitive, "") or "Decline to answer"
            elif not value and not essay and kind != "file":
                contact_key = mapping.get(name, name)
                value = profile.contact.get(contact_key, "")
            if kind == "file":
                # A resume upload only; never guess answers or attach arbitrary user files.
                if re.search(r"resume|cv", name + " " + label, re.I):
                    element.set_input_files(variant["pdf_path"])
                    value = str(Path(variant["pdf_path"]).name)
                else:
                    value = ""
            elif tag == "select":
                options = element.locator("option").evaluate_all(
                    "(els)=>els.map(e=>({value:e.value,label:e.textContent}))"
                )
                match = next(
                    (
                        o
                        for o in options
                        if value
                        and value.lower() in (o["label"].strip().lower(), o["value"].lower())
                    ),
                    None,
                )
                if match:
                    element.select_option(match["value"])
                    value = match["value"]
                else:
                    value = element.input_value()
                    if sensitive and value:
                        # An existing sensitive default is not consent; clear it when possible.
                        try:
                            element.select_option("")
                            value = ""
                        except Error:
                            raise ValueError(
                                "Sensitive dropdown has no decline/empty option; answer explicitly in your profile"
                            )
            elif kind in ("checkbox", "radio"):
                checked = value.lower() in ("yes", "true", "1", "agree")
                element.set_checked(checked)
                value = "yes" if checked else ""
            else:
                element.fill(value)
            fields.append(
                {
                    "name": name,
                    "label": label,
                    "value": value,
                    "type": kind,
                    "required": element.get_attribute("required") is not None,
                    "sensitive": bool(sensitive),
                    "essay": essay,
                    "edited": bool(essay and name in answers and value.strip()),
                    "index": i,
                }
            )
        token = secrets.token_urlsafe(32)
        session = {
            "page": page,
            "context": context,
            "fields": fields,
            "application_id": application_id,
            "variant_id": row["variant_id"],
            "started": time.monotonic(),
            "used": False,
        }
        session["digest"] = self.digest(fields)
        self.sessions[token] = session
        missing = [f["label"] for f in fields if f["required"] and not f["value"]]
        essays = [f["label"] for f in fields if f["essay"] and not f["edited"]]
        return {
            "available": True,
            "token": token,
            "application_id": application_id,
            "variant_id": row["variant_id"],
            "fields": fields,
            "missing": missing,
            "unedited_essays": essays,
            "can_confirm": not missing and not essays,
            "message": "Review every exact field value and attachment. Only Confirm submits this form.",
        }

    @staticmethod
    def digest(fields):
        return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()

    def validate(self, token: str, explicit_confirm: bool) -> dict:
        if explicit_confirm is not True:
            raise ValueError("Explicit user confirmation is required")
        session = self.sessions.get(token)
        if not session or session["used"]:
            raise ValueError("Preview expired or already confirmed")
        if time.monotonic() - session["started"] > 1800:
            raise ValueError("Preview expired; review a new diff")
        fields = session["fields"]
        if any(f["required"] and not f["value"] or f["essay"] and not f["edited"] for f in fields):
            raise ValueError("Required fields or unedited essays block submission")
        controls = session["page"].locator(
            "input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea"
        )
        current = []
        for field in fields:
            element = controls.nth(field["index"])
            value = (
                element.evaluate('(el)=>el.files?.[0]?.name || ""')
                if field["type"] == "file"
                else ("yes" if element.is_checked() else "")
                if field["type"] in ("checkbox", "radio")
                else element.input_value()
            )
            current.append(dict(field, value=value))
        if self.digest(current) != session["digest"]:
            raise ValueError("The form changed since preview. Generate and review a new diff.")
        return session

    def confirm(self, db: sqlite3.Connection, token: str, explicit_confirm: bool) -> dict:
        session = self.validate(token, explicit_confirm)
        session["used"] = True  # A network failure must not permit blind resubmission.
        page = session["page"]
        error = ""
        try:
            page.locator("button[type=submit],input[type=submit]").first.click()
            page.wait_for_function(
                "()=>/application received|thank you for applying|application submitted/i.test(document.body.innerText)",
                timeout=5000,
            )
            confirmation = "confirmed"
        except Error:
            confirmation = "unknown — inspect the visible browser before retrying"
            error = "Submission outcome could not be confirmed."
        folder = Path("exports/receipts")
        folder.mkdir(parents=True, exist_ok=True)
        screenshot = folder / f"application-{session['application_id']}.png"
        page.screenshot(path=str(screenshot), full_page=True)
        fields = session["fields"]
        with db:
            for field in fields:
                db.execute(
                    "INSERT INTO application_field(application_id,name,value,sensitive) VALUES(?,?,?,?)",
                    (
                        session["application_id"],
                        field["name"],
                        field["value"],
                        int(field["sensitive"]),
                    ),
                )
            db.execute(
                "UPDATE application SET confirmation=?,screenshot=?,minutes=?,field_count=?,has_essay=?,applied_at=? WHERE id=?",
                (
                    confirmation,
                    str(screenshot.resolve()),
                    (time.monotonic() - session["started"]) / 60,
                    len(fields),
                    int(any(f["essay"] for f in fields)),
                    now(),
                    session["application_id"],
                ),
            )
            db.execute(
                "UPDATE resume_variant SET used=1 WHERE id=? AND used=0", (session["variant_id"],)
            )
        result = transition(db, session["application_id"], "applied", error)
        session["context"].close()
        return dict(result, receipt=[dict(f) for f in fields])

    def batch_confirm(
        self, db: sqlite3.Connection, tokens: list[str], explicit_confirm: bool
    ) -> list[dict]:
        if len(tokens) != len(set(tokens)):
            raise ValueError("Duplicate preview in batch")
        for token in tokens:
            session = self.validate(token, explicit_confirm)
            if any(f["essay"] for f in session["fields"]):
                raise ValueError("Essay forms require individual confirmation")
        return [self.confirm(db, token, explicit_confirm) for token in tokens]


DRIVER = Driver()
