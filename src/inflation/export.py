"""Compute every metric and write schema-versioned JSON for the web app.

The web app only displays what is exported here; it never computes metrics. Every number
in the output traces back to a validated observation, a recorded expectation, or config.
Missing inputs become `null` with a reason, never a guess.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from inflation.config import CalendarEntry, CountryConfig
from inflation.countries.base import Normalized
from inflation.metrics import (
    base_effects,
    changes,
    contributions,
    cores,
    momentum,
    real_rate,
    surprise,
    target,
)
from inflation.metrics.seasonal import (
    REVISABLE_MONTHS,
    SeasonalAdjustmentUnavailable,
    seasonally_adjust,
)
from inflation.models import ValidationReport

SCHEMA_VERSION = 1
TOP_N = 5
SAME_MONTH_YEARS = 10
# X-13 estimates seasonal factors from this many years of history before the chart start.
SA_ESTIMATION_YEARS = 10


def _r(value: float | None, digits: int = 4) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), digits)


def _series(obs: pd.DataFrame, series_id: str, unit: str) -> pd.Series:
    rows = obs[(obs["series_id"] == series_id) & (obs["unit"] == unit)]
    return rows.set_index("period")["value"].sort_index()


def _points(s: pd.Series, start: str) -> dict[str, list[Any]]:
    s = s[s.index >= start]
    return {"periods": list(s.index), "values": [_r(v) for v in s]}


class CountryExport:
    def __init__(
        self,
        code: str,
        cfg: CountryConfig,
        data: Normalized,
        calendar: list[CalendarEntry],
        report: ValidationReport,
        now_utc: datetime,
    ) -> None:
        self.code, self.cfg, self.data, self.calendar, self.report, self.now = (
            code,
            cfg,
            data,
            calendar,
            report,
            now_utc,
        )
        self.obs = data.observations
        self.catalog = data.series.set_index("series_id")
        self.start = f"{cfg.chart_start_year}-01"

    # ---- helpers -------------------------------------------------------------------------

    def label(self, series_id: str) -> dict[str, str]:
        row = self.catalog.loc[series_id]
        return {"en": str(row["label_en"]), "pt-BR": str(row["label_pt"])}

    def indicator(self, series_id: str) -> str:
        return str(self.catalog.loc[series_id, "indicator"])

    def release(self, indicator: str, period: str) -> CalendarEntry | None:
        matches = [
            e for e in self.calendar if e.indicator == indicator and e.reference_period == period
        ]
        return matches[0] if matches else None

    def next_release(self, indicator: str) -> CalendarEntry | None:
        future = [
            e for e in self.calendar if e.indicator == indicator and e.scheduled_utc > self.now
        ]
        return min(future, key=lambda e: e.scheduled_utc) if future else None

    def yoy_from_mom(self, series_id: str) -> pd.Series:
        return changes.rolling_compound_pct(_series(self.obs, series_id, "mom_pct"), 12)

    def expectation(
        self, indicator: str, period: str, measure: str, before: date
    ) -> dict[str, Any] | None:
        primary = self.cfg.primary_expectation_source
        exp = self.data.expectations
        if primary is None or exp.empty:
            return None
        row = surprise.expectation_before(exp, indicator, period, measure, primary, before)
        if row is None:
            return None
        others = []
        for source in sorted(set(exp["source"]) - {primary}):
            alt = surprise.expectation_before(exp, indicator, period, measure, source, before)
            if alt is not None:
                others.append(
                    {
                        "source": source,
                        "median_pct": _r(alt["value"]),
                        "survey_date": str(alt["survey_date"]),
                    }
                )
        n = row["n_respondents"]
        return {
            "source": primary,
            "median_pct": _r(row["value"]),
            "survey_date": str(row["survey_date"]),
            "n_respondents": None if pd.isna(n) else int(n),
            "other_sources": others,
        }

    # ---- sections ------------------------------------------------------------------------

    def headline_release(self, series_id: str) -> dict[str, Any]:
        ind = self.indicator(series_id)
        mom = _series(self.obs, series_id, "mom_pct")
        yoy = _series(self.obs, series_id, "yoy_pct")
        ytd = _series(self.obs, series_id, "ytd_pct")
        period = mom.index.max()
        rel = self.release(ind, period)
        release_day = rel.release_date if rel else self.now.date()
        expected = self.expectation(ind, period, "mom_pct", release_day)
        nxt = self.next_release(ind)
        return {
            "series_id": series_id,
            "indicator": ind,
            "label": self.label(series_id),
            "reference_period": period,
            "release_date": str(rel.release_date) if rel else None,
            "mom_pct": _r(mom[period]),
            "yoy_pct": _r(yoy.get(period)),
            "ytd_pct": _r(ytd.get(period)),
            "previous_mom_pct": _r(mom.iloc[-2]) if len(mom) > 1 else None,
            "expected": expected,
            "surprise_pp": _r(surprise.surprise_pp(mom[period], expected["median_pct"]))
            if expected
            else None,
            "next_release": (
                {
                    "reference_period": nxt.reference_period,
                    "scheduled_utc": nxt.scheduled_utc.isoformat(),
                }
                if nxt
                else None
            ),
        }

    def target_section(self, yoy: pd.Series) -> dict[str, Any]:
        t = self.cfg.target
        latest = float(yoy.iloc[-1])
        out: dict[str, Any] = {
            "target_pct": t.target_pct,
            "band_low_pct": t.band_low_pct,
            "band_high_pct": t.band_high_pct,
            "distance_pp": _r(target.distance_pp(latest, t.target_pct)),
            "status": None,
            "months_outside_band": None,
            "miss_threshold_months": self.cfg.months_outside_band_for_miss,
            "missed": None,
        }
        if t.band_low_pct is not None and t.band_high_pct is not None:
            streak = target.months_outside_band(yoy, t.band_low_pct, t.band_high_pct)
            threshold = self.cfg.months_outside_band_for_miss
            out |= {
                "status": target.band_status(latest, t.band_low_pct, t.band_high_pct),
                "months_outside_band": streak,
                "missed": streak >= threshold if threshold else None,
            }
        return out

    def cores_section(self) -> dict[str, Any]:
        members = {}
        for sid in self.cfg.core_series_ids(self.code):
            if sid in self.catalog.index:
                members[sid] = self.yoy_from_mom(sid)
        if not members:
            return {"available": False}
        summary = cores.core_summary(pd.DataFrame(members))
        summary = summary[summary.index >= self.start]
        return {
            "available": True,
            "members": [
                {"series_id": sid, "label": self.label(sid), "latest_pct": _r(s.iloc[-1])}
                for sid, s in members.items()
            ],
            "periods": list(summary.index),
            "mean_pct": [_r(v) for v in summary["mean_pct"]],
            "min_pct": [_r(v) for v in summary["min_pct"]],
            "max_pct": [_r(v) for v in summary["max_pct"]],
            "latest_mean_pct": _r(summary["mean_pct"].iloc[-1]),
            "latest_period": summary.index[-1],
            "method_note": "12-month rates compounded from the BCB's monthly core series",
        }

    def components(self, parent_id: str, concept: str) -> pd.DataFrame:
        ids = self.catalog.index[
            (self.catalog["parent_id"] == parent_id) & (self.catalog["concept"] == concept)
        ]
        if concept == "item":
            ids = self.catalog.index[
                (self.catalog["concept"] == "item")
                & (self.catalog["indicator"] == self.indicator(parent_id))
            ]
        return pd.DataFrame(index=ids)

    def drivers_section(self, headline_id: str) -> dict[str, Any]:
        head_mom = _series(self.obs, headline_id, "mom_pct")
        period = head_mom.index.max()

        def wide(ids: pd.Index, unit: str) -> pd.DataFrame:
            sub = self.obs[self.obs["series_id"].isin(ids) & (self.obs["unit"] == unit)]
            return sub.pivot_table(index="period", columns="series_id", values="value").sort_index()

        groups = self.components(headline_id, "group").index
        g_mom, g_w = wide(groups, "mom_pct"), wide(groups, "weight_pct")
        g_c = contributions.monthly_pp(g_w, g_mom)
        latest = g_c.loc[period].sort_values(ascending=False)
        group_rows = [
            {
                "series_id": sid,
                "label": self.label(sid),
                "contribution_pp": _r(latest[sid]),
                "mom_pct": _r(g_mom.loc[period, sid]),
                "weight_pct": _r(g_w.loc[period, sid]),
            }
            for sid in latest.index
        ]

        items = self.components(headline_id, "item").index
        i_c = contributions.monthly_pp(wide(items, "weight_pct"), wide(items, "mom_pct"))
        i_mom = wide(items, "mom_pct")
        up, down = (
            contributions.top_movers(i_c.loc[period], TOP_N)
            if period in i_c.index
            else (pd.Series(), pd.Series())
        )

        def item_rows(s: pd.Series) -> list[dict[str, Any]]:
            return [
                {
                    "series_id": sid,
                    "label": self.label(sid),
                    "contribution_pp": _r(v),
                    "mom_pct": _r(i_mom.loc[period, sid]),
                }
                for sid, v in s.items()
            ]

        c12 = contributions.twelve_month_pp(g_c, head_mom)
        c12 = c12[c12.index >= self.start]
        yoy = _series(self.obs, headline_id, "yoy_pct").reindex(c12.index)
        return {
            "period": period,
            "groups": group_rows,
            "sum_pp": _r(latest.sum()),
            "headline_mom_pct": _r(head_mom[period]),
            "top_up": item_rows(up),
            "top_down": item_rows(down),
            "twelve_month": {
                "periods": list(c12.index),
                "series": [
                    {
                        "series_id": sid,
                        "label": self.label(sid),
                        "values_pp": [_r(v) for v in c12[sid]],
                    }
                    for sid in c12.columns
                ],
                "headline_yoy_pct": [_r(v) for v in yoy],
                "rounding_pp": [_r(v) for v in (yoy - c12.sum(axis=1))],
            },
        }

    def panel(self, ids: tuple[str, ...]) -> dict[str, Any]:
        series = []
        for sid in ids:
            if sid not in self.catalog.index:
                continue
            s = self.yoy_from_mom(sid)
            series.append({"series_id": sid, "label": self.label(sid), **_points(s, self.start)})
        return {"series": series}

    def diffusion_section(self) -> dict[str, Any] | None:
        sid = self.cfg.series.diffusion
        if not sid:
            return None
        s = _series(self.obs, sid, "share_pct")
        return (
            {"series_id": sid, "label": self.label(sid), **_points(s, self.start)}
            if len(s)
            else None
        )

    def momentum_section(self, headline_id: str) -> dict[str, Any]:
        index = _series(self.obs, headline_id, "index")
        yoy = _series(self.obs, headline_id, "yoy_pct")
        mom = _series(self.obs, headline_id, "mom_pct")
        out: dict[str, Any] = {
            "same_month": momentum.same_month_history(mom, mom.index.max(), SAME_MONTH_YEARS),
        }
        est_start = f"{self.cfg.chart_start_year - SA_ESTIMATION_YEARS}-01"
        try:
            if index.empty:
                raise SeasonalAdjustmentUnavailable("no index number published for this series")
            sa = seasonally_adjust(index[index.index >= est_start])
        except SeasonalAdjustmentUnavailable as exc:
            out["saar"] = {"available": False, "reason": str(exc)}
            return out
        saar3, saar6 = momentum.saar_pct(sa, 3), momentum.saar_pct(sa, 6)
        periods = [p for p in saar3.index if p >= self.start]
        out["saar"] = {
            "available": True,
            "method": "X-13ARIMA-SEATS (US Census Bureau), log, automatic model, outliers",
            "periods": periods,
            "saar3_pct": [_r(saar3[p]) for p in periods],
            "saar6_pct": [_r(saar6.get(p)) for p in periods],
            "yoy_pct": [_r(yoy.get(p)) for p in periods],
            "revisable_from": sa.index[-REVISABLE_MONTHS],
        }
        return out

    def base_effects_section(self, headline: dict[str, Any]) -> dict[str, Any]:
        sid = headline["series_id"]
        mom = _series(self.obs, sid, "mom_pct")
        period = headline["reference_period"]
        leaving = base_effects.dropping_out(mom, period, 3)
        next_period = str(leaving[0]["period"])
        leaving_mom = leaving[0]["leaving_mom_pct"]
        # Any survey up to today counts: the next release hasn't happened yet.
        tomorrow = (self.now + pd.Timedelta(days=1)).date()
        expected = self.expectation(headline["indicator"], next_period, "mom_pct", tomorrow)
        implied = None
        if expected and headline["yoy_pct"] is not None and isinstance(leaving_mom, float):
            implied = _r(
                base_effects.implied_next_yoy_pct(
                    headline["yoy_pct"], leaving_mom, expected["median_pct"]
                )
            )
        return {"dropping_out": leaving, "next_expected": expected, "implied_next_yoy_pct": implied}

    def policy_section(self) -> dict[str, Any]:
        daily = self.data.daily
        out: dict[str, Any] = {}
        exp = self.data.expectations
        primary = self.cfg.primary_expectation_source
        e12 = exp[
            (exp["measure"] == "next_12m_pct")
            & (exp["statistic"] == "median")
            & (exp["source"] == primary)
        ]
        e12 = e12.sort_values("survey_date")
        if self.cfg.series.policy_rate:
            rate = daily[daily["series_id"] == self.cfg.series.policy_rate].sort_values("date")
            if len(rate):
                last = rate.iloc[-1]
                out["policy_rate"] = {
                    "label": self.label(self.cfg.series.policy_rate),
                    "date": str(last["date"]),
                    "rate_pct": _r(last["value"]),
                }
                monthly = (
                    rate.assign(period=rate["date"].map(lambda d: d.strftime("%Y-%m")))
                    .groupby("period")["value"]
                    .last()
                )
                out["policy_rate"]["history"] = _points(monthly, self.start)
                if len(e12):
                    exp_m = (
                        e12.assign(period=e12["survey_date"].map(lambda d: d.strftime("%Y-%m")))
                        .groupby("period")["value"]
                        .last()
                    )
                    joined = pd.concat([monthly, exp_m], axis=1, keys=["i", "pi"]).dropna()
                    real = pd.Series(
                        [
                            real_rate.ex_ante_real_pct(i, p)
                            for i, p in zip(joined["i"], joined["pi"], strict=True)
                        ],
                        index=joined.index,
                    )
                    le = e12.iloc[-1]
                    out["real_ex_ante"] = {
                        "rate_pct": _r(
                            real_rate.ex_ante_real_pct(float(last["value"]), float(le["value"]))
                        ),
                        "expected_inflation_pct": _r(le["value"]),
                        "survey_date": str(le["survey_date"]),
                        "history": _points(real, self.start),
                    }
        if len(e12):
            out["expectations_12m"] = {
                "source": primary,
                **_points(
                    e12.assign(period=e12["survey_date"].map(lambda d: d.strftime("%Y-%m")))
                    .groupby("period")["value"]
                    .last(),
                    self.start,
                ),
            }
        year_end = exp[
            (exp["measure"] == "year_end_pct")
            & (exp["statistic"] == "median")
            & (exp["source"] == primary)
        ]
        years = []
        for year in (self.now.year, self.now.year + 1):
            rows = year_end[year_end["reference_period"] == f"{year}-12"].sort_values("survey_date")
            if len(rows):
                years.append(
                    {
                        "year": year,
                        "median_pct": _r(rows.iloc[-1]["value"]),
                        "survey_date": str(rows.iloc[-1]["survey_date"]),
                    }
                )
        out["year_end_expectations"] = years
        if self.cfg.series.fx:
            fx = (
                daily[daily["series_id"] == self.cfg.series.fx]
                .sort_values("date")
                .set_index("date")["value"]
            )
            if len(fx):
                last_day = fx.index[-1]
                year_ago = fx[fx.index <= last_day.replace(year=last_day.year - 1)]
                monthly = fx.groupby([d.strftime("%Y-%m") for d in fx.index]).mean()
                out["fx"] = {
                    "label": self.label(self.cfg.series.fx),
                    "date": str(last_day),
                    "value": _r(fx.iloc[-1]),
                    "yoy_pct": _r((fx.iloc[-1] / year_ago.iloc[-1] - 1) * 100)
                    if len(year_ago)
                    else None,
                    "monthly_average": _points(monthly, self.start),
                }
        return out

    def build(self) -> dict[str, Any]:
        hid = self.cfg.series.headline
        headline = self.headline_release(hid)
        yoy = _series(self.obs, hid, "yoy_pct")
        core = self.cores_section()
        drivers = self.drivers_section(hid)
        top = drivers["top_up"][0] if drivers["top_up"] else None
        out: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "sample": False,
            "generated_at_utc": self.now.isoformat(),
            "country": {
                "code": self.code,
                "name": {"en": self.cfg.name.en, "pt-BR": self.cfg.name.pt_BR},
                "default_locale": self.cfg.default_locale,
                "color_token": self.cfg.color_token,
                "currency": self.cfg.currency,
            },
            "headline": headline,
            "preview": self.headline_release(self.cfg.series.preview)
            if self.cfg.series.preview
            else None,
            "target": self.target_section(yoy),
            "summary": {
                "period": headline["reference_period"],
                "mom_pct": headline["mom_pct"],
                "top_driver": top,
                "all_groups_rose": all(g["mom_pct"] > 0 for g in drivers["groups"]),
            },
            "core": core,
            "drivers": drivers,
            "trend": {
                "panels": {name: self.panel(ids) for name, ids in self.cfg.panels.items()},
                "diffusion": self.diffusion_section(),
            },
            "momentum": self.momentum_section(hid),
            "base_effects": self.base_effects_section(headline),
            "policy": self.policy_section(),
            "history": {
                "headline_yoy": _points(yoy, self.start),
                "core_mean_yoy": {
                    "periods": core.get("periods", []),
                    "values": core.get("mean_pct", []),
                },
            },
            "validation": {
                "passed": self.report.passed,
                "checked_at_utc": self.report.created_at_utc.isoformat(),
                "checks": [{"name": c.name, "passed": c.passed} for c in self.report.checks],
            },
        }
        return out


def overview(
    countries: list[dict[str, Any]], site_default_locale: str, now: datetime
) -> dict[str, Any]:
    cards, feed = [], []
    for c in countries:
        h = c["headline"]
        cards.append(
            {
                "code": c["country"]["code"],
                "name": c["country"]["name"],
                "default_locale": c["country"]["default_locale"],
                "color_token": c["country"]["color_token"],
                "indicator": h["indicator"],
                "reference_period": h["reference_period"],
                "headline_yoy_pct": h["yoy_pct"],
                "headline_mom_pct": h["mom_pct"],
                "core_yoy_pct": c["core"].get("latest_mean_pct"),
                "target_status": c["target"]["status"],
                "last_release_date": h["release_date"],
                "next_release_utc": h["next_release"]["scheduled_utc"]
                if h["next_release"]
                else None,
            }
        )
        for rel in (h, c["preview"]):
            if rel and rel["release_date"]:
                feed.append(
                    {
                        "country": c["country"]["code"],
                        "indicator": rel["indicator"],
                        "reference_period": rel["reference_period"],
                        "released_utc": rel["release_date"],
                        "mom_pct": rel["mom_pct"],
                    }
                )
    feed.sort(key=lambda r: r["released_utc"], reverse=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "sample": False,
        "generated_at_utc": now.isoformat(),
        "site": {"default_locale": site_default_locale},
        "countries": cards,
        "latest_releases": feed,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), "utf-8"
    )


def now_utc() -> datetime:
    return datetime.now(UTC)
