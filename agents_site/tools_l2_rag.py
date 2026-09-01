"""L2 RAG facades — Eros then local corpus; no Vertex Discovery."""
from __future__ import annotations

import logging
import os
from typing import Callable

from agents_site.tools_eros import (
    consultar_eros_engenharia,
    consultar_eros_mercado,
    consultar_eros_regulatorio,
    consultar_eros_tecnico,
)

logger = logging.getLogger("gymsite.agents_site.tools_l2")

def _pack_eros_as_resultados(eros: dict, fonte: str) -> dict | None:
    """Normaliza resposta Eros → shape `{resultados,n_docs,fonte}` dos facades.

    None = sem conteúdo útil (caller tenta próximo backend ou stub).
    """
    if not isinstance(eros, dict):
        return None
    fontes = eros.get("fontes") or []
    if not isinstance(fontes, list):
        fontes = []
    resultados: list[dict] = []
    for f in fontes:
        if not isinstance(f, dict):
            continue
        resultados.append({
            "titulo": f.get("title") or f.get("titulo") or "Documento",
            "uri": f.get("url") or f.get("uri") or "",
            "trecho": f.get("snippet") or f.get("trecho") or "",
        })
    texto = (eros.get("texto_rag") or "").strip()
    if not resultados and texto:
        resultados = [{
            "titulo": fonte,
            "uri": "",
            "trecho": texto[:1200],
        }]
    n = len(resultados) or int(eros.get("n_docs") or 0)
    if not n and not texto:
        return None
    return {
        "resultados": resultados,
        "n_docs": n or len(resultados),
        "fonte": fonte,
        "texto_rag": texto,
        "status": "ok",
    }


def _rag_cascade(
    pergunta: str,
    *,
    eros_env: str,
    eros_fn: Callable[[str], dict],
    dominio_corpus: str,
    fonte_eros: str,
    eros_payload: dict | None = None,
) -> dict:
    """L2: Eros (se grupo set) → corpus local → stub vazio. Sem Discovery."""
    if (os.getenv(eros_env) or "").strip():
        eros = eros_payload if eros_payload is not None else eros_fn(pergunta)
        packed = _pack_eros_as_resultados(eros, fonte_eros)
        if packed and packed.get("n_docs", 0) > 0:
            return packed
        if isinstance(eros, dict) and eros.get("erro") and "eros_config_ausente" not in str(
            eros.get("erro")
        ):
            logger.warning("rag_cascade eros %s: %s", eros_env, eros.get("erro"))

    from agents_site.corpus_local import buscar_corpus_local

    local = buscar_corpus_local(pergunta, dominio=dominio_corpus, n=4)  # type: ignore[arg-type]
    if local.get("n_docs", 0) > 0:
        return local
    return {
        "resultados": [],
        "n_docs": 0,
        "fonte": f"corpus_local/{dominio_corpus}+eros",
        "status": "vazio",
        "aviso_usuario": (
            "A base qualitativa não cobriu esta pergunta. "
            "Use tools de números (Maps/IBGE) quando couber, ou diga que não há trecho."
        ),
    }


