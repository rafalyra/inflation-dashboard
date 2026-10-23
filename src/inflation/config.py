"""Load and validate `config/countries.yaml` and the release calendars (SPEC §4.4, §8)."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

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


HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$|^rgba\([0-9., ]+\)$")]


class ThemeColors(_Config):
    """One mode (light or dark) of a country's page palette. The web app turns each field
    into a CSS design token; `series` is the validated chart order (see docs/methodology.md)."""

    bg: HexColor
    surface: HexColor
    surface_muted: HexColor
    border: HexColor
    text: HexColor
    text_muted: HexColor
    link: HexColor
    header_bg: HexColor
    header_text: HexColor
    accent: HexColor
    band: HexColor
    up: HexColor  # price increases (bars, arrows)
    down: HexColor  # price decreases
    series: tuple[HexColor, ...] = Field(min_length=8, max_length=8)


class CountryTheme(_Config):
    light: ThemeColors
    dark: ThemeColors


class SeriesRoles(_Config):
    """Catalog series ids for each role on the country page."""

    headline: str
    preview: str | None = None  # e.g. Brazil's IPCA-15, a mid-month preview
    diffusion: str | None = None
    policy_rate: str | None = None
    fx: str | None = None


class Seasonality(_Config):
    """Which years define each calendar month's 'normal' change, and which series to show."""

    baseline_start_year: int
    baseline_exclude_years: tuple[int, ...] = ()
    series: tuple[str, ...] = ()

    def baseline_years(self, before_year: int) -> list[int]:
        """Baseline years up to (not including) `before_year`, minus the excluded ones."""
        return [
            y
            for y in range(self.baseline_start_year, before_year)
            if y not in self.baseline_exclude_years
        ]


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
    theme: CountryTheme | None = None
    panels: dict[str, tuple[str, ...]] = {}
    composition: dict[str, tuple[str, ...]] = {}
    seasonality: Seasonality | None = None
    diffusion_threshold_pct: float | None = None

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
