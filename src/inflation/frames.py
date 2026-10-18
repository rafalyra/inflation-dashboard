"""Tabular versions of the common data model.

A full backfill has hundreds of thousands of observations, so the pipeline passes pandas
DataFrames whose columns are exactly the fields of the pydantic models in `models.py`.
`check_*` functions enforce the same rules as the models, vectorized.
"""

from __future__ import annotations

import pandas as pd

from inflation.models import UNITS, DailyObservation, Expectation, Observation, Series

SERIES_COLUMNS = list(Series.model_fields)
OBSERVATION_COLUMNS = list(Observation.model_fields)
DAILY_COLUMNS = list(DailyObservation.model_fields)
EXPECTATION_COLUMNS = list(Expectation.model_fields)

OBSERVATION_KEY = ["series_id", "period", "unit"]

_PERIOD = r"^\d{4}-(0[1-9]|1[0-2])$"


class SchemaError(ValueError):
    pass


def check_observations(df: pd.DataFrame) -> None:
    """Raise SchemaError if `df` breaks any rule of the Observation model."""
    problems = []
    if list(df.columns) != OBSERVATION_COLUMNS:
        problems.append(f"columns {list(df.columns)} != {OBSERVATION_COLUMNS}")
    else:
        bad_period = ~df["period"].astype(str).str.match(_PERIOD)
        if bad_period.any():
            problems.append(
                f"{bad_period.sum()} bad periods, e.g. {df.loc[bad_period, 'period'].iloc[0]}"
            )
        bad_unit = ~df["unit"].isin(UNITS)
        if bad_unit.any():
            problems.append(f"unknown units {sorted(df.loc[bad_unit, 'unit'].unique())}")
        if df["value"].isna().any():
            problems.append(f"{df['value'].isna().sum()} missing values")
        dupes = df.duplicated(OBSERVATION_KEY)
        if dupes.any():
            problems.append(f"{dupes.sum()} duplicate (series_id, period, unit) rows")
        dtype = df["fetched_at_utc"].dtype
        if len(df) and not (isinstance(dtype, pd.DatetimeTZDtype) and str(dtype.tz) == "UTC"):
            problems.append(f"fetched_at_utc dtype is {dtype}, not UTC timestamps")
    if problems:
        raise SchemaError("; ".join(problems))
