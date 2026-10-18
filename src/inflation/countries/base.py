"""The interface every country adapter implements (SPEC §4.5).

An adapter is the only place that knows about an agency's API, its series codes, its
language and its structural breaks. It hands the rest of the pipeline data in the
common model (`inflation.models`, as DataFrames from `inflation.frames`), so storage,
validation, metrics and export are the same for every country.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import ClassVar

import pandas as pd

from inflation.config import CalendarEntry
from inflation.models import CheckResult


@dataclass(frozen=True)
class Normalized:
    """Everything an adapter produces from its raw files, in the common model."""

    series: pd.DataFrame  # columns: frames.SERIES_COLUMNS
    observations: pd.DataFrame  # columns: frames.OBSERVATION_COLUMNS
    daily: pd.DataFrame  # columns: frames.DAILY_COLUMNS
    expectations: pd.DataFrame  # columns: frames.EXPECTATION_COLUMNS


class CountryAdapter(ABC):
    #: Two-letter lowercase code, matching `config/countries.yaml` and the package name.
    code: str
    #: Where a full backfill starts, per kind of data: "index", "context", "expectations".
    history_start: ClassVar[dict[str, date]]

    def __init__(self, raw_dir: Path) -> None:
        # Raw responses are saved here unchanged, so any number can be traced back to
        # exactly what the agency returned.
        self.raw_dir = raw_dir

    @abstractmethod
    def fetch(self, since: date) -> None:
        """Download raw index data for periods from `since` onward and save it as-is."""

    @abstractmethod
    def fetch_expectations(self, since: date) -> None:
        """Download published forecasts (e.g. a survey) and save them as-is."""

    @abstractmethod
    def fetch_context(self, since: date) -> None:
        """Download context series (policy rate, FX, cores…) and save them as-is."""

    @abstractmethod
    def normalize(self) -> Normalized:
        """Turn saved raw responses into the common model.

        Structural breaks (basket or classification changes) are resolved here.
        """

    @abstractmethod
    def latest_reference_period(self, indicator: str) -> str:
        """The newest reference period (YYYY-MM) the source currently publishes.

        Release-watch compares this with the calendar to detect that a release landed.
        """

    @abstractmethod
    def official_checks(
        self, data: Normalized, calendar: list[CalendarEntry], now_utc: datetime
    ) -> list[CheckResult]:
        """The "answer key": compare our data with values the agency itself published."""

    @abstractmethod
    def fetch_calendar(self, start: date, end: date) -> list[dict[str, str]]:
        """Release schedule rows for `config/calendars/<code>.csv`, from the agency."""


_REGISTRY: dict[str, type[CountryAdapter]] = {}


def register(adapter: type[CountryAdapter]) -> type[CountryAdapter]:
    """Class decorator that makes an adapter available to the CLI by its code."""
    _REGISTRY[adapter.code] = adapter
    return adapter


def get_adapter_class(code: str) -> type[CountryAdapter]:
    try:
        return _REGISTRY[code]
    except KeyError:
        raise KeyError(f"no adapter registered for country {code!r}") from None


def registered_codes() -> list[str]:
    return sorted(_REGISTRY)
