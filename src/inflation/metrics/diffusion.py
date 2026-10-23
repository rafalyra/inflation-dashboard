"""How widespread are price increases? (docs/methodology.md §Diffusion)

The BCB's diffusion index counts items. Weighting by the basket instead says how much of
what households buy got dearer: a rise in rent matters more than a rise in coriander.
"""

from __future__ import annotations

import pandas as pd


def weighted_share_pct(condition: pd.DataFrame, weight_pct: pd.DataFrame) -> pd.Series:
    """Share of basket weight (%) where `condition` holds, month by month (rows = periods).

    Only components with both a value and a weight in that month count in the denominator.
    """
    weight, cond = weight_pct.align(condition, join="inner")
    valid = cond.notna() & weight.notna()
    total = weight.where(valid).sum(axis=1)
    hit = weight.where(valid & cond.fillna(False).astype(bool)).sum(axis=1)
    return (hit / total * 100).where(total > 0).dropna()
