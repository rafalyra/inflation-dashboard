"""Turning monthly changes into 12-month and year-to-date changes (docs/methodology.md §Changes).

Monthly rates compound: two months of +1% is a 2.01% rise, not 2%. So longer-horizon
changes multiply growth factors (1 + m/100) instead of adding percentages.
All series are pandas Series indexed by period strings 'YYYY-MM', in percent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compound_pct(mom_pct: pd.Series) -> float:
    """Total change over the given months: (1+m₁)(1+m₂)…(1+mₙ) − 1, in percent."""
    return float((np.prod(1 + mom_pct.to_numpy() / 100) - 1) * 100)


def rolling_compound_pct(mom_pct: pd.Series, months: int) -> pd.Series:
    """Change over each trailing window of `months` months (12 → the 12-month rate)."""
    growth = np.log1p(mom_pct.sort_index() / 100)
    return (np.expm1(growth.rolling(months).sum()) * 100).dropna()


def change_from_index_pct(index: pd.Series, months: int) -> pd.Series:
    """I_t / I_{t−months} − 1, in percent: the most precise way when an index is published."""
    index = index.sort_index()
    return ((index / index.shift(months) - 1) * 100).dropna()
