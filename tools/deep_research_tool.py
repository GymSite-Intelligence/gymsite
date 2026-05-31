# tools/deep_research_tool.py
"""
Deep Research via Gemini Interactions API (agente gerenciado) + fallback grounded.

Tiers:
  1. Interactions API — agent deep-research-max (background + poll)
  2. generate_content — gemini-2.5-flash + google_search + url_context
  3. Briefing estático — se ambos falharem ou timeout global

Cache: market_context/{cidade}_{bairro}.md (TTL 7 dias)
Investigações por imóvel: market_context/investigations/{id}.md (TTL 3 dias)
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

# ── Config (env overrides) ───────────────────────────────────────────────────
CACHE_TTL_DIAS = 7
TIMEOUT_SEGUNDOS = int(os.getenv("DEEP_RESEARCH_TIMEOUT_SEC", "1200"))  # 20 min (doc Google)
POLL_INTERVAL_SEC = int(os.getenv("DEEP_RESEARCH_POLL_SEC", "10"))
DEEP_RESEARCH_AGENT = os.getenv(
    "DEEP_RESEARCH_AGENT",
    "deep-research-max-preview-04-2026",
)
# Alternativa mais rápida: deep-research-preview-04-2026
FALLBACK_MODEL = os.getenv("DEEP_RESEARCH_FALLBACK_MODEL", "gemini-2.5-flash")

CACHE_DIR = Path(__file__).resolve().parent.parent / "market_context"
INVESTIGACAO_CACHE_DIR = CACHE_DIR / "investigations"

INVESTIGACAO_TTL_DIAS = int(os.getenv("INVESTIGACAO_CACHE_TTL_DIAS", "3"))
INVESTIGACAO_MAX_POR_RELATORIO = int(os.getenv("INVESTIGACAO_MAX_POR_RELATORIO", "5"))
INVESTIGACAO_TIMEOUT_SEC = int(os.getenv("INVESTIGACAO_TIMEOUT_SEC", "180"))
INVESTIGACAO_USE_INTERACTIONS_TOP = int(
    os.getenv("INVESTIGACAO_USE_INTERACTIONS_TOP", "0")
)
INVESTIGACAO_DISABLED = os.getenv("INVESTIGACAO_DISABLED", "").lower() in (
    "1",
    "true",
    "yes",
)

_LISTING_TRIGGER_WORDS = (
    "ponto",
    "galpao",
    "galpão",
    "predio",
    "prédio",
    "loja",
    "comercial",
    "salao",
    "salão",
    "imovel",
    "imóvel",
)

# Último tier usado (útil em testes/diagnóstico)
_last_execution_tier: str | None = None


def get_last_execution_tier() -> str | None:
    """Tier da última execução bem-sucedida (não cache)."""
    return _last_execution_tier


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _cache_path(cidade: str, bairro: str) -> Path:
    return CACHE_DIR / f"{_slug(cidade)}_{_slug(bairro)}.md"


def _cache_valido(path: Path) -> bool:
    if not path.exists():
        return False
    idade = time.time() - path.stat().st_mtime
    return idade < CACHE_TTL_DIAS * 24 * 3600


def _parse_cache_tier(content: str) -> str | None:
    m = re.search(r"^\s*tier:\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def _briefing_padrao(cidade: str, bairro: str) -> str:
    hoje = datetime.now().strftime("%Y-%m-%d")
    return f"""# Briefing de Mercado — {bairro}, {cidade}

**Data:** {hoje}
**Status:** Deep Research indisponível — usando briefing padrão

## ⚠️ Aviso
Esta análise foi gerada como fallback. Para dados completos e atualizados,
a API Deep Research precisa estar acessível. Os agentes do pipeline
seguintes operarão com benchmarks setoriais (ACAD/Sebrae) e dados públicos
do IBGE como fonte primária.

## MERCADO FITNESS LOCAL
- Dados não disponíveis em tempo real
- Use benchmarks ACAD: ticket médio nacional R$149,90; redes dominantes
  Smart Fit, Selfit, BlueFit (low cost), Bodytech (mid/premium)

