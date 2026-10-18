from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from inflation.countries.base import Normalized
from inflation.frames import (
    DAILY_COLUMNS,
    EXPECTATION_COLUMNS,
    OBSERVATION_COLUMNS,
    SERIES_COLUMNS,
    SchemaError,
    check_observations,
)
from inflation.store import Store
from inflation.validate import generic_checks

FETCHED = pd.Timestamp("2026-01-01", tz="UTC")


def _obs(rows: list[tuple[str, str, float, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "series_id": s,
                "period": p,
                "value": v,
                "unit": u,
                "release_id": "r",
                "fetched_at_utc": FETCHED,
            }
            for s, p, v, u in rows
        ],
        columns=OBSERVATION_COLUMNS,
    )


def _data(obs: pd.DataFrame) -> Normalized:
    series = pd.DataFrame(
        [
            {c: None for c in SERIES_COLUMNS}
            | {"series_id": "xx.cpi.headline", "concept": "headline"}
        ],
        columns=SERIES_COLUMNS,
    )
    return Normalized(
        series=series,
        observations=obs,
        daily=pd.DataFrame(columns=DAILY_COLUMNS),
        expectations=pd.DataFrame(columns=EXPECTATION_COLUMNS),
    )


def test_schema_rejects_unknown_unit_and_duplicates() -> None:
    obs = _obs(
        [
            ("xx.cpi.headline", "2026-01", 1.0, "percent"),
            ("xx.cpi.headline", "2026-01", 1.0, "percent"),
        ]
    )
    with pytest.raises(SchemaError, match="unknown units"):
        check_observations(obs)


def test_gap_in_headline_fails() -> None:
    obs = _obs(
        [
            ("xx.cpi.headline", "2026-01", 0.1, "mom_pct"),
            ("xx.cpi.headline", "2026-03", 0.2, "mom_pct"),
        ]
    )
    results = {c.name: c for c in generic_checks(_data(obs))}
    assert not results["xx.cpi.headline_no_gaps"].passed
    assert "2026-02" in results["xx.cpi.headline_no_gaps"].detail


def test_store_merges_partitions_and_keeps_first_vintage(tmp_path: Path) -> None:
    store = Store("xx", tmp_path)
    store.write(_data(_obs([("xx.cpi.headline", "2026-01", 0.1, "mom_pct")])))
    store.write(
        _data(
            _obs(
                [
                    ("xx.cpi.headline", "2026-01", 0.2, "mom_pct"),
                    ("xx.cpi.headline", "2026-02", 0.3, "mom_pct"),
                ]
            )
        )
    )
    back = store.read().observations.set_index("period")["value"]
    assert back.to_dict() == {"2026-01": 0.2, "2026-02": 0.3}  # revision replaced, new month added

    assert store.write_vintage("xx-cpi-2026-01", {"mom_pct": 0.1, "date": date(2026, 2, 10)})
    assert not store.write_vintage("xx-cpi-2026-01", {"mom_pct": 0.2})
    assert store.vintages()["xx-cpi-2026-01"]["mom_pct"] == 0.1
