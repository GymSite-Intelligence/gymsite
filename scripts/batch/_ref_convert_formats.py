#!/usr/bin/env python3
"""
02_convert_formats.py
─────────────────────
Converte o seed dataset (formato interno) para múltiplos formatos de 
treinamento suportados por diferentes plataformas:

  • Vertex AI (Gemini)     — supervised fine-tuning JSONL
  • OpenAI                 — chat completions fine-tuning JSONL
  • Anthropic (Claude)     — messages JSONL
  • Ollama / Llama.cpp     — Alpaca / ShareGPT JSON
  • HuggingFace datasets   — Parquet / CSV

Uso:
  python scripts/02_convert_formats.py --in data/seed_dataset.jsonl \
                                       --out-dir data/formats/
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


def load_seed_dataset(path: Path) -> list[dict]:
    """Carrega o dataset seed (JSONL)."""
    exemplos = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                exemplos.append(json.loads(line))
    print(f"📥 Carregados {len(exemplos)} exemplos do seed dataset")
    return exemplos


# ═══════════════════════════════════════════════════════════════════════════
# FORMATO 1: Vertex AI (Gemini) — Supervised Fine-Tuning
# ═══════════════════════════════════════════════════════════════════════════
def to_vertex_ai(exemplos: list[dict]) -> list[dict]:
    """
    Formato Vertex AI SFT (Gemini):
    {
      "systemInstruction": {"parts": [{"text": "..."}]},
      "contents": [
        {"role": "user", "parts": [{"text": "pergunta"}]},
        {"role": "model", "parts": [{"text": "resposta"}]}
      ]
    }
    """
    convertidos = []
    for ex in exemplos:
        convertidos.append({
            "systemInstruction": {
                "parts": [{"text": ex["system"]}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": ex["instruction"]}]},
                {"role": "model", "parts": [{"text": ex["response"]}]},
            ],
        })
    return convertidos


# ═══════════════════════════════════════════════════════════════════════════
# FORMATO 2: OpenAI — Chat Completions Fine-Tuning
# ═══════════════════════════════════════════════════════════════════════════
def to_openai(exemplos: list[dict]) -> list[dict]:
    """
    Formato OpenAI fine-tuning (gpt-3.5-turbo, gpt-4):
    {
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "pergunta"},
        {"role": "assistant", "content": "resposta"}
      ]
    }
    """
    convertidos = []
    for ex in exemplos:
        messages = [
            {"role": "system", "content": ex["system"]},
            {"role": "user", "content": ex["instruction"]},
            {"role": "assistant", "content": ex["response"]},
        ]
        convertidos.append({"messages": messages})
    return convertidos


# ═══════════════════════════════════════════════════════════════════════════
# FORMATO 3: Anthropic (Claude) — Messages
# ═══════════════════════════════════════════════════════════════════════════
def to_claude(exemplos: list[dict]) -> list[dict]:
    """
    Formato Anthropic Claude fine-tuning:
    {
      "system": "...",
      "messages": [
        {"role": "user", "content": "pergunta"},
        {"role": "assistant", "content": "resposta"}
      ]
    }
    
    Nota: O campo 'system' no nível raiz é suportado pelo Claude 3+
    """
    convertidos = []
    for ex in exemplos:
        convertidos.append({
            "system": ex["system"],
            "messages": [
                {"role": "user", "content": ex["instruction"]},
                {"role": "assistant", "content": ex["response"]},
            ],
        })
    return convertidos


# ═══════════════════════════════════════════════════════════════════════════
# FORMATO 4: Ollama / Llama.cpp — Alpaca
# ═══════════════════════════════════════════════════════════════════════════
def to_alpaca(exemplos: list[dict]) -> list[dict]:
    """
    Formato Alpaca (instrução → resposta):
    {
      "instruction": "pergunta",
      "input": "",
      "output": "resposta",
      "system": "..."
    }
    """
    convertidos = []
    for ex in exemplos:
        convertidos.append({
            "instruction": ex["instruction"],
            "input": "",
            "output": ex["response"],
            "system": ex["system"],
        })
    return convertidos


# ═══════════════════════════════════════════════════════════════════════════
# FORMATO 5: ShareGPT (conversação)
# ═══════════════════════════════════════════════════════════════════════════
def to_sharegpt(exemplos: list[dict]) -> list[dict]:
    """
    Formato ShareGPT (usado por muitos modelos open source):
    {
      "conversations": [
        {"from": "system", "value": "..."},
        {"from": "human", "value": "pergunta"},
        {"from": "gpt", "value": "resposta"}
      ]
    }
    """
    convertidos = []
    for ex in exemplos:
        convertidos.append({
            "conversations": [
                {"from": "system", "value": ex["system"]},
                {"from": "human", "value": ex["instruction"]},
                {"from": "gpt", "value": ex["response"]},
            ]
        })
    return convertidos


# ═══════════════════════════════════════════════════════════════════════════
# FORMATO 6: CSV (para análise e RAG)
# ═══════════════════════════════════════════════════════════════════════════
def to_csv(exemplos: list[dict], path: Path) -> None:
    """Exporta para CSV com colunas: system, instruction, response, metadata."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["system", "instruction", "response", "metadata"])
        for ex in exemplos:
            writer.writerow([
                ex["system"],
                ex["instruction"],
                ex["response"],
                json.dumps(ex.get("metadata", {}), ensure_ascii=False),
            ])


