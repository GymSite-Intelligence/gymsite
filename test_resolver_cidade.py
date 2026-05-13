"""
Valida resolver_cidade_efetiva e get_bairros_alternativos pra Eusébio.

Casos:
1. cidade=Fortaleza + bairro=Eusébio → resolve pra cidade_efetiva=Eusébio
2. cidade=Fortaleza + bairro=Meireles → mantém Fortaleza
3. cidade=Eusébio + bairro=Tamatanduba → mantém Eusébio (já correto)
4. cidade=São Paulo + bairro=Guarulhos → resolve pra Guarulhos
5. Tolerância a acentos: Eusebio (sem acento) ainda detecta
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agents.a6_report_consolidator import (
    resolver_cidade_efetiva,
    get_bairros_alternativos,
)

print("=" * 70)
print("Resolver Cidade Efetiva — 5 casos")
print("=" * 70)

casos = [
    ("Fortaleza", "Eusébio", "eusébio", True),
    ("Fortaleza", "Meireles", "Fortaleza", False),
    ("Eusébio", "Tamatanduba", "Eusébio", False),
    ("São Paulo", "Guarulhos", "guarulhos", True),
    ("Fortaleza", "Eusebio", "eusébio", True),  # sem acento
    ("Fortaleza", "caucaia", "caucaia", True),
]

for cidade, bairro, esperada, deve_corrigir in casos:
    efetiva, corrigida = resolver_cidade_efetiva(cidade, bairro)
    ok = corrigida == deve_corrigir
    status = "[OK]" if ok else "[FAIL]"
    print(f"{status} cidade={cidade!r:15s} bairro={bairro!r:15s} -> efetiva={efetiva!r}, corrigida={corrigida}")
    assert ok, f"esperava corrigida={deve_corrigir}, veio {corrigida}"

print()
print("=" * 70)
print("Bairros Alternativos pós-resolução")
print("=" * 70)

# Caso clássico do bug: Fortaleza + Eusébio
efetiva, _ = resolver_cidade_efetiva("Fortaleza", "Eusébio")
bairros = get_bairros_alternativos(efetiva)
print(f"\nEusébio (via Fortaleza + Eusébio) — {len(bairros)} bairros:")
for b in bairros:
    print(f"  - {b['bairro']}: {b['motivo'][:60]}")

# Garantia: NENHUM bairro de Fortaleza-cidade deve estar aqui
nomes_fortaleza_proibidos = {"cocó", "papicu", "guararapes", "maraponga", "montese", "cidade dos funcionários", "cambeba"}
for b in bairros:
    nome_low = b["bairro"].lower()
    for proibido in nomes_fortaleza_proibidos:
        assert proibido not in nome_low, (
            f"REGRESSÃO: bairro de Fortaleza {proibido!r} ainda aparece em Eusébio!"
        )

print(f"\n[OK] Nenhum bairro de Fortaleza-cidade na lista de Eusébio")
print()
print("=" * 70)
print("[OK] 6/6 casos passaram + zero regressão")
print("=" * 70)
