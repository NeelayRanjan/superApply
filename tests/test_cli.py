from firstlook.cli import app
from typer.testing import CliRunner


def test_cli_parity_and_no_submission_bypass(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRSTLOOK_DB", str(tmp_path / "cli.db"))
    runner = CliRunner()
    assert runner.invoke(app, ["health"]).exit_code == 0
    assert runner.invoke(app, ["estimate", "crawl", "--count", "1000"]).exit_code == 0
    result = runner.invoke(app, ["api", "GET", "health"])
    assert result.exit_code == 0 and "ok" in result.stdout
    assert runner.invoke(app, ["api", "POST", "applications/confirm"]).exit_code != 0
    result = runner.invoke(app, ["apply", "--help"])
    assert "--yes" not in result.stdout
