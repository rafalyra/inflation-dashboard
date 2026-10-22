"""Seasonal adjustment with the US Census Bureau's X-13ARIMA-SEATS (docs/methodology.md).

Why: many prices move with the calendar (school fees in February, food after harvests),
so a raw month-on-month change mixes trend with season. Annualizing a 3-month change
(SAAR) only makes sense on a seasonally adjusted index.

We call the official Census binary directly: write a small spec file, run it, read the
adjusted series (table D11) back. The latest few points of any seasonal adjustment are
revised as new data arrive; exports flag them as revisable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

# Where to find the binary: $X13PATH (a file or folder), else tools/x13/ in the repo.
DEFAULT_DIRS = [Path("tools/x13")]
BINARY_NAMES = ["x13as", "x13as.exe", "x13as_ascii", "x13as_ascii.exe"]

# The last REVISABLE_MONTHS adjusted values are the ones X-13 typically revises the most.
REVISABLE_MONTHS = 12


class SeasonalAdjustmentUnavailable(RuntimeError):
    pass


def find_binary() -> Path:
    candidates: list[Path] = []
    env = os.environ.get("X13PATH")
    if env:
        candidates.append(Path(env))
    candidates += DEFAULT_DIRS
    for base in candidates:
        if base.is_file():
            return base
        for name in BINARY_NAMES:
            if (base / name).is_file():
                return base / name
    found = shutil.which("x13as")
    if found:
        return Path(found)
    raise SeasonalAdjustmentUnavailable(
        "X-13ARIMA-SEATS binary not found; set X13PATH or run scripts/install_x13"
    )


def _spec(index: pd.Series) -> str:
    first = pd.Period(index.index[0], freq="M")
    values = "\n".join(f"{v:.6f}" for v in index.to_numpy())
    # log transform: seasonal effects on prices are proportional, not additive.
    # automdl + outlier: let X-13 pick the ARIMA model and flag one-off shocks
    # (e.g. a tax change) so they don't distort the seasonal factors.
    return (
        "series{\n"
        f"  start={first.year}.{first.month}\n"
        "  period=12\n"
        f"  data=(\n{values}\n  )\n"
        "}\n"
        "transform{function=log}\n"
        "automdl{}\n"
        "outlier{}\n"
        "x11{save=(d11)}\n"
    )


def _read_table(path: Path) -> pd.Series:
    rows = []
    for line in path.read_text(encoding="ascii", errors="replace").splitlines()[2:]:
        date, value = line.split()
        rows.append((f"{date[:4]}-{date[4:]}", float(value)))
    return pd.Series(dict(rows), name="sa")


def seasonally_adjust(index: pd.Series, binary: Path | None = None) -> pd.Series:
    """Seasonally adjusted version of a monthly index (periods 'YYYY-MM', no gaps)."""
    if len(index) < 36:
        raise SeasonalAdjustmentUnavailable("X-13 needs at least 3 years of monthly data")
    exe = binary or find_binary()
    with tempfile.TemporaryDirectory() as tmp:
        spec = Path(tmp) / "series.spc"
        spec.write_text(_spec(index), encoding="ascii")
        result = subprocess.run(
            [str(exe), str(spec.with_suffix(""))],
            capture_output=True,
            text=True,
            cwd=tmp,
            check=False,
        )
        table = spec.with_suffix(".d11")
        if result.returncode != 0 or not table.exists():
            errors = spec.with_suffix(".err")
            detail = errors.read_text(errors="replace") if errors.exists() else result.stdout
            raise SeasonalAdjustmentUnavailable(f"X-13 failed: {detail[-800:]}")
        adjusted = _read_table(table)
    if list(adjusted.index) != list(index.index):
        raise SeasonalAdjustmentUnavailable("X-13 output periods don't match the input")
    return adjusted
