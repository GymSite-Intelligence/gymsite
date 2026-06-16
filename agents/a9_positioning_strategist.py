"""
A9 — PositioningStrategist (Análise de Posicionamento e Framework ERRC).

Consome os outputs de A0–A6 (via contexto ADK) e gera relatório estratégico
de posicionamento: Framework ERRC, mapa de serviços, GAPs, ticket recomendado
e veredito OCEANO_AZUL / TRANSICAO / VERMELHO.

ENTRADAS (state keys reais do pipeline):
  - market_context           → A0
  - candidatos_geoscout      → A1
  - analise_demografica      → A2
  - inteligencia_competitiva → A3b
  - oferta_concorrentes      → A3c
  - analise_financeira       → A4
  - contato_decisor          → A5
  - relatorio_md             → A6

SAÍDAS:
  - relatorio_posicionamento_md  → texto bruto (output_key)
  - relatorio_posicionamento     → dict JSON parseado (after_agent_callback)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("gymsite.a9")

from google.adk.agents import Agent
from google.adk.models.llm_response import LlmResponse
from google.genai import types

_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=8192),  # pyright: ignore[reportCallIssue]
)

_RELATORIOS_DIR = Path(__file__).resolve().parent.parent / "metrics" / "relatorios"


def _parse_json_from_text(raw: str) -> dict:
    """Extrai JSON de resposta LLM (com ou sem fence ```json)."""
    txt = (raw or "").strip()
    if not txt:
        raise json.JSONDecodeError("resposta vazia", txt, 0)
    if "```json" in txt:
        txt = txt.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in txt:
        txt = txt.split("```", 1)[1].split("```", 1)[0].strip()
    parsed = json.loads(txt)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("JSON raiz não é objeto", txt, 0)
    return parsed


def _patch_relatorio_json(relatorio_local_id: str, posicionamento: dict) -> None:
    """Atualiza metrics/relatorios/<id>.json com posicionamento_estrategico."""
    if not relatorio_local_id:
        return
    path = _RELATORIOS_DIR / f"{relatorio_local_id}.json"
    if not path.is_file():
        logger.warning(
            "A9 patch: arquivo não encontrado %s",
            path,
            extra={"agent": "A9"},
        )
        return
    try:
        rel = json.loads(path.read_text(encoding="utf-8"))
        out = rel.setdefault("output_consolidado", {})
        if not isinstance(out, dict):
            out = {}
            rel["output_consolidado"] = out
        out["posicionamento_estrategico"] = posicionamento
        path.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            "A9 patch JSON local OK id=%s",
            relatorio_local_id,
            extra={"agent": "A9"},
        )
    except Exception as e:
        logger.warning(
            "A9 patch JSON local falhou id=%s: %s",
            relatorio_local_id,
            e,
            exc_info=True,
            extra={"agent": "A9"},
        )