## PERFIL SOCIOECONÔMICO
- Use dados IBGE (DemoAnalyst A2)
- Renda média do estado como proxy quando renda do bairro indisponível

## MERCADO IMOBILIÁRIO COMERCIAL
- Use benchmark `BENCHMARKS_ALUGUEL` em financial_tools.py
- Faixa típica capitais Norte/Nordeste: R$18-60/m²
- Capitais Sul/Sudeste: R$25-150/m²

## REGULAMENTAÇÃO
- Alvará de funcionamento municipal
- Registro CREF (Conselho Regional de Educação Física)
- Norma técnica ABNT NBR 16604 (academias de ginástica)

## TENDÊNCIAS
- Modelo low-cost continua liderando captação por volume
- Premium cresce em bairros de classe média alta
- 24h e operação flexível são diferenciais consolidados
"""


def _build_query(cidade: str, bairro: str) -> str:
    return f"""Pesquise profundamente sobre o mercado fitness em {bairro}, {cidade}, Brasil:

## 1. MERCADO FITNESS LOCAL
- Quais redes de academia operam em {cidade}? Quantas unidades de cada?
- Ticket médio praticado pelas academias em {cidade} (R$/mês)
- Planos de expansão de redes conhecidas para {bairro}?

## 2. PERFIL SOCIOECONÔMICO DE {bairro}
- Renda média dos moradores (fontes: IBGE, reportagens, dados oficiais)
- Faixa etária predominante
- Crescimento populacional recente

## 3. MERCADO IMOBILIÁRIO COMERCIAL
- Preço médio de aluguel comercial por m² em {bairro}, {cidade}
- Tendência: subindo, estável ou caindo?

## 4. REGULAMENTAÇÃO
- Requisitos de alvará para academia em {cidade}
- Exigências do CREF regional

## 5. TENDÊNCIAS FITNESS EM {cidade}
- Notícias recentes sobre abertura/fechamento de academias
- Modalidades mais demandadas

