"""Exercise the built UI with every browser request fulfilled locally."""

import json

import pytest
from fastapi.testclient import TestClient
from firstlook.api import app
from firstlook.paths import ROOT
from playwright.sync_api import Error, sync_playwright


def test_virtualised_table_handles_20000_rows_and_every_panel_renders(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRSTLOOK_DB", str(tmp_path / "browser.db"))
    client = TestClient(app)
    client.post("/api/demo")
    sample = client.get("/api/jobs").json()[0]
    jobs = [dict(sample, id=i + 1, title=f"Software Engineer {i + 1}") for i in range(20000)]
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Error as exc:
            if "Executable doesn't exist" in str(exc):
                pytest.skip("Optional Playwright browser absent; manual mode tested separately")
            raise
        page = browser.new_page(viewport={"width": 1512, "height": 982})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def route(request):
            from urllib.parse import urlparse

            path = urlparse(request.request.url).path
            if path == "/api/jobs":
                request.fulfill(status=200, content_type="application/json", body=json.dumps(jobs))
            elif path.startswith("/api/"):
                response = client.request(
                    request.request.method, path, content=request.request.post_data
                )
                request.fulfill(
                    status=response.status_code,
                    content_type=response.headers.get("content-type", "application/json"),
                    body=response.content,
                )
            elif path.startswith("/assets/"):
                file = ROOT / "frontend/dist" / path.lstrip("/")
                request.fulfill(
                    status=200,
                    content_type="application/javascript" if file.suffix == ".js" else "text/css",
                    body=file.read_bytes(),
                )
            elif path == "/":
                request.fulfill(
                    status=200,
                    content_type="text/html",
                    body=(ROOT / "frontend/dist/index.html").read_text(),
                )
            else:
                request.abort()

        page.route("**/*", route)
        page.goto("http://127.0.0.1:8765")
        page.get_by_role("table", name="Job opportunities").wait_for()
        assert page.get_by_role("table").get_attribute("aria-rowcount") == "20000"
        assert page.get_by_role("row").count() < 50
        page.get_by_role("button", name="Software Engineer 1", exact=False).first.click()
        page.get_by_role("dialog", name="Job detail").wait_for()
        page.get_by_role("button", name="Back to opportunities").click()
        for name in ["Pipeline", "Analytics", "Bank", "Registry", "Settings"]:
            page.locator(".rail").get_by_role("button", name=name, exact=True).click()
            assert page.locator("h1").inner_text()
        page.locator(".rail").get_by_role("button", name="Jobs", exact=False).first.click()
        screenshot = ROOT / "exports/ui-preview.png"
        screenshot.parent.mkdir(exist_ok=True)
        page.screenshot(path=str(screenshot))
        assert not errors
        browser.close()
