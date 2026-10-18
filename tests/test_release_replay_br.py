"""Replay the Sep 2026 IPCA and IPCA-15 releases from recorded IBGE/BCB responses.

Anchors (SPEC §6.1, confirmed against SIDRA on 2026-10-17): IPCA Sep 2026 +0.82% m/m,
Aug −0.32%, YTD 3.95%, 12-month 4.58%; IPCA-15 Sep 2026 +0.70% m/m, 12-month 4.47%.
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

from inflation.config import load_calendar
from inflation.countries.base import Normalized
from inflation.countries.br.adapter import BrazilAdapter
from inflation.countries.br.checks import official_checks
from inflation.frames import check_observations

FIXTURES = Path(__file__).parent / "fixtures" / "br" / "raw"
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


def test_ibge_answer_key_passes(data: Normalized, adapter: BrazilAdapter) -> None:
    calendar = load_calendar("br", Path(__file__).parents[1] / "config")
    results = {c.name: c for c in official_checks(data, adapter.raw, calendar, NOW)}
    ibge_checks = [name for name in results if not name.startswith(("br.bcb", "sgs_"))]
    failed = {name: results[name] for name in ibge_checks if not results[name].passed}
    assert not failed, failed
    assert len(ibge_checks) >= 14


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
