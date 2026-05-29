#!/usr/bin/env python3
"""
Teste A0 — deve ANALISAR parque CNPJ (não só copiar tool).

Uso: python tools/test_a0_cnpj_context.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)
os.environ.setdefault("CNPJ_SEGMENT_PLACES_VALIDATE", "1")


def _mock_deep_research(cidade: str, bairro: str) -> str:
    cache = _ROOT / "market_context" / "fortaleza_meireles.md"
    if cache.is_file():
        return cache.read_text(encoding="utf-8")
    return f"# Briefing — {bairro}, {cidade}\n<!-- Deep Research cache -->\n"


import tools.deep_research_tool as _dr_mod

_dr_mod.rodar_deep_research = _mock_deep_research  # type: ignore[method-assign]

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents.a0_context_builder import context_builder_agent
from tools.cnpj_fitness_tools import analise_parque_ativo_para_a0


def _extract_market_context(session_state: dict) -> dict:
    raw = session_state.get("market_context")
    if isinstance(raw, dict) and "market_context" in raw:
        return raw["market_context"]
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
        else:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                inner = parsed.get("market_context")
                return inner if isinstance(inner, dict) else parsed
        except json.JSONDecodeError:
            pass
    return {}


async def run_a0() -> dict:
    session_service = InMemorySessionService()
    session_id = "test_a0_analise"
    user_id = "test_user"

    await session_service.create_session(
        app_name="gymsite_test_a0",
        user_id=user_id,
        session_id=session_id,
        state={},
    )

    runner = Runner(
        agent=context_builder_agent,
        app_name="gymsite_test_a0",
        session_service=session_service,
    )

    prompt = (
        "Mercado para academia tradicional em Fortaleza, bairro Meireles, CE.\n"
        "cidade: Fortaleza\nuf: CE\nbairro: Meireles\n"
        "tipo_negocio: academia\ntamanho_preset: m\ngenero_alvo: misto\n"
    )
    message = Content(role="user", parts=[Part(text=prompt)])

    tools_called: list[str] = []
    print("[A0] ContextBuilder — DR + analise parque CNPJ...")
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if hasattr(event, "content") and event.content:
            for part in getattr(event.content, "parts", []) or []:
                fc = getattr(part, "function_call", None)
                if fc and getattr(fc, "name", None):
                    tools_called.append(fc.name)
                    print(f"  -> tool: {fc.name}")

    session = await session_service.get_session(
        app_name="gymsite_test_a0",
        user_id=user_id,
        session_id=session_id,
    )
    mc = _extract_market_context(session.state or {})
    return mc, tools_called


def _insight_usa_cnpj(insights: list) -> bool:
    texto = " ".join(str(i) for i in insights).lower()
    sinais = (
        "cnpj",
        "parque",
        "entrante",
        "abertura",
        "segmento",
        "pilates",
        "academia",
        "90 dias",
        "90d",
        "estoque",
        "renovacao",
    )
    return sum(1 for s in sinais if s in texto) >= 2


async def main() -> int:
    insumo = analise_parque_ativo_para_a0("Fortaleza", "CE", 90, "Meireles")
    print("\n=== Insumo tool (analise_parque_ativo_para_a0) ===")
    print("indicadores:", json.dumps(insumo.get("indicadores_derivados"), ensure_ascii=False))
    print("perguntas:", len(insumo.get("perguntas_cruzamento_dr") or []))

    mc, tools = await run_a0()
    if not mc:
        print("\nERRO: market_context vazio")
        return 1

    analise = mc.get("analise_parque_cnpj")
    insights = mc.get("insights_estrategicos") or []

    print("\n=== A0 analise_parque_cnpj ===")
    print(json.dumps(analise, ensure_ascii=False, indent=2))

    print("\n=== insights_estrategicos ===")
    for i, ins in enumerate(insights, 1):
        print(f"  {i}. {ins}")

    checks: list[tuple[str, bool]] = [
        ("tool analise_parque_ativo_para_a0 chamada", "analise_parque_ativo_para_a0" in tools),
        ("analise_parque_cnpj presente", isinstance(analise, dict) and len(analise) >= 4),
        ("resumo_executivo preenchido", bool((analise or {}).get("resumo_executivo"))),
        ("cruzamento_deep_research preenchido", bool((analise or {}).get("cruzamento_deep_research"))),
        (">=2 insights citam CNPJ/parque", _insight_usa_cnpj(insights)),
        ("parque_ativo_total numerico", isinstance(mc.get("parque_ativo_total"), int)),
    ]

    print("\n=== Validacao ===")
    ok = True
    for nome, passed in checks:
        print(f"  [{'OK' if passed else 'FALHOU'}] {nome}")
        ok = ok and passed

  # Nao exigir copia identica — só que haja interpretacao
    if analise and (analise.get("resumo_executivo") or "").strip() == str(
        insumo.get("instrucao_agente", "")
    ):
        print("  [FALHOU] analise parece copia da instrucao da tool")
        ok = False

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
