"""Turn Brazil's raw responses into the common model.

Basket eras (structural breaks), see NOTES.md:
- Table 1419 covers Jan 2012–Dec 2019 (POF 2008–2009 basket).
- Table 7060 covers Jan 2020 onward (POF 2017–2018 basket).
- Table 1737 has the headline back to 1979 plus the index number.
Where tables overlap we keep the most detailed one (7060, then 1419, then 1737). The
overlap itself is checked in checks.py, so a disagreement between tables is reported.

Series identity across eras uses IBGE's hierarchical code ("1" group, "11" subgroup,
"1101" item, "1101002" subitem). The 9 group codes are the same in both baskets; lower
levels can start or end at a basket change, which `first_period`/`last_period` record.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path

import pandas as pd

from inflation.countries.base import Normalized
from inflation.countries.br import sgs, sidra
from inflation.countries.br.adapter import SIDRA_TABLES
from inflation.countries.br.ibge_calendar import release_id
from inflation.frames import (
    DAILY_COLUMNS,
    EXPECTATION_COLUMNS,
    OBSERVATION_COLUMNS,
    OBSERVATION_KEY,
    SERIES_COLUMNS,
)
from inflation.raw import RawStore

LEVEL_NAMES = {1: "group", 2: "subgroup", 3: "item", 4: "subitem"}
TABLE_PRIORITY = {7060: 0, 1419: 1, 7062: 0, 1737: 2}
UNIT_BY_TABLE_VARIABLE = {
    (spec.table, str(var)): unit for spec in SIDRA_TABLES for var, unit in spec.variables.items()
}
INDICATOR_BY_TABLE = {spec.table: spec.indicator for spec in SIDRA_TABLES}

FOCUS_SOURCE = {0: "bcb_focus_30d", 1: "bcb_focus_5d"}


def _rel(raw: RawStore, path: Path) -> str:
    return path.relative_to(raw.root).as_posix()


def sidra_frame(raw: RawStore) -> pd.DataFrame:
    """Every SIDRA value in the raw files, one row each, before choosing between tables."""
    frames = []
    for path in raw.files("sidra/*_v*_*.json"):
        table = int(path.name.split("_")[0])
        body = raw.read_json(path)
        assert isinstance(body, list)
        values = sidra.parse_values(table, body)
        df = pd.DataFrame([v.__dict__ for v in values])
        if df.empty:
            continue
        df["fetched_at_utc"] = raw.fetched_at(_rel(raw, path))
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["fetched_at_utc"] = pd.to_datetime(df["fetched_at_utc"], utc=True)
    df["unit"] = [
        UNIT_BY_TABLE_VARIABLE[(t, v)] for t, v in zip(df["table"], df["variable"], strict=True)
    ]
    df["indicator"] = df["table"].map(INDICATOR_BY_TABLE)
    # Re-fetches overwrite whole files, but a file from an older fetch with a different
    # window could still overlap; keep the most recently fetched value.
    df = df.sort_values("fetched_at_utc").drop_duplicates(
        ["table", "variable", "period", "category"], keep="last"
    )
    return df.reset_index(drop=True)


def _codes(df: pd.DataFrame) -> pd.DataFrame:
    is_headline = df["category"].isna() | (df["category"] == sidra.GENERAL_INDEX_CATEGORY)
    split = [
        ("", "") if headline else sidra.split_code(str(name))
        for headline, name in zip(is_headline, df["category_name"], strict=True)
    ]
    df = df.assign(code=[c for c, _ in split], name=[n for _, n in split])
    df["level"] = [sidra.level_of(code) for code in df["code"]]
    return df


def _series_id(indicator: str, level: int, code: str, groups: dict[tuple[str, str], str]) -> str:
    prefix = f"br.{indicator.lower()}"
    if level == 0:
        return f"{prefix}.headline"
    if level == 1:
        return groups[(indicator, code)]
    return f"{prefix}.{LEVEL_NAMES[level]}.{code}"


def _sidra_observations(
    raw: RawStore, catalog: list[dict[str, str]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = _codes(sidra_frame(raw))
    df = df[df["value"].notna()]
    groups = {
        (row["indicator"], row["source_code"]): row["series_id"]
        for row in catalog
        if row["concept"] == "group"
    }
    df["series_id"] = [
        _series_id(ind, lvl, code, groups)
        for ind, lvl, code in zip(df["indicator"], df["level"], df["code"], strict=True)
    ]
    df["priority"] = df["table"].map(TABLE_PRIORITY)
    df = df.sort_values(["priority", "period"]).drop_duplicates(OBSERVATION_KEY, keep="first")
    df["release_id"] = [
        release_id(i, p) for i, p in zip(df["indicator"], df["period"], strict=True)
    ]
    return df[OBSERVATION_COLUMNS].reset_index(drop=True), df


def _generated_series(detail: pd.DataFrame, catalog: list[dict[str, str]]) -> pd.DataFrame:
    """Catalog rows for subgroups, items and subitems, built from IBGE's classification."""
    known = {row["series_id"] for row in catalog}
    lower = detail[~detail["series_id"].isin(known)]
    # Label from the newest basket in which the series appears.
    latest = lower.sort_values("period").groupby("series_id").tail(1).set_index("series_id")
    units = lower.groupby("series_id")["unit"].agg(lambda u: "|".join(sorted(set(u))))
    rows = []
    for series_id, row in latest.iterrows():
        level, code, indicator = int(row["level"]), str(row["code"]), str(row["indicator"])
        parent_code = {2: code[:1], 3: code[:2], 4: code[:4]}[level]
        parent_level = level - 1
        rows.append(
            {
                "series_id": series_id,
                "country": "br",
                "indicator": indicator,
                "concept": LEVEL_NAMES[level],
                "parent_id": _series_id(
                    indicator,
                    parent_level,
                    parent_code,
                    {
                        (r["indicator"], r["source_code"]): r["series_id"]
                        for r in catalog
                        if r["concept"] == "group"
                    },
                ),
                "level": level,
                # English labels for items are added in Part B (item_labels.csv); until
                # then the Portuguese name is used in both languages.
                "label_en": row["name"],
                "label_pt": row["name"],
                "source": "ibge_sidra",
                "source_code": code,
                "unit": units[series_id],
                "frequency": "monthly",
                "adjustment": "nsa",
            }
        )
    return pd.DataFrame(rows)


