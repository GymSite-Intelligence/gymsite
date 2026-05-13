"""
Valida geo-fence da busca expandida A0.

Cenário: bairro alvo Eusébio/CE com redes do A0 que NÃO têm unidade local:
- Selfit (mais perto fica em Fortaleza-centro, ~13km)
- Dumbbells (Jardim Guanabara, ~15km)
- Porão Pro CT (Varjota, ~14km)

Esperado: nenhuma dessas redes deve aparecer no Top 5 — todas vão pra
redes_a0_nao_encontradas. Smart Fit e Greenlife (com unidades locais) sim devem
aparecer, com distancia_km baixa.
"""
import os
import sys
from pathlib import Path

# Garante que .env é carregado
from dotenv import load_dotenv
# .env do package tem GOOGLE_MAPS_API_KEY (root .env só tem MAPS_API_KEY)
load_dotenv(Path(__file__).parent / "gymsite_intelligence" / ".env")
load_dotenv(Path(__file__).parent / ".env", override=False)

from tools.competitor_tools import (
    _buscar_rede_geofenced,
    buscar_concorrentes_balanceados,
)
from tools.maps_tools import geocode_endereco

print("=" * 70)
print("GEO-FENCE Eusébio/CE — validacao das redes do Deep Research")
print("=" * 70)

# Geocoda centro de Eusébio
geo = geocode_endereco("Eusébio, Eusébio, CE, Brasil")
if "error" in geo:
    print(f"[FALHA] Geocode: {geo['error']}")
    sys.exit(1)
lat, lng = geo["lat"], geo["lng"]
print(f"\nCentro Eusébio: ({lat:.4f}, {lng:.4f})")

print("\n[1] Redes que o DR errou — esperado: None ou unidade DENTRO do raio 5km")
for rede in ["Selfit", "Dumbbells", "Porão Pro CT", "Porão Academia"]:
    match = _buscar_rede_geofenced(rede, lat, lng, raio_max_metros=5000)
    if match:
        print(f"  {rede:25s} -> ACHOU: {match['nome'][:45]:45s} ({match['distancia_km']} km)")
    else:
        print(f"  {rede:25s} -> [OK] None (nenhuma unidade no raio 5km)")

print("\n[2] Redes que o DR acertou — esperado: match DENTRO do raio")
for rede in ["Smart Fit", "Greenlife"]:
    match = _buscar_rede_geofenced(rede, lat, lng, raio_max_metros=5000)
    if match:
        print(f"  {rede:25s} -> [OK] {match['nome'][:45]:45s} ({match['distancia_km']} km)")
    else:
        print(f"  {rede:25s} -> [FALHA] não achou unidade local")

print("\n[3] Macro-tool com market_context simulado do A0")

class _FakeState(dict):
    pass

class _FakeContext:
    def __init__(self, redes):
        self.state = _FakeState({
            "market_context": {
                "principais_redes_concorrentes": redes
            }
        })

ctx = _FakeContext([
    "Smart Fit",       # tem unidade local
    "Greenlife",       # tem unidade local
    "Selfit",          # ❌ DR errou
    "Dumbbells",       # ❌ DR errou
    "Porão Academia",  # ❌ DR errou
])

resultado = buscar_concorrentes_balanceados(
    tool_context=ctx,
    bairro="Eusébio",
    cidade="Eusébio",
    raio_metros=3000,
    raio_expandido_metros=5000,
)

print(f"  redes_a0_cobertas: {resultado.get('redes_a0_cobertas')}")
print(f"  redes_a0_nao_encontradas: {resultado.get('redes_a0_nao_encontradas')}")
print()
print("  Top 5 selecionados:")
for c in resultado.get("concorrentes_top_5_balanceados", [])[:10]:
    origem = c.get("origem_busca", "primaria")
    nome = c.get("nome", "?")[:40]
    dist = c.get("distancia_km", "?")
    print(f"    - {nome:40s} ({dist} km) [{origem}]")

print()
nao_encontradas = resultado.get('redes_a0_nao_encontradas', [])
problema_resolvido = (
    "Selfit" in nao_encontradas
    or "Dumbbells" in nao_encontradas
    or "Porão Academia" in nao_encontradas
)
if problema_resolvido:
    print("[OK] Geo-fence funcionou: redes sem unidade local viraram nao_encontradas")
else:
    print("[ATENCAO] revisar — alguma rede sem unidade local ainda foi puxada")
