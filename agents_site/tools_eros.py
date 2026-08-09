"""Eros RAG factory — Edge Function knowledge-ask."""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("gymsite.agents_site.tools_eros")

# ─────────────────────────────────────────────────────────────────────────────
# Eros RAG — Edge Function Supabase `knowledge-ask` (groupId por especialista)
# ─────────────────────────────────────────────────────────────────────────────

_EROS_GROUP_SUFFIX = {
    "EROS_GROUP_ID_REGULATORIO": "regulatorio",
    "EROS_GROUP_ID_TECNICO": "tecnico",
    "EROS_GROUP_ID_ARQUITETO": "arquiteto",
    "EROS_GROUP_ID_ENGENHARIA": "engenharia",
    "EROS_GROUP_ID_MERCADO": "mercado",
}


def criar_tool_consultar_eros(grupo_id_env: str):
    """Fábrica: tool `consultar_eros_*` → Edge Function Supabase `knowledge-ask` (Eros RAG).

    Cada instância lê o UUID do grupo em `grupo_id_env` e expõe nome ADK único
    (`consultar_eros_regulatorio`, …) para grounding + inject de `sources` no polling.
    """
    suffix = _EROS_GROUP_SUFFIX.get(
        grupo_id_env,
        grupo_id_env.replace("EROS_GROUP_ID_", "").lower(),
    )
    tool_name = f"consultar_eros_{suffix}"

    def consultar_eros_conhecimento(pergunta: str) -> dict:
        grupo_uuid = (os.getenv(grupo_id_env) or "").strip()
        # Arquiteto compartilha corpus de obra até existir grupo próprio no Eros.
        if not grupo_uuid and grupo_id_env == "EROS_GROUP_ID_ARQUITETO":
            grupo_uuid = (os.getenv("EROS_GROUP_ID_ENGENHARIA") or "").strip()
        # Projeto Eros (assistent-control) ≠ GymSite/cargo-flow Supabase.
        base = (
            os.getenv("EROS_SUPABASE_URL")
            or os.getenv("SUPABASE_URL")
            or ""
        ).rstrip("/")
        key = (
            os.getenv("EROS_SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or ""
        )
        if not grupo_uuid or not base or not key:
            return {
                "texto_rag": "",
                "fontes": [],
                "n_docs": 0,
                "erro": (
                    f"eros_config_ausente: defina {grupo_id_env}, "
                    "EROS_SUPABASE_URL e EROS_SUPABASE_SERVICE_ROLE_KEY"
                ),
            }
        try:
            resp = httpx.post(
                f"{base}/functions/v1/knowledge-ask",
                headers={
                    "Authorization": f"Bearer {key}",
                    "apikey": key,
                    "Content-Type": "application/json",
                },
                json={
                    "groupId": grupo_uuid,
                    "messages": [{"role": "user", "content": (pergunta or "")[:4000]}],
                },
                timeout=60.0,
            )
            if resp.status_code >= 400:
                detail = (resp.text or "")[:300]
                logger.warning(
                    "%s HTTP %s: %s", tool_name, resp.status_code, detail
                )
                return {
                    "texto_rag": "",
                    "fontes": [],
                    "n_docs": 0,
                    "erro": f"falha_conexao_eros: HTTP {resp.status_code} {detail}",
                }
            data = resp.json() if resp.content else {}
            if not isinstance(data, dict):
                data = {}
            sources = data.get("sources") or data.get("fontes") or []
            if not isinstance(sources, list):
                sources = []
            return {
                "texto_rag": data.get("text") or data.get("texto_rag") or "",
                "fontes": sources,
                "n_docs": len(sources),
                "fonte": "Eros RAG",
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("%s falhou", tool_name)
            return {
                "texto_rag": "",
                "fontes": [],
                "n_docs": 0,
                "erro": f"falha_conexao_eros: {e}",
            }

    consultar_eros_conhecimento.__name__ = tool_name
    consultar_eros_conhecimento.__qualname__ = tool_name
    consultar_eros_conhecimento.__doc__ = (
        f"Consulta a base Eros RAG ({suffix}). Use SEMPRE antes de afirmar fatos desta "
        "especialidade. Retorna `texto_rag` (fonte da verdade factual) e `fontes` "
        "(metadados para carimbo/citações).\n\n"
        "Args:\n"
        "    pergunta: o que buscar na base Eros, em linguagem natural.\n\n"
        "Returns:\n"
        "    dict com `texto_rag`, `fontes`, `n_docs` e `fonte`='Eros RAG'."
    )
    return consultar_eros_conhecimento


consultar_eros_regulatorio = criar_tool_consultar_eros("EROS_GROUP_ID_REGULATORIO")
consultar_eros_tecnico = criar_tool_consultar_eros("EROS_GROUP_ID_TECNICO")
consultar_eros_arquiteto = criar_tool_consultar_eros("EROS_GROUP_ID_ARQUITETO")
consultar_eros_engenharia = criar_tool_consultar_eros("EROS_GROUP_ID_ENGENHARIA")
consultar_eros_mercado = criar_tool_consultar_eros("EROS_GROUP_ID_MERCADO")
