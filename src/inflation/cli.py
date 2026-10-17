"""Command-line entry point: `inflation fetch|validate|compute|export|run|due|backfill`."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from inflation.calendar import due_releases
from inflation.config import DEFAULT_CONFIG_DIR, load_calendar, load_settings

app = typer.Typer(help="Fetch, validate and export official inflation data.", no_args_is_help=True)

CountryArg = Annotated[str, typer.Argument(help="Two-letter country code, e.g. br.")]
ConfigDirOpt = Annotated[Path, typer.Option(help="Directory holding countries.yaml.")]


def _require_enabled(country: str, config_dir: Path) -> None:
    settings = load_settings(config_dir)
    if country not in settings.enabled_countries():
        typer.echo(f"Country {country!r} is not enabled in countries.yaml.", err=True)
        raise typer.Exit(code=2)


def _not_implemented(step: str) -> None:
    typer.echo(f"`{step}` is not implemented yet (Phase 1).", err=True)
    raise typer.Exit(code=1)


@app.command()
def fetch(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Download raw responses for a country and save them unchanged."""
    _require_enabled(country, config_dir)
    _not_implemented("fetch")


@app.command()
def validate(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Run generic and official checks; exit non-zero if any fails."""
    _require_enabled(country, config_dir)
    _not_implemented("validate")


@app.command()
def compute(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Compute country-agnostic metrics from validated data."""
    _require_enabled(country, config_dir)
    _not_implemented("compute")


@app.command()
def export(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Write JSON for the web app."""
    _require_enabled(country, config_dir)
    _not_implemented("export")


@app.command()
def run(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Fetch, normalize, validate, compute and export, stopping at the first failure."""
    _require_enabled(country, config_dir)
    _not_implemented("run")


@app.command()
def backfill(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Rebuild a country's full history from the sources."""
    _require_enabled(country, config_dir)
    _not_implemented("backfill")


@app.command()
def due(config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """List releases past their scheduled time that are not yet published."""
    settings = load_settings(config_dir)
    now = datetime.now(UTC)
    # TODO(Phase 2): read published release ids from the publish log on the data branch.
    published: set[str] = set()
    found = False
    for code in settings.enabled_countries():
        for entry in due_releases(load_calendar(code, config_dir), published, now):
            found = True
            typer.echo(f"{code}\t{entry.release_id}\t{entry.scheduled_utc.isoformat()}")
    if not found:
        typer.echo("No releases due.")


if __name__ == "__main__":
    app()
