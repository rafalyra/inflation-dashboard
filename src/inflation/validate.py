"""Generic validation checks plus each adapter's official answer-key checks.

A failed check stops the pipeline before export (CLAUDE.md, data integrity). Checks are
never loosened to make data pass; the mismatch is reported instead.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from inflation.config import CalendarEntry
from inflation.countries.base import CountryAdapter, Normalized
from inflation.frames import SchemaError, check_observations
from inflation.models import CheckResult, ValidationReport


def _schema(data: Normalized) -> CheckResult:
    try:
        check_observations(data.observations)
    except SchemaError as exc:
        return CheckResult(name="observations_schema", passed=False, detail=str(exc))
    return CheckResult(name="observations_schema", passed=True, actual=len(data.observations))


def _catalog_covers_observations(data: Normalized) -> CheckResult:
    unknown = set(data.observations["series_id"]) - set(data.series["series_id"])
    unknown |= set(data.daily["series_id"]) - set(data.series["series_id"])
    return CheckResult(
        name="catalog_covers_observations",
        passed=not unknown,
        detail=f"not in catalog: {sorted(unknown)[:10]}" if unknown else "",
    )


def _months_between(first: str, last: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(first, last, freq="M")]


# Series whose months must be complete: a hole would silently break chained metrics
# (12-month rates, contributions) for every month whose window contains it.
GAP_FREE_CONCEPTS = ("headline", "group")


def _headline_has_no_gaps(data: Normalized) -> list[CheckResult]:
    """No missing months in headline and group series."""
    results = []
    headlines = data.series.loc[data.series["concept"].isin(GAP_FREE_CONCEPTS), "series_id"]
    for series_id in headlines:
        periods = data.observations.loc[
            (data.observations["series_id"] == series_id)
            & (data.observations["unit"] == "mom_pct"),
            "period",
        ]
        if periods.empty:
            results.append(
                CheckResult(name=f"{series_id}_present", passed=False, detail="no mom_pct data")
            )
            continue
        missing = sorted(set(_months_between(periods.min(), periods.max())) - set(periods))
        results.append(
            CheckResult(
                name=f"{series_id}_no_gaps",
                passed=not missing,
                detail=f"missing months: {missing[:12]}"
                if missing
                else f"{periods.min()} to {periods.max()}",
            )
        )
    return results


def _expectations_are_dated_before_capture(data: Normalized) -> CheckResult:
    exp = data.expectations
    if exp.empty:
        return CheckResult(name="expectations_dates", passed=True, detail="no expectations")
    captured = exp["captured_at_utc"].dt.date
    late = exp[exp["survey_date"] > captured]
    return CheckResult(
        name="expectations_dates",
        passed=late.empty,
        detail=f"{len(late)} surveys dated after capture" if len(late) else "",
    )


def generic_checks(data: Normalized) -> list[CheckResult]:
    return [
        _schema(data),
        _catalog_covers_observations(data),
        *_headline_has_no_gaps(data),
        _expectations_are_dated_before_capture(data),
    ]


def run_validation(
    adapter: CountryAdapter,
    data: Normalized,
    calendar: list[CalendarEntry],
    now_utc: datetime | None = None,
    release_id: str | None = None,
) -> ValidationReport:
    now = now_utc or datetime.now(UTC)
    checks = [*generic_checks(data), *adapter.official_checks(data, calendar, now)]
    return ValidationReport(
        country=adapter.code, release_id=release_id, checks=tuple(checks), created_at_utc=now
    )


def format_report(report: ValidationReport) -> str:
    lines = [f"Validation for {report.country}: {'PASSED' if report.passed else 'FAILED'}"]
    for check in report.checks:
        mark = "ok  " if check.passed else "FAIL"
        extra = []
        if check.expected is not None:
            extra.append(f"expected={check.expected}")
        if check.actual is not None:
            extra.append(f"actual={check.actual}")
        if check.tolerance is not None:
            extra.append(f"tol={check.tolerance}")
        if check.detail:
            extra.append(check.detail)
        lines.append(f"  [{mark}] {check.name}  " + "  ".join(extra))
    return "\n".join(lines)