Entregue relatório estruturado em markdown com fontes (URLs completas ou nome de portais)
ao final de cada seção. Foque em dados quantitativos (números, faixas, datas).
"""


def _interactions_disponivel() -> bool:
    """Deep Research agent só no Gemini Developer API (não Vertex ainda)."""
    try:
        from tools._genai_client import is_vertex_mode

        return not is_vertex_mode()
    except Exception:
        return True


def _extrair_texto_generate(response) -> str:
    if hasattr(response, "text") and response.text:
        return response.text
    if hasattr(response, "candidates") and response.candidates:
        chunks = []
        for cand in response.candidates:
            if hasattr(cand, "content") and cand.content:
                for part in getattr(cand.content, "parts", []) or []:
                    if hasattr(part, "text") and part.text:
                        chunks.append(part.text)
        if chunks:
            return "\n".join(chunks)
    return ""


def _extrair_texto_interaction(interaction) -> str:
    """Texto final de uma Interaction completed."""
    out_text = getattr(interaction, "output_text", None)
    if out_text and str(out_text).strip():
        return str(out_text).strip()

    outputs = getattr(interaction, "outputs", None) or []
    chunks: list[str] = []
    for out in outputs:
        text = getattr(out, "text", None)
        if text and str(text).strip():
            chunks.append(str(text).strip())
    return "\n\n".join(chunks)


def _executar_deep_research_interactions(query: str, *, deadline: float) -> str:
    """
    Tier 1: agente Deep Research via Interactions API (background + poll).

    Ref: https://ai.google.dev/gemini-api/docs/interactions/deep-research
    """
    from tools._genai_client import build_genai_client

    client = build_genai_client()

    interaction = client.interactions.create(
        input=query,
        agent=DEEP_RESEARCH_AGENT,
        background=True,
        agent_config={"type": "deep-research", "thinking_summaries": "auto"},
    )
    interaction_id = interaction.id
    if not interaction_id:
        raise RuntimeError("Interactions API não retornou interaction.id")

    while time.time() < deadline:
        interaction = client.interactions.get(interaction_id)
        status = (getattr(interaction, "status", None) or "").lower()

        if status == "completed":
            texto = _extrair_texto_interaction(interaction)
            if texto:
                return texto
            raise RuntimeError("Deep Research completed com output vazio")

        if status in ("failed", "cancelled"):
            err = getattr(interaction, "error", None)
            raise RuntimeError(f"Deep Research {status}: {err}")

        time.sleep(POLL_INTERVAL_SEC)

    raise TimeoutError(
        f"Deep Research ({DEEP_RESEARCH_AGENT}) não concluiu antes do deadline "
        f"({TIMEOUT_SEGUNDOS}s)"
    )


def _executar_grounded_fallback(query: str, *, deadline: float) -> str:
    """Tier 2: Flash + Search + URL context (pesquisa grounded 'lite')."""
    from google.genai import types
    from tools._genai_client import build_genai_client

    client = build_genai_client()
    config = types.GenerateContentConfig(
        tools=[
            types.Tool(google_search=types.GoogleSearch()),
            types.Tool(url_context=types.UrlContext()),
        ],
    )

    backoffs = [2, 4, 8]
    ultimo_erro: object = "Resposta vazia"
    for tentativa, delay in enumerate(backoffs, start=1):
        if time.time() >= deadline:
            raise TimeoutError("Deadline esgotado antes do fallback grounded")

        try:
            response = client.models.generate_content(
                model=FALLBACK_MODEL,
                contents=query,
                config=config,
            )
            texto = _extrair_texto_generate(response)
            if texto:
                return texto
            ultimo_erro = "Resposta vazia"
        except Exception as e:
            ultimo_erro = e
            erro_str = str(e)
            transient = any(
                t in erro_str for t in ["503", "UNAVAILABLE", "timed out", "504"]
            )
            if not transient:
                break
            if tentativa < len(backoffs) and time.time() + delay < deadline:
                time.sleep(delay)

    raise RuntimeError(
        f"Fallback grounded ({FALLBACK_MODEL}, {len(backoffs)} tentativas): {ultimo_erro}"
    )


def _executar_deep_research(query: str) -> tuple[str, str]:
    """
    Executa pesquisa de mercado. Retorna (markdown, tier_label).

    tier_label exemplos:
      - interactions:deep-research-max-preview-04-2026
      - grounded:gemini-2.5-flash
    """
    global _last_execution_tier

    deadline = time.time() + TIMEOUT_SEGUNDOS
    tier1_erro: Exception | None = None

    if _interactions_disponivel():
        try:
            texto = _executar_deep_research_interactions(query, deadline=deadline)
            tier = f"interactions:{DEEP_RESEARCH_AGENT}"
            _last_execution_tier = tier
            return texto, tier
        except Exception as e:
            tier1_erro = e

    try:
        texto = _executar_grounded_fallback(query, deadline=deadline)
        tier = f"grounded:{FALLBACK_MODEL}"
        _last_execution_tier = tier
        return texto, tier
    except Exception as tier2_erro:
        msg_t1 = f"{type(tier1_erro).__name__}: {tier1_erro}" if tier1_erro else "skipped (Vertex)"
        raise RuntimeError(
            f"Deep Research falhou. Tier1 ({DEEP_RESEARCH_AGENT}): {msg_t1}. "
            f"Tier2 ({FALLBACK_MODEL}): {tier2_erro}"
        ) from tier2_erro


def _gravar_cache(cidade: str, bairro: str, tier: str, corpo: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    header = (
        f"<!-- Deep Research cache\n"
        f"     cidade: {cidade}\n"
        f"     bairro: {bairro}\n"
        f"     tier: {tier}\n"
        f"     agent: {DEEP_RESEARCH_AGENT}\n"
        f"     data: {datetime.now().isoformat()}\n"
        f"-->\n\n"
    )
    _cache_path(cidade, bairro).write_text(header + corpo, encoding="utf-8")


def _langcache_prompt(cidade: str, bairro: str) -> str:
    """Chave semântica estável para Deep Research (A0)."""
    return f"deep_research_a0:{cidade.strip().lower()}:{bairro.strip().lower()}"


def rodar_deep_research(cidade: str, bairro: str) -> str:
    """
    Executa Deep Research para (cidade, bairro). Cache + timeout + fallback estático.

    Com A0_RESEARCH_PROVIDER=kimi|openclaw delega para tools.kimi_research.

    Returns:
        Markdown com briefing. Nunca lança exceção para o ADK.
    """
    global _last_execution_tier

    try:
        from tools.research_provider import get_a0_research_provider
        from tools.kimi_research import rodar_kimi_research

        if get_a0_research_provider() == "kimi":
            return rodar_kimi_research(cidade, bairro)
    except Exception:
        pass

    cache = _cache_path(cidade, bairro)
    if _cache_valido(cache):
        _last_execution_tier = _parse_cache_tier(cache.read_text(encoding="utf-8")[:500]) or "cache"
        return cache.read_text(encoding="utf-8")

    query = _build_query(cidade, bairro)

    # LangCache semântico (entre disco e Gemini — ~200ms vs minutos)
    try:
        from tools.langcache_client import langcache_search, langcache_set

        lc_key = _langcache_prompt(cidade, bairro)
        lc_hit = langcache_search(lc_key, similarity_threshold=0.92)
        if not lc_hit:
            lc_hit = langcache_search(query[:1024], similarity_threshold=0.90)
        if lc_hit:
            _last_execution_tier = "langcache"
            tier = "langcache:semantic"
            try:
                _gravar_cache(cidade, bairro, tier, lc_hit)
            except Exception:
                pass
            header = (
                f"<!-- Deep Research cache\n"
                f"     cidade: {cidade}\n"
                f"     bairro: {bairro}\n"
                f"     tier: {tier}\n"
                f"     data: {datetime.now().isoformat()}\n"
                f"-->\n\n"
            )
            print(f"[A0] LangCache hit: {cidade}/{bairro}")
            return header + lc_hit
    except Exception as e:
        print(f"[A0] LangCache skip: {e}")

    resultado: str | None = None
    tier: str | None = None

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_executar_deep_research, query)
            try:
                resultado, tier = future.result(timeout=TIMEOUT_SEGUNDOS + 30)
            except FuturesTimeout:
                resultado = None
    except Exception:
        resultado = None

    if resultado and tier:
        try:
            _gravar_cache(cidade, bairro, tier, resultado)
            try:
                from tools.langcache_client import langcache_set

                langcache_set(_langcache_prompt(cidade, bairro), resultado)
                langcache_set(query[:1024], resultado)
            except Exception:
                pass
            return _cache_path(cidade, bairro).read_text(encoding="utf-8")
        except Exception:
            header = (
                f"<!-- Deep Research cache\n"
                f"     cidade: {cidade}\n"
                f"     bairro: {bairro}\n"
                f"     tier: {tier}\n"
                f"     data: {datetime.now().isoformat()}\n"
                f"-->\n\n"
            )
            return header + resultado

    _last_execution_tier = "briefing_padrao"
    return _briefing_padrao(cidade, bairro)


# ── Investigação micro (imóvel potencial → o que opera no endereço) ─────────


def _normalizar_chave(s: str) -> str:
    return _slug(s or "")


def marcar_gatilhos_investigacao(candidatos: list[dict]) -> list[dict]:
    """
    Marca candidatos que devem disparar investigação web (sem chamar API).

    Preenche candidato["investigacao"] = {disparar, prioridade, motivo_gatilho}.
    """
    for c in candidatos:
        inv = {"disparar": False, "prioridade": 99, "motivo_gatilho": None}
        qs = (c.get("qualidade_sinal") or "").lower()
        status = (c.get("business_status") or c.get("status") or "").upper()
        motivo = (c.get("motivo") or "").lower()
        titulo = (c.get("nome") or c.get("title") or "").lower()
        score = float(c.get("score_geoscout") or 0)
        tem_endereco = bool((c.get("endereco") or "").strip())
        tem_listing = bool(c.get("listing_url"))

        if qs == "direto-listing" and tem_endereco and tem_listing:
            inv = {
                "disparar": True,
                "prioridade": 1,
                "motivo_gatilho": "listing_com_endereco",
            }
        elif status in ("CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY") and tem_endereco:
            inv = {
                "disparar": True,
                "prioridade": 2,
                "motivo_gatilho": f"places_{status.lower()}",
            }
        elif "investigar" in motivo and score >= 7.0 and tem_endereco:
            inv = {
                "disparar": True,
                "prioridade": 3,
                "motivo_gatilho": "ancora_alto_score",
            }
        elif qs == "direto-listing" and any(w in titulo for w in _LISTING_TRIGGER_WORDS):
            inv = {
                "disparar": True,
                "prioridade": 4,
                "motivo_gatilho": "listing_titulo_comercial",
            }

        c["investigacao"] = inv
        try:
            from tools.investigacao_context import inferir_tipo_imovel_candidato

            c["tipo_imovel_inferido"] = inferir_tipo_imovel_candidato(c)
        except Exception:
            pass
    return candidatos


def _investigacao_id(candidato: dict) -> str:
    parts = [
        candidato.get("listing_id") or "",
        candidato.get("place_id") or "",
        candidato.get("endereco") or candidato.get("nome") or "",
        candidato.get("listing_url") or "",
    ]
    base = "|".join(p.strip() for p in parts if p and str(p).strip())
    if not base:
        base = json.dumps(
            {
                "lat": candidato.get("lat"),
                "lng": candidato.get("lng"),
                "nome": candidato.get("nome"),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    return _slug(base)[:120] or "sem_id"


def _cache_path_investigacao(inv_id: str) -> Path:
    return INVESTIGACAO_CACHE_DIR / f"{inv_id}.md"


def _cache_valido_investigacao(path: Path) -> bool:
    if not path.exists():
        return False
    idade = time.time() - path.stat().st_mtime
    return idade < INVESTIGACAO_TTL_DIAS * 24 * 3600


def _build_query_investigacao(
    candidato: dict,
    *,
    cidade: str,
    uf: str,
    bairro: str,
    contexto_relatorio: dict[str, Any] | None = None,
) -> str:
    from tools.investigacao_context import (
        build_contexto_investigacao,
        formatar_bloco_contexto_prompt,
    )

    ctx = contexto_relatorio or build_contexto_investigacao(
        {
            "cidade": cidade,
            "bairro": bairro,
            "uf": uf,
        }
    )
    if not ctx.get("cidade"):
        ctx["cidade"] = cidade
    if bairro and not ctx.get("bairro"):
        ctx["bairro"] = bairro
    if uf and not ctx.get("uf"):
        ctx["uf"] = uf

    bloco_contexto = formatar_bloco_contexto_prompt(ctx, candidato)

    nome = candidato.get("nome") or candidato.get("title") or "Imóvel sem nome"
    endereco = candidato.get("endereco") or ""
    listing_url = candidato.get("listing_url") or ""
    area = (
        candidato.get("area_m2")
        or candidato.get("area_estimada_m2")
        or candidato.get("area")
        or ""
    )
    preco = candidato.get("price_raw") or candidato.get("preco") or ""
    lat = candidato.get("lat")
    lng = candidato.get("lng")
    coords = f"{lat}, {lng}" if lat is not None and lng is not None else "não informadas"
    status_maps = candidato.get("business_status") or candidato.get("status") or ""

    url_block = (
        f"\nAnúncio para cruzar (use url_context se possível): {listing_url}\n"
        if listing_url
        else ""
    )

    return f"""Investigue o que está em FUNCIONAMENTO HOJE neste endereço comercial no Brasil.

