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

import json
from pathlib import Path

from google.adk.agents import Agent
from google.genai import types

_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=8192),
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
        return
    try:
        rel = json.loads(path.read_text(encoding="utf-8"))
        out = rel.setdefault("output_consolidado", {})
        if not isinstance(out, dict):
            out = {}
            rel["output_consolidado"] = out
        out["posicionamento_estrategico"] = posicionamento
        path.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[A9] aviso: falha patch JSON local: {e}")


def _a9_after_agent_callback(callback_context):
    """Parseia JSON do output_key e persiste no state + JSON local + Supabase."""
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

        veredito = parsed.get("veredito_posicionamento", "N/A")
        gaps = len(parsed.get("gaps_identificados") or [])
        ticket = (parsed.get("recomendacao_ticket") or {}).get("ticket_recomendado", "N/A")
        print(f"[A9] Posicionamento gerado: veredito={veredito}, gaps={gaps}, ticket=R${ticket}")

        local_id = state.get("relatorio_local_id")
        if isinstance(local_id, str) and local_id:
            _patch_relatorio_json(local_id, parsed)

        rel_uuid = state.get("relatorio_id")
        if isinstance(rel_uuid, str) and rel_uuid:
            try:
                from db.supabase_writer import write_posicionamento_failsafe

                write_posicionamento_failsafe(rel_uuid, parsed)
            except Exception as e:
                print(f"[A9] aviso: Supabase posicionamento: {e}")

    except json.JSONDecodeError as e:
        st = getattr(callback_context, "state", {}) or {}
        raw_preview = str(st.get("relatorio_posicionamento_md") or "")[:2000]
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Falha ao parsear JSON: {e}",
            "raw_output": raw_preview,
        }
        print(f"[A9] ERRO ao parsear JSON: {e}")
    except Exception as e:
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Erro inesperado: {e}",
        }
        print(f"[A9] ERRO inesperado: {e}")


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
- OCEANO_AZUL: renda alta, baixa concorrência premium, 3+ GAPs, break-even viável
- TRANSICAO: renda média-alta, concorrência moderada, 1–2 GAPs
- VERMELHO: saturado low-cost, renda baixa, 0–1 GAPs

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
  "markdown": "# Relatório de Posicionamento Estratégico\\n\\n..."
}

## REGRAS
- Use dados REAIS do pipeline. Não invente números.
- Se dado ausente, indique "dado indisponível".
- O campo markdown deve ser relatório executivo completo em português.
- Foque em acionabilidade: o gestor deve saber EXATAMENTE o que fazer.
""",
    generate_content_config=_GENERATE_CONFIG,
    tools=[],
    output_key="relatorio_posicionamento_md",
    after_agent_callback=_a9_after_agent_callback,
)