def consultar_catalogo_equipamentos(pergunta: str) -> dict:
    """Consulta os CATÁLOGOS de fornecedores de equipamento de academia (Matrix,
    Life Fitness, Total Health) na base de conhecimento. Use SEMPRE antes de citar
    qualquer modelo, código, especificação, dimensão ou carga máxima de um equipamento.

    Ordem: (1) Eros se `EROS_GROUP_ID_TECNICO`; (2) corpus local; (3) stub limpo.

    Args:
        pergunta: o que buscar no catálogo, em linguagem natural
            (ex.: "leg press 45 graus Life Fitness", "esteira Matrix dimensões").

    Returns:
        dict com `resultados` (lista de {titulo, uri, trecho}), `n_docs` e `fonte`.
        Se vier vazio, o modelo NÃO existe no catálogo — não invente.
    """
    return _rag_cascade(
        pergunta,
        eros_env="EROS_GROUP_ID_TECNICO",
        eros_fn=consultar_eros_tecnico,
        dominio_corpus="tecnico",
        fonte_eros="Eros RAG (catálogo equipamentos)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DADOS / VIABILIDADE — port do consultor_engine (Fase 0 da migração ADK).
# Reusam os mesmos tools.* por baixo; params explícitos p/ o schema do ADK.
# (reviews/oferta/relatório dependem de cache/estado → Fase 2.)
# ─────────────────────────────────────────────────────────────────────────────

_HVAC_HINTS = (
    "refriger", "climatiz", "ar-cond", "ar cond", "hvac", "16401",
    "renova", "pmoc", "carga term", "carga térm", "btu", "exaust",
)


def consultar_engenharia_obra(pergunta: str) -> dict:
    """Consulta a base de ENGENHARIA DE OBRA, PROJETO ARQUITETÔNICO e LAYOUT de academia
    (normas ABNT, licenças, estrutura/laje, instalações, acústica, incêndio, acessibilidade,
    sanitários/vestiários, pisos, etapas de projeto, checklists retrofit × obra do zero). Use
    SEMPRE antes de afirmar uma exigência de obra, norma, valor estrutural ou regra de projeto.

    Ordem: (1) Eros `EROS_GROUP_ID_ENGENHARIA` (+ reforço HVAC); (2) corpus local; (3) stub.

    Args:
        pergunta: o que buscar em linguagem natural (ex.: "carga de laje academia NBR 6120",
            "alvará de reforma vs construção", "sanitários por lotação", "isolamento acústico peso").

    Returns:
        dict com `resultados` (lista de {titulo, uri, trecho}), `n_docs` e `fonte`.
        Vazio = a base não cobre; oriente consultar engenheiro/arquiteto e órgão local, não invente.
        Se n_docs>0 e o trecho cita norma/número, USE com carimbo — não diga que a base falhou.
    """
    from agents_site.carimbo import anotar_retrieval_legal

    eros_payload = None
    if (os.getenv("EROS_GROUP_ID_ENGENHARIA") or "").strip():
        q = (pergunta or "").lower()
        eros = consultar_eros_engenharia(pergunta)
        if any(h in q for h in _HVAC_HINTS):
            import re

            area_m = re.search(r"(\d{2,4})\s*(?:m(?:2|²)|mts?|metros?)", q)
            area_bit = ""
            if area_m:
                area_bit = (
                    f" sala {area_m.group(1)} m2 exemplo ocupantes vazão l/s carga térmica BTU"
                )
            eros_hvac = consultar_eros_engenharia(
                "NBR 16401-3 vazão ar exterior academia PMOC split renovação carga térmica coletivas"
                + area_bit
            )
            t1 = (eros_hvac.get("texto_rag") or "").strip()
            t0 = (eros.get("texto_rag") or "").strip()
            if t1:
                merged_text = t1 if not t0 else f"{t1}\n\n{t0}"
                eros = {
                    **eros_hvac,
                    "texto_rag": merged_text[:8000],
                    "fontes": (eros_hvac.get("fontes") or []) + (eros.get("fontes") or []),
                    "n_docs": int(eros_hvac.get("n_docs") or 0)
                    + int(eros.get("n_docs") or 0),
                }
        eros_payload = eros

    r = _rag_cascade(
        pergunta,
        eros_env="EROS_GROUP_ID_ENGENHARIA",
        eros_fn=consultar_eros_engenharia,
        dominio_corpus="engenharia",
        fonte_eros="Eros RAG (engenharia de obra / projeto)",
        eros_payload=eros_payload,
    )
    return anotar_retrieval_legal(r, r.get("fonte") or "RAG engenharia")


def consultar_base_regulatoria(pergunta: str) -> dict:
    """Consulta a base REGULATÓRIA dedicada (documentos CONFEF/CREF, Lei 9.696/1998,
    anuidades, registro PJ, licenças de funcionamento). Use SEMPRE antes de afirmar uma
    exigência legal, valor de anuidade, prazo ou regra.

    Ordem: (1) Eros `EROS_GROUP_ID_REGULATORIO`; (2) corpus local; (3) stub.

    Args:
        pergunta: o que buscar, em linguagem natural
            (ex.: "registro CREF pessoa jurídica", "Lei 9.696 quem pode dar aula").

    Returns:
        dict com `resultados` (lista de {titulo, uri, trecho}), `n_docs` e `fonte`.
        Se vier vazio, a base não cobre — oriente confirmar no CREF/prefeitura, não invente.
    """
    from agents_site.carimbo import anotar_retrieval_legal

    r = _rag_cascade(
        pergunta,
        eros_env="EROS_GROUP_ID_REGULATORIO",
        eros_fn=consultar_eros_regulatorio,
        dominio_corpus="regulatorio",
        fonte_eros="Eros RAG (regulatório CREF/Lei)",
    )
    return anotar_retrieval_legal(r, r.get("fonte") or "RAG regulatório")


_AGREGADOR_ROTAS: tuple[tuple[tuple[str, ...], str, str, str], ...] = (
    (("wellhub", "gympass", "well hub"), "EROS_GROUP_ID_WELLHUB", "consultar_eros_wellhub", "Eros RAG (Wellhub)"),
    (("totalpass", "total pass"), "EROS_GROUP_ID_TOTALPASS", "consultar_eros_totalpass", "Eros RAG (TotalPass)"),
    (("gurupass", "guru pass"), "EROS_GROUP_ID_GURUPASS", "consultar_eros_gurupass", "Eros RAG (GuruPass)"),
)

def _merge_agregador_hits(hits: list[dict]) -> dict:
    if len(hits) == 1:
        return hits[0]
    resultados: list[dict] = []
    textos: list[str] = []
    fontes: list[str] = []
    n = 0
    for h in hits:
        resultados.extend(h.get("resultados") or [])
        n += int(h.get("n_docs") or 0)
        fonte = (h.get("fonte") or "").strip()
        if fonte:
            fontes.append(fonte)
        t = (h.get("texto_rag") or "").strip()
        if t:
            textos.append(f"{fonte}: {t}" if fonte else t)
    return {
        "resultados": resultados,
        "n_docs": n or len(resultados),
        "fonte": " + ".join(fontes) if fontes else "Eros RAG (agregadores)",
        "texto_rag": "\n\n".join(textos),
    }


def _consultar_agregador_eros(pergunta: str) -> dict | None:
    import agents_site.tools_eros as eros

    q = (pergunta or "").casefold()
    hits: list[dict] = []
    for keys, env, fn_name, fonte in _AGREGADOR_ROTAS:
        if not any(k in q for k in keys):
            continue
        if not (os.getenv(env) or "").strip():
            continue
        fn = getattr(eros, fn_name)
        packed = _pack_eros_as_resultados(fn(pergunta), fonte)
        if packed and packed.get("n_docs", 0) > 0:
            hits.append(packed)
    if not hits:
        return None
    return _merge_agregador_hits(hits)


def consultar_base_mercado(pergunta: str) -> dict:
    """Consulta a base de MERCADO (metodologia GymSite, benchmarks, franquias, tendências).

    Ordem: (0) share credenciadas Brasil/município se a pergunta for market share;
    (1) catálogo agregador Eros se citar Wellhub/TotalPass/GuruPass;
    (2) Eros metodologia se `EROS_GROUP_ID_MERCADO` set; (3) corpus local; (4) stub.

    NÃO use para saturação/contagem (isso é `buscar_concorrentes` + `nivel_saturacao`).
    NÃO use para exigência legal (`consultar_base_regulatoria` / Eros regulatório).

    Returns:
        dict com `resultados`/`texto_rag`, `n_docs`, `fonte`, e opcionalmente
        `status`=`vazio` + `aviso_usuario` quando a base qualitativa não cobre.
    """
    from agents_site.agregador_share import consultar_share_agregadores, is_share_agregadores

    if is_share_agregadores(pergunta):
        return consultar_share_agregadores(pergunta)
    hit = _consultar_agregador_eros(pergunta)
    if hit:
        return hit
    return _rag_cascade(
        pergunta,
        eros_env="EROS_GROUP_ID_MERCADO",
        eros_fn=consultar_eros_mercado,
        dominio_corpus="mercado",
        fonte_eros="Eros RAG (mercado)",
    )

