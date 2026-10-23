"""Is inflation speeding up or slowing down? (docs/methodology.md §Momentum)

The 12-month rate is slow to turn: it averages a whole year. Annualizing the last 3 or 6
months of a seasonally adjusted index shows a turning point earlier. The price is noise,
which is why we show 3- and 6-month rates side by side with the 12-month rate.
"""

from __future__ import annotations

import pandas as pd


def saar_pct(sa_index: pd.Series, months: int) -> pd.Series:
    """Seasonally adjusted annualized rate over `months`: (I_t / I_{t−k})^(12/k) − 1, in %."""
    sa_index = sa_index.sort_index()
    return (((sa_index / sa_index.shift(months)) ** (12 / months) - 1) * 100).dropna()


def same_month_history(mom_pct: pd.Series, period: str, years: int) -> dict[str, object]:
    """This month's change next to the same calendar month in earlier years.

    Seasonality means a 0.8% September isn't comparable with a 0.8% January; comparing
    with past Septembers shows whether this one is unusual for the time of year.
    """
    month = period[5:]
    past = mom_pct[(mom_pct.index.str[5:] == month) & (mom_pct.index < period)].sort_index()
    past = past.iloc[-years:]
    return {
        "period": period,
        "value_pct": float(mom_pct[period]),
        "years": [p[:4] for p in past.index],
        "past_pct": [float(v) for v in past],
        "median_pct": float(past.median()) if len(past) else None,
        "min_pct": float(past.min()) if len(past) else None,
        "max_pct": float(past.max()) if len(past) else None,
    }


def sa_mom_pct(sa_index: pd.Series) -> pd.Series:
    """Seasonally adjusted monthly change: I_t / I_{t−1} − 1 on the adjusted index, in %."""
    sa_index = sa_index.sort_index()
    return ((sa_index / sa_index.shift(1) - 1) * 100).dropna()


def index_from_mom(mom_pct: pd.Series, base: float = 100.0) -> pd.Series:
    """An index built by chaining monthly changes, for series published only as rates
    (e.g. a core-measure average), so it can be seasonally adjusted."""
    mom_pct = mom_pct.sort_index().dropna()
    return base * (1 + mom_pct / 100).cumprod()
