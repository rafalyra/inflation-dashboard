"""Parsers and guards for Brazil's sources. Inputs mirror the shapes seen live in Oct 2026."""

from datetime import date
from itertools import pairwise

import httpx
import pytest

from inflation.countries.br import focus, ibge_calendar, sgs, sidra
from inflation.http import BadResponse


def _response(body: str, content_type: str) -> httpx.Response:
    return httpx.Response(200, text=body, headers={"content-type": content_type})


# ---- SIDRA ----


@pytest.mark.parametrize(
    ("raw", "expected"), [("0.82", 0.82), ("-0.32", -0.32), ("-", 0.0), ("...", None), ("X", None)]
)
def test_sidra_special_values(raw: str, expected: float | None) -> None:
    assert sidra.parse_value(raw) == expected


@pytest.mark.parametrize(
    ("label", "code", "level"),
    [
        ("Índice geral", "", 0),
        ("1.Alimentação e bebidas", "1", 1),
        ("11.Alimentação no domicílio", "11", 2),
        ("1101.Cereais, leguminosas e oleaginosas", "1101", 3),
        ("1101002.Arroz", "1101002", 4),
    ],
)
def test_sidra_codes_and_levels(label: str, code: str, level: int) -> None:
    parsed_code, _ = sidra.split_code(label)
    assert parsed_code == code
    assert sidra.level_of(parsed_code) == level


def test_sidra_rejects_reordered_header() -> None:
    header = {"V": "Valor", "D1C": "Something else"}
    with pytest.raises(BadResponse):
        sidra.parse_values(7060, [header])


# ---- SGS ----


def test_sgs_rejects_html_error_page() -> None:
    with pytest.raises(BadResponse):
        sgs.validate(_response("<html>Requisição inválida</html>", "text/html; charset=utf-8"))


def test_sgs_rejects_json_error_body() -> None:
    body = '{"erro":{"statusCode":500,"detail":"Internal error"}}'
    with pytest.raises(BadResponse):
        sgs.validate(_response(body, "application/json; charset=utf-8"))


def test_sgs_drops_future_dated_rows() -> None:
    body = [{"data": "17/10/2026", "valor": "1.0"}, {"data": "04/11/2026", "valor": "1.0"}]
    values = sgs.parse(432, body, as_of=date(2026, 10, 18))
    assert [v.date for v in values] == [date(2026, 10, 17)]


def test_sgs_windows_cover_range_without_overlap() -> None:
    spans = sgs.windows(date(1995, 1, 1), date(2026, 10, 18))
    assert spans[0] == (date(1995, 1, 1), date(2004, 12, 31))
    assert spans[-1][1] == date(2026, 10, 18)
    for (_, end), (start, _) in pairwise(spans):
        assert start.toordinal() == end.toordinal() + 1


# ---- Focus ----


def test_focus_url_encodes_spaces_as_percent20() -> None:
    url = focus.url(focus.MONTHLY, focus.ipca_filter(date(2026, 1, 1)), 0)
    assert "+" not in url
    assert "Indicador%20eq%20%27IPCA%27" in url


# ---- IBGE calendar ----


def test_calendar_reads_utc_and_converts_to_brasilia() -> None:
    body = {
        "items": [
            {
                "data_divulgacao": "23/10/2026 12:00:00",
                "ano_referencia_inicio": 2026,
                "mes_referencia_inicio": 10,
            }
        ]
    }
    (row,) = ibge_calendar.rows("IPCA15", body, "America/Sao_Paulo")
    assert row["release_id"] == "br-ipca15-2026-10"
    assert (row["release_date"], row["release_time_local"]) == ("2026-10-23", "09:00")
