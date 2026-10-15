import typer

app = typer.Typer(help="firstlook: your local job search workbench")


@app.command()
def serve() -> None:
    import uvicorn

    uvicorn.run("firstlook.api:app", host="127.0.0.1", port=8765)


@app.command()
def health() -> None:
    typer.echo("firstlook 0.1.0 — local, private, ready")
