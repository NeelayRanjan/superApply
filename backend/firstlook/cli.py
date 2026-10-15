import typer

app = typer.Typer(help="firstlook: your local job search workbench")


@app.command()
def serve() -> None:
    import uvicorn

    uvicorn.run("firstlook.api:app", host="127.0.0.1", port=8765)


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
