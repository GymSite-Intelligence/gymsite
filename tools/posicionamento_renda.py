"""
Posicionamento por headroom de renda — DETERMINÍSTICO, sourced.

Spec: docs/metodologia/posicionamento_headroom_premium.md
Fonte de renda: tabela Supabase `ipece_renda_bairro` (IPECE Informe 272, Censo 2022).

Métrica principal (headroom premium): quanto da capacidade de pagar do bairro NÃO está
sendo capturada pelos concorrentes atuais → veredito OCEANO_AZUL / TRANSICAO / VERMELHO.
Substitui o chute do LLM no A9. Cortes via param() (recalibráveis).
"""
from __future__ import annotations

import os
import re
import statistics
import unicodedata
from typing import Any

from tools.parametros_metodologia import param


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", s)


def renda_bairro_ipece(cidade: str, uf: str, bairro: str) -> dict | None:
    """Linha do `ipece_renda_bairro` p/ o bairro (renda_resp, renda_pc, percentil, ranking)."""
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not (os.environ.get("SUPABASE_URL") and key and (bairro or "").strip()):
        return None
    try:
        from tools.supabase_client import load_create_client

        cli = load_create_client()(os.environ["SUPABASE_URL"], key)
        res = (cli.table("ipece_renda_bairro").select("*")
               .eq("bairro_norm", _norm(bairro)).limit(1).execute())
        rows = getattr(res, "data", None) or []
        return rows[0] if rows else None
    except Exception as exc:
        print(f"[posicionamento] renda IPECE indisponível: {type(exc).__name__}: {exc}")
        return None


def _mediana_ticket_concorrentes(concorrentes: list[dict]) -> tuple[float | None, str]:
    """Mediana do ticket praticado pelos concorrentes (planos_precos > nivel_preco)."""
    tickets: list[float] = []
    for c in concorrentes or []:
        planos = c.get("planos_precos") or []
        if isinstance(planos, list):
            for p in planos:
                v = (p or {}).get("valor") if isinstance(p, dict) else None
                try:
                    if v and 30 <= float(v) <= 2000:
                        tickets.append(float(v))
                except (TypeError, ValueError):
                    continue
    if tickets:
        return round(statistics.median(tickets), 2), "planos_precos_concorrentes"
    return None, "indisponivel"


def avaliar_posicionamento(
    cidade: str, uf: str, bairro: str,
    *,
    concorrentes: list[dict] | None = None,
    ticket_mercado: float | None = None,
    densidade_premium_baixa: bool = True,
) -> dict[str, Any]:
    """Veredito de posicionamento DETERMINÍSTICO via headroom de renda + percentil.

    ticket_mercado explícito tem precedência; senão calcula a mediana dos concorrentes.
    densidade_premium_baixa confirma o gap (poucos players premium no raio).
    """
    renda = renda_bairro_ipece(cidade, uf, bairro)
    if not renda:
        return {"status": "sem_renda_ipece", "bairro": bairro, "cidade": cidade,
                "veredito_posicionamento": None,
                "nota": "bairro fora do IPECE 272 (só Fortaleza) — A9 cai no fallback narrativo"}

    renda_pc = float(renda.get("renda_pc") or 0)
    percentil = float(renda.get("percentil") or 0)
    ticket_teto = round(renda_pc * param("ticket_renda_pct_premium"), 2)

    if ticket_mercado is None:
        ticket_mercado, fonte_ticket = _mediana_ticket_concorrentes(concorrentes or [])
    else:
        fonte_ticket = "informado"

    headroom = ratio = None
    if ticket_mercado and ticket_mercado > 0:
        headroom = round(ticket_teto - ticket_mercado, 2)
        ratio = round(ticket_teto / ticket_mercado, 2)

    # Tier de modelo por percentil (data-driven)
    if percentil >= param("renda_percentil_premium"):
        tier_modelo = "Premium"
    elif percentil >= param("renda_percentil_mid"):
        tier_modelo = "Mid Market"
    else:
        tier_modelo = "Low Cost"

    # Veredito determinístico
    if ratio is None:
        veredito = "INDETERMINADO"
    elif ratio >= param("headroom_ratio_oceano_azul") and densidade_premium_baixa:
        veredito = "OCEANO_AZUL"
    elif ratio >= param("headroom_ratio_transicao"):
        veredito = "TRANSICAO"
    else:
        veredito = "VERMELHO"

    return {
        "status": "ok",
        "bairro": renda.get("bairro"), "cidade": cidade, "uf": uf,
        "renda_resp_domicilio": float(renda.get("renda_resp_domicilio") or 0),
        "renda_pc": renda_pc,
        "renda_percentil": percentil,
        "ranking_cidade": renda.get("ranking"),
        "tier_modelo_percentil": tier_modelo,
        "ticket_teto_sustentavel": ticket_teto,
        "ticket_mercado": ticket_mercado,
        "fonte_ticket_mercado": fonte_ticket,
        "headroom_premium": headroom,
        "headroom_ratio": ratio,
        "veredito_posicionamento": veredito,
        "fonte_renda": renda.get("fonte"),
        "ano_renda": renda.get("ano"),
        "metodo": "headroom = renda_pc×ticket_renda_pct_premium − ticket_mercado; cutoffs via param()",
    }
