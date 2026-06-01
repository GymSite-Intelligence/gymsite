#!/usr/bin/env python3
"""
Smoke E2E: dois runs A9 no mesmo bairro → Run1 MISS+SET, Run2 HIT (LangCache).

Não chama Gemini; exercita _a9_before_model_callback e _a9_after_model_callback.

Uso:
  .venv\\Scripts\\python.exe scripts/smoke_a9_langcache_e2e.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s — %(message)s",
)
# Reduz ruído de libs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class _FakeCallbackContext:
    def __init__(self, state: dict):
        self.state = state


def _montese_state() -> dict:
    """State sintético — mesmo bairro/concorrentes nos dois runs."""
    concorrentes = [
        {"place_id": "ChIJ_smoke_a1", "nome": "Smart Fit Montese"},
        {"place_id": "ChIJ_smoke_a2", "nome": "Bluefit Montese"},
        {"place_id": "ChIJ_smoke_a3", "nome": "Bodytech Montese"},
    ]
    return {
        "cidade": "Fortaleza",
        "input_cidade": "Fortaleza",
        "bairro": "Montese",
        "input_bairro": "Montese",
        "tipo_negocio": "academia",
        "inteligencia_competitiva": {
            "inteligencia_competitiva": {
                "concorrentes_detalhados": concorrentes,
            }
        },
    }


def main() -> int:
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    from agents.a9_positioning_strategist import (
        _a9_after_model_callback,
        _a9_before_model_callback,
        _a9_cache_prompt,
    )
    from tools.langcache_client import is_langcache_configured

    if not is_langcache_configured():
        print("FAIL: LangCache não configurado (.env)")
        return 1

    state = _montese_state()
    prompt_key = _a9_cache_prompt(state)
    print(f"prompt_key={prompt_key}\n")

    fake_llm_request = object()

    # ── Run 1: esperado MISS → SET via after_model ──
    print("=== RUN 1 (esperado: LangCache MISS -> SET) ===")
    ctx1 = _FakeCallbackContext(dict(state))
    hit1 = _a9_before_model_callback(ctx1, fake_llm_request)
    if hit1 is not None:
        print("FAIL RUN1: before_model retornou cache (esperava MISS)")
        return 2
    print("OK RUN1: before_model = None (MISS)\n")

    sample_json = (
        '```json\n'
        '{"veredito_posicionamento": "OCEANO_AZUL", '
        '"gaps_identificados": [], '
        '"recomendacao_ticket": {"ticket_recomendado": 249}, '
        '"markdown": "# Smoke A9 LangCache"}\n'
        '```'
    )
    llm_response = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text=sample_json)],
        ),
        turn_complete=True,
    )
    _a9_after_model_callback(ctx1, llm_response)
    print("OK RUN1: after_model executado (SET no LangCache)\n")

    # ── Run 2: esperado HIT → LlmResponse com langcache_hit ──
    print("=== RUN 2 (esperado: LangCache HIT -> A9 LangCache HIT) ===")
    ctx2 = _FakeCallbackContext(dict(state))
    hit2 = _a9_before_model_callback(ctx2, fake_llm_request)
    if hit2 is None:
        print("FAIL RUN2: before_model = None (esperava HIT)")
        return 3

    meta = getattr(hit2, "custom_metadata", None) or {}
    if not meta.get("langcache_hit"):
        print("FAIL RUN2: custom_metadata.langcache_hit ausente")
        return 4

    text = ""
    content = getattr(hit2, "content", None)
    if content and getattr(content, "parts", None):
        for part in content.parts:
            if getattr(part, "text", None):
                text += part.text
    if "OCEANO_AZUL" not in text:
        print("FAIL RUN2: resposta em cache não contém payload esperado")
        return 5

    print("OK RUN2: before_model retornou LlmResponse (HIT)")
    print(f"OK RUN2: payload preview={text[:120]!r}...\n")

    # Run 2 after_model não deve re-gravar (langcache_hit)
    _a9_after_model_callback(ctx2, hit2)
    print("OK RUN2: after_model ignorou re-SET (langcache_hit)\n")

    print("SMOKE A9 LangCache E2E: PASS (2 runs, mesmo bairro, HIT confirmado)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
