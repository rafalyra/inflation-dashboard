"""BCB Focus market survey via the Olinda OData API (see docs/sources.md).

Focus collects forecasts from ~140 banks and consultancies. Each day's row summarizes the
forecasts submitted over a window: `baseCalculo` 0 = last 30 days (the figure in the
published Focus report, our primary), 1 = last 5 business days (fresher, fewer
respondents; shown as secondary).

OData filters must be percent-encoded with %20 for spaces: Olinda reads "+" literally.
"""

from __future__ import annotations

from datetime import date
from urllib.parse import quote

import httpx

from inflation.http import BadResponse, require_json

BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"

MONTHLY = "ExpectativaMercadoMensais"
TWELVE_MONTHS = "ExpectativasMercadoInflacao12Meses"
ANNUAL = "ExpectativasMercadoAnuais"

PAGE_SIZE = 10_000


def validate(response: httpx.Response) -> None:
    require_json(response)
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("value"), list):
        raise BadResponse(f"unexpected Olinda body: {response.text[:200]}")


def url(entity: str, odata_filter: str, skip: int) -> str:
    query = {
        "$filter": odata_filter,
        "$orderby": "Data asc",
        "$top": str(PAGE_SIZE),
        "$skip": str(skip),
        "$format": "json",
    }
    qs = "&".join(f"{k}={quote(v, safe='')}" for k, v in query.items())
    return f"{BASE}/{entity}?{qs}"


def ipca_filter(since: date) -> str:
    return f"Indicador eq 'IPCA' and Data ge '{since.isoformat()}'"
