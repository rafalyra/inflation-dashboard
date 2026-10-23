"""The BCB's segments of the IPCA (food at home, industrial goods, services, administered),
built from IBGE subitems with the BCB's own classification (bcb_classification.csv).

Each segment's monthly change is the weight-averaged change of its subitems; its weight is
the sum of their weights. This is how the BCB itself aggregates, and a validation check
compares the result with the series it publishes in SGS (see checks.py).

The classification file covers the POF 2017–2018 basket, so segments start in January 2020.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from inflation.frames import OBSERVATION_COLUMNS

CLASSIFICATION_PATH = Path(__file__).with_name("bcb_classification.csv")
FIRST_PERIOD = "2020-01"
SEGMENT_IDS = {
    "food": "br.ipca.bcb.food",
    "industrial": "br.ipca.bcb.industrial",
    "services": "br.ipca.bcb.services",
    "administered": "br.ipca.bcb.administered",
}


def load_rules() -> dict[str, str]:
    with CLASSIFICATION_PATH.open(encoding="utf-8", newline="") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return {row["code"]: row["category"] for row in rows}


def classify(code: str, rules: dict[str, str]) -> str:
    """The rule with the longest matching code prefix wins; unmatched subitems are industrial
    goods (the BCB defines that segment as what remains of free prices)."""
    matches = [prefix for prefix in rules if code.startswith(prefix)]
    return rules[max(matches, key=len)] if matches else "industrial"


def segment_observations(sidra_obs: pd.DataFrame) -> pd.DataFrame:
    """Monthly change and weight of each segment, as observations in the common model."""
    rules = load_rules()
    sub = sidra_obs[
        sidra_obs["series_id"].str.startswith("br.ipca.subitem.")
        & (sidra_obs["period"] >= FIRST_PERIOD)
    ]
    if sub.empty:
        return pd.DataFrame(columns=OBSERVATION_COLUMNS)
    weight = sub[sub["unit"] == "weight_pct"].pivot_table(
        index="period", columns="series_id", values="value"
    )
    change = sub[sub["unit"] == "mom_pct"].pivot_table(
        index="period", columns="series_id", values="value"
    )
    weight, change = weight.align(change, join="inner")
    segment = pd.Series({sid: classify(sid.rsplit(".", 1)[-1], rules) for sid in weight.columns})

    meta = sub.groupby("period").agg(
        release_id=("release_id", "first"), fetched_at_utc=("fetched_at_utc", "max")
    )
    rows = []
    for name, series_id in SEGMENT_IDS.items():
        cols = segment.index[segment == name]
        w = weight[cols].where(change[cols].notna())
        seg_weight = w.sum(axis=1)
        seg_change = (w * change[cols]).sum(axis=1) / seg_weight
        for period in weight.index:
            for unit, value in (
                ("weight_pct", seg_weight[period]),
                ("mom_pct", seg_change[period]),
            ):
                rows.append(
                    {
                        "series_id": series_id,
                        "period": period,
                        "value": float(value),
                        "unit": unit,
                        "release_id": meta.loc[period, "release_id"],
                        "fetched_at_utc": meta.loc[period, "fetched_at_utc"],
                    }
                )
    return pd.DataFrame(rows, columns=OBSERVATION_COLUMNS)
