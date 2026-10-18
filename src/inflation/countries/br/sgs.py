"""BCB SGS API: time series by numeric code (see docs/sources.md).

Quirks seen in October 2026:
- Errors can arrive with HTTP 200, as an HTML page ("Requisição inválida") or as JSON
  like {"erro": {"statusCode": 500, ...}}. Both are rejected here so they get retried.
- The firewall blocks clients that send bursts, so callers must throttle generously.
- Daily series (e.g. the Selic target, 432) can include rows dated in the future: the
  value in force until the next policy meeting. Those rows are dropped at parse time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import httpx

from inflation.http import BadResponse, require_json

URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

# SGS refuses daily-series requests spanning more than 10 years; we use the same window
# for monthly series too, which keeps every request small.
MAX_WINDOW_YEARS = 10


@dataclass(frozen=True)
class SgsValue:
    code: int
    date: date
    value: float


def validate(response: httpx.Response) -> None:
    require_json(response)
    body = response.json()
    if isinstance(body, dict) and "erro" in body:
        raise BadResponse(f"SGS error body: {body['erro']}")
    if not isinstance(body, list):
        raise BadResponse(f"unexpected SGS body: {response.text[:200]}")


def windows(start: date, end: date) -> list[tuple[date, date]]:
    """Split [start, end] into consecutive windows of at most MAX_WINDOW_YEARS."""
    spans = []
    cursor = start
    while cursor <= end:
        stop = min(date(cursor.year + MAX_WINDOW_YEARS - 1, 12, 31), end)
        spans.append((cursor, stop))
        cursor = date.fromordinal(stop.toordinal() + 1)
    return spans


def params(start: date, end: date) -> dict[str, str]:
    return {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }


def parse(code: int, body: list[dict[str, str]], as_of: date) -> list[SgsValue]:
    values = []
    for row in body:
        day = datetime.strptime(row["data"], "%d/%m/%Y").date()
        if day > as_of:
            continue  # forward-filled future rows (see module docstring)
        values.append(SgsValue(code=code, date=day, value=float(row["valor"])))
    return values
