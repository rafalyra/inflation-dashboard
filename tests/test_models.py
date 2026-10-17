from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from inflation.models import CheckResult, Observation, ValidationReport

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _obs(**overrides: object) -> Observation:
    fields: dict[str, object] = {
        "series_id": "xx.test.headline",
        "period": "2026-01",
        "value": 1.0,
        "unit": "pct",
        "release_id": "test-release",
        "fetched_at_utc": NOW,
    }
    fields.update(overrides)
    return Observation.model_validate(fields)


@pytest.mark.parametrize("period", ["2026-1", "2026-13", "26-01", "2026/01", "2026-01-01"])
def test_bad_period_rejected(period: str) -> None:
    with pytest.raises(ValidationError):
        _obs(period=period)


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ValidationError):
        _obs(fetched_at_utc=datetime(2026, 1, 1))


def test_non_utc_timestamp_rejected() -> None:
    with pytest.raises(ValidationError):
        _obs(fetched_at_utc=datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=-3))))


def test_unknown_field_rejected() -> None:
    with pytest.raises(ValidationError):
        _obs(colour="red")


def _report(*passed: bool) -> ValidationReport:
    checks = tuple(CheckResult(name=f"check_{i}", passed=p) for i, p in enumerate(passed))
    return ValidationReport(country="xx", release_id=None, checks=checks, created_at_utc=NOW)


def test_report_passes_only_when_all_checks_pass() -> None:
    assert _report(True, True).passed
    failing = _report(True, False)
    assert not failing.passed
    assert [c.name for c in failing.failures] == ["check_1"]


def test_empty_report_never_passes() -> None:
    assert not _report().passed
