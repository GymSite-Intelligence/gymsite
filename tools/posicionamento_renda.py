"""
Posicionamento por headroom de renda — DETERMINÍSTICO, sourced.

Spec: docs/metodologia/posicionamento_headroom_premium.md
Fonte de renda: tabela Supabase `renda_bairro` (IBGE Censo 2022 nacional, 17k bairros).
(`ipece_renda_bairro` é legada — só Fortaleza, sem reconciliação ativa.)

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


# Bairros POPULARES ausentes da base → vizinho/RA coberto MESMO tier. APROXIMAÇÃO
# (resultado marca `fonte`). Alias errado injeta renda errada — conservador.
# SP capital: ainda sem camada bairro/distrito na base (não mapear Moema→outro município).
# DF: PDAD 2024 cobre RAs; aliases Receita (Asa Norte, Samambaia Sul) → RA administrativa.
_ALIAS_BAIRRO: dict[tuple[str, str], str] = {
    ("DF", "asa norte"): "Plano Piloto",
    ("DF", "asa sul"): "Plano Piloto",
    ("DF", "noroeste"): "Plano Piloto",
    ("DF", "samambaia sul"): "Samambaia",
    ("DF", "samambaia norte"): "Samambaia",
    ("DF", "samambaia sul (samambaia)"): "Samambaia",
    ("DF", "taguatinga norte"): "Taguatinga",
    ("DF", "taguatinga sul"): "Taguatinga",
    ("DF", "ceilandia norte"): "Ceilândia",
    ("DF", "ceilandia sul"): "Ceilândia",
    ("DF", "guara i"): "Guará",
    ("DF", "guara ii"): "Guará",
    ("DF", "estrutural"): "SCIA/Estrutural",
    ("DF", "scia"): "SCIA/Estrutural",
    ("DF", "octogonal"): "Sudoeste/Octogonal",
    ("DF", "sudoeste"): "Sudoeste/Octogonal",
    # RJ — base renda_bairro usa "Lagoa"; nome longo (geocode/OSM) → chave da tabela.
    ("RJ", "lagoa rodrigo de freitas"): "Lagoa",
    ("RJ", "rodrigo de freitas"): "Lagoa",
}


def renda_bairro_ipece(cidade: str, uf: str, bairro: str) -> dict | None:
    """Renda do bairro — fonte NACIONAL `renda_bairro` (IBGE Censo 2022, 17k bairros).

    Filtra por uf+bairro_norm (refina por cidade quando bate). Retorna dict com chaves
    normalizadas (renda_pc, percentil, ranking, renda_resp_domicilio, fonte, ano) p/ o
    avaliar_posicionamento consumir igual. Funciona em qualquer cidade com bairros IBGE.

    Bairro popular ausente da base (ex: Moema/SP) → resolve via `_ALIAS_BAIRRO` pro vizinho
    coberto de mesmo tier; o resultado marca `fonte` como aproximação + `_alias`.
    """
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not (os.environ.get("SUPABASE_URL") and key and (bairro or "").strip()):
        return None
    try:
        from tools.supabase_client import load_create_client

        cli = load_create_client()(os.environ["SUPABASE_URL"], key)
        # (a) alias: bairro popular ausente → vizinho coberto de mesmo tier
        bn = _norm(bairro)
        alias = _ALIAS_BAIRRO.get(((uf or "").strip().upper(), bn))
        bn_query = _norm(alias) if alias else bn
        q = cli.table("renda_bairro").select("*").eq("bairro_norm", bn_query)
        if (uf or "").strip():
            q = q.eq("uf", uf.strip().upper())
        rows = getattr(q.limit(5).execute(), "data", None) or []
        if not rows:
            return None
        # refina pela cidade quando houver match (evita bairro homônimo em outra cidade)
        cnorm = _norm(cidade)
        pick = next((r for r in rows if _norm(r.get("cidade") or "") == cnorm), None)
        if pick is None:
            # Homônimos (ex.: Lagoa em Macaé vs Rio) — sem match de cidade não inventa.
            if len(rows) > 1:
                return None
            pick = rows[0]
        # (c) transparência: marca a fonte quando veio por alias (aproximação)
        fonte = pick.get("fonte")
        if alias:
            fonte = f"{fonte} [aprox. via bairro vizinho '{alias}' — '{bairro}' ausente na base IBGE]"
        return {
            "bairro": pick.get("bairro"), "renda_resp_domicilio": pick.get("renda_media"),
            "renda_pc": pick.get("renda_pc"), "percentil": pick.get("percentil_municipio"),
            "ranking": pick.get("ranking_municipio"), "fonte": fonte,
            "ano": pick.get("ano"), "_alias_bairro": alias or None,
        }
    except Exception as exc:
        print(f"[posicionamento] renda_bairro indisponível: {type(exc).__name__}: {exc}")
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


# ── 6 Zonas de Percepção (Zonas de Valor — Luiza Castanho) ───────────────────
# PLANO_MOTOR_FINANCEIRO_V3 §2.1. Substitui o veredito de 3 caixas (OCEANO_AZUL/
# TRANSICAO/VERMELHO) por um raio-X de posicionamento em 6 zonas. A classificação é
# DETERMINÍSTICA, a partir do headroom de renda (ratio = ticket_teto / ticket_mercado),
# do tier de renda, da densidade competitiva e da contagem de gaps reais.
#   1 Comodidade — oceano vermelho, só preço (sem headroom).
#   2 Satisfação — conveniência, sem diferenciação.
#   3 Resultado — custo-benefício, "teto de vidro".
#   4 Superação — inovação (há gaps OU densidade baixa).
#   5 Excelência — status/prestígio (Premium + gaps + densidade baixa).
#   6 Culto/Pertença — pertença; o PDF afirma que NÃO existe marca no Brasil na Zona 6,
#     então NUNCA é atribuída automaticamente (alvo aspiracional citado no texto).
_ZONAS_PERCEPCAO = {
    1: ("Comodidade", "Oceano vermelho — competição só por preço, sem headroom de renda."),
    2: ("Satisfação", "Conveniência e proximidade — entrega o básico, sem diferenciação."),
    3: ("Resultado", "Custo-benefício e entrega de resultado — 'teto de vidro' do mid-market."),
    4: ("Superação", "Inovação e experiência superior — há espaço real acima do mercado."),
    5: ("Excelência", "Status e prestígio — marca premium com diferenciação defensável."),
    6: ("Culto/Pertença", "Pertença e identidade — inexistente no Brasil; alvo aspiracional, nunca calculado."),
}


def classificar_zona_percepcao(
    ratio: float | None,
    tier: str | None,
    densidade_baixa: bool,
    tem_gaps: bool,
) -> dict:
    """Classifica a Zona de Percepção (1..5) a partir dos sinais determinísticos.

    Limiares EXATOS do §2.1 (PLANO_MOTOR_FINANCEIRO_V3 / Zonas de Valor de Luiza Castanho):
      - ratio < 1.0                        → Zona 1 (Comodidade)
      - 1.0 ≤ ratio < 1.2                  → Zona 2 (Satisfação)
      - 1.2 ≤ ratio < 2.0                  → Zona 3 (Resultado)
      - ratio ≥ 2.0 + (gaps OU dens.baixa) → Zona 4 (Superação)
      - ratio ≥ 2.0 + Premium + gaps + dens.baixa → Zona 5 (Excelência)
    Zona 6 (Culto) NUNCA é atribuída automaticamente.
    Ordem: avalia Zona 5 (mais restritiva) ANTES da Zona 4.
    Sem ratio → cai na Zona 1 (sem sinal de headroom = posição de preço por padrão).
    """
    r = ratio if isinstance(ratio, (int, float)) else 0.0
    is_premium = str(tier or "").strip().lower() == "premium"

    if r >= 2.0:
        # Zona 5 primeiro (mais restritiva): Premium + gaps reais + densidade baixa.
        if is_premium and tem_gaps and densidade_baixa:
            zona = 5
        elif tem_gaps or densidade_baixa:
            zona = 4
        else:
            # ratio alto mas sem gaps nem densidade baixa → ainda é "Resultado".
            zona = 3
    elif r >= 1.2:
        zona = 3
    elif r >= 1.0:
        zona = 2
    else:
        zona = 1

    nome, descricao = _ZONAS_PERCEPCAO[zona]
    return {"zona": zona, "nome": nome, "descricao": descricao}


def veredito_legado_de_zona(zona: int | None) -> str | None:
    """Deriva o veredito legado (compat) a partir da Zona de Percepção.
    Zona 1-2 → VERMELHO; Zona 3 → TRANSICAO; Zona 4-5 → OCEANO_AZUL. §2.1."""
    if zona in (1, 2):
        return "VERMELHO"
    if zona == 3:
        return "TRANSICAO"
    if zona in (4, 5):
        return "OCEANO_AZUL"
    return None


def avaliar_posicionamento(
    cidade: str, uf: str, bairro: str,
    *,
    concorrentes: list[dict] | None = None,
    ticket_mercado: float | None = None,
    densidade_premium_baixa: bool = True,
    tem_gaps: bool = False,
) -> dict[str, Any]:
    """Veredito de posicionamento DETERMINÍSTICO via headroom de renda + percentil.

    ticket_mercado explícito tem precedência; senão calcula a mediana dos concorrentes.
    densidade_premium_baixa confirma o gap (poucos players premium no raio).
    tem_gaps sinaliza serviços que nenhum concorrente oferece (substrato da Zona 4/5).

    Classifica a Zona de Percepção (§2.1) e DERIVA o veredito legado dela (compat).
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

    # Zona de Percepção (§2.1) — nasce do ratio/tier/densidade/gaps; veredito legado DERIVA dela.
    if ratio is None:
        zona = None
        veredito = "INDETERMINADO"
        zona_info = {"zona": None, "nome": None, "descricao": None}
    else:
        zona_info = classificar_zona_percepcao(
            ratio, tier_modelo, densidade_baixa=bool(densidade_premium_baixa), tem_gaps=bool(tem_gaps)
        )
        zona = zona_info["zona"]
        veredito = veredito_legado_de_zona(zona) or "INDETERMINADO"

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
        # §2.1 — 6 Zonas de Percepção (substitui o veredito de 3 caixas; legado derivado).
        "zona_percepcao": zona,
        "zona_nome": zona_info["nome"],
        "zona_descricao": zona_info["descricao"],
        "veredito_posicionamento": veredito,  # legado (compat): derivado da zona
        "fonte_renda": renda.get("fonte"),
        "ano_renda": renda.get("ano"),
        "metodo": "zona = f(headroom_ratio, tier, densidade, gaps); veredito legado derivado da zona; cutoffs via param()",
    }