{bloco_contexto}

## Alvo (endereço)
- Nome / título do candidato: {nome}
- Endereço: {endereco}
- Bairro: {bairro or 'não informado'}, Cidade: {cidade}, UF: {uf or 'não informada'}
- Coordenadas: {coords}
- Status Google (se houver): {status_maps or 'não informado'}
- Área informada: {area or 'não informada'}
- Preço aluguel (anúncio): {preco or 'não informado'}
{url_block}

## Perguntas obrigatórias
1. Qual negócio opera HOJE neste endereço (nome fantasia e segmento)?
2. Está aberto, fechado, em reforma ou aparenta vago?
3. O anúncio de aluguel (se houver URL) bate com a realidade do local?
4. Há notícias ou redes sociais recentes (12 meses) sobre o ponto?
5. Se era varejo/academia grande: houve fechamento ou substituição?

## Formato de resposta
1. Relatório curto em markdown (máx. 400 palavras) com bullet points e URLs de evidência.
2. Ao final, bloco JSON EXATO entre ```json e ``` com:
{{
  "status_operacao": "em_funcionamento|fechado|reforma|vago|incerto",
  "operador_atual": "nome ou null",
  "segmento": "academia|varejo|restaurante|servicos|vazio|outro",
  "confianca": "alta|media|baixa",
  "coerencia_listing": "sim|nao|incerto|na",
  "evidencias": [{{"fonte": "...", "url": "https://...", "trecho": "..."}}],
  "implicacao_site": "uma frase acionável para quem avalia ponto de academia"
}}

