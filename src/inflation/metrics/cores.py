"""Average of several core measures (docs/methodology.md §Core).

Each core measure strips out volatile prices in a different way (excluding items, trimming
the extremes, re-weighting by volatility). No single one is "the" trend, so central banks
watch their average, with the spread between them as a sense of uncertainty.
"""

from __future__ import annotations

import pandas as pd


def core_summary(core_yoy_pct: pd.DataFrame) -> pd.DataFrame:
    """Mean, min and max across core measures (columns), only for months where all exist."""
    complete = core_yoy_pct.dropna()
    return pd.DataFrame(
        {
            "mean_pct": complete.mean(axis=1),
            "min_pct": complete.min(axis=1),
            "max_pct": complete.max(axis=1),
        }
    )


def core_mean_mom(core_mom_pct: pd.DataFrame) -> pd.Series:
    """Average monthly change across core measures (columns), for months where all exist.

    Used to build a core index for seasonal adjustment and core momentum.
    """
    return core_mom_pct.dropna().mean(axis=1)
