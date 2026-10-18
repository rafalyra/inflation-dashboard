"""IBGE release calendar API -> rows for config/calendars/br.csv (see docs/sources.md).

The API lists release times as "dd/mm/yyyy 12:00:00" for products that IBGE releases at
09:00 Brasília time, so we read the timestamp as UTC and convert it to local time.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import httpx

from inflation.http import BadResponse, require_json

URL = "https://servicodados.ibge.gov.br/api/v3/calendario/{product}"

# IBGE product ids, verified 2026-10-18.
PRODUCTS = {"IPCA": 9256, "IPCA15": 9260}

SOURCE_PAGE = "https://www.ibge.gov.br/calendario-de-divulgacoes.html"


def validate(response: httpx.Response) -> None:
    require_json(response)
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        raise BadResponse(f"unexpected IBGE calendar body: {response.text[:200]}")


def params(start: date, end: date) -> dict[str, str]:
    return {"de": start.strftime("%m-%d-%Y"), "ate": end.strftime("%m-%d-%Y"), "qtd": "500"}


def release_id(indicator: str, period: str) -> str:
    return f"br-{indicator.lower()}-{period}"


def rows(
    indicator: str, body: dict[str, list[dict[str, object]]], timezone: str
) -> list[dict[str, str]]:
    tz = ZoneInfo(timezone)
    out = []
    for item in body["items"]:
        year, month = item["ano_referencia_inicio"], item["mes_referencia_inicio"]
        if not isinstance(year, int) or not isinstance(month, int):
            raise BadResponse(f"calendar item without reference month: {item}")
        released = datetime.strptime(str(item["data_divulgacao"]), "%d/%m/%Y %H:%M:%S")
        local = released.replace(tzinfo=UTC).astimezone(tz)
        period = f"{year:04d}-{month:02d}"
        out.append(
            {
                "release_id": release_id(indicator, period),
                "indicator": indicator,
                "reference_period": period,
                "release_date": local.date().isoformat(),
                "release_time_local": local.strftime("%H:%M"),
                "timezone": timezone,
                "source_url": SOURCE_PAGE,
            }
        )
    return sorted(out, key=lambda r: (r["release_date"], r["indicator"]))
