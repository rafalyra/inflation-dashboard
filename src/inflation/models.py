"""Common data model shared by every country (SPEC §4.3).

Adapters translate each agency's format into these shapes during `normalize()`;
everything downstream (validation, metrics, export) only ever sees these models.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _check_period(value: str) -> str:
    """A reference period is a calendar month written YYYY-MM (e.g. 2026-09)."""
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"period must be YYYY-MM, got {value!r}") from exc
    if parsed.strftime("%Y-%m") != value:
        raise ValueError(f"period must be zero-padded YYYY-MM, got {value!r}")
    return value


def _check_utc(value: datetime) -> datetime:
    """Timestamps are stored in UTC so releases from different time zones compare correctly."""
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value


Period = Annotated[str, AfterValidator(_check_period)]
UtcDatetime = Annotated[datetime, AfterValidator(_check_utc)]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Adjustment(StrEnum):
    NSA = "nsa"  # not seasonally adjusted, as published
    OFFICIAL_SA = "official_sa"  # seasonally adjusted by the agency
    OWN_SA = "own_sa"  # seasonally adjusted by this project (revisable; see methodology)


class Series(_Model):
    """One row of a country's series catalog (`countries/<code>/catalog.csv`)."""

    series_id: str = Field(pattern=r"^[a-z]{2}\.[a-z0-9_.]+$")
    country: str = Field(pattern=r"^[a-z]{2}$")
    indicator: str
    concept: str
    parent_id: str | None = None
    level: int = Field(ge=0)
    label_en: str
    label_pt: str
    source: str
    source_code: str
    unit: str
    frequency: str
    adjustment: Adjustment


class Observation(_Model):
    """A single value of a series for one reference month, tied to the release it came from."""

    series_id: str
    period: Period
    value: float
    unit: str
    release_id: str
    fetched_at_utc: UtcDatetime


class ReleaseStatus(StrEnum):
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class Release(_Model):
    release_id: str
    country: str
    indicator: str
    reference_period: Period
    scheduled_utc: UtcDatetime
    detected_utc: UtcDatetime | None = None
    status: ReleaseStatus = ReleaseStatus.SCHEDULED


class ExpectationMeasure(StrEnum):
    MOM_PCT = "mom_pct"
    YOY_PCT = "yoy_pct"
    YEAR_END_PCT = "year_end_pct"
    NEXT_12M_PCT = "next_12m_pct"


class Statistic(StrEnum):
    MEDIAN = "median"
    MEAN = "mean"


class Expectation(_Model):
    """A published forecast for a release (e.g. the BCB Focus median for next month's IPCA)."""

    country: str
    indicator: str
    reference_period: Period
    measure: ExpectationMeasure
    statistic: Statistic
    value: float
    n_respondents: int | None = Field(default=None, ge=0)
    source: str
    survey_date: date
    captured_at_utc: UtcDatetime


class CheckResult(_Model):
    """Outcome of one validation check, with enough detail to explain a failure."""

    name: str
    passed: bool
    expected: float | str | None = None
    actual: float | str | None = None
    tolerance: float | None = None
    detail: str = ""


class ValidationReport(_Model):
    """All checks for one country run. Publishing is allowed only if every check passed."""

    country: str
    release_id: str | None
    checks: tuple[CheckResult, ...]
    created_at_utc: UtcDatetime

    @property
    def passed(self) -> bool:
        # An empty report is a failure: "nothing was checked" must never count as "all good".
        return bool(self.checks) and all(check.passed for check in self.checks)

    @property
    def failures(self) -> tuple[CheckResult, ...]:
        return tuple(check for check in self.checks if not check.passed)
