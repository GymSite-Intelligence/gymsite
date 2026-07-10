#!/usr/bin/env python3
"""
Auditoria de fidelidade de relatório — gate para alimentar o RAG de mercado.

Determina se um relatório gerado é "bem-sucedido e fidedigno o bastante" (>= 80%)
para virar conhecimento. NÃO inventa score: compõe sinais que o pipeline JÁ produz.

Fontes (todas por relatorio_id):
  - relatorios.status            → só 'done' passa (queued/running/failed/cancelled reprovam)
  - validacoes (saída do A8)     → score_validacao (0-1), status_validacao, revisar_manual,
                                    alertas[] (severidade CRITICO/ALTA/...)
  - relatorio_outputs            → output_consolidado (JSON canônico): nº concorrentes,
                                    3 cenários financeiros, score demográfico, cobertura A0

Uso:
  python scripts/audit_relatorio_fidelidade.py --relatorio-id <uuid>
  python scripts/audit_relatorio_fidelidade.py --scan --limit 50
  python scripts/audit_relatorio_fidelidade.py --scan --so-elegiveis

Saída: JSON por relatório com {relatorio_id, fidelidade, elegivel, gate, motivos}.
NÃO faz upload — decide. O upload ao bucket é etapa separada (fase 2).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.cnpj_fitness_tools import _supabase_client

# ─── Parâmetros do gate (ajustáveis) ─────────────────────────────────────────
LIMIAR_FIDELIDADE = 0.80          # >= 80% = elegível
CONCORRENTES_META = 8             # nº de concorrentes p/ cobertura competitiva plena
PESOS = {
    "a8": 0.55,                   # score do A8 validator (já cruza coerência veredito×dado)
    "concorrentes": 0.20,         # cobertura competitiva real
    "financeiro": 0.15,           # aluguel determinístico (MRLR) vs fallback
    "demografia": 0.10,           # score demográfico real (>0)
}
# status_validacao que reprova (match por substring — cobre REPROVADO_VALIDACAO etc.)
STATUS_VALIDACAO_REPROVA = ("reprovad", "erro", "falh", "invalid")
# fonte de aluguel considerada determinística (Tier 0 MRLR). Portais/OLX/ZAP = fallback.
ALUGUEL_DETERMINISTICO = ("mrlr",)
# score do financeiro quando o aluguel é fallback (portais) e não MRLR. MRLR indisponível
# é COMUM (~68% dos relatórios) e não torna o FATO DE MERCADO ruim — só o financeiro menos
# preciso. Penalidade moderada, não punitiva.
ALUGUEL_FALLBACK_SCORE = 0.6
# veredito de baixa confiança = dado insuficiente → não vira base de conhecimento.
VEREDITO_BAIXA_CONFIANCA = {"", "indeterminado", "investigar", "investigar mais"}


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def auditar(rel: dict, inp: dict | None, val: dict | None, out: dict | None) -> dict:
    """Computa fidelidade + decisão de um relatório. Puro (sem I/O).
    Campos vêm das colunas top-level de relatorio_outputs (NÃO de output_consolidado)."""
    rid = rel.get("id")
    status = (rel.get("status") or "").lower()
    inp = inp or {}
    val = val or {}
    out = out or {}
    motivos: list[str] = []

    # ── Gates duros (qualquer um reprova, fidelidade nem importa) ──
    gate_status = status == "done" and not (rel.get("erro_mensagem") or "").strip()
    if not gate_status:
        motivos.append(f"status='{status}'" + (" +erro" if rel.get("erro_mensagem") else "")
                       + " (só 'done' sem erro passa)")

    revisar_manual = bool(val.get("revisar_manual"))
    alertas = val.get("alertas") or []
    tem_critico = revisar_manual or any(
        str((a or {}).get("severidade", "")).upper() == "CRITICO" for a in alertas
    )
    if tem_critico:
        motivos.append("A8 marcou inconsistência CRÍTICA (revisar_manual)")

    status_val = (val.get("status_validacao") or "").lower()
    gate_validacao = not any(bad in status_val for bad in STATUS_VALIDACAO_REPROVA)
    if not gate_validacao:
        motivos.append(f"status_validacao='{status_val}' reprova")

    # ── Veredito: INDETERMINADO/vazio = dado insuficiente → gate duro ──
    veredito = (out.get("veredito") or "").strip().lower()
    gate_veredito = veredito not in VEREDITO_BAIXA_CONFIANCA
    if not gate_veredito:
        motivos.append(f"veredito='{veredito or 'None'}' = baixa confiança (dado insuficiente)")

    # ── Score A8 (0-1). Ausente = não assume: trata como 0 (reprova). ──
    a8 = val.get("score_validacao")
    if a8 is None:
        motivos.append("sem score_validacao do A8 (não assumir — reprova)")
        s_a8 = 0.0
    else:
        s_a8 = max(0.0, min(1.0, _num(a8)))

    # ── Cobertura competitiva (coluna top-level) ──
    n_conc = _num(out.get("total_concorrentes_analisados"))
    s_conc = min(1.0, n_conc / CONCORRENTES_META) if CONCORRENTES_META else 0.0
    if n_conc < CONCORRENTES_META:
        motivos.append(f"cobertura competitiva parcial ({int(n_conc)}/{CONCORRENTES_META})")

    # ── Financeiro: aluguel determinístico (MRLR) vale 1.0; fallback (portais) = 0.4 ──
    fonte_aluguel = (out.get("fonte_aluguel") or "").lower()
    aluguel_det = any(fonte_aluguel.startswith(p) for p in ALUGUEL_DETERMINISTICO)
    tem_aluguel = out.get("aluguel_mensal") is not None
    if not tem_aluguel:
        s_fin = 0.0
        motivos.append("sem aluguel_mensal")
    elif aluguel_det:
        s_fin = 1.0
    else:
        s_fin = ALUGUEL_FALLBACK_SCORE
        motivos.append(f"aluguel NÃO-determinístico (fonte: {out.get('fonte_aluguel')}) — MRLR indisponível")

    # ── Demografia real (coluna top-level) ──
    s_demo = 1.0 if _num(out.get("score_demografico")) > 0 else 0.0
    if s_demo == 0.0:
        motivos.append("score demográfico ausente/zero")

    # ── Fidelidade composta ──
    fidelidade = round(
        PESOS["a8"] * s_a8
        + PESOS["concorrentes"] * s_conc
        + PESOS["financeiro"] * s_fin
        + PESOS["demografia"] * s_demo,
        4,
    )

    elegivel = (
        gate_status
        and gate_validacao
        and gate_veredito
        and not tem_critico
        and fidelidade >= LIMIAR_FIDELIDADE
    )
    if elegivel:
        motivos = ["ok"]
    elif fidelidade < LIMIAR_FIDELIDADE and gate_status and gate_validacao \
            and gate_veredito and not tem_critico:
        motivos.append(f"fidelidade {fidelidade:.0%} < {LIMIAR_FIDELIDADE:.0%}")

    return {
        "relatorio_id": rid,
        "cidade": inp.get("cidade"),
        "bairro": inp.get("bairro"),
        "status": status,
        "veredito": out.get("veredito"),
        "fidelidade": fidelidade,
        "elegivel": elegivel,
        "gate": {
            "status_done": gate_status,
            "sem_critico_a8": not tem_critico,
            "validacao_ok": gate_validacao,
            "veredito_confiavel": gate_veredito,
            "fidelidade_ok": fidelidade >= LIMIAR_FIDELIDADE,
        },
        "breakdown": {"a8": s_a8, "concorrentes": s_conc, "financeiro": s_fin, "demografia": s_demo},
        "motivos": motivos,
    }


def _carregar(sb, rid: str) -> tuple[dict | None, dict | None, dict | None, dict | None]:
    rel = sb.table("relatorios").select("id,status,erro_mensagem").eq("id", rid) \
        .is_("deleted_at", "null").maybe_single().execute().data
    inp = sb.table("relatorio_inputs").select("cidade,bairro,uf,tipo_negocio") \
        .eq("relatorio_id", rid).maybe_single().execute().data
    val = (sb.table("validacoes").select("*").eq("relatorio_id", rid)
           .order("created_at", desc=True).limit(1).execute().data or [None])[0]
    out = sb.table("relatorio_outputs").select("*").eq("relatorio_id", rid) \
        .maybe_single().execute().data
    return rel, inp, val, out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Auditoria de fidelidade de relatório (gate RAG)")
    ap.add_argument("--relatorio-id", help="Audita um relatório específico")
    ap.add_argument("--scan", action="store_true", help="Varre relatórios 'done'")
    ap.add_argument("--limit", type=int, default=50, help="Máx. de relatórios no scan")
    ap.add_argument("--so-elegiveis", action="store_true", help="No scan, imprime só os elegíveis")
    args = ap.parse_args(argv)

    sb = _supabase_client()
    if sb is None:
        print(json.dumps({"erro": "SUPABASE não configurado"}), file=sys.stderr)
        return 1

    resultados: list[dict] = []
    if args.relatorio_id:
        rel, inp, val, out = _carregar(sb, args.relatorio_id)
        if not rel:
            print(json.dumps({"erro": "relatório não encontrado"})); return 1
        resultados.append(auditar(rel, inp, val, out))
    elif args.scan:
        rows = sb.table("relatorios").select("id").eq("status", "done") \
            .is_("deleted_at", "null").order("created_at", desc=True) \
            .limit(args.limit).execute().data or []
        for row in rows:
            rel, inp, val, out = _carregar(sb, row["id"])
            if rel:
                resultados.append(auditar(rel, inp, val, out))
    else:
        ap.error("informe --relatorio-id <uuid> ou --scan")

    if args.so_elegiveis:
        resultados = [r for r in resultados if r["elegivel"]]

    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    n_el = sum(1 for r in resultados if r["elegivel"])
    print(f"\n[resumo] {n_el}/{len(resultados)} elegíveis (fidelidade >= {LIMIAR_FIDELIDADE:.0%})",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
