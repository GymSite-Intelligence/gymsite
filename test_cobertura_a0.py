"""
Valida _build_cobertura_redes_a0 do A6.

Casos:
1. A3a emitiu redes_a0_nao_encontradas explicitamente (caso Eusébio)
2. Fallback: A3a antigo não emite, deduz a partir de inteligencia_competitiva
3. Tudo vazio (market_context sem redes do DR)
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "gymsite_intelligence" / ".env")

# Importa só o helper (não dispara o agent)
sys.path.insert(0, str(Path(__file__).parent))
from agents.a6_report_consolidator import _build_cobertura_redes_a0

print("=" * 70)
print("Cobertura A0 helper — 3 casos")
print("=" * 70)

# Caso 1: A3a moderno (geo-fence ativo) — emite explicitamente as listas
print("\n[1] A3a moderno: emite redes_a0_nao_encontradas")
cs_moderno = {
    "redes_a0_cobertas": ["Smart Fit", "Greenlife"],
    "redes_a0_nao_encontradas": ["Selfit", "Dumbbells", "Porão Academia"],
    "concorrentes_excluidos": [
        {"nome": "Clínica Pilates Reformer X", "motivo": "clinica_fisio"},
    ],
}
inner_mc = {
    "principais_redes_concorrentes": [
        "Smart Fit", "Greenlife", "Selfit", "Dumbbells", "Porão Academia"
    ]
}
inner_ic = {}
result = _build_cobertura_redes_a0(cs_moderno, inner_mc, inner_ic)
print(f"  redes_solicitadas: {result['redes_solicitadas']}")
print(f"  redes_cobertas: {result['redes_cobertas']}")
print(f"  redes_nao_encontradas: {result['redes_nao_encontradas']}")
print(f"  concorrentes_excluidos: {len(result['concorrentes_excluidos'])} items")
print(f"  tem_redes_fantasma: {result['tem_redes_fantasma']}")
assert result["tem_redes_fantasma"] == True
assert "Selfit" in result["redes_nao_encontradas"]
assert "Smart Fit" in result["redes_cobertas"]
print("  [OK]")

# Caso 2: A3a antigo, sem campos explícitos — deduz a partir de A3b
print("\n[2] Fallback: deduz a partir de inteligencia_competitiva")
cs_legado = {}  # vazio
inner_ic_legado = {
    "concorrentes_detalhados": [
        {"nome": "Smart Fit - Shopping Eusébio", "rating_geral": 3.9},
        {"nome": "Greenlife - Eusébio", "rating_geral": 4.4},
    ]
}
result2 = _build_cobertura_redes_a0(cs_legado, inner_mc, inner_ic_legado)
print(f"  redes_cobertas (dedut.): {result2['redes_cobertas']}")
print(f"  redes_nao_encontradas (deriv.): {result2['redes_nao_encontradas']}")
assert "Smart Fit" in result2["redes_cobertas"]
assert "Selfit" in result2["redes_nao_encontradas"]
print("  [OK]")

# Caso 3: sem redes do DR
print("\n[3] DR não listou redes")
result3 = _build_cobertura_redes_a0({}, {}, {})
print(f"  output: {result3}")
assert result3["redes_solicitadas"] == []
assert result3["tem_redes_fantasma"] == False
print("  [OK]")

print("\n" + "=" * 70)
print("Helper _build_cobertura_redes_a0: 3/3 casos OK")
print("=" * 70)
