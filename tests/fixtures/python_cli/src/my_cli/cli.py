"""CLI entry point."""

import typer
from my_cli.utils import format_greeting

app = typer.Typer(help="My CLI tool")


@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")) -> None:
    """Greet someone."""
    typer.echo(format_greeting(name))


if __name__ == "__main__":
    app()
