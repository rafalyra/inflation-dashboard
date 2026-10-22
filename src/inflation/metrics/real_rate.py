"""The real policy rate (docs/methodology.md §Real rate).

What a saver earns after inflation is what matters for spending and borrowing decisions.
Ex-ante means "using expected inflation": the policy rate deflated by what people expect
prices to do over the next 12 months. The exact form divides growth factors; subtracting
rates is only an approximation.
"""

from __future__ import annotations


def ex_ante_real_pct(nominal_pct: float, expected_inflation_pct: float) -> float:
    """(1 + i) / (1 + π_expected) − 1, in percent."""
    return ((1 + nominal_pct / 100) / (1 + expected_inflation_pct / 100) - 1) * 100
