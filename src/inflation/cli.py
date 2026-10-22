"""Command-line entry point: `inflation fetch|validate|compute|export|run|due|backfill|calendar`."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from inflation import pipeline
from inflation.calendar import due_releases
from inflation.config import DEFAULT_CONFIG_DIR, load_calendar, load_settings
from inflation.http import FetchError
from inflation.validate import format_report

app = typer.Typer(help="Fetch, validate and export official inflation data.", no_args_is_help=True)

CountryArg = Annotated[str, typer.Argument(help="Two-letter country code, e.g. br.")]
ConfigDirOpt = Annotated[Path, typer.Option(help="Directory holding countries.yaml.")]


def _require_enabled(country: str, config_dir: Path) -> None:
    settings = load_settings(config_dir)
    if country not in settings.enabled_countries():
        typer.echo(f"Country {country!r} is not enabled in countries.yaml.", err=True)
        raise typer.Exit(code=2)


def _fetch(country: str, full_history: bool) -> None:
    try:
        pipeline.fetch(country, full_history=full_history)
    except FetchError as exc:
        typer.echo(f"Fetch failed; nothing was changed downstream.\n{exc}", err=True)
        raise typer.Exit(code=1) from exc


def _build(country: str, config_dir: Path, write: bool, export: bool = False) -> None:
    step = pipeline.export if export else pipeline.build
    result = step(country, config_dir=config_dir, write=write)
    typer.echo(format_report(result.report))
    if not result.report.passed:
        typer.echo("Validation failed: nothing was stored or published.", err=True)
        raise typer.Exit(code=1)
    if write:
        typer.echo(f"Stored {len(result.data.observations):,} observations for {country}.")
    if export and write:
        typer.echo(f"Wrote {pipeline.EXPORT_DIR / (country + '.json')} and overview.json.")


@app.command()
def fetch(
    country: CountryArg,
    config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR,
    full: Annotated[
        bool, typer.Option(help="Download all history instead of the last ~13 months.")
    ] = False,
) -> None:
    """Download raw responses for a country and save them unchanged."""
    _require_enabled(country, config_dir)
    _fetch(country, full_history=full)


@app.command()
def validate(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Normalize the saved raw files and run every check; exit non-zero if any fails."""
    _require_enabled(country, config_dir)
    _build(country, config_dir, write=False)


@app.command()
def compute(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Validate and compute every metric from the saved raw files, without writing anything."""
    _require_enabled(country, config_dir)
    _build(country, config_dir, write=False, export=True)


@app.command()
def export(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Validate the saved raw files, store them, and write the web app's JSON."""
    _require_enabled(country, config_dir)
    _build(country, config_dir, write=True, export=True)


@app.command()
def run(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Refresh recent data, validate it, and store it only if every check passes."""
    _require_enabled(country, config_dir)
    _fetch(country, full_history=False)
    _build(country, config_dir, write=True, export=True)


@app.command()
def backfill(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Download a country's full history, validate it, and store it if every check passes."""
    _require_enabled(country, config_dir)
    _fetch(country, full_history=True)
    _build(country, config_dir, write=True, export=True)


@app.command()
def calendar(country: CountryArg, config_dir: ConfigDirOpt = DEFAULT_CONFIG_DIR) -> None:
    """Rewrite config/calendars/<country>.csv from the agency's official release calendar."""
    _require_enabled(country, config_dir)
    try:
        path = pipeline.update_calendar(country, config_dir)
    except FetchError as exc:
        typer.echo(f"Calendar fetch failed; the file was not changed.\n{exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Wrote {len(load_calendar(country, config_dir))} releases to {path}.")


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
