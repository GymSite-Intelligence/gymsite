"""Aluguel comercial DETERMINÍSTICO via MRLR (IBAPE-GO), lendo espelhos.

Substitui o scraping de portais (não-determinístico → audit Cocó mostrou aluguel
17k→88k na MESMA praça). Aqui o aluguel é CALCULADO da equação MRLR sobre inputs
ESTÁVEIS, todos espelhados:
  - área: do form
  - zona (LUOS): do zoneamento
  - porte + PIB: municipio_pib (espelho IBGE/BQ)
  - padrão (acabamento): da renda do bairro (renda_bairro espelho) — percentil alto =
    padrão alto. NÃO de preço raspado.

Mesma praça → sempre o mesmo aluguel (recalibrável via coeficientes do catálogo).
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("gymsite.aluguel_mrlr")


def _sb():
    from tools.supabase_client import load_create_client

    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not (url and key):
        return None
    return load_create_client()(url, key)


def _padrao_de_renda(percentil: float | None) -> int:
    """Padrão de acabamento a partir do percentil de renda do bairro no município.
    Top (≥0.66) → alto (3); meio → normal (2); base (<0.33) → baixo (1)."""
    if percentil is None:
        return 2
    if percentil >= 0.66:
        return 3
    if percentil < 0.33:
        return 1
    return 2


def aluguel_deterministico(*, area_m2: float, cidade: str, bairro: str,
                           zona_sigla: str | None = None,
                           id_municipio: str | int | None = None) -> dict[str, Any]:
    """Aluguel/m² + total via MRLR, dos espelhos. status=ok|indisponivel (caller cai
    pro portal). Best-effort — falha de DB degrada limpo. id_municipio é derivado do
    renda_bairro quando não passado (uma leitura dá municipio_cod + percentil)."""
    from tools.mrlr_modelo import (
        fator_de_pib_per_capita, local_de_zona, porte_de_populacao, valor_unitario_mrlr,
    )

    if not area_m2 or area_m2 <= 0:
        return {"status": "indisponivel", "motivo": "área ausente"}
    sb = _sb()
    if not sb:
        return {"status": "indisponivel", "motivo": "supabase indisponível"}

    # renda_bairro: dá municipio_cod (id) + percentil (→ padrão) numa leitura
    percentil = None
    cod = str(id_municipio or "").strip()
    try:
        rb = (sb.table("renda_bairro").select("municipio_cod,percentil_municipio")
              .ilike("cidade", f"%{cidade}%").ilike("bairro", f"%{bairro}%")
              .limit(1).execute().data or [None])[0]
        if rb:
            percentil = rb.get("percentil_municipio")
            if not cod and rb.get("municipio_cod"):
                cod = str(rb["municipio_cod"]).strip()
    except Exception:
        pass

    if not cod:
        return {"status": "indisponivel", "motivo": "id_municipio não resolvido"}
    try:
        m = (sb.table("municipio_pib").select("populacao,pib_reais,pib_per_capita")
             .eq("id_municipio", cod).limit(1).execute().data or [None])[0]
    except Exception:
        return {"status": "indisponivel", "motivo": "leitura municipio_pib falhou"}
    if not m or not m.get("populacao") or not m.get("pib_reais"):
        return {"status": "indisponivel", "motivo": "municipio_pib sem dado"}

    pop = float(m["populacao"]); pib = float(m["pib_reais"]); pib_pc = float(m.get("pib_per_capita") or 0)
    porte = porte_de_populacao(pop)
    fator = fator_de_pib_per_capita(pib_pc)
    local = local_de_zona(zona_sigla)
    padrao = _padrao_de_renda(percentil)
    vu = valor_unitario_mrlr(area_m2, padrao, local, porte, pib, fator)
    if vu is None:
        return {"status": "indisponivel", "motivo": "MRLR inputs insuficientes"}
    return {
        "status": "ok",
        "valor_unitario_m2": vu,
        "aluguel_total": round(vu * area_m2, 2),
        "inputs": {"area_m2": area_m2, "padrao": padrao, "local": local, "porte": porte,
                   "pib": pib, "fator_economico": fator, "renda_percentil": percentil},
        "fonte": "MRLR IBAPE-GO (R²=0,8633) — espelhos municipio_pib + renda_bairro",
        "metodo": "Valor Unitário² determinístico; recalibrável via catalogos_metodologia",
    }
