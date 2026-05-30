"""
Smoke test: valida que a migração pra Vertex AI funcionou.

Roda 3 checagens em ordem:
  1. Variáveis de ambiente corretas
  2. Auth via Service Account → simple text generation (sem grounding)
  3. Search Grounding → query que exige busca atual ("preço dólar hoje")

Uso:
    python tests/test_vertex_setup.py

Saída esperada: três ✓ verdes e tempo total. Se algum passo falhar, mostra
o erro completo pra debug.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def step(name: str, fn):
    print(f"\n> {name}...", flush=True)
    t0 = time.time()
    try:
        fn()
        print(f"  ✓ OK ({time.time() - t0:.2f}s)", flush=True)
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def check_env():
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower()
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "")
    sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    if use_vertex != "true":
        raise RuntimeError(
            "GOOGLE_GENAI_USE_VERTEXAI != 'true'. Setar no .env."
        )
    if project != "gen-lang-client-0106729343":
        raise RuntimeError(
            f"GOOGLE_CLOUD_PROJECT={project!r} (esperado 'gen-lang-client-0106729343')"
        )
    if location != "us-central1":
        raise RuntimeError(
            f"GOOGLE_CLOUD_LOCATION={location!r} (esperado 'us-central1' p/ Grounding)"
        )
    if not sa_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS vazio")
    if not Path(sa_path).exists():
        raise RuntimeError(f"SA JSON não encontrado em: {sa_path}")
    print(f"  - VERTEXAI=true, project={project}, region={location}")
    print(f"  - SA: {sa_path}")


def check_simple_call():
    """Chamada Vertex básica sem grounding."""
    from google import genai
    client = genai.Client()  # usa env vars + ADC
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Responda apenas 'pong'.",
    )
    text = (resp.text or "").strip().lower()
    if "pong" not in text:
        raise RuntimeError(f"resposta inesperada: {text!r}")
    print(f"  - resposta: {text!r}")


def check_grounding():
    """Search Grounding ativo — exige busca em tempo real."""
    from google import genai
    from google.genai import types

    client = genai.Client()
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            "Qual o ticket médio mensal das academias Smart Fit no Brasil em 2026? "
            "Responda em uma frase com fontes."
        ),
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    text = (resp.text or "").strip()
    if len(text) < 30:
        raise RuntimeError(f"resposta muito curta (grounding off?): {text!r}")
    # Checa se houve grounding_metadata
    grounding = None
    cands = getattr(resp, "candidates", []) or []
    if cands:
        grounding = getattr(cands[0], "grounding_metadata", None)
    print(f"  - resposta ({len(text)} chars): {text[:160]}...")
    if grounding:
        chunks = getattr(grounding, "grounding_chunks", None) or []
        print(f"  - grounding_chunks: {len(chunks)} fontes")
    else:
        print("  ! sem grounding_metadata (verificar se Search está ativo na região)")


def main():
    print("=" * 60)
    print("Vertex AI Setup — Smoke Test")
    print("=" * 60)

    ok1 = step("1. Variáveis de ambiente", check_env)
    if not ok1:
        sys.exit(1)
    ok2 = step("2. Auth + chamada simples", check_simple_call)
    if not ok2:
        sys.exit(1)
    ok3 = step("3. Search Grounding em us-central1", check_grounding)

    print("\n" + "=" * 60)
    if ok1 and ok2 and ok3:
        print("✓ Vertex AI operacional. Pipeline pronto pra usar.")
        sys.exit(0)
    else:
        print("✗ Alguma checagem falhou — ver logs acima.")
        sys.exit(1)


if __name__ == "__main__":
    main()
