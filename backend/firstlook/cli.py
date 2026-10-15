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