def _sgs(raw: RawStore, catalog: list[dict[str, str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_code = {int(r["source_code"]): r for r in catalog if r["source"] == "bcb_sgs"}
    monthly, daily = [], []
    for path in raw.files("sgs/*.json"):
        code = int(path.name.split("_")[0])
        row = by_code.get(code)
        if row is None:
            continue  # a series that was dropped from the catalog
        fetched = raw.fetched_at(_rel(raw, path))
        body = raw.read_json(path)
        assert isinstance(body, list)
        for value in sgs.parse(code, body, as_of=fetched.date()):
            record = {
                "series_id": row["series_id"],
                "value": value.value,
                "unit": row["unit"],
                "fetched_at_utc": fetched,
            }
            if row["frequency"] == "daily":
                daily.append({**record, "date": value.date})
            else:
                period = value.date.strftime("%Y-%m")
                monthly.append(
                    {**record, "period": period, "release_id": release_id(row["indicator"], period)}
                )
    obs = pd.DataFrame(monthly, columns=OBSERVATION_COLUMNS)
    day = pd.DataFrame(daily, columns=DAILY_COLUMNS)
    for df, key in ((obs, OBSERVATION_KEY), (day, ["series_id", "date"])):
        if not df.empty:
            df["fetched_at_utc"] = pd.to_datetime(df["fetched_at_utc"], utc=True)
            df.sort_values("fetched_at_utc", inplace=True)
            df.drop_duplicates(key, keep="last", inplace=True)
    return obs.reset_index(drop=True), day.reset_index(drop=True)


def _focus_rows(entity: str, item: dict[str, object]) -> Iterable[dict[str, object]]:
    survey = date.fromisoformat(str(item["Data"]))
    if entity.startswith("ExpectativaMercadoMensais"):
        month, year = str(item["DataReferencia"]).split("/")
        measure, period = "mom_pct", f"{year}-{month}"
    elif entity.startswith("ExpectativasMercadoInflacao12Meses"):
        # Use the smoothed series, as the BCB does for its own ex-ante real rate.
        if item.get("Suavizada") != "S":
            return
        measure, period = "next_12m_pct", survey.strftime("%Y-%m")
    else:
        measure, period = "year_end_pct", f"{item['DataReferencia']}-12"
    base = int(str(item["baseCalculo"]))
    for statistic, field in (("median", "Mediana"), ("mean", "Media")):
        if item.get(field) is None:
            continue
        yield {
            "country": "br",
            "indicator": "IPCA",
            "reference_period": period,
            "measure": measure,
            "statistic": statistic,
            "value": float(str(item[field])),
            "n_respondents": item.get("numeroRespondentes"),
            "source": FOCUS_SOURCE[base],
            "survey_date": survey,
        }


def _focus(raw: RawStore) -> pd.DataFrame:
    rows = []
    for path in raw.files("focus/*.json"):
        entity = path.name.split("_")[0]
        fetched = raw.fetched_at(_rel(raw, path))
        body = raw.read_json(path)
        assert isinstance(body, dict)
        for item in body["value"]:
            for row in _focus_rows(entity, item):
                rows.append({**row, "captured_at_utc": fetched})
    df = pd.DataFrame(rows, columns=EXPECTATION_COLUMNS)
    if df.empty:
        return df
    df["captured_at_utc"] = pd.to_datetime(df["captured_at_utc"], utc=True)
    df["n_respondents"] = df["n_respondents"].astype("Int64")
    key = ["indicator", "reference_period", "measure", "statistic", "source", "survey_date"]
    return (
        df.sort_values("captured_at_utc").drop_duplicates(key, keep="last").reset_index(drop=True)
    )


def normalize(raw: RawStore, catalog: list[dict[str, str]]) -> Normalized:
    sidra_obs, detail = _sidra_observations(raw, catalog)
    sgs_obs, daily = _sgs(raw, catalog)
    observations = pd.concat([sidra_obs, sgs_obs], ignore_index=True).astype({"value": float})
    observations["fetched_at_utc"] = pd.to_datetime(observations["fetched_at_utc"], utc=True)
    daily = daily.astype({"value": float})
    daily["fetched_at_utc"] = pd.to_datetime(daily["fetched_at_utc"], utc=True)

    series = pd.concat(
        [pd.DataFrame(catalog), _generated_series(detail, catalog)], ignore_index=True
    )
    span = pd.concat(
        [
            observations.groupby("series_id")["period"].agg(["min", "max"]),
            daily.assign(period=daily["date"].map(lambda d: d.strftime("%Y-%m")))
            .groupby("series_id")["period"]
            .agg(["min", "max"]),
        ]
    )
    series["first_period"] = series["series_id"].map(span["min"])
    series["last_period"] = series["series_id"].map(span["max"])
    series["level"] = series["level"].astype(int)
    series = series.astype({"parent_id": "string"})
    return Normalized(
        series=series[SERIES_COLUMNS],
        observations=observations,
        daily=daily,
        expectations=_focus(raw),
    )
