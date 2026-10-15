import typer

app = typer.Typer(help="firstlook: your local job search workbench")


@app.command()
def serve() -> None:
    import uvicorn

    from firstlook.api import app as api_app
    from firstlook.api import mount_frontend

    mount_frontend()
    uvicorn.run(api_app, host="127.0.0.1", port=8765)


@app.command()
def health() -> None:
    typer.echo("firstlook 0.1.0 — local, private, ready")


registry_app = typer.Typer(help="Seed and explicitly verify company boards")
app.add_typer(registry_app, name="registry")


@registry_app.command("seed")
def registry_seed() -> None:
    from firstlook.db import connect
    from firstlook.registry import seed

    with connect() as db:
        typer.echo(f"Loaded {seed(db)} unverified seed companies")


@registry_app.command("list")
def registry_list() -> None:
    import json

    from firstlook.db import connect
    from firstlook.registry import companies

    with connect() as db:
        typer.echo(json.dumps(companies(db), indent=2))


@registry_app.command("discover")
def registry_discover(url: str) -> None:
    import httpx

    from firstlook.db import connect
    from firstlook.registry import discover

    with (
        connect() as db,
        httpx.Client(
            timeout=30, headers={"User-Agent": "firstlook/0.1 contact: configure-me"}
        ) as client,
    ):
        typer.echo(discover(db, url, client).model_dump_json())


@registry_app.command("verify")
def registry_verify(all: bool = typer.Option(False, "--all")) -> None:
    import json

    import httpx

    from firstlook.db import connect
    from firstlook.registry import verify

    with (
        connect() as db,
        httpx.Client(
            timeout=30, headers={"User-Agent": "firstlook/0.1 contact: configure-me"}
        ) as client,
    ):
        typer.echo(json.dumps(verify(db, client), indent=2))


@app.command()
def demo() -> None:
    from firstlook.db import connect
    from firstlook.demo import populate

    with connect() as db:
        typer.echo(populate(db))
    typer.echo("Loaded clearly labelled synthetic demo jobs.")


@app.command("crawl")
def crawl_command(full: bool = False) -> None:
    import json

    from firstlook.db import connect
    from firstlook.embed import index
    from firstlook.ingest import crawl
    from firstlook.ingest.http import PoliteClient
    from firstlook.match import require_targets

    with connect() as db:
        require_targets(db)
        client = PoliteClient(db, full=full)
        try:
            typer.echo(json.dumps(crawl(db, client), indent=2))
            typer.echo(index(db))
        finally:
            client.close()


@app.command("index")
def index_command() -> None:
    from firstlook.db import connect
    from firstlook.embed import index

    with connect() as db:
        typer.echo(index(db))


@app.command()
def jobs(include_filtered: bool = False) -> None:
    import json

    from firstlook.db import connect
    from firstlook.match import rank

    with connect() as db:
        typer.echo(json.dumps(rank(db, include_filtered=include_filtered), indent=2))


@app.command()
def profile(file: str) -> None:
    from pathlib import Path

    from firstlook.db import connect
    from firstlook.match import Profile, save_profile

    with connect() as db:
        save_profile(db, Profile.model_validate_json(Path(file).read_text()))
    typer.echo("Profile saved")


@app.command()
def retrain() -> None:
    from firstlook.db import connect
    from firstlook.match import train

    with connect() as db:
        typer.echo(train(db))


@app.command("estimate")
def estimate_command(command: str, count: int = 1) -> None:
    from firstlook.llm import estimate

    typer.echo(estimate(command, count))


@app.command("tool")
def tool_command(name: str, arguments: str = "{}", yes: bool = False) -> None:
    import json

    from firstlook.chat import tool
    from firstlook.db import connect

    args = json.loads(arguments)
    batch = args if isinstance(args, list) else [args]
    if len(batch) > 25 and not yes:
        raise typer.BadParameter(
            "Bulk operations over 25 jobs require --yes; inspect estimate first."
        )
    with connect() as db:
        for item in batch:
            typer.echo(json.dumps(tool(db, name, item), indent=2))


@app.command("bank-save")
def bank_save(file: str) -> None:
    from pathlib import Path

    from firstlook.bank import Entry, save
    from firstlook.db import connect

    with connect() as db:
        typer.echo(save(db, Entry.model_validate_json(Path(file).read_text())))


@app.command("render")
def render_command(variant_id: int) -> None:
    from firstlook.db import connect
    from firstlook.tailor import render

    with connect() as db:
        typer.echo(render(db, variant_id))


@app.command("apply")
def apply_command(application_id: int, answers_file: str = "") -> None:
    import json
    from pathlib import Path

    from firstlook.apply import Driver
    from firstlook.db import connect

    driver = Driver()
    try:
        with connect() as db:
            preview = driver.preview(
                db,
                application_id,
                json.loads(Path(answers_file).read_text()) if answers_file else {},
            )
            typer.echo(json.dumps(preview, indent=2))
            if preview.get("can_confirm") and typer.confirm(
                "Submit exactly the fields and attachment shown above?", default=False
            ):
                typer.echo(json.dumps(driver.confirm(db, preview["token"], True), indent=2))
    finally:
        driver.close()


@app.command("api")
def api_command(method: str, path: str, data: str = "{}") -> None:
    """CLI parity for API operations. Application submission uses `firstlook apply`."""
    import json

    from fastapi.testclient import TestClient

    from firstlook.api import app as api_app

    if "/confirm" in path or "/preview" in path:
        raise typer.BadParameter(
            "Use firstlook apply for a persistent, explicitly confirmed browser session."
        )
    response = TestClient(api_app).request(
        method.upper(),
        "/api/" + path.lstrip("/"),
        json=json.loads(data) if method.upper() != "GET" else None,
    )
    typer.echo(json.dumps(response.json(), indent=2))
    if response.status_code >= 400:
        raise typer.Exit(1)
