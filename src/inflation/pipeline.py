"""The pipeline steps, in order: fetch → normalize → validate → store (→ compute → export).

Validation gates everything after it: if any check fails, nothing is written and the
caller gets the report explaining what failed.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

# Importing each country package registers its adapter.
import inflation.countries.br  # noqa: F401
from inflation.config import CALENDAR_COLUMNS, DEFAULT_CONFIG_DIR, load_calendar
from inflation.countries.base import CountryAdapter, Normalized, get_adapter_class
from inflation.models import ValidationReport
from inflation.store import DEFAULT_ROOT, Store
from inflation.validate import run_validation

RAW_ROOT = Path("raw")

# A routine refresh re-reads a little over a year, so revisions and the 12-month window
# are always current without re-downloading all history.
REFRESH_WINDOW = timedelta(days=400)


@dataclass(frozen=True)
class BuildResult:
    report: ValidationReport
    data: Normalized


def adapter_for(country: str) -> CountryAdapter:
    return get_adapter_class(country)(RAW_ROOT / country)


def fetch(country: str, full_history: bool = False) -> None:
    adapter = adapter_for(country)
    if full_history:
        starts = adapter.history_start
        adapter.fetch(starts["index"])
        adapter.fetch_context(starts["context"])
        adapter.fetch_expectations(starts["expectations"])
    else:
        since = datetime.now(UTC).date() - REFRESH_WINDOW
        adapter.fetch(since)
        adapter.fetch_context(since)
        adapter.fetch_expectations(since)


def build(
    country: str,
    config_dir: Path = DEFAULT_CONFIG_DIR,
    data_root: Path = DEFAULT_ROOT,
    write: bool = True,
) -> BuildResult:
    """Normalize the raw files and validate them; store the result only if it passed."""
    adapter = adapter_for(country)
    data = adapter.normalize()
    report = run_validation(adapter, data, load_calendar(country, config_dir))
    if report.passed and write:
        Store(country, data_root).write(data)
    return BuildResult(report=report, data=data)


def update_calendar(country: str, config_dir: Path = DEFAULT_CONFIG_DIR) -> Path:
    """Rewrite config/calendars/<country>.csv from the agency's official calendar."""
    adapter = adapter_for(country)
    today = datetime.now(UTC).date()
    rows = adapter.fetch_calendar(date(today.year - 1, 1, 1), date(today.year + 1, 12, 31))
    path = config_dir / "calendars" / f"{country}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CALENDAR_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path
