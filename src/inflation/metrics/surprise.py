"""Was the release more or less than expected? (docs/methodology.md §Surprise)

The expectation for a release is the latest survey published *before* release day, so
the comparison only uses what was known in advance. Surprise = actual − expected, in pp.
"""

from __future__ import annotations

from datetime import date

import pandas as pd


def expectation_before(
    expectations: pd.DataFrame,
    indicator: str,
    reference_period: str,
    measure: str,
    source: str,
    release_date: date,
    statistic: str = "median",
) -> pd.Series | None:
    """The latest matching survey row dated before `release_date`, or None if there is none."""
    rows = expectations[
        (expectations["indicator"] == indicator)
        & (expectations["reference_period"] == reference_period)
        & (expectations["measure"] == measure)
        & (expectations["source"] == source)
        & (expectations["statistic"] == statistic)
        & (expectations["survey_date"] < release_date)
    ]
    if rows.empty:
        return None
    return rows.sort_values("survey_date").iloc[-1]


def surprise_pp(actual_pct: float, expected_pct: float) -> float:
    return actual_pct - expected_pct