Não invente nome de loja sem URL ou citação. Se não achar nada, use status_operacao=incerto e confianca=baixa.
"""


def _extrair_json_investigacao(texto: str) -> dict[str, Any] | None:
    m = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _gravar_cache_investigacao(
    inv_id: str,
    tier: str,
    corpo_md: str,
    parsed: dict[str, Any] | None,
    candidato: dict,
) -> None:
    INVESTIGACAO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    header = (
        f"<!-- investigacao_imovel\n"
        f"     id: {inv_id}\n"
        f"     tier: {tier}\n"
        f"     endereco: {candidato.get('endereco', '')}\n"
        f"     data: {datetime.now().isoformat()}\n"
        f"-->\n\n"
    )
    _cache_path_investigacao(inv_id).write_text(header + corpo_md, encoding="utf-8")


def _executar_investigacao_query(
    query: str,
    *,
    use_interactions: bool,
) -> tuple[str, str]:
    """Executa pesquisa micro; preferência grounded salvo flag interactions."""
    deadline = time.time() + INVESTIGACAO_TIMEOUT_SEC
    if use_interactions and _interactions_disponivel():
        try:
            texto = _executar_deep_research_interactions(query, deadline=deadline)
            return texto, f"interactions:{DEEP_RESEARCH_AGENT}"
        except Exception:
            pass
    texto = _executar_grounded_fallback(query, deadline=deadline)
    return texto, f"grounded:{FALLBACK_MODEL}"


def investigar_operacao_endereco(
    candidato: dict,
    *,
    cidade: str,
    bairro: str = "",
    uf: str = "",
    use_interactions: bool = False,
    contexto_relatorio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Pesquisa na web o que opera no endereço do candidato. Nunca lança exceção.

    Returns:
        dict com status, tier, markdown, resultado (JSON parseado ou fallback).
    """
    inv_id = _investigacao_id(candidato)
    cache = _cache_path_investigacao(inv_id)
    if _cache_valido_investigacao(cache):
        texto = cache.read_text(encoding="utf-8")
        parsed = _extrair_json_investigacao(texto)
        return {
            "status": "ok",
            "cache": True,
            "investigacao_id": inv_id,
            "tier": _parse_cache_tier(texto[:500]) or "cache",
            "markdown": texto,
            "resultado": parsed or {"status_operacao": "incerto", "confianca": "baixa"},
        }

    query = _build_query_investigacao(
        candidato,
        cidade=cidade,
        uf=uf,
        bairro=bairro,
        contexto_relatorio=contexto_relatorio,
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _executar_investigacao_query,
                query,
                use_interactions=use_interactions,
            )
            markdown, tier = future.result(timeout=INVESTIGACAO_TIMEOUT_SEC + 15)
    except Exception as exc:
        return {
            "status": "erro",
            "cache": False,
            "investigacao_id": inv_id,
            "tier": "erro",
            "markdown": "",
            "resultado": {
                "status_operacao": "incerto",
                "confianca": "baixa",
                "implicacao_site": f"Investigação falhou: {exc}",
                "evidencias": [],
            },
        }

    parsed = _extrair_json_investigacao(markdown) or {
        "status_operacao": "incerto",
        "confianca": "baixa",
        "implicacao_site": "Validar presencialmente — JSON estruturado ausente na resposta.",
        "evidencias": [],
    }
    parsed.setdefault("investigado_em", datetime.now().strftime("%Y-%m-%d"))
    if contexto_relatorio:
        parsed["contexto_relatorio"] = {
            "tamanho_preset": contexto_relatorio.get("tamanho_preset"),
            "area_m2_min": contexto_relatorio.get("area_m2_min"),
            "area_m2_max": contexto_relatorio.get("area_m2_max"),
            "tipo_negocio": contexto_relatorio.get("tipo_negocio"),
        }

    try:
        _gravar_cache_investigacao(inv_id, tier, markdown, parsed, candidato)
    except Exception:
        pass

    return {
        "status": "ok",
        "cache": False,
        "investigacao_id": inv_id,
        "tier": tier,
        "markdown": markdown,
        "resultado": parsed,
    }


