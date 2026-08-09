"""Janelas temporais determinísticas para métricas CNPJ oferta (RFB).

Stdlib only. as_of respeita atraso do ref_month; Q = último trimestre civil fechado.
"""

from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import date, timedelta
from typing import Any


def ultimo_dia_mes(ref_month: date) -> date:
    """Último dia civil do mês de `ref_month` (dia do input ignorado além de ano/mês)."""
    last = calendar.monthrange(ref_month.year, ref_month.month)[1]
    return date(ref_month.year, ref_month.month, last)


def as_of_ref(hoje: date, ref_month: date) -> date:
    """Âncora temporal: min(hoje, último dia do mês de ref_month)."""
    return min(hoje, ultimo_dia_mes(ref_month))


def ultimo_trimestre_fechado(as_of: date) -> tuple[date, date, str]:
    """Último trimestre civil completamente fechado relativo a `as_of`.

    Ex.: as_of em maio → Q1 (jan–mar). Label: ``YYYY-Qn``.
    """
    q_atual = (as_of.month - 1) // 3 + 1
    if q_atual == 1:
        year = as_of.year - 1
        q = 4
    else:
        year = as_of.year
        q = q_atual - 1
    start_month = 3 * (q - 1) + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    return start, end, f"{year}-Q{q}"


def janela_90d(as_of: date) -> tuple[date, date]:
    """Intervalo fechado [as_of - 90 dias, as_of]."""
    return as_of - timedelta(days=90), as_of


def parse_rfb_date(value: Any) -> date | None:
    """Parse data RFB: int/str YYYYMMDD, date, ou None/0 inválido."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, int):
        if value <= 0:
            return None
        s = f"{value:08d}"
    else:
        s = str(value).strip()
        if not s or s in ("0", "00000000"):
            return None
        s = s.replace("-", "")[:8]
        if not s.isdigit():
            return None
    try:
        y, m, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
        return date(y, m, d)
    except ValueError:
        return None


def normalize_bairro(s: str) -> str:
    """Upper, sem acento, espaços colapsados."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only).strip().upper()
