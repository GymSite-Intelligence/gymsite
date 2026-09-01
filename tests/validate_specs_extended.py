"""
tests/validate_specs_extended.py

Extensão L4 para A0, A2, A3a, A3b, A7 — reutiliza validadores de validate_specs.

Uso:
  python tests/validate_specs_extended.py \\
    --json metrics/relatorios/rpt_1786399356.json \\
    --agentes A0,A2,A3a,A3b,A7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante import do sibling validate_specs quando rodado como script
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from validate_specs import (  # noqa: E402
    carregar_resultado,
    validar_a0,
    validar_a2,
    validar_a3a,
    validar_a3b,
    validar_a7,
)

VALIDADORES = {
    "A0": validar_a0,
    "A2": validar_a2,
    "A3a": validar_a3a,
    "A3b": validar_a3b,
    "A7": validar_a7,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validação L4 estendida — A0, A2, A3a, A3b, A7"
    )
    parser.add_argument("--json", required=True, help="Path do relatório JSON")
    parser.add_argument(
        "--agentes",
        default="A0,A2,A3a,A3b,A7",
        help="Lista de agentes (vírgula)",
    )
    args = parser.parse_args()

    if not Path(args.json).exists():
        print(f"Erro: arquivo nao encontrado: {args.json}")
        sys.exit(1)

    resultado = carregar_resultado(args.json)
    agentes = [a.strip() for a in args.agentes.split(",") if a.strip()]
    todas_falhas: list[str] = []
    resumo: dict[str, str] = {}

    print("=" * 70)
    print("VALIDACAO L4 ESTENDIDA — A0, A2, A3a, A3b, A7")
    print("=" * 70)

    for agente in agentes:
        validador = VALIDADORES.get(agente)
        if not validador:
            print(f"\n[{agente}] validador nao encontrado")
            continue
        falhas = validador(resultado)
        resumo[agente] = "APROVADO" if not falhas else "REPROVADO"
        todas_falhas.extend(falhas)
        status = "APROVADO" if not falhas else f"REPROVADO ({len(falhas)})"
        print(f"\n[{agente}] {status}")
        for f in falhas:
            print(f"    - {f}")

    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    for agente, status in resumo.items():
        print(f"  {agente}: {status}")

    if todas_falhas:
        print(f"\nTotal de falhas: {len(todas_falhas)}")
        sys.exit(1)

    print("\nTodos os agentes APROVADOS")
    sys.exit(0)


if __name__ == "__main__":
    main()
