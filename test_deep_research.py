"""Teste isolado do Deep Research — verifica se o modelo está disponível."""
import sys

print("=" * 60)
print("Teste Deep Research - GymSite Intelligence v0.4")
print("=" * 60)

try:
    from tools.deep_research_tool import _executar_deep_research, DEEP_RESEARCH_MODEL
    print(f"Modelo configurado: {DEEP_RESEARCH_MODEL}")
    print(f"Chamando API... (pode demorar ate 30s)")
    print()

    query = "Resumo curto do mercado fitness em Fortaleza, Ceara, Brasil. Maximo 500 caracteres."
    resultado = _executar_deep_research(query)

    print("[OK] API respondeu!")
    print()
    print("--- Preview do resultado (primeiros 800 chars) ---")
    print(resultado[:800])
    print()
    print("--- Total de chars retornados:", len(resultado))

except Exception as e:
    print(f"[FALHA] {type(e).__name__}: {e}")
    print()
    print("Possiveis causas:")
    print("1. Modelo nao disponivel na conta (404 NotFound)")
    print("2. Quota excedida")
    print("3. Tools incompativeis (url_context+google_search no mesmo modelo)")
    print()
    print("Cole esta saida no chat para diagnostico.")
    sys.exit(1)
