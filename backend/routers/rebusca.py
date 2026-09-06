"""
Router /api/relatorios/{id}/rebuscar-candidatos — re-busca cirúrgica (Motor v2.0).

Re-executa SÓ a caça de imóveis (OLX+ImovelWeb) para um relatório pronto,
sem tocar no resto do pipeline. Aplica o gate de elegibilidade da spec
MOTOR_CANDIDATOS_V2: fora da cidade ou tipo residencial reprova; fora do
bairro alvo e preço suspeito viram avisos (re-busca ampliada aceita bairro
adjacente por definição). Reprovados voltam na resposta com as flags —
não são persistidos.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from supabase import create_client

from tools.listing_tools import fetch_commercial_listings_async

logger = logging.getLogger("gymsite.rebusca")

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios — Re-busca"])

_TIPOS_RESIDENCIAIS = ("casa", "apartamento", "terreno", "fração", "fracao")
_RS_M2_MINIMO_LOCACAO = 8.0  # abaixo disso a área anunciada é quase sempre de terreno


def _sb():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    return create_client(url, key)


def _require_user(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        user = _sb().auth.get_user(token).user
    except Exception:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    return user.id


def _preco_numerico(price_raw: str) -> Optional[float]:
    if not price_raw:
        return None
    m = re.search(r"R\$\s*([\d.]+(?:,\d{2})?)", price_raw)
    if not m:
        return None
    try:
        return float(m.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _normalizar(texto: str) -> str:
    texto = (texto or "").lower()
    trocas = {"á": "a", "à": "a", "â": "a", "ã": "a", "é": "e", "ê": "e",
              "í": "i", "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c"}
    for de, para in trocas.items():
        texto = texto.replace(de, para)
    return texto


def aplicar_gate(listing, bairro_alvo: str, cidade_alvo: str) -> tuple[bool, list[str]]:
    """Gate v2.0 da spec: (aprovado, flags). Reprovam: fora da cidade,
    tipo residencial. Avisam: fora do bairro alvo, preço suspeito."""
    flags: list[str] = []
    addr = _normalizar(listing.address)
    bairro = _normalizar(bairro_alvo)
    cidade = _normalizar(cidade_alvo)

    no_bairro = bool(bairro) and bairro in addr
    na_cidade = bool(cidade) and cidade in addr
    if not no_bairro:
        flags.append("fora_do_bairro_alvo")
    if not na_cidade and not no_bairro:
        flags.append("fora_da_cidade")

    label = _normalizar(listing.tipo_imovel_label or "")
    if any(t in label for t in _TIPOS_RESIDENCIAIS):
        flags.append("tipo_incompativel")

    preco = listing.price_numeric or _preco_numerico(listing.price_raw)
    if preco and listing.area_m2:
        rs_m2 = preco / listing.area_m2
        if rs_m2 < _RS_M2_MINIMO_LOCACAO:
            flags.append("preco_suspeito_area_de_terreno")

    aprovado = "fora_da_cidade" not in flags and "tipo_incompativel" not in flags
    return aprovado, flags


class RebuscaRequest(BaseModel):
    max_candidatos: int = Field(5, ge=1, le=10)


@router.post("/{relatorio_id}/rebuscar-candidatos")
async def rebuscar_candidatos(relatorio_id: str, data: RebuscaRequest, request: Request):
    user_id = _require_user(request)
    sb = _sb()

    rel = (
        sb.table("relatorios")
        .select("id, user_id, status")
        .eq("id", relatorio_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not rel or not rel.data:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    # Fail-closed: empty/missing owner must not skip ownership (IDOR).
    owner_id = rel.data.get("user_id") or ""
    if not owner_id or owner_id != user_id:
        raise HTTPException(status_code=403, detail="Este relatório pertence a outra conta")
    if rel.data.get("status") != "done":
        raise HTTPException(status_code=400, detail="Espere a análise terminar antes de re-buscar pontos.")

    inputs = (
        sb.table("relatorio_inputs")
        .select("cidade, uf, bairro, area_m2_min, area_m2_max")
        .eq("relatorio_id", relatorio_id)
        .maybe_single()
        .execute()
    )
    if not inputs or not inputs.data:
        raise HTTPException(status_code=400, detail="Relatório sem parâmetros de busca.")
    cidade = inputs.data.get("cidade") or ""
    uf = inputs.data.get("uf") or ""
    bairro = inputs.data.get("bairro") or ""
    area_min = int(inputs.data.get("area_m2_min") or 800)
    area_max = int(inputs.data.get("area_m2_max") or 2000)

    listings = await fetch_commercial_listings_async(cidade, uf, area_min, area_max)

    existentes = (
        sb.table("candidatos")
        .select("listing_id, posicao")
        .eq("relatorio_id", relatorio_id)
        .execute()
    ).data or []
    ids_existentes = {c.get("listing_id") for c in existentes if c.get("listing_id")}
    proxima_posicao = max((c.get("posicao") or 0 for c in existentes), default=0) + 1

    aprovados: list[dict[str, Any]] = []
    reprovados: list[dict[str, Any]] = []
    for l in listings:
        if l.listing_id and l.listing_id in ids_existentes:
            continue
        ok, flags = aplicar_gate(l, bairro, cidade)
        resumo = {
            "nome": f"Imóvel anunciado · {l.area_m2}m² · {l.source.upper()}",
            "endereco": l.address,
            "area_m2": l.area_m2,
            "preco": l.price_raw,
            "tipo": l.tipo_imovel_label,
            "listing_url": l.listing_url,
            "flags": flags,
        }
        if ok and len(aprovados) < data.max_candidatos:
            avisos = f" Avisos do gate: {', '.join(flags)}." if flags else ""
            aprovados.append({
                "relatorio_id": relatorio_id,
                "posicao": proxima_posicao + len(aprovados),
                "place_id": f"listing_{l.source}_{l.listing_id or l.area_m2}_rebusca",
                "nome": resumo["nome"],
                "endereco": l.address or "Endereço não disponível",
                "tipo": "imovel_anunciado",
                "area_estimada_m2": l.area_m2,
                "qualidade_sinal": "rebusca-ampliada",
                "listing_url": l.listing_url,
                "listing_id": l.listing_id,
                "price_raw": l.price_raw,
                "listing_source": l.source,
                "tipo_imovel_codigo_onr": l.tipo_imovel_codigo_onr,
                "tipo_imovel_label": l.tipo_imovel_label,
                "modalidade": l.modalidade or "locacao",
                "motivo": (
                    f"Re-busca ampliada (gate v2): oferta ativa em {l.source.upper()} — "
                    f"{l.price_raw or 'preço a confirmar'}.{avisos}"
                ),
                "proximo_passo": "Validar no anúncio e agendar visita.",
            })
        elif not ok:
            reprovados.append(resumo)

    if aprovados:
        sb.table("candidatos").insert(aprovados).execute()

    logger.info(
        "rebusca %s: %d brutos, %d aprovados, %d reprovados",
        relatorio_id, len(listings), len(aprovados), len(reprovados),
    )
    return {
        "encontrados": len(listings),
        "aprovados": len(aprovados),
        "reprovados": reprovados[:10],
        "candidatos_novos": [
            {"nome": a["nome"], "endereco": a["endereco"], "motivo": a["motivo"]}
            for a in aprovados
        ],
    }
