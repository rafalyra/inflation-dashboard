"""What happens to the 12-month rate next month? (docs/methodology.md §Base effects)

The 12-month window moves forward one month at a time: next month's print comes in and the
print from 12 months earlier drops out. If the new print is bigger than the one leaving,
the 12-month rate rises, whatever the trend. Exactly:

    1 + Y_{t+1} = (1 + Y_t) · (1 + m_{t+1}) / (1 + m_{t−11})
"""

from __future__ import annotations

import pandas as pd


def dropping_out(mom_pct: pd.Series, last_period: str, months: int = 3) -> list[dict[str, object]]:
    """For each of the next `months` releases, the month that leaves the 12-month window."""
    last = pd.Period(last_period, freq="M")
    out = []
    for ahead in range(1, months + 1):
        incoming = last + ahead
        leaving = (incoming - 12).strftime("%Y-%m")
        out.append(
            {
                "period": incoming.strftime("%Y-%m"),
                "leaving_period": leaving,
                "leaving_mom_pct": float(mom_pct[leaving]) if leaving in mom_pct.index else None,
            }
        )
    return out


def implied_next_yoy_pct(yoy_pct: float, leaving_mom_pct: float, incoming_mom_pct: float) -> float:
    """The 12-month rate next month if the new monthly print equals `incoming_mom_pct`."""
    return (
        (1 + yoy_pct / 100) * (1 + incoming_mom_pct / 100) / (1 + leaving_mom_pct / 100) - 1
    ) * 100
