"""Metric formulas checked against small hand-computed examples (SPEC §7)."""

import pandas as pd
import pytest

from inflation.metrics import (
    base_effects,
    changes,
    contributions,
    cores,
    momentum,
    real_rate,
    target,
)


def months(start: str, n: int) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(start, periods=n, freq="M")]


def test_compounding_two_months_of_one_percent() -> None:
    assert changes.compound_pct(pd.Series([1.0, 1.0])) == pytest.approx(2.01)


def test_12_month_rate_from_monthly_chain() -> None:
    # 12 months of 0.5%: 1.005^12 − 1 = 6.1678%
    mom = pd.Series([0.5] * 13, index=months("2025-01", 13))
    yoy = changes.rolling_compound_pct(mom, 12)
    assert list(yoy.index) == ["2025-12", "2026-01"]
    assert yoy.iloc[0] == pytest.approx(6.167781, abs=1e-6)


def test_change_from_index() -> None:
    index = pd.Series([100.0, 101.0, 103.02], index=months("2026-01", 3))
    assert changes.change_from_index_pct(index, 2).iloc[0] == pytest.approx(3.02)


def test_saar_three_months() -> None:
    # Index up 1% over 3 months → (1.01)^4 − 1 = 4.0604% annualized
    sa = pd.Series([100.0, 100.3, 100.6, 101.0], index=months("2026-01", 4))
    assert momentum.saar_pct(sa, 3).iloc[0] == pytest.approx(4.060401, abs=1e-6)


def test_same_month_history() -> None:
    mom = pd.Series([0.1, 0.9, 0.3, 0.5], index=["2023-09", "2024-08", "2024-09", "2025-09"])
    out = momentum.same_month_history(mom, "2025-09", years=5)
    assert out["past_pct"] == [0.1, 0.3]
    assert out["median_pct"] == pytest.approx(0.2)


def test_monthly_contributions_sum_to_headline() -> None:
    # Two components, weights 60/40, changes 1% and −0.5% → 0.6 − 0.2 = 0.4 pp
    w = pd.DataFrame({"a": [60.0], "b": [40.0]}, index=["2026-01"])
    m = pd.DataFrame({"a": [1.0], "b": [-0.5]}, index=["2026-01"])
    c = contributions.monthly_pp(w, m)
    assert c.loc["2026-01"].tolist() == pytest.approx([0.6, -0.2])
    assert c.sum(axis=1).iloc[0] == pytest.approx(0.4)


def test_12_month_contributions_add_up_exactly() -> None:
    idx = months("2025-01", 12)
    a = pd.Series([0.3, 0.1, 0.4, 0.2, 0.0, 0.5, 0.1, 0.2, 0.3, 0.1, 0.0, 0.2], index=idx)
    b = pd.Series([0.1, -0.1, 0.2, 0.0, 0.1, 0.1, -0.2, 0.1, 0.0, 0.2, 0.1, 0.1], index=idx)
    headline = a + b
    c12 = contributions.twelve_month_pp(pd.DataFrame({"a": a, "b": b}), headline)
    yoy = changes.compound_pct(headline)
    assert c12.loc["2025-12"].sum() == pytest.approx(yoy, abs=1e-12)


def test_top_movers() -> None:
    c = pd.Series({"x": 0.3, "y": -0.1, "z": 0.05, "w": -0.4})
    up, down = contributions.top_movers(c, 1)
    assert list(up.index) == ["x"]
    assert list(down.index) == ["w"]


@pytest.mark.parametrize(
    ("value", "status"), [(4.6, "above"), (4.5, "inside"), (1.5, "inside"), (1.4, "below")]
)
def test_band_status(value: float, status: str) -> None:
    assert target.band_status(value, 1.5, 4.5) == status


def test_consecutive_months_outside_band() -> None:
    yoy = pd.Series([4.0, 4.8, 4.2, 4.6, 4.9, 5.1], index=months("2026-01", 6))
    assert target.months_outside_band(yoy, 1.5, 4.5) == 3
    assert target.months_outside_band(yoy.iloc[:3], 1.5, 4.5) == 0


def test_base_effect_identity() -> None:
    # Rebuild a 12-month rate one month later and compare with the identity.
    mom = pd.Series(
        [0.4, 0.2, 0.1, 0.3, 0.5, 0.2, 0.3, 0.1, 0.4, 0.2, 0.3, 0.6, 0.25],
        index=months("2025-01", 13),
    )
    yoy = changes.rolling_compound_pct(mom, 12)
    implied = base_effects.implied_next_yoy_pct(yoy["2025-12"], mom["2025-01"], mom["2026-01"])
    assert implied == pytest.approx(yoy["2026-01"], abs=1e-12)


def test_dropping_out_months() -> None:
    mom = pd.Series([0.09, 0.18, 0.33], index=["2025-10", "2025-11", "2025-12"])
    out = base_effects.dropping_out(mom, "2026-09", months=3)
    assert [(o["period"], o["leaving_period"], o["leaving_mom_pct"]) for o in out] == [
        ("2026-10", "2025-10", 0.09),
        ("2026-11", "2025-11", 0.18),
        ("2026-12", "2025-12", 0.33),
    ]


def test_real_rate() -> None:
    # (1.15 / 1.05) − 1 = 9.5238%
    assert real_rate.ex_ante_real_pct(15.0, 5.0) == pytest.approx(9.523810, abs=1e-6)


def test_core_summary_needs_all_members() -> None:
    df = pd.DataFrame({"a": [4.0, 5.0], "b": [6.0, None]}, index=["2026-01", "2026-02"])
    out = cores.core_summary(df)
    assert list(out.index) == ["2026-01"]
    assert out.iloc[0].tolist() == [5.0, 4.0, 6.0]