# ═══════════════════════════════════════════════════════════════════════════
# FORMATO 7: JSON consolidado (array único)
# ═══════════════════════════════════════════════════════════════════════════
def to_json_array(exemplos: list[dict]) -> list[dict]:
    """Retorna o formato interno como array JSON."""
    return exemplos


# ── Registry de formatos ─────────────────────────────────────────────────

FORMATS: dict[str, Callable] = {
    "vertex_ai": to_vertex_ai,
    "openai": to_openai,
    "claude": to_claude,
    "alpaca": to_alpaca,
    "sharegpt": to_sharegpt,
    "json_array": to_json_array,
}


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Converte seed dataset para múltiplos formatos")
    p.add_argument("--in", dest="input", type=Path,
                   default=ROOT / "data" / "seed_dataset.jsonl",
                   help="Arquivo seed dataset (JSONL)")
    p.add_argument("--out-dir", type=Path,
                   default=ROOT / "data" / "formats",
                   help="Diretório de saída")
    p.add_argument("--formats", nargs="+", choices=list(FORMATS.keys()) + ["all", "csv"],
                   default=["all"],
                   help="Formatos a gerar (default: all)")
    args = p.parse_args()

    # Carrega seed
    if not args.input.exists():
        print(f"❌ Arquivo não encontrado: {args.input}")
        print("   Execute primeiro: python scripts/01_generate_seed_dataset.py")
        return 1

    exemplos = load_seed_dataset(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    formats_to_generate = list(FORMATS.keys()) + ["csv"] if "all" in args.formats else args.formats

    print(f"\n🔄 Convertendo para {len(formats_to_generate)} formato(s)...\n")

    for fmt_name in formats_to_generate:
        if fmt_name == "csv":
            out_path = args.out_dir / "dataset.csv"
            to_csv(exemplos, out_path)
            print(f"   ✅ CSV         → {out_path}")
            continue

        converter = FORMATS[fmt_name]
        convertidos = converter(exemplos)

        if fmt_name == "json_array":
            out_path = args.out_dir / "dataset.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(convertidos, f, ensure_ascii=False, indent=2)
        else:
            out_path = args.out_dir / f"dataset_{fmt_name}.jsonl"
            with out_path.open("w", encoding="utf-8") as f:
                for ex in convertidos:
                    f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        print(f"   ✅ {fmt_name:<12} → {out_path} ({len(convertidos)} exemplos)")

    print(f"\n📁 Todos os formatos salvos em: {args.out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
