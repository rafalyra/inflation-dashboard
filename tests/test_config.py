from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from inflation.config import CalendarEntry, Target, load_calendar, load_settings


def test_repo_config_loads(repo_config_dir: Path) -> None:
    settings = load_settings(repo_config_dir)
    assert "pt-BR" in settings.site.locales
    assert settings.site.default_locale in settings.site.locales
    for country in settings.countries.values():
        assert country.default_locale in settings.site.locales


def test_repo_calendars_parse(repo_config_dir: Path) -> None:
    settings = load_settings(repo_config_dir)
    for code in settings.countries:
        load_calendar(code, repo_config_dir)  # raises if any row is malformed


def test_band_must_surround_target() -> None:
    with pytest.raises(ValidationError):
        Target(target_pct=5.0, band_low_pct=1.0, band_high_pct=4.0)


def test_band_edges_set_together() -> None:
    with pytest.raises(ValidationError):
        Target(target_pct=2.0, band_low_pct=1.0)


def test_target_without_band_is_allowed() -> None:
    assert Target(target_pct=2.0).band_low_pct is None


def test_unknown_timezone_rejected(tmp_path: Path) -> None:
    (tmp_path / "countries.yaml").write_text(
        """
site: {locales: [en], default_locale: en}
countries:
  xx:
    enabled: true
    name: {en: X, pt-BR: X}
    default_locale: en
    timezone: Mars/Olympus
    currency: XXX
    color_token: country-xx
    target: {target_pct: 2.0}
    chart_start_year: 2010
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="timezone"):
        load_settings(tmp_path)


def test_calendar_entry_converts_local_time_to_utc() -> None:
    entry = CalendarEntry.model_validate(
        {
            "release_id": "test-release",
            "indicator": "TEST",
            "reference_period": "2026-01",
            "release_date": "2026-02-10",
            "release_time_local": "09:00",
            "timezone": "America/Sao_Paulo",  # UTC-3, no daylight saving since 2019
            "source_url": "https://example.org",
        }
    )
    assert entry.scheduled_utc == datetime(2026, 2, 10, 12, 0, tzinfo=UTC)


def test_missing_calendar_is_empty(tmp_path: Path) -> None:
    assert load_calendar("zz", tmp_path) == []