def executar_investigacoes_candidatos(
    candidatos: list[dict],
    *,
    cidade: str,
    bairro: str = "",
    uf: str = "",
    max_total: int | None = None,
    contexto_relatorio: dict[str, Any] | None = None,
    input_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Roda investigações web nos candidatos com investigacao.disparar=True.

    Ordena por prioridade (menor = mais urgente), limita a max_total (env default 5).
    Preenche candidato["investigacao_resultado"] in-place.
    """
    if INVESTIGACAO_DISABLED:
        return {"disparados": 0, "executados": 0, "erros": 0, "limite": 0, "desabilitado": True}

    if contexto_relatorio is None and input_params is not None:
        from tools.investigacao_context import build_contexto_investigacao

        contexto_relatorio = build_contexto_investigacao(input_params)
    elif contexto_relatorio is None:
        from tools.investigacao_context import build_contexto_investigacao

        contexto_relatorio = build_contexto_investigacao(
            {"cidade": cidade, "bairro": bairro, "uf": uf}
        )

    limite = max_total if max_total is not None else INVESTIGACAO_MAX_POR_RELATORIO
    fila = [
        c
        for c in candidatos
        if isinstance(c.get("investigacao"), dict) and c["investigacao"].get("disparar")
    ]
    fila.sort(key=lambda x: int(x.get("investigacao", {}).get("prioridade", 99)))

    executados = 0
    erros = 0
    for i, c in enumerate(fila):
        if executados >= limite:
            break
        use_ix = i < INVESTIGACAO_USE_INTERACTIONS_TOP
        try:
            res = investigar_operacao_endereco(
                c,
                cidade=cidade,
                bairro=bairro,
                uf=uf,
                use_interactions=use_ix,
                contexto_relatorio=contexto_relatorio,
            )
            c["investigacao_resultado"] = res
            if res.get("status") == "ok":
                executados += 1
            else:
                erros += 1
        except Exception as exc:
            erros += 1
            c["investigacao_resultado"] = {
                "status": "erro",
                "resultado": {
                    "status_operacao": "incerto",
                    "confianca": "baixa",
                    "implicacao_site": str(exc),
                },
            }

    return {
        "disparados": len(fila),
        "executados": executados,
        "erros": erros,
        "limite": limite,
        "contexto_relatorio": {
            "cidade": contexto_relatorio.get("cidade"),
            "bairro": contexto_relatorio.get("bairro"),
            "uf": contexto_relatorio.get("uf"),
            "tipo_negocio": contexto_relatorio.get("tipo_negocio"),
            "tamanho_preset": contexto_relatorio.get("tamanho_preset"),
            "area_m2_min": contexto_relatorio.get("area_m2_min"),
            "area_m2_max": contexto_relatorio.get("area_m2_max"),
            "faixa_porte_preset": contexto_relatorio.get("faixa_porte_preset"),
        },
    }
