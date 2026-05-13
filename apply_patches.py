#!/usr/bin/env python3
"""
apply_patches.py -- Aplica patches da integracao Google Distance Matrix
nos arquivos existentes do projeto GymSite Intelligence.

Uso (na raiz do projeto):
    python apply_patches.py [--dry-run]

O que faz:
    1. Faz backup de cada arquivo antes de modificar (.bak)
    2. Patcha tools/antt_tools.py (nova assinatura + resolucao de distancia)
    3. Patcha tools/financial_tools.py (propaga lat/lng)
    4. Patcha agents/a4_financial_estimator.py (extrai lat/lng do candidato top-1)
    5. Atualiza requirements.txt (adiciona googlemaps)
    6. Atualiza .env.example (adiciona GOOGLE_DISTANCE_MATRIX_API_KEY)
"""

import re
import shutil
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv
BASE = Path(__file__).parent


def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    print(f"  [backup] {bak.name}")


def write_file(path: Path, content: str):
    if DRY_RUN:
        print(f"  [dry-run] would write {path}")
        return
    backup(path)
    path.write_text(content, encoding="utf-8")
    print(f"  [ok] {path}")


def append_if_missing(path: Path, line: str, comment: str = ""):
    """Adiciona linha ao arquivo apenas se ainda nao existir."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if line.strip() in text:
        print(f"  [skip] ja existe em {path.name}: {line.strip()!r}")
        return
    new_text = text.rstrip() + "\n" + (f"# {comment}\n" if comment else "") + line + "\n"
    if DRY_RUN:
        print(f"  [dry-run] would append to {path.name}: {line!r}")
        return
    path.write_text(new_text, encoding="utf-8")
    print(f"  [ok] appended to {path.name}: {line!r}")


# --------------------------------------------------------------------------
# 1. tools/antt_tools.py
# --------------------------------------------------------------------------
print("\n=== Patch 1: tools/antt_tools.py ===")
antt_path = BASE / "tools" / "antt_tools.py"
if not antt_path.exists():
    print(f"  [skip] {antt_path} nao encontrado")
else:
    src = antt_path.read_text(encoding="utf-8")

    # a) Garante import Optional
    if "from typing import" in src:
        src = re.sub(
            r"(from typing import )([^\n]+)",
            lambda m: m.group(0) if "Optional" in m.group(2)
                     else m.group(1) + m.group(2).rstrip() + ", Optional",
            src,
            count=1,
        )
    elif "import typing" not in src:
        src = "from typing import Optional\n" + src

    # b) Substitui assinatura da funcao (variantes com e sem parametros adicionais)
    old_sig_pattern = re.compile(
        r"def calcular_frete_kit_equipamentos\(\s*"
        r"valor_kit:\s*float,\s*"
        r"uf_destino:\s*str,?\s*"
        r"(?:distancia_km:\s*float\s*=\s*None,?\s*)?"
        r"\)\s*->\s*dict:",
        re.DOTALL,
    )
    new_sig = (
        "def calcular_frete_kit_equipamentos(\n"
        "    valor_kit: float,\n"
        "    uf_destino: str,\n"
        "    destino_lat: Optional[float] = None,\n"
        "    destino_lng: Optional[float] = None,\n"
        "    fornecedor_principal: str = \"default\",\n"
        "    distancia_km: Optional[float] = None,\n"
        ") -> dict:"
    )
    if old_sig_pattern.search(src):
        src = old_sig_pattern.sub(new_sig, src)
        print("  [ok] assinatura substituida")
    else:
        print("  [warn] padrao de assinatura nao encontrado  verificar manualmente")

    # c) Injeta bloco de resolucao de distancia ANTES da primeira chamada a
    #    estimar_distancia_sp_para_uf (se ainda nao foi injetado)
    distance_block = '''
    # --- Resolucao de distancia (injetado por apply_patches.py) ---
    _fonte_distancia: str
    if distancia_km is None:
        if destino_lat is not None and destino_lng is not None:
            try:
                from tools.distance_matrix_tools import distancia_fornecedor_para_cidade
                _res = distancia_fornecedor_para_cidade(
                    fornecedor_principal, destino_lat, destino_lng
                )
                if _res:
                    distancia_km = _res["distancia_km"]
                    _fonte_distancia = _res["fonte"]
            except Exception as _exc:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "frete: fallback distancia -- %s", _exc
                )
        if distancia_km is None:
            distancia_km = estimar_distancia_sp_para_uf(uf_destino)
            _fonte_distancia = "estimativa_por_uf"
    else:
        _fonte_distancia = "informada_pelo_chamador"
    # --- fim resolucao de distancia ---
'''
    if "injetado por apply_patches.py" not in src:
        # Insere antes da primeira chamada a estimar_distancia_sp_para_uf
        src = re.sub(
            r"(\s*distancia_km\s*=\s*estimar_distancia_sp_para_uf\()",
            distance_block + "    \\1",
            src,
            count=1,
        )

    # d) Adiciona fonte_distancia no dict de retorno (se nao existir)
    if '"fonte_distancia"' not in src and "'fonte_distancia'" not in src:
        src = re.sub(
            r"(return\s*\{)",
            '\\1\n        "fonte_distancia": _fonte_distancia,\n        "distancia_km_utilizada": distancia_km,',
            src,
            count=1,
        )

    write_file(antt_path, src)


# --------------------------------------------------------------------------
# 2. tools/financial_tools.py
# --------------------------------------------------------------------------
print("\n=== Patch 2: tools/financial_tools.py ===")
fin_path = BASE / "tools" / "financial_tools.py"
if not fin_path.exists():
    print(f"  [skip] {fin_path} nao encontrado")
else:
    src = fin_path.read_text(encoding="utf-8")

    # Adiciona Optional import se necessario
    if "from typing import" in src and "Optional" not in src:
        src = re.sub(
            r"(from typing import )([^\n]+)",
            lambda m: m.group(1) + m.group(2).rstrip() + ", Optional",
            src, count=1,
        )
    elif "Optional" not in src and "from typing" not in src:
        src = "from typing import Optional\n" + src

    # Patcha _calcular_capex_detalhado para aceitar destino_lat/lng
    old_capex_sig = re.compile(
        r"def _calcular_capex_detalhado\(\s*([^)]+)\)\s*->",
        re.DOTALL,
    )
    match = old_capex_sig.search(src)
    if match:
        params = match.group(1)
        if "destino_lat" not in params:
            new_params = params.rstrip() + ",\n    destino_lat: Optional[float] = None,\n    destino_lng: Optional[float] = None,\n    fornecedor_principal: str = \"default\","
            src = src[:match.start(1)] + new_params + src[match.end(1):]
            print("  [ok] _calcular_capex_detalhado assinatura atualizada")
        else:
            print("  [skip] destino_lat ja existe em _calcular_capex_detalhado")
    else:
        print("  [warn] _calcular_capex_detalhado nao encontrado  verificar manualmente")

    # Patcha chamada interna a calcular_frete_kit_equipamentos para passar lat/lng
    if "destino_lat=destino_lat" not in src:
        src = re.sub(
            r"(calcular_frete_kit_equipamentos\([^)]+)(\))",
            lambda m: m.group(1)
                + ",\n        destino_lat=destino_lat,\n        destino_lng=destino_lng,\n        fornecedor_principal=fornecedor_principal"
                + m.group(2)
                if "destino_lat" not in m.group(0) else m.group(0),
            src,
        )

    write_file(fin_path, src)


# --------------------------------------------------------------------------
# 3. agents/a4_financial_estimator.py
# --------------------------------------------------------------------------
print("\n=== Patch 3: agents/a4_financial_estimator.py ===")
a4_path = BASE / "agents" / "a4_financial_estimator.py"
if not a4_path.exists():
    print(f"  [skip] {a4_path} nao encontrado")
else:
    src = a4_path.read_text(encoding="utf-8")

    # Adiciona extracao de lat/lng do candidato top-1 antes da chamada a
    # analise_financeira_a4_completo (ou _calcular_capex_detalhado)
    latlng_snippet = '''
    # Extrai lat/lng do candidato top-1 (injetado por apply_patches.py)
    _candidatos = state.get("candidatos_geoscout", {}).get("candidatos", [{}])
    _top1 = _candidatos[0] if _candidatos else {}
    _latlng = _top1.get("latlng") or _top1.get("location") or {}
    _destino_lat = _latlng.get("lat") if isinstance(_latlng, dict) else None
    _destino_lng = _latlng.get("lng") if isinstance(_latlng, dict) else None
    # fim extracao lat/lng
'''
    if "injetado por apply_patches.py" not in src:
        # Insere antes da chamada principal
        for target in [
            "analise_financeira_a4_completo(",
            "_calcular_capex_detalhado(",
            "calcular_frete_kit_equipamentos(",
        ]:
            if target in src:
                src = src.replace(target, latlng_snippet + "    " + target, 1)
                print(f"  [ok] snippet lat/lng inserido antes de {target}")
                break
        else:
            print("  [warn] ponto de insercao nao encontrado em a4  adicionar manualmente")

    # Adiciona destino_lat/lng na chamada se ainda nao estiver la
    for call_target in [
        "analise_financeira_a4_completo(",
        "_calcular_capex_detalhado(",
    ]:
        if call_target in src and "destino_lat=_destino_lat" not in src:
            # Localiza o fechamento da chamada e injeta args
            src = re.sub(
                r"(" + re.escape(call_target) + r"[^)]+)(\))",
                lambda m: m.group(1)
                    + ",\n        destino_lat=_destino_lat,\n        destino_lng=_destino_lng"
                    + m.group(2)
                    if "destino_lat" not in m.group(0) else m.group(0),
                src,
            )

    write_file(a4_path, src)


# --------------------------------------------------------------------------
# 4. requirements.txt
# --------------------------------------------------------------------------
print("\n=== Patch 4: requirements.txt ===")
req_path = BASE / "requirements.txt"
append_if_missing(req_path, "googlemaps>=4.10.0", "Google Maps Platform SDK")


# --------------------------------------------------------------------------
# 5. .env.example
# --------------------------------------------------------------------------
print("\n=== Patch 5: .env.example ===")
env_path = BASE / ".env.example"
append_if_missing(
    env_path,
    "GOOGLE_DISTANCE_MATRIX_API_KEY=AIzaSy...",
    "Distance Matrix API (pode reusar GOOGLE_MAPS_API_KEY se habilitada pra Distance Matrix)",
)


print("\n=== Concluido! ===")
if DRY_RUN:
    print("Modo dry-run: nenhum arquivo foi modificado.")
else:
    print("Verifique os arquivos .bak para rollback se necessario.")
    print("Execute: python -m pytest tests/test_distance_matrix.py -v")
