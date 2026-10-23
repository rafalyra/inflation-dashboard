"""Composition, seasonality and explorer sections of the country export.

Split from export.py to keep each file readable. Like everything exported, these only
combine validated observations with the metric functions in `inflation.metrics`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from inflation.metrics import changes, contributions, cores, diffusion, momentum, seasonality
from inflation.metrics.seasonal import (
    REVISABLE_MONTHS,
    SeasonalAdjustmentUnavailable,
    seasonally_adjust,
)

if TYPE_CHECKING:
    from inflation.export import CountryExport

RECENT_MONTHS = 24  # monthly contribution bars
PROFILE_PREVIOUS_YEARS = 3
TOP_DEVIATIONS = 8
EXPLORE_START = "2012-01"  # item-level history starts with the 2012 basket


def _r(value: float | None, digits: int = 4) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), digits)


def _series(obs: pd.DataFrame, series_id: str, unit: str) -> pd.Series:
    rows = obs[(obs["series_id"] == series_id) & (obs["unit"] == unit)]
    return rows.set_index("period")["value"].sort_index()


def wide(obs: pd.DataFrame, ids: list[str] | pd.Index, unit: str) -> pd.DataFrame:
    sub = obs[obs["series_id"].isin(list(ids)) & (obs["unit"] == unit)]
    return sub.pivot_table(index="period", columns="series_id", values="value").sort_index()


def _children(ex: CountryExport, parent_id: str) -> list[str]:
    cat = ex.catalog
    return list(cat.index[cat["parent_id"] == parent_id])


# ---- Composition -------------------------------------------------------------------------


def _stack_series(
    ex: CountryExport, frame: pd.DataFrame, ids: list[str], weights: pd.Series
) -> list[dict[str, Any]]:
    """Chart series for a stacked chart. Beyond MAX_STACK parts, the smallest by latest weight
    are summed into "Other" (a chart can only tell 8 colors apart); kept parts stay in order."""
    from inflation.export import MAX_STACK

    kept = list(ids)
    other_ids: list[str] = []
    if len(kept) > MAX_STACK:
        other_ids = list(weights[kept].sort_values().index[: len(kept) - MAX_STACK + 1])
        kept = [sid for sid in kept if sid not in set(other_ids)]
    out: list[dict[str, Any]] = [
        {"series_id": sid, "label": ex.label(sid), "values_pp": [_r(v) for v in frame[sid]]}
        for sid in kept
    ]
    if other_ids:
        out.append(
            {
                "series_id": "other",
                "label": {"en": "Other", "pt-BR": "Outros"},
                "members": [ex.label(sid) for sid in other_ids],
                "values_pp": [_r(v) for v in frame[other_ids].sum(axis=1)],
            }
        )
    return out


def _contribution_set(ex: CountryExport, ids: list[str], headline_id: str) -> dict[str, Any]:
    """Monthly (recent) and 12-month contributions for a set of parts of the headline."""
    head_mom = _series(ex.obs, headline_id, "mom_pct")
    w, m = wide(ex.obs, ids, "weight_pct"), wide(ex.obs, ids, "mom_pct")
    c = contributions.monthly_pp(w, m).dropna(how="all")
    c = c.dropna()  # months where every part exists
    recent = c.iloc[-RECENT_MONTHS:]
    c12 = contributions.twelve_month_pp(c, head_mom)
    yoy = _series(ex.obs, headline_id, "yoy_pct")
    period = c.index[-1]
    return {
        "parts": [
            {
                "series_id": sid,
                "label": ex.label(sid),
                "weight_pct": _r(w.loc[period, sid]),
                "mom_pct": _r(m.loc[period, sid]),
                "contribution_pp": _r(c.loc[period, sid]),
                "yoy_pct": _r(changes.rolling_compound_pct(m[sid].dropna(), 12).get(period)),
            }
            for sid in ids
        ],
        "period": period,
        "monthly": {
            "periods": list(recent.index),
            "series": _stack_series(ex, recent, ids, w.loc[c.index[-1]]),
            "headline_mom_pct": [_r(head_mom.get(p)) for p in recent.index],
        },
        "twelve_month": {
            "periods": list(c12.index),
            "series": _stack_series(ex, c12, ids, w.loc[c.index[-1]]),
            "headline_yoy_pct": [_r(yoy.get(p)) for p in c12.index],
        },
        "yoy": {
            "series": [
                {
                    "series_id": sid,
                    "label": ex.label(sid),
                    **_points(changes.rolling_compound_pct(m[sid].dropna(), 12), ex.start),
                }
                for sid in ids
            ]
        },
    }


def _points(s: pd.Series, start: str) -> dict[str, list[Any]]:
    s = s[s.index >= start]
    return {"periods": list(s.index), "values": [_r(v) for v in s]}


def treemap(ex: CountryExport, headline_id: str, period: str) -> list[dict[str, Any]]:
    """Every node below the headline for one month: weight, change and contribution."""
    nodes: list[dict[str, Any]] = []
    obs = ex.obs[ex.obs["period"] == period]
    vals = obs.pivot_table(index="series_id", columns="unit", values="value")

    def walk(parent: str) -> None:
        for sid in _children(ex, parent):
            if sid not in vals.index or ex.catalog.loc[sid, "concept"] not in (
                "group",
                "subgroup",
                "item",
                "subitem",
            ):
                continue
            w, m = vals.loc[sid].get("weight_pct"), vals.loc[sid].get("mom_pct")
            if pd.isna(w) or pd.isna(m):
                continue
            nodes.append(
                {
                    "id": sid,
                    "parent": parent,
                    "label": ex.label(sid),
                    "level": int(ex.catalog.loc[sid, "level"]),
                    "weight_pct": _r(w),
                    "mom_pct": _r(m),
                    "contribution_pp": _r(w * m / 100),
                }
            )
            walk(sid)

    walk(headline_id)
    return nodes


def weighted_diffusion(ex: CountryExport, indicator_prefix: str) -> dict[str, Any] | None:
    subitems = [s for s in ex.catalog.index if s.startswith(f"{indicator_prefix}.subitem.")]
    if not subitems:
        return None
    w = wide(ex.obs, subitems, "weight_pct")
    m = wide(ex.obs, subitems, "mom_pct")
    y = wide(ex.obs, subitems, "yoy_pct")
    rising = diffusion.weighted_share_pct(m > 0, w.where(m.notna()))
    out: dict[str, Any] = {"rising": _points(rising, ex.start)}
    threshold = ex.cfg.diffusion_threshold_pct
    if threshold is not None:
        above = diffusion.weighted_share_pct(y > threshold, w.where(y.notna()))
        out["above_threshold"] = {"threshold_pct": threshold, **_points(above, ex.start)}
    return out


def composition_section(ex: CountryExport, headline_id: str, period: str) -> dict[str, Any]:
    groups = list(ex.components(headline_id, "group").index)
    sets = {"groups": _contribution_set(ex, groups, headline_id)}
    for name, ids in ex.cfg.composition.items():
        present = [sid for sid in ids if sid in ex.catalog.index]
        if present:
            sets[name] = _contribution_set(ex, present, headline_id)
    group_yoy = [
        {
            "series_id": sid,
            "label": ex.label(sid),
            **_points(_series(ex.obs, sid, "yoy_pct"), ex.start),
        }
        for sid in groups
    ]
    return {
        "sets": sets,
        "groups_yoy": group_yoy,
        "treemap": {"period": period, "nodes": treemap(ex, headline_id, period)},
        "weighted_diffusion": weighted_diffusion(ex, headline_id.rsplit(".", 1)[0]),
    }


# ---- Seasonality -------------------------------------------------------------------------


def _core_mean_mom(ex: CountryExport) -> pd.Series:
    ids = [sid for sid in ex.cfg.core_series_ids(ex.code) if sid in ex.catalog.index]
    return cores.core_mean_mom(wide(ex.obs, ids, "mom_pct")) if ids else pd.Series(dtype=float)


def seasonality_section(ex: CountryExport, headline_id: str, period: str) -> dict[str, Any] | None:
    cfg = ex.cfg.seasonality
    if cfg is None:
        return None
    year = int(period[:4])
    years = cfg.baseline_years(before_year=year)
    core_label = {"en": "Core average", "pt-BR": "Média dos núcleos"}
    series: list[tuple[str, dict[str, str], pd.Series]] = []
    for sid in cfg.series:
        if sid in ex.catalog.index:
            series.append((sid, ex.label(sid), _series(ex.obs, sid, "mom_pct")))
    core = _core_mean_mom(ex)
    if len(core):
        series.insert(1, ("core_mean", core_label, core))
    groups = list(ex.components(headline_id, "group").index)
    for sid in groups:
        series.append((sid, ex.label(sid), _series(ex.obs, sid, "mom_pct")))

    rows = []
    for sid, label, mom in series:
        if period not in mom.index:
            continue
        stats = seasonality.monthly_stats(mom, years)
        rows.append(
            {
                "series_id": sid,
                "label": label,
                "kind": "group" if sid in groups else "aggregate",
                "latest": {
                    k: _r(v) if isinstance(v, float) else v
                    for k, v in seasonality.latest_vs_pattern(mom, period, stats).items()
                },
                "profile": _round_profile(
                    seasonality.profile(mom, year, PROFILE_PREVIOUS_YEARS, stats)
                ),
            }
        )

    items = [s for s in ex.catalog.index if s.startswith(headline_id.rsplit(".", 1)[0] + ".item.")]
    dev = seasonality.weighted_deviation(
        wide(ex.obs, items, "mom_pct"), wide(ex.obs, items, "weight_pct"), period, years
    )
    g_dev = seasonality.weighted_deviation(
        wide(ex.obs, groups, "mom_pct"), wide(ex.obs, groups, "weight_pct"), period, years
    )

    def dev_rows(s: pd.Series) -> list[dict[str, Any]]:
        return [
            {"series_id": sid, "label": ex.label(sid), "deviation_pp": _r(v)}
            for sid, v in s.items()
        ]

    return {
        "period": period,
        "baseline_years": years,
        "series": rows,
        "deviation": {
            "groups": dev_rows(g_dev.sort_values(ascending=False)),
            "items_up": dev_rows(dev[dev > 0].sort_values(ascending=False).head(TOP_DEVIATIONS)),
            "items_down": dev_rows(dev[dev < 0].sort_values().head(TOP_DEVIATIONS)),
            "total_pp": _r(g_dev.sum()),
        },
    }


def _round_profile(p: dict[str, Any]) -> dict[str, Any]:
    def rl(values: list[float | None]) -> list[float | None]:
        return [_r(v) for v in values]

    return {
        "year": p["year"],
        "current": rl(p["current"]),
        "previous": {y: rl(v) for y, v in p["previous"].items()},
        "median_pct": rl(p["median_pct"]),
        "q25_pct": rl(p["q25_pct"]),
        "q75_pct": rl(p["q75_pct"]),
    }


def adjusted_momentum(ex: CountryExport, headline_id: str, est_start: str) -> dict[str, Any]:
    """Seasonally adjusted monthly change (headline and core average) and core momentum."""
    out: dict[str, Any] = {}
    try:
        head_sa = seasonally_adjust(_series(ex.obs, headline_id, "index").loc[est_start:])
        core_mom = _core_mean_mom(ex).loc[est_start:]
        core_sa = seasonally_adjust(momentum.index_from_mom(core_mom))
    except SeasonalAdjustmentUnavailable as exc:
        return {"available": False, "reason": str(exc)}
    head_m, core_m = momentum.sa_mom_pct(head_sa), momentum.sa_mom_pct(core_sa)
    periods = [p for p in head_m.index if p >= ex.start]
    c3, c6 = momentum.saar_pct(core_sa, 3), momentum.saar_pct(core_sa, 6)
    core_yoy = changes.rolling_compound_pct(_core_mean_mom(ex), 12)
    out = {
        "available": True,
        "sa_mom": {
            "periods": periods,
            "headline_pct": [_r(head_m.get(p)) for p in periods],
            "core_pct": [_r(core_m.get(p)) for p in periods],
        },
        "core_saar": {
            "periods": periods,
            "saar3_pct": [_r(c3.get(p)) for p in periods],
            "saar6_pct": [_r(c6.get(p)) for p in periods],
            "yoy_pct": [_r(core_yoy.get(p)) for p in periods],
        },
        "revisable_from": head_sa.index[-REVISABLE_MONTHS],
    }
    return out


# ---- Explorer ----------------------------------------------------------------------------


def explore_payload(ex: CountryExport, headline_id: str) -> dict[str, Any]:
    """Every category of the headline index (all levels) plus extra composition parts, with
    monthly change, 12-month change, weight and seasonal pattern. Loaded only by the
    Explore tab, so it stays out of the main country file."""
    prefix = headline_id.rsplit(".", 1)[0]
    ids = [headline_id] + [
        s for s in ex.catalog.index if s.startswith(prefix + ".") and s != headline_id
    ]
    obs = ex.obs[ex.obs["series_id"].isin(ids) & (ex.obs["period"] >= EXPLORE_START)]
    periods = sorted(obs["period"].unique())
    latest_year = int(periods[-1][:4])
    years = ex.cfg.seasonality.baseline_years(latest_year) if ex.cfg.seasonality else []
    tables = {
        u: obs[obs["unit"] == u]
        .pivot_table(index="period", columns="series_id", values="value")
        .reindex(periods)
        for u in ("mom_pct", "yoy_pct", "weight_pct")
    }
    series = []
    for sid in ids:
        mom = tables["mom_pct"].get(sid)
        if mom is None or mom.dropna().empty:
            continue
        row = ex.catalog.loc[sid]
        stats = seasonality.monthly_stats(mom.dropna(), years)
        series.append(
            {
                "series_id": sid,
                "label": ex.label(sid),
                "concept": str(row["concept"]),
                "level": int(row["level"]),
                "parent": None if pd.isna(row["parent_id"]) else str(row["parent_id"]),
                "mom_pct": [_r(v) for v in mom],
                "yoy_pct": [
                    _r(v) for v in tables["yoy_pct"].get(sid, pd.Series(index=periods, dtype=float))
                ],
                "weight_pct": [
                    _r(v)
                    for v in tables["weight_pct"].get(sid, pd.Series(index=periods, dtype=float))
                ],
                "seasonal": {
                    "median_pct": [_r(v) for v in stats["median_pct"]],
                    "q25_pct": [_r(v) for v in stats["q25_pct"]],
                    "q75_pct": [_r(v) for v in stats["q75_pct"]],
                },
            }
        )
    return {"periods": periods, "baseline_years": years, "series": series}
