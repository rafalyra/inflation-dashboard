"""Brazil's answer key (SPEC §6.1): our data must reproduce what IBGE and the BCB published.

Tolerance: IBGE publishes percent changes with 2 decimals, so values derived from other
published values can differ by rounding. TOLERANCE_PP is one unit in the last published
digit. A gap analysis over 2012–2026 (Oct 2026, see docs/methodology.md) found the largest
rounding gaps for the latest-period checks below at 0.0049–0.0091 pp, so 0.01 holds with
no loosening.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from inflation.config import CalendarEntry
from inflation.countries.base import Normalized
from inflation.countries.br.normalize import sidra_frame
from inflation.models import CheckResult
from inflation.raw import RawStore

TOLERANCE_PP = 0.01
# Two copies of the same published number (e.g. SGS 433 and SIDRA) must match exactly; this
# only absorbs floating-point noise.
EXACT = 1e-9

INDICATORS = ("IPCA", "IPCA15")

# Monthly SGS series published on IPCA release day; they must reach the latest month too.
SGS_SAME_DAY = (
    "br.bcb.ipca",
    "br.bcb.ipca_12m",
    "br.core.ms",
    "br.core.ex0",
    "br.core.ex3",
    "br.core.dp",
    "br.core.p55",
    "br.ipca.diffusion",
    "br.ipca.free",
    "br.ipca.administered",
    "br.ipca.services",
)


def _series(obs: pd.DataFrame, series_id: str, unit: str) -> pd.Series:
    rows = obs[(obs["series_id"] == series_id) & (obs["unit"] == unit)]
    return rows.set_index("period")["value"].sort_index()


def _compare(
    name: str, expected: float, actual: float, tolerance: float, detail: str = ""
) -> CheckResult:
    return CheckResult(
        name=name,
        passed=bool(abs(expected - actual) <= tolerance + EXACT),
        expected=round(expected, 4),
        actual=round(actual, 4),
        tolerance=tolerance,
        detail=detail,
    )


def latest_period_matches_calendar(
    obs: pd.DataFrame, indicator: str, calendar: list[CalendarEntry], now_utc: datetime
) -> CheckResult:
    name = f"{indicator.lower()}_latest_period_matches_calendar"
    released = [e for e in calendar if e.indicator == indicator and e.scheduled_utc <= now_utc]
    if not released:
        return CheckResult(
            name=name, passed=False, detail="calendar has no past release for this indicator"
        )
    expected = max(released, key=lambda e: e.scheduled_utc).reference_period
    head = _series(obs, f"br.{indicator.lower()}.headline", "mom_pct")
    actual = head.index.max() if len(head) else "none"
    return CheckResult(name=name, passed=actual == expected, expected=expected, actual=actual)


def yoy_chained_matches_published(obs: pd.DataFrame, indicator: str) -> CheckResult:
    """Chain the 12 latest monthly prints: (1+m1)(1+m2)…(1+m12) − 1 must equal the
    published 12-month rate."""
    sid = f"br.{indicator.lower()}.headline"
    mom, yoy = _series(obs, sid, "mom_pct"), _series(obs, sid, "yoy_pct")
    last = yoy.index.max()
    window = mom.loc[:last].iloc[-12:]
    chained = (np.prod(1 + window.to_numpy() / 100) - 1) * 100
    return _compare(
        f"{indicator.lower()}_yoy_chained_matches_published",
        float(yoy[last]),
        chained,
        TOLERANCE_PP,
        f"period {last}",
    )


def ytd_chained_matches_published(obs: pd.DataFrame, indicator: str) -> CheckResult:
    sid = f"br.{indicator.lower()}.headline"
    mom, ytd = _series(obs, sid, "mom_pct"), _series(obs, sid, "ytd_pct")
    last = ytd.index.max()
    window = mom[(mom.index >= f"{last[:4]}-01") & (mom.index <= last)]
    chained = (np.prod(1 + window.to_numpy() / 100) - 1) * 100
    return _compare(
        f"{indicator.lower()}_ytd_chained_matches_published",
        float(ytd[last]),
        chained,
        TOLERANCE_PP,
        f"period {last}",
    )


def yoy_from_index_matches_published(obs: pd.DataFrame) -> CheckResult:
    """The index number (table 1737) carries more precision than the rounded monthly prints."""
    index = _series(obs, "br.ipca.headline", "index")
    yoy = _series(obs, "br.ipca.headline", "yoy_pct")
    last = index.index.max()
    year_ago = (pd.Period(last, freq="M") - 12).strftime("%Y-%m")
    implied = (index[last] / index[year_ago] - 1) * 100
    return _compare(
        "ipca_yoy_from_index_matches_published",
        float(yoy[last]),
        float(implied),
        TOLERANCE_PP,
        f"period {last}",
    )


def groups_sum_to_headline(obs: pd.DataFrame, indicator: str) -> list[CheckResult]:
    """Σ weight_g × change_g / 100 over the 9 groups must give the headline change.

    IBGE's weight for month t is the one that applies to month t's change (the gap
    analysis confirmed this; using t−1 weights misses by up to 0.04 pp).
    """
    prefix = f"br.{indicator.lower()}"
    head = _series(obs, f"{prefix}.headline", "mom_pct")
    last = head.index.max()
    month = obs[(obs["period"] == last) & obs["series_id"].str.startswith(f"{prefix}.group.")]
    wide = month.pivot_table(index="series_id", columns="unit", values="value")
    n_groups = len(wide.dropna(subset=["mom_pct", "weight_pct"]))
    weights = float(wide["weight_pct"].sum())
    implied = float((wide["weight_pct"] * wide["mom_pct"]).sum() / 100)
    detail = f"period {last}, {n_groups} groups"
    return [
        CheckResult(
            name=f"{indicator.lower()}_has_9_groups",
            passed=n_groups == 9,
            expected=9,
            actual=n_groups,
        ),
        _compare(
            f"{indicator.lower()}_group_weights_sum_to_100", 100.0, weights, TOLERANCE_PP, detail
        ),
        _compare(
            f"{indicator.lower()}_groups_sum_to_headline",
            float(head[last]),
            implied,
            TOLERANCE_PP,
            detail,
        ),
    ]


def sgs_copy_matches_sidra(obs: pd.DataFrame, sgs_id: str, unit: str) -> CheckResult:
    """The BCB republishes IPCA in SGS; every overlapping month must match IBGE exactly."""
    name = f"{sgs_id}_matches_sidra_{unit}"
    sgs = _series(obs, sgs_id, unit)
    sidra = _series(obs, "br.ipca.headline", unit)
    both = pd.concat([sgs, sidra], axis=1, keys=["sgs", "sidra"]).dropna()
    if both.empty:
        return CheckResult(
            name=name, passed=False, detail="no overlapping months (is SGS data missing?)"
        )
    diff = (both["sgs"] - both["sidra"]).abs()
    bad = diff[diff > EXACT]
    return CheckResult(
        name=name,
        passed=bad.empty,
        actual=f"{len(bad)} of {len(both)} months differ",
        detail=f"first mismatches: {list(bad.index[:5])}"
        if len(bad)
        else f"{both.index.min()} to {both.index.max()}",
    )


def sgs_series_are_current(obs: pd.DataFrame) -> CheckResult:
    latest = _series(obs, "br.ipca.headline", "mom_pct").index.max()
    stale = {}
    for sid in SGS_SAME_DAY:
        periods = obs.loc[obs["series_id"] == sid, "period"]
        last = periods.max() if len(periods) else "none"
        if last != latest:
            stale[sid] = last
    return CheckResult(
        name="sgs_series_reach_latest_ipca_month",
        passed=not stale,
        expected=latest,
        detail=f"behind: {stale}" if stale else "",
    )


def tables_agree_on_overlap(raw: RawStore) -> CheckResult:
    """Tables 7060/1419 and the long-run table 1737 must publish identical headline values."""
    df = sidra_frame(raw)
    head = df[(df["indicator"] == "IPCA") & (df["category"].isna() | (df["category"] == "7169"))]
    wide = head.pivot_table(index=["period", "unit"], columns="table", values="value")
    problems, compared = [], 0
    for table in (7060, 1419):
        if table not in wide or 1737 not in wide:
            problems.append(f"table {table} or 1737 missing")
            continue
        pair = wide[[table, 1737]].dropna()
        compared += len(pair)
        bad = pair[(pair[table] - pair[1737]).abs() > EXACT]
        problems += [f"{table} vs 1737 at {idx}" for idx in bad.index[:5]]
    return CheckResult(
        name="sidra_tables_agree_on_overlap",
        passed=not problems,
        actual=f"{compared} values compared",
        detail="; ".join(problems),
    )


def segments_match_published(obs: pd.DataFrame) -> list[CheckResult]:
    """Our BCB segments (built from IBGE subitems) must reproduce the series the BCB and IBGE
    publish: free prices (SGS 11428), administered (4449), services (10844) and food at home
    (IBGE subgroup 11), in every month since Jan 2020, within rounding."""
    seg = {
        k: _series(obs, f"br.ipca.bcb.{k}", u)
        for k in ("food", "industrial", "services", "administered")
        for u in ("mom_pct",)
    }
    weights = {k: _series(obs, f"br.ipca.bcb.{k}", "weight_pct") for k in seg}
    if any(s.empty for s in seg.values()):
        return [CheckResult(name="bcb_segments_present", passed=False, detail="no segment data")]
    free_keys = ("food", "industrial", "services")
    free_w = sum(weights[k] for k in free_keys)
    free = sum(weights[k] * seg[k] for k in free_keys) / free_w
    pairs = {
        "free": (free, _series(obs, "br.ipca.free", "mom_pct")),
        "administered": (seg["administered"], _series(obs, "br.ipca.administered", "mom_pct")),
        "services": (seg["services"], _series(obs, "br.ipca.services", "mom_pct")),
        "food": (seg["food"], _series(obs, "br.ipca.subgroup.11", "mom_pct")),
    }
    results = []
    for name, (ours, published) in pairs.items():
        both = pd.concat([ours, published], axis=1, keys=["ours", "published"]).dropna()
        gap = (both["ours"] - both["published"]).abs()
        worst = gap.idxmax() if len(gap) else None
        results.append(
            CheckResult(
                name=f"bcb_segment_{name}_matches_published",
                passed=bool(len(gap)) and bool((gap <= TOLERANCE_PP + EXACT).all()),
                expected=round(float(both.loc[worst, "published"]), 4) if worst else None,
                actual=round(float(both.loc[worst, "ours"]), 4) if worst else None,
                tolerance=TOLERANCE_PP,
                detail=f"{len(gap)} months, largest gap at {worst}"
                if worst
                else "no overlapping months",
            )
        )
    return results


def official_checks(
    data: Normalized, raw: RawStore, calendar: list[CalendarEntry], now_utc: datetime
) -> list[CheckResult]:
    obs = data.observations
    results: list[CheckResult] = []
    for indicator in INDICATORS:
        results.append(latest_period_matches_calendar(obs, indicator, calendar, now_utc))
        results.append(yoy_chained_matches_published(obs, indicator))
        results.append(ytd_chained_matches_published(obs, indicator))
        results.extend(groups_sum_to_headline(obs, indicator))
    results.append(yoy_from_index_matches_published(obs))
    results.append(sgs_copy_matches_sidra(obs, "br.bcb.ipca", "mom_pct"))
    results.append(sgs_copy_matches_sidra(obs, "br.bcb.ipca_12m", "yoy_pct"))
    results.append(sgs_series_are_current(obs))
    results.append(tables_agree_on_overlap(raw))
    results.extend(segments_match_published(obs))
    return results