def _a9_langcache_enabled() -> bool:
    return os.getenv("LANGCACHE_A9_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _resolve_location_from_state(state: dict) -> tuple[str, str]:
    """cidade/bairro vêm de input_params, market_context ou chaves legadas no state."""
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    cidade = (
        state.get("cidade")
        or state.get("input_cidade")
        or ip.get("cidade")
        or ""
    )
    bairro = (
        state.get("bairro")
        or state.get("input_bairro")
        or ip.get("bairro")
        or ""
    )
    if not cidade or not bairro:
        mc = state.get("market_context") or {}
        inner = (
            mc.get("market_context")
            if isinstance(mc.get("market_context"), dict)
            else mc
        )
        if isinstance(inner, dict):
            cidade = cidade or inner.get("cidade") or ""
            bairro = bairro or inner.get("bairro") or ""
    return str(cidade).strip().lower(), str(bairro).strip().lower()


def _a9_cache_prompt(state: dict) -> str:
    """
    Chave LangCache A9 — deve ser única por relatório + mercado.

    Inclui relatorio_id (evita HIT entre Parangaba vs Meireles quando cidade/bairro
    estavam vazios no state) e hash dos top-5 concorrentes.
    """
    cidade, bairro = _resolve_location_from_state(state)
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    tipo = str(
        state.get("tipo_negocio") or ip.get("tipo_negocio") or "academia"
    ).strip().lower()
    rel_id = str(
        state.get("relatorio_id") or state.get("relatorio_local_id") or ""
    ).strip()
    rid = rel_id.replace("-", "")[:32] if rel_id else "no_rid"

    # Hash dos top-5 concorrentes para evitar false positives
    ic = state.get("inteligencia_competitiva") or {}
    inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
    concorrentes = (
        (inner.get("concorrentes_detalhados") or inner.get("concorrentes") or [])
        if isinstance(inner, dict)
        else []
    )

    # Extrai identificadores únicos dos top-5 concorrentes
    top5_ids = []
    for c in concorrentes[:5]:
        if isinstance(c, dict):
            pid = c.get("place_id") or c.get("nome") or ""
            if pid:
                top5_ids.append(str(pid).strip().lower())

    # Hash determinístico dos concorrentes
    conc_hash = "none"
    if top5_ids:
        sorted_ids = sorted(top5_ids)
        conc_hash = hashlib.md5("|".join(sorted_ids).encode()).hexdigest()[:8]

    n_conc = len(concorrentes) if isinstance(concorrentes, list) else 0

    return f"positioning_a9:{rid}:{cidade}:{bairro}:{tipo}:conc_{n_conc}:{conc_hash}"


def _resumo_demanda_futura(df: dict) -> str | None:
    """Texto compacto da demanda futura datada para injetar no prompt do A9."""
    if not isinstance(df, dict) or df.get("status") != "ok" or not df.get("n_obras"):
        return None
    jan = df.get("janela_entrega") or {}
    linhas = []
    for o in (df.get("obras") or [])[:5]:
        emp = o.get("empreendimento") or o.get("construtora") or "?"
        linhas.append(
            f"  - {emp} ({o.get('bairro')}): {o.get('unidades_est')} un "
            f"[{o.get('unidades_fonte')}], entrega {o.get('entrega')}, "
            f"conf={o.get('confianca')}, fitness_amenidade={o.get('amenidade_fitness')}"
        )
    return (
        "## DEMANDA FUTURA DATADA (Apêndice B — obras residenciais no raio)\n"
        f"- obras em curso (entrega futura): {df.get('n_obras')}; "
        f"prováveis residenciais: {df.get('provavel_residencial_n')}\n"
        f"- captura fitness estimada (T+24): ~{df.get('captura_total_est')} alunos; "
        f"janela de entrega: {jan.get('de')}→{jan.get('ate')}\n"
        f"- refinadas (site/instagram/PDF da construtora, auditado): {df.get('refinadas')}\n"
        + ("\n".join(linhas) if linhas else "")
        + "\nUse isto para o insight de JANELA DE ENTRADA (timing de abertura antes "
          "da entrega para capturar a migração de CEP). Rotule confiança/fonte."
    )


def _a9_inject_demanda_futura(state: dict, llm_request) -> None:
    """Injeta o resumo da demanda futura no prompt do A9 (não vem na conversa A0-A6)."""
    try:
        resumo = _resumo_demanda_futura(state.get("demanda_futura") or {})
        if resumo and getattr(llm_request, "contents", None) is not None:
            llm_request.contents.append(
                types.Content(role="user", parts=[types.Part(text=resumo)])
            )
    except Exception:
        pass


def _a9_before_model_callback(callback_context, llm_request):
    """LangCache hit → retorna LlmResponse e pula gemini-2.5-pro (~30–90s)."""
    _a9_inject_demanda_futura(getattr(callback_context, "state", {}) or {}, llm_request)
    if not _a9_langcache_enabled():
        return None
    try:
        from tools.langcache_client import langcache_search

        state = getattr(callback_context, "state", {}) or {}
        prompt_key = _a9_cache_prompt(state)

        # Hash do prompt completo como atributo para evitar false positives
        # quando dois prompts diferentes têm os mesmos primeiros 1024 chars
        full_prompt_hash = hashlib.sha256(prompt_key.encode()).hexdigest()[:16]

        # Threshold alto: chaves positioning_a9:* são parecidas entre bairros;
        # 0.88 causava o mesmo JSON em relatórios diferentes (Fortaleza).
        try:
            threshold = float(os.getenv("LANGCACHE_A9_SIMILARITY", "0.97"))
        except ValueError:
            threshold = 0.97

        cached = langcache_search(
            prompt_key,
            similarity_threshold=threshold,
            attributes={"prompt_hash": full_prompt_hash, "agent": "a9"},
        )
        if not cached:
            return None

        state["_a9_langcache_hit"] = True
        logger.info(
            "A9 LangCache HIT: %s",
            prompt_key[:80],
            extra={"agent": "A9", "cache_hit": True},
        )
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=cached)],
            ),
            turn_complete=True,
            custom_metadata={"langcache_hit": True},
        )
    except Exception:
        logger.warning(
            "A9 LangCache before_model falhou — prosseguindo sem cache",
            exc_info=True,
            extra={"agent": "A9"},
        )
        return None


