"""Seasonality, diffusion and momentum helpers, checked against hand-computed examples."""

import pandas as pd
import pytest

from inflation.countries.br.composition import classify, load_rules
from inflation.metrics import cores, diffusion, momentum, seasonality


def test_monthly_stats_use_only_baseline_years() -> None:
    # Septembers: 2018 0.1, 2019 0.3, 2021 5.0 (excluded year), 2023 0.5
    mom = pd.Series(
        {"2018-09": 0.1, "2019-09": 0.3, "2021-09": 5.0, "2023-09": 0.5, "2023-10": 9.0}
    )
    stats = seasonality.monthly_stats(mom, [2018, 2019, 2023])
    assert stats.loc["09", "median_pct"] == pytest.approx(0.3)
    assert stats.loc["09", "n"] == 3
    stats2 = seasonality.monthly_stats(mom, [2023])
    assert stats2.loc["10", "median_pct"] == pytest.approx(9.0)


def test_latest_vs_pattern_deviation() -> None:
    mom = pd.Series({"2018-09": 0.1, "2019-09": 0.3, "2026-09": 0.82})
    stats = seasonality.monthly_stats(mom, [2018, 2019])
    out = seasonality.latest_vs_pattern(mom, "2026-09", stats)
    assert out["median_pct"] == pytest.approx(0.2)
    assert out["deviation_pp"] == pytest.approx(0.62)


def test_profile_fills_missing_months_with_none() -> None:
    mom = pd.Series({"2026-01": 0.5, "2026-02": 0.7, "2025-01": 0.4})
    stats = seasonality.monthly_stats(mom, [2025])
    p = seasonality.profile(mom, 2026, 1, stats)
    assert p["current"][:3] == [0.5, 0.7, None]
    assert p["previous"]["2025"][0] == 0.4


def test_weighted_seasonal_deviation() -> None:
    # Item a: usual September +0.2, now +1.2, weight 10 → (1.2 − 0.2) × 10 / 100 = 0.10 pp
    mom = pd.DataFrame({"a": [0.2, 1.2], "b": [0.5, 0.5]}, index=["2019-09", "2026-09"])
    w = pd.DataFrame({"a": [10.0, 10.0], "b": [20.0, 20.0]}, index=mom.index)
    dev = seasonality.weighted_deviation(mom, w, "2026-09", [2019])
    assert dev["a"] == pytest.approx(0.10)
    assert dev["b"] == pytest.approx(0.0)


def test_weighted_diffusion_share() -> None:
    # Rising: a (weight 30) and c (weight 10) out of 100 → 40%
    m = pd.DataFrame({"a": [0.5], "b": [-0.1], "c": [0.2]}, index=["2026-09"])
    w = pd.DataFrame({"a": [30.0], "b": [60.0], "c": [10.0]}, index=["2026-09"])
    assert diffusion.weighted_share_pct(m > 0, w).iloc[0] == pytest.approx(40.0)


def test_index_from_mom_and_sa_mom_roundtrip() -> None:
    mom = pd.Series([1.0, 2.0, -0.5], index=["2026-01", "2026-02", "2026-03"])
    idx = momentum.index_from_mom(mom)
    assert idx.iloc[-1] == pytest.approx(100 * 1.01 * 1.02 * 0.995)
    assert momentum.sa_mom_pct(idx).tolist() == pytest.approx([2.0, -0.5])


def test_core_mean_mom_needs_all_members() -> None:
    df = pd.DataFrame({"a": [0.2, 0.4], "b": [0.4, None]}, index=["2026-01", "2026-02"])
    assert cores.core_mean_mom(df).to_dict() == pytest.approx({"2026-01": 0.3})


@pytest.mark.parametrize(
    ("code", "segment"),
    [
        ("1101002", "food"),  # Arroz, food at home
        ("1201001", "services"),  # Refeição, food away from home
        ("7101010", "services"),  # Empregado doméstico (personal services)
        ("7101034", "administered"),  # Cartório, the exception within personal services
        ("7201063", "administered"),  # Jogos de azar
        ("7201023", "industrial"),  # Brinquedo, excluded from Recreação services
        ("7201090", "services"),  # Hospedagem
        ("5104001", "administered"),  # Gasolina
        ("5104002", "industrial"),  # Etanol is a free price, so an industrial good
        ("6101001", "administered"),  # medicines (Produtos farmacêuticos)
        ("9101019", "industrial"),  # Aparelho telefônico
    ],
)
def test_bcb_classification(code: str, segment: str) -> None:
    assert classify(code, load_rules()) == segment
