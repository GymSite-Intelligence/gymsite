"""Roteamento de schema para a separação gymsite/shared (migração jun/2026).

CONTEXTO: as tabelas do GymSite estão sendo movidas de `public` para os schemas
`gymsite` (negócio) e `shared` (dado aberto/tenancy). Durante a transição há views
de compatibilidade em `public.<t>` (security_invoker) que cobrem LEITURA — mas
`INSERT ... ON CONFLICT` (upsert) NÃO funciona através de view. Então ESCRITA/upsert
tem que ir direto no schema real via `.schema()`.

Este módulo centraliza o roteamento. Enquanto `GYMSITE_SCHEMA_SEP` está OFF (default),
tudo aponta para `public` — ZERO mudança de comportamento (seguro pra mergear antes da
migração). Quando a leva G1/G2 do banco subir, liga a flag (deploy sincronizado) e as
chamadas que usam `tbl()`/`schema_de()` passam a apontar pro schema real.

Uso:
    from tools.db_schema import tbl
    tbl(sb, "competidor_intel_cache").upsert(reg, on_conflict="place_id").execute()
    # flag OFF → sb.table(...) (public);  flag ON → sb.schema("gymsite").table(...)
"""
from __future__ import annotations

import os

# Negócio GymSite → schema `gymsite`
_GYMSITE = frozenset({
    "relatorios", "relatorio_inputs", "relatorio_outputs", "relatorio_custos_agentes",
    "relatorio_api_calls", "candidatos", "competidores", "competidor_intel_cache",
    "cenarios_financeiros", "sensibilidade_cenarios", "bairros_alternativos", "prospects",
    "scout_jobs", "scout_eventos", "scout_messages", "scout_cadencia", "leads", "validacoes",
    "oportunidades_prospeccao", "otimizacoes_custo", "user_projects", "project_messages",
    "projeto_membros", "projeto_pessoas", "parceiro_leads", "playbooks", "sessions",
    "chat_interacoes", "cnpj_contato_cache", "cache_reviews", "analise_gratuita",
    "parametros_metodologia", "catalogos_metodologia",
    # caches/estado do pipeline GymSite (classificados jun/2026; alguns ainda não criados)
    "market_bundles", "market_snapshots", "relatorio_state_checkpoint",
    "cache_market_context", "cache_places_details", "cache_popular_times",
    "search_raw",
})

# Dado aberto + tenancy → schema `shared`
_SHARED = frozenset({
    "organizations", "organization_members", "cache_geocode",
    "cnpj_fitness_estabelecimentos", "cno_obras_fitness", "cno_obras_grande_porte",
    "censo_setor", "censo_setor_idade_sexo", "ipece_renda_bairro", "renda_bairro",
    "municipio_pib", "municipio_publico_sexo", "municipio_rf_ibge",
})


def _on(env: str) -> bool:
    return os.getenv(env, "").strip().lower() in {"1", "true", "yes", "on"}


def shared_migrado() -> bool:
    """shared já movido (levas S1/S2). Pode ligar independente do gymsite — os writers
    de open-data (loaders RFB/CNO/censo) precisam apontar pra shared.* após a leva S1,
    senão o upsert bate na view de compat e quebra."""
    return _on("SHARED_SCHEMA_SEP")


def gymsite_migrado() -> bool:
    """gymsite já movido (levas G1/G2). Liga junto com o deploy de código."""
    return _on("GYMSITE_SCHEMA_SEP")


def separacao_ligada() -> bool:
    """Compat: True se QUALQUER leva está ativa."""
    return shared_migrado() or gymsite_migrado()


def schema_de(tabela: str) -> str:
    """Schema de uma tabela, por leva. Flags por-schema (shared e gymsite são levas
    independentes). Default: 'public' (comportamento atual)."""
    if tabela in _SHARED and shared_migrado():
        return "shared"
    if tabela in _GYMSITE and gymsite_migrado():
        return "gymsite"
    return "public"


def tbl(sb, tabela: str):
    """Builder da tabela no schema correto. Use SEMPRE em ESCRITA/upsert (e pode usar em
    leitura também). Flag OFF → sb.table(tabela). Flag ON → sb.schema(<esc>).table(tabela)."""
    esc = schema_de(tabela)
    if esc == "public":
        return sb.table(tabela)
    return sb.schema(esc).table(tabela)


def rpc(sb, nome: str, params: dict, *, schema: str = "gymsite"):
    """Chama uma RPC no schema correto. Funções que escrevem em tabelas movidas (ex:
    marcar_pesquisa → user_projects) precisam morar no schema da tabela quando a flag liga."""
    if not separacao_ligada():
        return sb.rpc(nome, params)
    return sb.schema(schema).rpc(nome, params)
