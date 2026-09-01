"""PONTO 75 — sanitizer de tipos antes do insert Supabase."""

from tools.supabase_type_sanitizer import (
    _coerce_float,
    _coerce_int,
    sanitize_nested_records,
    sanitize_record,
)


def test_coerce_int():
    assert _coerce_int(5) == 5
    assert _coerce_int(5.0) == 5
    assert _coerce_int("5") == 5
    assert _coerce_int("5.0") == 5
    assert _coerce_int(5.5) is None
    assert _coerce_int(None) is None
    assert _coerce_int("abc") is None
    assert _coerce_int(True) == 1


def test_coerce_float():
    assert _coerce_float(3.65) == 3.65
    assert _coerce_float("3.65") == 3.65
    assert _coerce_float(3) == 3.0
    assert _coerce_float(None) is None
    assert _coerce_float("abc") is None


def test_sanitize_record():
    record = {
        "area_m2": 5.0,
        "area_estimada_m2": 90.0,
        "score_bairro": "3.65",
        "nome": "Teste",
    }
    sanitizado, stats = sanitize_record(record)

    assert sanitizado["area_m2"] == 5
    assert isinstance(sanitizado["area_m2"], int)
    assert sanitizado["area_estimada_m2"] == 90
    assert isinstance(sanitizado["area_estimada_m2"], int)
    assert sanitizado["score_bairro"] == 3.65
    assert sanitizado["nome"] == "Teste"
    assert stats["int_convertidos"] == 2
    assert stats["float_convertidos"] == 1


def test_sanitize_nested_top3():
    data = {
        "top_3_candidatos": [
            {"area_m2": 5.0, "area_estimada_m2": 5.0, "nome": "Cand 1"},
            {"area_m2": 90.0, "area_estimada_m2": 90.0, "nome": "Cand 2"},
        ],
        "score_bairro": 3.65,
    }
    sanitizado = sanitize_nested_records(data)

    assert sanitizado["top_3_candidatos"][0]["area_m2"] == 5
    assert isinstance(sanitizado["top_3_candidatos"][0]["area_m2"], int)
    assert sanitizado["top_3_candidatos"][1]["area_estimada_m2"] == 90
    assert sanitizado["score_bairro"] == 3.65


def test_rows_candidatos_area_float_vira_int():
    from db.supabase_writer import _rows_candidatos, _sanitize_rows

    rel = {
        "output_consolidado": {
            "top_3_candidatos": [
                {
                    "nome": "Apartamento à venda",
                    "area_m2": 5.0,
                    "area_estimada_m2": 5.0,
                },
                {
                    "nome": "Galpão",
                    "area_m2": 90.0,
                    "area_estimada_m2": 90.0,
                },
            ]
        }
    }
    rows = _sanitize_rows(_rows_candidatos(rel, "rid-test"))
    assert rows[0]["area_estimada_m2"] == 5
    assert isinstance(rows[0]["area_estimada_m2"], int)
    assert rows[1]["area_estimada_m2"] == 90
    assert isinstance(rows[1]["area_estimada_m2"], int)
