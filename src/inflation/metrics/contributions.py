"""What drove the headline? Contributions in percentage points (docs/methodology.md §Contributions).

A component's contribution is its weight times its own change: a group with a 20% weight
whose prices rose 1% added 0.20 pp to the headline. Monthly contributions add up to the
headline monthly change (up to the agency's rounding).

Over 12 months, contributions must account for compounding. With headline monthly rates
h and component contributions c (as decimals), the 12-month rate is

    Y = Π(1 + h_s) − 1 = Σ_s h_s · Π_{k<s}(1 + h_k)

so component i's share of Y is Σ_s c_{i,s} · Π_{k<s}(1 + h_k): each month's contribution
scaled by how much prices had already risen earlier in the window. These add up exactly to Y
when the monthly contributions add up to h; any gap is the agency's rounding, which we
report as a separate "rounding" residual rather than hiding it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def monthly_pp(weight_pct: pd.DataFrame, mom_pct: pd.DataFrame) -> pd.DataFrame:
    """Contribution of each component (columns) in each month (rows), in pp."""
    return weight_pct * mom_pct / 100


def twelve_month_pp(contrib_pp: pd.DataFrame, headline_mom_pct: pd.Series) -> pd.DataFrame:
    """Chain-linked contributions to the 12-month rate, for every month with a full window."""
    contrib_pp = contrib_pp.sort_index()
    headline = headline_mom_pct.reindex(contrib_pp.index)
    rows = {}
    for end in range(11, len(contrib_pp)):
        window = slice(end - 11, end + 1)
        h = headline.iloc[window].to_numpy() / 100
        # Growth already accumulated before each month in the window: 1, (1+h₁), (1+h₁)(1+h₂)…
        carried = np.concatenate([[1.0], np.cumprod(1 + h)[:-1]])
        c = contrib_pp.iloc[window]
        if c.isna().any().any() or np.isnan(h).any():
            continue
        rows[contrib_pp.index[end]] = (c.to_numpy() * carried[:, None]).sum(axis=0)
    return pd.DataFrame.from_dict(rows, orient="index", columns=contrib_pp.columns)


def top_movers(contrib_pp: pd.Series, n: int) -> tuple[pd.Series, pd.Series]:
    """The n largest positive and n largest negative contributions for one month."""
    contrib_pp = contrib_pp.dropna()
    up = contrib_pp[contrib_pp > 0].sort_values(ascending=False).head(n)
    down = contrib_pp[contrib_pp < 0].sort_values().head(n)
    return up, down