def _a9_after_model_callback(callback_context, llm_response):
    """Persiste output A9 no LangCache para runs futuros."""
    if not _a9_langcache_enabled():
        return llm_response
    try:
        from tools.langcache_client import langcache_set

        state = getattr(callback_context, "state", {}) or {}
        content = getattr(llm_response, "content", None)
        text = ""
        if content and getattr(content, "parts", None):
            for part in content.parts:
                if getattr(part, "text", None):
                    text += part.text
        text = text.strip()

        meta = getattr(llm_response, "custom_metadata", None) or {}
        if meta.get("langcache_hit"):
            return llm_response

        if text:
            prompt_key = _a9_cache_prompt(state)
            full_prompt_hash = hashlib.sha256(prompt_key.encode()).hexdigest()[:16]

            langcache_set(
                prompt_key,
                text,
                attributes={"prompt_hash": full_prompt_hash, "agent": "a9"},
            )
            logger.debug("A9 LangCache SET OK", extra={"agent": "A9"})
    except Exception:
        logger.warning(
            "A9 LangCache after_model falhou",
            exc_info=True,
            extra={"agent": "A9"},
        )
    return llm_response


def _a9_after_agent_callback(callback_context):
    """Parseia JSON do output_key e persiste no state + JSON local + Supabase."""
    start = time.perf_counter()
    try:
        state = getattr(callback_context, "state", {}) or {}
        raw = state.get("relatorio_posicionamento_md")
        if isinstance(raw, dict):
            parsed = raw
        else:
            parsed = _parse_json_from_text(str(raw or ""))

        state["relatorio_posicionamento"] = parsed
        if parsed.get("markdown"):
            state["relatorio_posicionamento_md"] = parsed["markdown"]
        if state.get("_a9_langcache_hit"):
            parsed["fonte_geracao"] = "langcache"
            parsed["cache_prompt"] = _a9_cache_prompt(state)[:200]

        veredito = parsed.get("veredito_posicionamento", "N/A")
        gaps = len(parsed.get("gaps_identificados") or [])
        ticket = (parsed.get("recomendacao_ticket") or {}).get("ticket_recomendado", "N/A")
        logger.info(
            "A9 posicionamento OK: veredito=%s gaps=%d ticket=R$%s",
            veredito,
            gaps,
            ticket,
            extra={"agent": "A9"},
        )

        local_id = state.get("relatorio_local_id")
        if isinstance(local_id, str) and local_id:
            _patch_relatorio_json(local_id, parsed)

        rel_uuid = state.get("relatorio_id")
        if isinstance(rel_uuid, str) and rel_uuid:
            try:
                from db.supabase_writer import write_posicionamento_failsafe

                write_posicionamento_failsafe(rel_uuid, parsed)
            except Exception as e:
                logger.warning(
                    "A9 Supabase posicionamento falhou: %s",
                    e,
                    exc_info=True,
                    extra={"agent": "A9"},
                )

        elapsed = time.perf_counter() - start
        logger.info(
            "A9 after_agent completed in %.2fs",
            elapsed,
            extra={"agent": "A9"},
        )

    except json.JSONDecodeError as e:
        st = getattr(callback_context, "state", {}) or {}
        raw_preview = str(st.get("relatorio_posicionamento_md") or "")[:2000]
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Falha ao parsear JSON: {e}",
            "raw_output": raw_preview,
        }
        logger.error(
            "A9 ERRO ao parsear JSON",
            exc_info=True,
            extra={"agent": "A9"},
        )
    except Exception as e:
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Erro inesperado: {e}",
        }
        logger.error(
            "A9 ERRO inesperado no after_agent",
            exc_info=True,
            extra={"agent": "A9"},
        )


