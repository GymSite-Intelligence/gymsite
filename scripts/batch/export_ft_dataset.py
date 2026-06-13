#!/usr/bin/env python3
"""
Exporta chat_interacoes → JSONL no formato Vertex AI SFT (Gemini tuning).

Seleção:
  - feedback = 1            → resposta usada como alvo (exemplo bom)
  - correcao IS NOT NULL    → correção usada como alvo (ouro — sobrepõe resposta)
  - feedback = -1 sem correcao é DESCARTADO (sabemos que é ruim, não sabemos o certo)

Formato (Vertex supervised tuning, gemini):
  {"systemInstruction": {"parts": [{"text": ...}]},
   "contents": [{"role": "user", "parts": [{"text": pergunta}]},
                {"role": "model", "parts": [{"text": alvo}]}]}

Uso:
  python scripts/batch/export_ft_dataset.py --out metrics/ft_dataset.jsonl [--min-exemplos 100]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

_SYSTEM = (
    "Você é o GymSite Assistant, especialista em viabilidade e expansão de "
    "academias no Brasil. Responda em português, com objetividade, citando "
    "fonte e ano dos dados quando disponíveis. Nunca dê recomendação de "
    "investimento financeiro."
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "metrics" / "ft_dataset.jsonl")
    p.add_argument("--min-exemplos", type=int, default=100,
                   help="aborta se houver menos exemplos que isso (dataset imaturo)")
    args = p.parse_args()

    from db.supabase_writer import _get_client

    client = _get_client()
    if client is None:
        print("ERRO: credenciais Supabase ausentes")
        return 1

    res = (
        client.table("chat_interacoes")
        .select("pergunta, resposta, correcao, feedback")
        .or_("feedback.eq.1,correcao.not.is.null")
        .order("created_at")
        .execute()
    )
    rows = res.data or []

    exemplos = []
    for r in rows:
        alvo = (r.get("correcao") or "").strip() or (r.get("resposta") or "").strip()
        pergunta = (r.get("pergunta") or "").strip()
        if not pergunta or not alvo:
            continue
        exemplos.append({
            "systemInstruction": {"parts": [{"text": _SYSTEM}]},
            "contents": [
                {"role": "user", "parts": [{"text": pergunta}]},
                {"role": "model", "parts": [{"text": alvo}]},
            ],
        })

    print(f"exemplos elegíveis: {len(exemplos)} (minimo configurado: {args.min_exemplos})")
    if len(exemplos) < args.min_exemplos:
        print("dataset ainda imaturo — colete mais feedback antes de tunar. Nada exportado.")
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for ex in exemplos:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"exportado: {args.out}")
    print("próximo passo: upload pro GCS e job de tuning no Vertex (console ou gcloud).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
