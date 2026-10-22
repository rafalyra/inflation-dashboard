"""How far is inflation from the central bank's target? (docs/methodology.md §Target)"""

from __future__ import annotations

from typing import Literal

import pandas as pd

Status = Literal["above", "inside", "below"]


def band_status(value_pct: float, low_pct: float, high_pct: float) -> Status:
    """Where a 12-month rate sits relative to the tolerance band (edges count as inside)."""
    if value_pct > high_pct:
        return "above"
    if value_pct < low_pct:
        return "below"
    return "inside"


def distance_pp(value_pct: float, target_pct: float) -> float:
    return value_pct - target_pct


def months_outside_band(yoy_pct: pd.Series, low_pct: float, high_pct: float) -> int:
    """Consecutive months, ending with the latest, that the 12-month rate was outside the band.

    Brazil's continuous target (since 2025) counts as missed after 6 such months.
    """
    count = 0
    for value in yoy_pct.sort_index().iloc[::-1]:
        if low_pct <= value <= high_pct:
            break
        count += 1
    return count
