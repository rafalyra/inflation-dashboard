"""Load and validate `config/countries.yaml` and the release calendars (SPEC §4.4, §8)."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from inflation.models import Period

Locale = Literal["en", "pt-BR"]

DEFAULT_CONFIG_DIR = Path("config")


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class LocalizedName(_Config):
    en: str
    pt_BR: str = Field(alias="pt-BR")


class Target(_Config):
    """Central-bank target and tolerance band, in percent per year."""

    target_pct: float
    band_low_pct: float | None = None
    band_high_pct: float | None = None

    @model_validator(mode="after")
    def _band_surrounds_target(self) -> Self:
        low, high = self.band_low_pct, self.band_high_pct
        if (low is None) != (high is None):
            raise ValueError("band_low_pct and band_high_pct must be set together")
        if low is not None and high is not None and not low <= self.target_pct <= high:
            raise ValueError("target_pct must lie inside the band")
        return self


class SeriesRoles(_Config):
    """Catalog series ids for each role on the country page."""

    headline: str
    preview: str | None = None  # e.g. Brazil's IPCA-15, a mid-month preview
    diffusion: str | None = None
    policy_rate: str | None = None
    fx: str | None = None


class CountryConfig(_Config):
    enabled: bool
    name: LocalizedName
    default_locale: Locale
    timezone: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    color_token: str
    target: Target
    months_outside_band_for_miss: int | None = Field(default=None, ge=1)
    primary_expectation_source: str | None = None
    core_set: tuple[str, ...] = ()
    chart_start_year: int = Field(ge=1900)
    series: SeriesRoles
    panels: dict[str, tuple[str, ...]] = {}

    def core_series_ids(self, code: str) -> list[str]:
        return [f"{code}.core.{name.lower().replace('-', '_')}" for name in self.core_set]

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown IANA timezone {value!r}") from exc
        return value


class SiteConfig(_Config):
    locales: tuple[Locale, ...]
    default_locale: Locale


class Settings(_Config):
    site: SiteConfig
    countries: dict[str, CountryConfig]

    @field_validator("countries")
    @classmethod
    def _two_letter_codes(cls, value: dict[str, CountryConfig]) -> dict[str, CountryConfig]:
        for code in value:
            if len(code) != 2 or not code.isalpha() or not code.islower():
                raise ValueError(f"country code must be two lowercase letters, got {code!r}")
        return value

    def enabled_countries(self) -> dict[str, CountryConfig]:
        return {code: c for code, c in self.countries.items() if c.enabled}


def load_settings(config_dir: Path = DEFAULT_CONFIG_DIR) -> Settings:
    with (config_dir / "countries.yaml").open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Settings.model_validate(raw)


CALENDAR_COLUMNS = [
    "release_id",
    "indicator",
    "reference_period",
    "release_date",
    "release_time_local",
    "timezone",
    "source_url",
]


class CalendarEntry(_Config):
    """One scheduled release, as listed in `config/calendars/<country>.csv`."""

    release_id: str
    indicator: str
    reference_period: Period
    release_date: date
    release_time_local: time
    timezone: str
    source_url: str

    @property
    def scheduled_utc(self) -> datetime:
        local = datetime.combine(
            self.release_date, self.release_time_local, ZoneInfo(self.timezone)
        )
        return local.astimezone(UTC)


def load_calendar(country: str, config_dir: Path = DEFAULT_CONFIG_DIR) -> list[CalendarEntry]:
    path = config_dir / "calendars" / f"{country}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [CalendarEntry.model_validate(row) for row in csv.DictReader(f)]
