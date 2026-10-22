"""Brazil adapter: IPCA and IPCA-15 (IBGE), cores and context (BCB SGS), Focus (BCB Olinda).

See NOTES.md in this folder for the data quirks, and docs/sources.md for every endpoint.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import ClassVar

from inflation.config import CalendarEntry
from inflation.countries.base import CountryAdapter, Normalized, register
from inflation.countries.br import focus, ibge_calendar, sgs, sidra
from inflation.http import PoliteClient
from inflation.models import CheckResult
from inflation.raw import RawStore

CATALOG_PATH = Path(__file__).with_name("catalog.csv")


@dataclass(frozen=True)
class SidraTable:
    table: int
    indicator: str
    variables: dict[int, str]  # SIDRA variable id -> our unit
    with_categories: bool
    first: int  # first month (YYYYMM), from the table's metadata
    last: int | None = None  # last month for closed tables; None = still updated


# Basket eras (see NOTES.md): table 1419 covers Jan 2012–Dec 2019, table 7060 Jan 2020 on.
# Table 1737 carries the long headline history and the index number. First/last months were
# read from each table's metadata on 2026-10-17/18 (docs/sources.md). We don't query the
# metadata host at fetch time: it was unreachable on 2026-10-22, also from GitHub runners.
SIDRA_TABLES = [
    SidraTable(
        7060,
        "IPCA",
        {63: "mom_pct", 69: "ytd_pct", 2265: "yoy_pct", 66: "weight_pct"},
        True,
        202001,
    ),
    SidraTable(
        1419,
        "IPCA",
        {63: "mom_pct", 69: "ytd_pct", 2265: "yoy_pct", 66: "weight_pct"},
        True,
        201201,
        201912,
    ),
    SidraTable(
        1737, "IPCA", {2266: "index", 63: "mom_pct", 69: "ytd_pct", 2265: "yoy_pct"}, False, 197912
    ),
    SidraTable(
        7062,
        "IPCA15",
        {355: "mom_pct", 356: "ytd_pct", 1120: "yoy_pct", 357: "weight_pct"},
        True,
        202002,
    ),
]

# The table that answers "what is the newest month?" for each indicator.
LATEST_TABLE = {"IPCA": 7060, "IPCA15": 7062}


def load_catalog_rows() -> list[dict[str, str]]:
    with CATALOG_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _chunks(start: int, end: int, by_year: bool) -> list[tuple[int, int, str]]:
    """Split a YYYYMM range into request windows: per calendar year, or all at once.

    The label names the file, so it must describe exactly the range inside: a short
    refresh must never overwrite a file that holds the full history.
    """
    if not by_year:
        return [(start, end, f"{start}-{end}")]
    windows = [
        (max(start, year * 100 + 1), min(end, year * 100 + 12))
        for year in range(start // 100, end // 100 + 1)
    ]
    return [(a, b, f"{a}-{b}") for a, b in windows]


@register
class BrazilAdapter(CountryAdapter):
    code = "br"
    timezone = "America/Sao_Paulo"
    history_start: ClassVar[dict[str, date]] = {
        "index": date(1979, 12, 1),  # table 1737 starts Dec 1979
        "context": date(1995, 1, 1),  # SPEC §9: headline history from 1995
        "expectations": date(2012, 1, 1),  # matches the group/item history
    }

    def __init__(self, raw_dir: Path, client: PoliteClient | None = None) -> None:
        super().__init__(raw_dir)
        self.raw = RawStore(raw_dir)
        self.client = client or PoliteClient(min_interval_s=1.0)
        # SGS blocks bursts (seen 2026-10-18), so it gets its own slower client.
        self.sgs_client = PoliteClient(min_interval_s=3.0, backoff_s=20.0)

    # ---- fetch -------------------------------------------------------------------------

    def _latest_month(self, spec: SidraTable) -> int:
        """Newest month the table publishes, asked of the values API itself ("last 1")."""
        path = sidra.latest_path(spec.table, next(iter(spec.variables)), spec.with_categories)
        body = self.client.get(path, validate=sidra.validate_values).json()
        (value,) = sidra.parse_values(spec.table, body)
        return int(value.period.replace("-", ""))

    def fetch(self, since: date) -> None:
        for spec in SIDRA_TABLES:
            first = spec.first
            last = spec.last if spec.last is not None else self._latest_month(spec)
            start = max(first, since.year * 100 + since.month)
            if start > last:
                continue  # a closed basket table outside the requested window
            for p_from, p_to, label in _chunks(start, last, by_year=spec.with_categories):
                # One request per variable (and per year for the ~460-category tables)
                # keeps each response far below SIDRA's 100,000-value limit.
                for variable in spec.variables:
                    path = sidra.values_path(
                        spec.table, [variable], str(p_from), str(p_to), spec.with_categories
                    )
                    response = self.client.get(path, validate=sidra.validate_values)
                    self.raw.save(
                        f"sidra/{spec.table}_v{variable}_{label}.json", response.content, path
                    )

    def fetch_context(self, since: date) -> None:
        today = datetime.now(UTC).date()
        for row in load_catalog_rows():
            if row["source"] != "bcb_sgs":
                continue
            code = int(row["source_code"])
            for start, end in sgs.windows(since, today):
                url = sgs.URL.format(code=code)
                params = sgs.params(start, end)
                response = self.sgs_client.get(url, params=params, validate=sgs.validate)
                self.raw.save(
                    f"sgs/{code}_{start.year}-{end.year}.json",
                    response.content,
                    str(response.request.url),
                )

    def fetch_expectations(self, since: date) -> None:
        for entity in (focus.MONTHLY, focus.TWELVE_MONTHS, focus.ANNUAL):
            skip = 0
            while True:
                url = focus.url(entity, focus.ipca_filter(since), skip)
                response = self.client.get(url, validate=focus.validate)
                self.raw.save(
                    f"focus/{entity}_{since.isoformat()}_{skip:07d}.json", response.content, url
                )
                if len(response.json()["value"]) < focus.PAGE_SIZE:
                    break
                skip += focus.PAGE_SIZE

    def fetch_calendar(self, start: date, end: date) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for indicator, product in ibge_calendar.PRODUCTS.items():
            url = ibge_calendar.URL.format(product=product)
            response = self.client.get(
                url, params=ibge_calendar.params(start, end), validate=ibge_calendar.validate
            )
            self.raw.save(f"calendar/{indicator}.json", response.content, str(response.request.url))
            rows.extend(ibge_calendar.rows(indicator, response.json(), self.timezone))
        return sorted(rows, key=lambda r: (r["release_date"], r["indicator"]))

    def latest_reference_period(self, indicator: str) -> str:
        spec = next(t for t in SIDRA_TABLES if t.table == LATEST_TABLE[indicator])
        last = str(self._latest_month(spec))
        return f"{last[:4]}-{last[4:]}"

    # ---- normalize & checks: below -------------------------------------------------------

    def normalize(self) -> Normalized:
        from inflation.countries.br.normalize import normalize

        return normalize(self.raw, load_catalog_rows())

    def official_checks(
        self, data: Normalized, calendar: list[CalendarEntry], now_utc: datetime
    ) -> list[CheckResult]:
        from inflation.countries.br.checks import official_checks

        return official_checks(data, self.raw, calendar, now_utc)
