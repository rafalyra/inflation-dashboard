"""IBGE SIDRA API: request building and parsing (verified 2026-10-17/18, see docs/sources.md).

A SIDRA response is a JSON list whose first element is a header row that names each
column (e.g. "D3C": "Mês (Código)"). We locate columns by those labels rather than by
position, so a reordering by IBGE fails loudly instead of silently mislabeling data.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from inflation.http import BadResponse, require_json

VALUES_URL = "https://apisidra.ibge.gov.br/values"
METADATA_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/{table}/metadados"

# Classification 315: "Geral, grupo, subgrupo, item e subitem".
CLASSIFICATION = 315
GENERAL_INDEX_CATEGORY = "7169"

# IBGE's "special values": "-" is a numeric zero not caused by rounding; the others mean
# the value doesn't exist or is suppressed (IBGE, "Sinais convencionais").
ZERO_SIGN = "-"
MISSING_SIGNS = frozenset({"..", "...", "X"})


@dataclass(frozen=True)
class SidraValue:
    table: int
    variable: str
    period: str  # YYYY-MM
    category: str | None  # classification 315 category id, None for tables without it
    category_name: str | None
    unit: str
    value: float | None  # None when IBGE marks the value as missing


def values_path(
    table: int,
    variables: list[int],
    period_from: str,
    period_to: str,
    with_categories: bool,
) -> str:
    """URL path for one request. Periods are YYYYMM, inclusive."""
    path = (
        f"{VALUES_URL}/t/{table}/n1/all/v/{','.join(map(str, variables))}"
        f"/p/{period_from}-{period_to}"
    )
    if with_categories:
        path += f"/c{CLASSIFICATION}/all"
    return path


def validate_values(response: httpx.Response) -> None:
    require_json(response)
    body = response.json()
    if not isinstance(body, list) or not body or not isinstance(body[0], dict):
        raise BadResponse(f"unexpected SIDRA body: {response.text[:200]}")


CATEGORY_LABEL = "Geral, grupo, subgrupo, item e subitem"


def _find(header: dict[str, str], label: str) -> str:
    for key, value in header.items():
        if value == label:
            return key
    raise BadResponse(f"SIDRA header has no column {label!r}: {header}")


def parse_value(raw: str) -> float | None:
    if raw == ZERO_SIGN:
        return 0.0
    if raw in MISSING_SIGNS:
        return None
    return float(raw)


def parse_values(table: int, body: list[dict[str, str]]) -> list[SidraValue]:
    header, rows = body[0], body[1:]
    variable_key = _find(header, "Variável (Código)")
    month_key = _find(header, "Mês (Código)")
    unit_key = _find(header, "Unidade de Medida")
    category_key = category_name_key = None
    if CATEGORY_LABEL in header.values():
        category_key = _find(header, f"{CATEGORY_LABEL} (Código)")
        category_name_key = _find(header, CATEGORY_LABEL)

    parsed = []
    for row in rows:
        month = row[month_key]  # YYYYMM
        parsed.append(
            SidraValue(
                table=table,
                variable=row[variable_key],
                period=f"{month[:4]}-{month[4:]}",
                category=row[category_key] if category_key else None,
                category_name=row[category_name_key] if category_name_key else None,
                unit=row[unit_key],
                value=parse_value(row["V"]),
            )
        )
    return parsed


def split_code(category_name: str) -> tuple[str, str]:
    """IBGE labels look like "1101002.Arroz": hierarchical code, then name.

    The general index ("Índice geral") has no code; we give it the empty string.
    """
    code, sep, name = category_name.partition(".")
    if not sep or not code.isdigit():
        return "", category_name
    return code, name


def level_of(code: str) -> int:
    """Hierarchy depth from the code length: group 1 digit, subgroup 2, item 4, subitem 7.

    Table 1419 (2012–2019) doesn't publish levels in its metadata, so we derive them here
    the same way for every table.
    """
    return {0: 0, 1: 1, 2: 2, 4: 3, 7: 4}[len(code)]
