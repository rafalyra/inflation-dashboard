"""Build the Brazil test fixtures by trimming real raw responses saved by `inflation fetch br`.

Run from the repo root after a fetch:  uv run python tests/fixtures/br/record.py

Nothing here is invented: every kept row is copied verbatim from a raw response; rows are
only dropped, to keep the fixtures small: headline and 9 groups for Sep 2025 – Sep 2026, every
level for Sep 2026, and Dec 2019 for the table-overlap check. Each file keeps its original
fetch record (URL and time).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from inflation.raw import RawStore

RAW = RawStore(Path("raw/br"))
OUT = RawStore(Path("tests/fixtures/br/raw"))

FIRST, LAST = "202509", "202609"
OVERLAP = "201912"


def keep_sidra(rows: list[dict[str, str]], first: str, last: str) -> list[dict[str, str]]:
    header, body = rows[0], rows[1:]
    month_key = next(k for k, v in header.items() if v == "Mês (Código)")
    name_key = next((k for k, v in header.items() if v.endswith("item e subitem")), None)

    def wanted(row: dict[str, str]) -> bool:
        if not first <= row[month_key] <= last:
            return False
        if name_key is None:
            return True
        code = row[name_key].partition(".")[0]
        # General index and the 9 groups (1 digit) every month; items (4 digits) only in
        # the latest month, where the top movers are computed.
        # Subgroups and subitems too in the latest month (BCB segments, basket map).
        latest_only = len(code) in (2, 4, 7) and row[month_key] == last
        return not code.isdigit() or len(code) == 1 or latest_only

    return [header, *[r for r in body if wanted(r)]]


def copy(name: str, content: object) -> None:
    path = OUT.root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=0), "utf-8")
    meta = RAW.meta(name)
    Path(f"{path}.meta").write_text(json.dumps(meta, indent=1), "utf-8")


def main() -> None:
    # Clear the contents (not the folder itself, which an editor may hold open on Windows).
    for child in OUT.root.glob("*"):
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    for path in RAW.files("sidra/*_v*_*.json"):
        name = f"sidra/{path.name}"
        rows = json.loads(path.read_text("utf-8"))
        table = path.name.split("_")[0]
        if table in ("7060", "7062") and ("2025" in path.name or "2026" in path.name):
            copy(name, keep_sidra(rows, FIRST, LAST))
        elif table == "1419" and "2019" in path.name:
            # General index only, so no group series has a hole before Sep 2025.
            general = [
                r for r in keep_sidra(rows, OVERLAP, OVERLAP) if "Índice geral" in r.values()
            ]
            copy(name, [rows[0], *general])
        elif table == "1737":
            # Continuous from Dec 2019, so the headline has no gaps.
            copy(name, keep_sidra(rows, OVERLAP, LAST))

    # SGS: monthly series Sep 2025 – Sep 2026, daily series from 1 Sep 2025.
    for path in RAW.files("sgs/*.json"):
        if not path.name.endswith("2026.json"):
            continue
        rows = json.loads(path.read_text("utf-8"))
        kept = [r for r in rows if (r["data"][6:] + r["data"][3:5]) >= FIRST]
        copy(f"sgs/{path.name}", kept)

    # Focus: surveys from 1 Sep 2026; monthly rows only for Sep–Nov 2026 reference months.
    for path in RAW.files("focus/*.json"):
        body = json.loads(path.read_text("utf-8"))
        rows = [r for r in body["value"] if r["Data"] >= "2026-09-01"]
        if path.name.startswith("ExpectativaMercadoMensais"):
            rows = [r for r in rows if r["DataReferencia"] in {"09/2026", "10/2026", "11/2026"}]
        if rows:
            copy(f"focus/{path.name}", {**body, "value": rows})

    print(f"wrote {len(OUT.files('*/*.json'))} fixture files to {OUT.root}")


if __name__ == "__main__":
    main()
