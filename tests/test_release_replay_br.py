"""Replay the Sep 2026 IPCA and IPCA-15 releases from recorded IBGE/BCB responses.

Anchors (SPEC §6.1, confirmed against SIDRA on 2026-10-17): IPCA Sep 2026 +0.82% m/m,
Aug −0.32%, YTD 3.95%, 12-month 4.58%; IPCA-15 Sep 2026 +0.70% m/m, 12-month 4.47%.
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

from inflation.config import load_calendar, load_settings
from inflation.countries.base import Normalized
from inflation.countries.br.adapter import BrazilAdapter
from inflation.countries.br.checks import official_checks
from inflation.export import CountryExport
from inflation.frames import check_observations
from inflation.metrics.seasonal import SeasonalAdjustmentUnavailable
from inflation.models import CheckResult, ValidationReport
from inflation.validate import generic_checks

FIXTURES = Path(__file__).parent / "fixtures" / "br" / "raw"
CONFIG_DIR = Path(__file__).parents[1] / "config"
# Just after the IPCA-15 Sep release window closed and before the Oct IPCA-15.
NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def adapter() -> BrazilAdapter:
    return BrazilAdapter(FIXTURES)


@pytest.fixture(scope="module")
def data(adapter: BrazilAdapter) -> Normalized:
    return adapter.normalize()


def value(data: Normalized, series_id: str, period: str, unit: str) -> float:
    obs = data.observations
    row = obs[(obs.series_id == series_id) & (obs.period == period) & (obs.unit == unit)]
    assert len(row) == 1, f"{series_id} {period} {unit}: {len(row)} rows"
    return float(row["value"].iloc[0])


def test_observations_follow_schema(data: Normalized) -> None:
    check_observations(data.observations)


@pytest.mark.parametrize(
    ("series_id", "period", "unit", "expected"),
    [
        ("br.ipca.headline", "2026-09", "mom_pct", 0.82),
        ("br.ipca.headline", "2026-08", "mom_pct", -0.32),
        ("br.ipca.headline", "2026-09", "ytd_pct", 3.95),
        ("br.ipca.headline", "2026-09", "yoy_pct", 4.58),
        ("br.ipca15.headline", "2026-09", "mom_pct", 0.70),
        ("br.ipca15.headline", "2026-09", "yoy_pct", 4.47),
    ],
)
def test_published_headline_numbers(
    data: Normalized, series_id: str, period: str, unit: str, expected: float
) -> None:
    assert value(data, series_id, period, unit) == pytest.approx(expected, abs=1e-9)


def test_all_nine_groups_rose_in_sep_2026(data: Normalized) -> None:
    # IBGE's Sep 2026 release: every group rose.
    obs = data.observations
    groups = obs[
        obs.series_id.str.startswith("br.ipca.group.")
        & (obs.period == "2026-09")
        & (obs.unit == "mom_pct")
    ]
    assert len(groups) == 9
    assert (groups["value"] > 0).all()


def test_full_answer_key_passes(data: Normalized, adapter: BrazilAdapter) -> None:
    calendar = load_calendar("br", CONFIG_DIR)
    results = official_checks(data, adapter.raw, calendar, NOW)
    failed = {c.name: c for c in results if not c.passed}
    assert not failed, failed
    assert len(results) == 21  # 17 headline checks + 4 BCB segment checks


def test_generic_checks_pass(data: Normalized) -> None:
    failed = [c for c in generic_checks(data) if not c.passed]
    assert not failed, failed


def test_export_reproduces_the_release(data: Normalized, monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate a machine without the X-13 binary (like CI): momentum must say why it's missing.
    def no_x13(index: pd.Series) -> pd.Series:
        raise SeasonalAdjustmentUnavailable("X-13 binary not found")

    monkeypatch.setattr("inflation.export.seasonally_adjust", no_x13)
    monkeypatch.setattr("inflation.export_deep.seasonally_adjust", no_x13)
    settings = load_settings(CONFIG_DIR)
    report = ValidationReport(
        country="br",
        release_id=None,
        checks=(CheckResult(name="x", passed=True),),
        created_at_utc=NOW,
    )
    out = CountryExport(
        "br", settings.countries["br"], data, load_calendar("br", CONFIG_DIR), report, NOW
    ).build()
    head = out["headline"]
    assert (head["mom_pct"], head["yoy_pct"], head["ytd_pct"]) == (0.82, 4.58, 3.95)
    assert head["expected"]["median_pct"] == pytest.approx(0.60)
    assert head["surprise_pp"] == pytest.approx(0.22)
    assert out["summary"]["all_groups_rose"] is True
    assert out["summary"]["top_driver"]["label"]["en"] == "Residential electricity"
    # Contributions of the 9 groups add up to the headline within IBGE's rounding.
    assert out["drivers"]["sum_pp"] == pytest.approx(0.82, abs=0.01)
    # Oct 2025 (+0.09%) is the month that leaves the 12-month window at the next release.
    assert out["base_effects"]["dropping_out"][0] == {
        "period": "2026-10",
        "leaving_period": "2025-10",
        "leaving_mom_pct": 0.09,
    }
    assert out["target"]["status"] == "above"
    assert out["preview"]["mom_pct"] == 0.70
    assert out["preview"]["expected"] is None  # Focus has no IPCA-15 survey
    assert out["momentum"]["saar"] == {"available": False, "reason": "X-13 binary not found"}
    assert out["adjusted"] == {"available": False, "reason": "X-13 binary not found"}
    # BCB segments add up to the headline within rounding (Sep 2026).
    parts = out["composition"]["sets"]["bcb_segments"]["parts"]
    assert [p["label"]["en"] for p in parts] == [
        "Food at home",
        "Industrial goods",
        "Services",
        "Administered prices",
    ]
    assert sum(p["contribution_pp"] for p in parts) == pytest.approx(0.82, abs=0.01)
    assert sum(p["weight_pct"] for p in parts) == pytest.approx(100.0, abs=0.01)
    # The basket map covers groups down to subitems for the latest month.
    levels = {n["level"] for n in out["composition"]["treemap"]["nodes"]}
    assert levels == {1, 2, 3, 4}


def test_focus_expectation_for_sep_2026(data: Normalized) -> None:
    """The 'expected' value is the latest Focus survey dated before the release day (9 Oct)."""
    exp = data.expectations
    sep = exp[
        (exp.reference_period == "2026-09")
        & (exp.measure == "mom_pct")
        & (exp.statistic == "median")
        & (exp.source == "bcb_focus_30d")
        & (exp.survey_date < date(2026, 10, 9))
    ].sort_values("survey_date")
    latest = sep.iloc[-1]
    assert latest["survey_date"] == date(2026, 10, 8)
    assert latest["value"] == pytest.approx(0.60)
    assert latest["n_respondents"] == 136


def test_group_series_have_spans(data: Normalized) -> None:
    series = data.series.set_index("series_id")
    assert series.loc["br.ipca.group.food", "last_period"] == "2026-09"
    assert pd.notna(series.loc["br.ipca.group.food", "first_period"])
