"""Build the Brazil test fixtures by trimming real raw responses saved by `inflation fetch br`.

Run from the repo root after a fetch:  uv run python tests/fixtures/br/record.py

Nothing here is invented: every kept row is copied verbatim from a raw response; rows are
only dropped, to keep the fixtures small (headline + 9 groups, Sep 2025 – Sep 2026).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

RAW = Path("raw/br")
OUT = Path("tests/fixtures/br/raw")

FIRST, LAST = "202509", "202609"
GROUP_CATEGORIES = {"7169", "7170", "7445", "7486", "7558", "7625", "7660", "7712", "7766", "7786"}


def keep_sidra(rows: list[dict[str, str]], first: str, last: str) -> list[dict[str, str]]:
    header, body = rows[0], rows[1:]
    month_key = next(k for k, v in header.items() if v == "Mês (Código)")
    cat_key = next((k for k, v in header.items() if v.endswith("subitem (Código)")), None)
    kept = [
        r
        for r in body
        if first <= r[month_key] <= last and (cat_key is None or r[cat_key] in GROUP_CATEGORIES)
    ]
    return [header, *kept]


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    manifest = json.loads((RAW / "manifest.json").read_text("utf-8"))
    out_manifest = {}

    def save(name: str, content: object) -> None:
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False, indent=0), "utf-8")
        out_manifest[name] = manifest[name]

    # IPCA (7060) and IPCA-15 (7062): 2025 and 2026 files, trimmed to the window.
    for table in (7060, 7062):
        for path in sorted((RAW / "sidra").glob(f"{table}_v*_202[56].json")):
            save(f"sidra/{path.name}", keep_sidra(json.loads(path.read_text("utf-8")), FIRST, LAST))
    # Long-run table 1737 (index number etc.), same window.
    for path in sorted((RAW / "sidra").glob("1737_v*_all.json")):
        save(f"sidra/{path.name}", keep_sidra(json.loads(path.read_text("utf-8")), FIRST, LAST))
    # Previous basket (1419): Dec 2019 only, so the table-overlap check has something to compare.
    for path in sorted((RAW / "sidra").glob("1419_v*_2019.json")):
        save(
            f"sidra/{path.name}",
            keep_sidra(json.loads(path.read_text("utf-8")), "201912", "201912"),
        )
    # The 1737 window must reach Dec 2019 too for that overlap.
    for path in sorted((RAW / "sidra").glob("1737_v*_all.json")):
        rows = json.loads(path.read_text("utf-8"))
        extra = keep_sidra(rows, "201912", "201912")[1:]
        current = json.loads((OUT / "sidra" / path.name).read_text("utf-8"))
        save(f"sidra/{path.name}", [current[0], *extra, *current[1:]])

    # Focus: surveys from 1 Sep 2026; monthly rows only for Sep/Oct 2026 reference months.
    for path in sorted((RAW / "focus").glob("*.json")):
        body = json.loads(path.read_text("utf-8"))
        rows = [r for r in body["value"] if r["Data"] >= "2026-09-01"]
        if path.name.startswith("ExpectativaMercadoMensais"):
            rows = [r for r in rows if r["DataReferencia"] in {"09/2026", "10/2026"}]
        if rows:
            save(f"focus/{path.name}", {**body, "value": rows})

    (OUT / "manifest.json").write_text(json.dumps(out_manifest, indent=1, sort_keys=True), "utf-8")
    print(f"wrote {len(out_manifest)} fixture files to {OUT}")


if __name__ == "__main__":
    main()
