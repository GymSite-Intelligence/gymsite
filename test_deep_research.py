"""Teste isolado do Deep Research — verifica tier Interactions vs grounded."""
import sys

print("=" * 60)
print("Teste Deep Research - GymSite Intelligence")
print("=" * 60)

try:
    from tools.deep_research_tool import (
        DEEP_RESEARCH_AGENT,
        FALLBACK_MODEL,
        TIMEOUT_SEGUNDOS,
        _executar_deep_research,
        get_last_execution_tier,
    )

    print(f"Agent (Tier 1): {DEEP_RESEARCH_AGENT}")
    print(f"Fallback (Tier 2): {FALLBACK_MODEL}")
    print(f"Timeout global: {TIMEOUT_SEGUNDOS}s")
    print()
    print("Chamando API (Tier 1 Interactions pode levar vários minutos)...")
    print()

    query = (
        "Resumo curto do mercado fitness em Fortaleza, Ceará, Brasil. "
        "Máximo 600 caracteres. Inclua 1 URL de fonte."
    )
    resultado, tier = _executar_deep_research(query)

    print("[OK] API respondeu!")
    print(f"Tier usado: {tier}")
    print(f"get_last_execution_tier(): {get_last_execution_tier()}")
    print()
    print("--- Preview (primeiros 800 chars) ---")
    print(resultado[:800])
    print()
    print("--- Total de chars:", len(resultado))

    if tier.startswith("interactions:"):
        print("\n[SUCESSO] Deep Research agent (Interactions API) ativo.")
    elif tier.startswith("grounded:"):
        print("\n[AVISO] Caiu no fallback grounded — Tier 1 falhou ou estourou prazo.")
        sys.exit(2)

except Exception as e:
    print(f"[FALHA] {type(e).__name__}: {e}")
    print()
    print("Possíveis causas:")
    print("1. Conta sem acesso ao agente Deep Research")
    print("2. Quota / billing")
    print("3. GOOGLE_GENAI_USE_VERTEXAI=true (Interactions agent não disponível)")
    print()
    sys.exit(1)