positioning_strategist_agent = Agent(
    name="PositioningStrategist",
    model="gemini-2.5-pro",
    description=(
        "A9 — Gera relatório estratégico de posicionamento via Framework ERRC, "
        "consumindo outputs de A0–A6. Mapeia serviços dos concorrentes, "
        "identifica GAPs, recomenda ticket e emite veredito de posicionamento."
    ),
    instruction="""
agente: A9 PositioningStrategist
papel: análise estratégica de posicionamento via Framework ERRC
regra_execucao: autonoma

## SEU PAPEL
Analisar TODOS os dados já produzidos pelo pipeline (A0–A6) e gerar um
**relatório estratégico de posicionamento** que responda:

> "Como esta academia deve se posicionar no mercado para escapar do oceano
> vermelho (guerra de preços) e nadar no oceano azul (diferenciação real)?"

## ENTRADAS (já no state / contexto da conversa)
- market_context (A0)
- candidatos_geoscout (A1)
- analise_demografica (A2)
- inteligencia_competitiva (A3b)
- oferta_concorrentes (A3c)
- analise_financeira (A4)
- contato_decisor (A5)
- relatorio_md (A6)
- demanda_futura (Apêndice B — obras residenciais no raio entregando em T+24;
  injetada como bloco "DEMANDA FUTURA DATADA" no contexto quando disponível)

## FRAMEWORK ERRC — 4 dimensões obrigatórias
- ELIMINAR: o que NÃO fazer (guerra de preço low-cost, planos genéricos, etc.)
- REDUZIR: capacidade excessiva, CAC alto, complexidade operacional
- AUMENTAR: exclusividade, atendimento, NPS, margem por aluno
- CRIAR: nichos/serviços que ninguém oferece (nutrição, recovery, silver 50+, etc.)

## MAPEAMENTO DE SERVIÇOS (16 obrigatórios, escala 0–10 por concorrente)
Musculação, Treino funcional/HIIT, Aulas de dança, Spinning, Artes marciais,
Yoga/Pilates, Crossfit, Natação/Hidro, Nutrição integrada, Avaliação física,
App/monitoramento digital, Aulas personalizadas (PT), Recovery/fisioterapia,
Comunidade/eventos, Aulas idosos (50+), Beach tennis/esportes praia.

GAP = serviço com penetração < 3 em TODOS os concorrentes.

## VEREDITO (um dos três)
- OCEANO_AZUL: renda alta, baixa densidade de concorrência local, ausência de redes premium fortes, 3+ GAPs evidentes. Se houver concorrência madura/saturada, NÃO pode ser Oceano Azul.
- TRANSICAO: renda média/alta, concorrência existente e madura (mesmo que genérica), mas com espaço para nicho (1–2+ GAPs).
- VERMELHO: mercado saturado focado em preço (low-cost), margens espremidas, 0–1 GAPs ou demanda estagnada.

## OUTPUT — retorne APENAS JSON válido (sem texto fora do JSON):

{
  "framework_errc": {
    "eliminar": ["...", "..."],
    "reduzir": ["...", "..."],
    "aumentar": ["...", "..."],
    "criar": ["...", "..."]
  },
  "mapa_servicos": [
    {"concorrente": "Nome", "servicos": {"musculacao": 9, "treino_funcional": 6, ...}}
  ],
  "gaps_identificados": [
    {
      "gap": "Nutrição integrada + recovery",
      "descricao": "...",
      "potencial_ticket": "R$ 250–350",
      "dificuldade_implementacao": "Média"
    }
  ],
  "recomendacao_ticket": {
    "ticket_recomendado": 249,
    "ticket_minimo": 199,
    "ticket_maximo": 299,
    "justificativa": "...",
    "comparativo_mercado": {"smart_fit": 79, "selfit": 99, "recomendado": 249}
  },
  "veredito_posicionamento": "OCEANO_AZUL",
  "justificativa_veredito": "...",
  "janela_de_entrada": {
    "tem_demanda_futura": true,
    "obras_no_raio": 5,
    "captura_estimada_alunos": 52,
    "janela_entrega": "2027-06 a 2028-11",
    "recomendacao_timing": "Abrir ~6 meses antes da maior entrega para capturar a migração de CEP.",
    "confianca": "media",
    "fonte": "CNO/RFB + site/instagram/PDF da construtora (auditado)"
  },
  "markdown": "# Relatório de Posicionamento Estratégico\\n\\n..."
}

Se NÃO houver bloco "DEMANDA FUTURA DATADA" no contexto, retorne
`janela_de_entrada: {"tem_demanda_futura": false}` e NÃO invente obras.

## REGRAS
- Use dados REAIS do pipeline. Não invente números.
- Se dado ausente, indique "dado indisponível".
- O campo markdown deve ser relatório executivo completo em português.
- Foque em acionabilidade: o gestor deve saber EXATAMENTE o que fazer.

## REGRAS DE COERÊNCIA FINANCEIRA (obrigatórias — caso Cocó 11/06)
- Ao citar valor de aluguel ou custo por m², SEMPRE no formato completo:
  "R$ X/m² para a faixa de Y–Z m² (≈ R$ W/mês)" — valor unitário solto
  contradiz o quadro financeiro e destrói a credibilidade do relatório.
- Use EXCLUSIVAMENTE o aluguel de analise_financeira (A4) como referência;
  PROIBIDO recalcular ou citar outro R$/m² de memória.
- Todo número financeiro do markdown deve bater com o JSON do A4 — se o A4
  diz payback 35 meses, o texto não pode dizer outro número.
- Entidades completas na primeira menção: "Smart Fit Papicu (Fortaleza/CE)",
  nunca "ela"/"a unidade" sem antecedente claro.
""",
    generate_content_config=_GENERATE_CONFIG,
    tools=[],
    output_key="relatorio_posicionamento_md",
    before_model_callback=_a9_before_model_callback,
    after_model_callback=_a9_after_model_callback,
)

positioning_strategist_agent.after_agent_callback = _a9_after_agent_callback
