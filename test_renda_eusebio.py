"""
Valida fix de renda municipal: Eusébio deve voltar R$ 1.835 (Censo municipal),
não R$ 870 (média UF do CE).

Também testa:
- Município ausente do dict (fallback UF + aviso)
- Tolerância a acentos (Eusebio vs Eusébio)
"""
import sys
import json

# Não imprime emoji em terminal Windows que não suporta
def p(label, val):
    print(f"{label}: {val}")

print("=" * 70)
print("FIX RENDA MUNICIPAL — Validação Eusébio/CE")
print("=" * 70)

from tools.ibge_tools import (
    buscar_renda,
    buscar_municipio,
    analise_demografica_completa,
    RENDA_PER_CAPITA_MUNICIPIO,
    RENDA_MEDIA_UF,
)

print("\n[1] buscar_municipio('Eusebio', 'CE') — sem acento, tolerância")
mun = buscar_municipio("Eusebio", "CE")
p("  resultado", mun)
assert mun is not None, "FALHA: deveria achar Eusébio mesmo sem acento"
assert mun["codigo"] == "2304285", f"FALHA: código errado {mun['codigo']}"
print("  [OK] achou Eusébio (cod 2304285)")

print("\n[2] buscar_renda('2304285') — Eusébio direto")
renda = buscar_renda("2304285")
p("  renda_media", renda["renda_media"])
p("  fonte", renda["fonte"])
p("  granularidade", renda["granularidade"])
assert renda["renda_media"] == 1835, (
    f"FALHA: esperava R$ 1.835, veio R$ {renda['renda_media']}"
)
assert renda["granularidade"] == "municipal", "FALHA: granularidade deveria ser municipal"
assert "Censo IBGE 2022 (per capita municipal)" in renda["fonte"]
print("  [OK] renda municipal correta")

print("\n[3] buscar_renda('2304400') — Fortaleza (outro municipal)")
renda_fz = buscar_renda("2304400")
p("  renda_media", renda_fz["renda_media"])
p("  granularidade", renda_fz["granularidade"])
assert renda_fz["renda_media"] == 1572
assert renda_fz["granularidade"] == "municipal"
print("  [OK] Fortaleza retorna municipal R$ 1.572")

print("\n[4] buscar_renda('2300000') — código fictício CE (fallback UF)")
renda_fake = buscar_renda("2300000")
p("  renda_media", renda_fake["renda_media"])
p("  fonte", renda_fake["fonte"])
p("  granularidade", renda_fake["granularidade"])
p("  aviso", renda_fake.get("aviso", "(sem aviso)")[:120] + "...")
assert renda_fake["renda_media"] == RENDA_MEDIA_UF["CE"]
assert renda_fake["granularidade"] == "uf"
assert "aviso" in renda_fake
print("  [OK] fallback UF com aviso explícito")

print("\n[5] analise_demografica_completa('Eusebio', 'CE') — pipeline real")
result = analise_demografica_completa("Eusebio", "CE")
p("  municipio", result["municipio"])
p("  codigo_ibge", result["codigo_ibge"])
p("  populacao_total", result["populacao_total"])
p("  populacao_faixa_18_45", result["populacao_faixa_18_45"])
p("  renda_media_domiciliar", result["renda_media_domiciliar"])
p("  renda_granularidade", result["renda_granularidade"])
p("  fonte_renda", result["fonte_renda"])
p("  score_demografico", result["score_demografico"])
p("  classificacao", result["classificacao"])

assert result["municipio"] == "Eusébio"
assert result["populacao_total"] == 57345
assert result["renda_media_domiciliar"] == 1835, (
    f"REGRESSÃO: renda voltou pra média UF! Veio {result['renda_media_domiciliar']}"
)
assert result["renda_granularidade"] == "municipal"
assert "renda_aviso" not in result, "Não deve ter aviso quando é municipal"
print("  [OK] Eusébio com renda municipal R$ 1.835 + score real")

print("\n" + "=" * 70)
print("ANTES vs DEPOIS")
print("=" * 70)
print(f"  ANTES (média UF CE):     R$ {RENDA_MEDIA_UF['CE']:>6}  -> score baixo")
print(f"  DEPOIS (Censo municipal): R$ {result['renda_media_domiciliar']:>6}  -> score {result['score_demografico']}")
print(f"  Delta: R$ {result['renda_media_domiciliar'] - RENDA_MEDIA_UF['CE']:+}")
print()
print(f"Total municípios no dict: {len(RENDA_PER_CAPITA_MUNICIPIO)}")
print()
print("RESULTADO: [OK] Fix validado. Pipeline pode rodar Eusébio com confiança.")
