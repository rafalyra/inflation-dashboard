"""The interface every country adapter implements (SPEC §4.5).

An adapter is the only place that knows about an agency's API, its series codes, its
language and its structural breaks. It hands the rest of the pipeline data in the
common model (`inflation.models`), so storage, validation, metrics and export are the
same for every country.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from inflation.models import CheckResult, Expectation, Observation, Period, Series


class CountryAdapter(ABC):
    #: Two-letter lowercase code, matching `config/countries.yaml` and the package name.
    code: str

    def __init__(self, raw_dir: Path) -> None:
        # Raw responses are saved here unchanged, so any number can be traced back to
        # exactly what the agency returned.
        self.raw_dir = raw_dir

    @abstractmethod
    def fetch(self, since: date) -> None:
        """Download raw responses for periods from `since` onward and save them as-is."""

    @abstractmethod
    def normalize(self) -> tuple[list[Series], list[Observation]]:
        """Turn saved raw responses into catalog series and observations.

        Structural breaks (basket or classification changes) are resolved here.
        """

    @abstractmethod
    def latest_reference_period(self) -> Period:
        """The newest reference period the source currently publishes.

        Release-watch compares this with the calendar to detect that a release landed.
        """

    @abstractmethod
    def official_checks(self, observations: list[Observation]) -> list[CheckResult]:
        """The "answer key": compare our data with values the agency itself published."""

    @abstractmethod
    def fetch_expectations(self) -> list[Expectation]:
        """Published forecasts for upcoming releases (e.g. a survey median)."""

    @abstractmethod
    def fetch_context(self) -> list[Observation]:
        """Context series: policy rate, FX, and similar."""


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
