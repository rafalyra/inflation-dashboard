"""Read and write canonical partitions and vintages (SPEC §4.1, storage).

Layout under `<root>/<country>/`:
  series.parquet                    the catalog, including generated series
  observations/<YYYY-MM>.parquet    one partition per reference month
  daily/<series_id>.parquet         daily context series
  expectations.parquet              survey expectations
  vintages/<release_id>.json        headline numbers as first published (never overwritten)

Phase 1 writes this locally (gitignored). Phase 2 points the same layout at the `data`
branch, where a release only touches the partitions for the months it changed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from inflation.countries.base import Normalized
from inflation.frames import (
    DAILY_COLUMNS,
    EXPECTATION_COLUMNS,
    OBSERVATION_COLUMNS,
    OBSERVATION_KEY,
    SERIES_COLUMNS,
)

DEFAULT_ROOT = Path("data")


class Store:
    def __init__(self, country: str, root: Path = DEFAULT_ROOT) -> None:
        self.dir = root / country

    def write(self, data: Normalized) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        data.series.to_parquet(self.dir / "series.parquet", index=False)
        data.expectations.to_parquet(self.dir / "expectations.parquet", index=False)
        self._write_observations(data.observations)
        self._write_daily(data.daily)

    def _write_observations(self, obs: pd.DataFrame) -> None:
        part_dir = self.dir / "observations"
        part_dir.mkdir(parents=True, exist_ok=True)
        for period, new in obs.groupby("period"):
            path = part_dir / f"{period}.parquet"
            if path.exists():
                # Merge: rows for the same (series, period, unit) are replaced by the new
                # value; series not in this write keep their stored values.
                old = pd.read_parquet(path)
                new = pd.concat([old, new]).drop_duplicates(OBSERVATION_KEY, keep="last")
            new.sort_values(OBSERVATION_KEY).to_parquet(path, index=False)

    def _write_daily(self, daily: pd.DataFrame) -> None:
        part_dir = self.dir / "daily"
        part_dir.mkdir(parents=True, exist_ok=True)
        for series_id, new in daily.groupby("series_id"):
            path = part_dir / f"{series_id}.parquet"
            if path.exists():
                old = pd.read_parquet(path)
                new = pd.concat([old, new]).drop_duplicates(["series_id", "date"], keep="last")
            new.sort_values("date").to_parquet(path, index=False)

    def read(self) -> Normalized:
        def read_dir(sub: str, columns: list[str]) -> pd.DataFrame:
            parts = sorted((self.dir / sub).glob("*.parquet"))
            if not parts:
                return pd.DataFrame(columns=columns)
            return pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)

        return Normalized(
            series=pd.read_parquet(self.dir / "series.parquet")[SERIES_COLUMNS],
            observations=read_dir("observations", OBSERVATION_COLUMNS)[OBSERVATION_COLUMNS],
            daily=read_dir("daily", DAILY_COLUMNS)[DAILY_COLUMNS],
            expectations=pd.read_parquet(self.dir / "expectations.parquet")[EXPECTATION_COLUMNS],
        )

    def write_vintage(self, release_id: str, values: dict[str, object]) -> bool:
        """Freeze a release's headline numbers as first published. Returns False if the
        vintage already exists: a vintage is never overwritten, so revisions stay visible."""
        path = self.dir / "vintages" / f"{release_id}.json"
        if path.exists():
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values, indent=1, default=str), "utf-8")
        return True

    def vintages(self) -> dict[str, dict[str, object]]:
        out = {}
        for path in sorted((self.dir / "vintages").glob("*.json")):
            out[path.stem] = json.loads(path.read_text("utf-8"))
        return out
