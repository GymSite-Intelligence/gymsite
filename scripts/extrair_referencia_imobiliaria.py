"""CLI simples para extrair referência macro imobiliária via BCB/Olinda.

Uso esperado:
    python scripts/extrair_referencia_imobiliaria.py --cidade "Hortolândia/SP"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

# Permite execução direta `python scripts/extrair_referencia_imobiliaria.py`.
if __package__ is None or __package__ == "":
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

from tools.bcb_imobiliario_olinda import extrair_resumo_imobiliario


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Extrai referência macro de mercado imobiliário via Banco Central (Olinda). "
            "Complementa o Tier 1 de portais municipais."
        )
    )
    p.add_argument(
        "--cidade",
        type=str,
        default="",
        help=(
            "Cidade/UF apenas para contexto textual (ex.: 'Hortolândia/SP'). "
            "Não altera a consulta macro no BCB."
        ),
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Imprime somente o JSON estruturado (stdout).",
    )
    return p


def _format_human(resumo: Dict[str, Any]) -> str:
    linhas: list[str] = []
    fonte = resumo.get("fonte") or "Banco Central do Brasil — MercadoImobiliario (Olinda)"
    cidade = resumo.get("cidade_contexto") or ""
    norte = resumo.get("norte") or ""

    header_ctx = f"Contexto: {cidade}" if cidade else ""
    if header_ctx:
        linhas.append(header_ctx)
    linhas.append(f"Fonte macro: {fonte}")
    if resumo.get("url_base"):
        linhas.append(f"URL base: {resumo['url_base']}")
    if norte:
        linhas.append("")
        linhas.append(norte)

    # Lista até algumas séries com data/valor pra ancorar o analista.
    series = resumo.get("series") or []
    if series:
        linhas.append("")
        linhas.append("Séries recentes (amostra):")
        for s in series[:6]:
            nome = str(s.get("info") or "")
            data = str(s.get("data") or "")
            valor = s.get("valor")
            if isinstance(valor, (int, float)):
                valor_txt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                valor_txt = str(valor)
            linhas.append(f"- {nome} — {data} — {valor_txt}")

    destaques = resumo.get("destaques") or {}
    if destaques:
        linhas.append("")
        linhas.append("Destaques identificados (financiamento/crédito):")
        for chave, s in destaques.items():
            nome = str(s.get("info") or chave)
            data = str(s.get("data") or "")
            valor = s.get("valor")
            if isinstance(valor, (int, float)):
                valor_txt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                valor_txt = str(valor)
            linhas.append(f"- {chave}: {nome} — {data} — {valor_txt}")

    if not resumo.get("ok"):
        erro = resumo.get("erro") or "Motivo não informado."
        linhas.append("")
        linhas.append(f"[AVISO] Consulta ao BCB falhou: {erro}")

    return "\n".join(linhas)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    cidade_contexto = (args.cidade or "").strip() or None
    resumo = extrair_resumo_imobiliario(cidade_contexto=cidade_contexto)

    if args.json:
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
        return

    texto = _format_human(resumo)
    print(texto)


if __name__ == "__main__":
    main()

