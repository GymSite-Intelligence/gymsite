"""
Playbook Service — leitura e atualização do plano de abertura.

Regras de domínio (regra mestra do processo de mudança):
- Estado derivado calculado em RUNTIME (P2): dias_atraso, esta_atrasada,
  progresso. Os contadores cacheados em playbooks são atualizados na MESMA
  operação que muda tarefa (consistência, LT-005-style).
- Dependências validadas no backend (P-005): tarefa só CONCLUIDA quando todas
  as predecessoras TERMINA_PARA_COMECAR estiverem concluídas; o erro lista o
  que falta em linguagem do domínio.
- Custos em centavos (int). Soft delete em tudo (P-007). Auditoria de eventos
  importantes em auditoria_eventos (append-only).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("gymsite.playbook_service")

STATUS_TAREFA_VALIDOS = {"A_FAZER", "EM_ANDAMENTO", "CONCLUIDA", "BLOQUEADA", "CANCELADA"}


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dias_atraso(tarefa: dict[str, Any]) -> int:
    """Derivado em runtime — nunca armazenado (C-02 do doc V1)."""
    if tarefa.get("status") in ("CONCLUIDA", "CANCELADA"):
        return 0
    prevista = tarefa.get("data_prevista_conclusao")
    if not prevista:
        return 0
    try:
        alvo = date.fromisoformat(str(prevista)[:10])
    except ValueError:
        return 0
    atraso = (date.today() - alvo).days
    return max(atraso, 0)


def _enriquecer_tarefa(t: dict[str, Any]) -> dict[str, Any]:
    atraso = _dias_atraso(t)
    t["dias_atraso"] = atraso
    t["esta_atrasada"] = atraso > 0
    return t


def listar_playbooks(sb, user_id: str) -> list[dict[str, Any]]:
    res = (
        sb.table("playbooks")
        .select("id, projeto_id, relatorio_id, nome, status, data_inicio, "
                "data_prevista_conclusao, custo_planejado_total, custo_real_total, "
                "total_tarefas, tarefas_concluidas, created_at")
        .eq("user_id", user_id)
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def obter_playbook_completo(sb, playbook_id: str, user_id: str) -> Optional[dict[str, Any]]:
    pb = (
        sb.table("playbooks")
        .select("*")
        .eq("id", playbook_id)
        .eq("user_id", user_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not pb or not pb.data:
        return None

    tarefas = (
        sb.table("tarefas")
        .select("*")
        .eq("playbook_id", playbook_id)
        .is_("deleted_at", "null")
        .order("ordem")
        .execute()
    )
    lista = [_enriquecer_tarefa(t) for t in (tarefas.data or [])]
    ids = [t["id"] for t in lista]

    deps: list[dict[str, Any]] = []
    checklist: list[dict[str, Any]] = []
    if ids:
        deps = (
            sb.table("tarefa_dependencias")
            .select("tarefa_id, depende_de_tarefa_id, tipo")
            .in_("tarefa_id", ids)
            .execute()
        ).data or []
        checklist = (
            sb.table("tarefa_checklist")
            .select("id, tarefa_id, descricao, concluido, ordem")
            .in_("tarefa_id", ids)
            .is_("deleted_at", "null")
            .order("ordem")
            .execute()
        ).data or []

    por_tarefa: dict[str, list[dict[str, Any]]] = {}
    for item in checklist:
        por_tarefa.setdefault(item["tarefa_id"], []).append(item)
    for t in lista:
        t["checklist"] = por_tarefa.get(t["id"], [])

    out = dict(pb.data)
    concluidas = sum(1 for t in lista if t["status"] == "CONCLUIDA")
    contaveis = [t for t in lista if t["status"] != "CANCELADA"]
    out["tarefas"] = lista
    out["dependencias"] = deps
    out["total_tarefas"] = len(contaveis)
    out["tarefas_concluidas"] = concluidas
    out["percentual_concluido"] = round(concluidas / len(contaveis) * 100, 1) if contaveis else 0.0
    out["custo_real_total"] = sum(t.get("custo_real") or 0 for t in lista)
    out["tarefas_atrasadas"] = sum(1 for t in lista if t["esta_atrasada"])
    return out


def _predecessoras_pendentes(sb, tarefa_id: str) -> list[str]:
    """Títulos das predecessoras TERMINA_PARA_COMECAR ainda não concluídas."""
    deps = (
        sb.table("tarefa_dependencias")
        .select("depende_de_tarefa_id")
        .eq("tarefa_id", tarefa_id)
        .eq("tipo", "TERMINA_PARA_COMECAR")
        .execute()
    ).data or []
    ids = [d["depende_de_tarefa_id"] for d in deps]
    if not ids:
        return []
    preds = (
        sb.table("tarefas")
        .select("titulo, status")
        .in_("id", ids)
        .is_("deleted_at", "null")
        .execute()
    ).data or []
    return [p["titulo"] for p in preds if p["status"] not in ("CONCLUIDA", "CANCELADA")]


def _recalcular_contadores(sb, playbook_id: str) -> None:
    """Atualiza cache do playbook na mesma operação da mudança de tarefa."""
    tarefas = (
        sb.table("tarefas")
        .select("status, custo_real")
        .eq("playbook_id", playbook_id)
        .is_("deleted_at", "null")
        .execute()
    ).data or []
    contaveis = [t for t in tarefas if t["status"] != "CANCELADA"]
    concluidas = sum(1 for t in contaveis if t["status"] == "CONCLUIDA")
    custo_real = sum(t.get("custo_real") or 0 for t in tarefas)
    pct = round(concluidas / len(contaveis) * 100, 1) if contaveis else 0.0
    sb.table("playbooks").update({
        "total_tarefas": len(contaveis),
        "tarefas_concluidas": concluidas,
        "percentual_concluido": pct,
        "custo_real_total": custo_real or None,
        "updated_at": _agora_iso(),
    }).eq("id", playbook_id).execute()


def _tarefa_do_usuario(sb, tarefa_id: str, user_id: str) -> dict[str, Any]:
    t = (
        sb.table("tarefas")
        .select("*, playbooks!inner(user_id)")
        .eq("id", tarefa_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not t or not t.data or (t.data.get("playbooks") or {}).get("user_id") != user_id:
        raise LookupError("Tarefa não encontrada.")
    return t.data


def atualizar_status_tarefa(
    sb,
    tarefa_id: str,
    user_id: str,
    novo_status: str,
    *,
    custo_real: Optional[int] = None,
) -> dict[str, Any]:
    if novo_status not in STATUS_TAREFA_VALIDOS:
        raise ValueError("Situação inválida para a tarefa.")
    tarefa = _tarefa_do_usuario(sb, tarefa_id, user_id)

    if novo_status == "CONCLUIDA":
        pendentes = _predecessoras_pendentes(sb, tarefa_id)
        if pendentes:
            faltam = ", ".join(f"“{p}”" for p in pendentes[:3])
            raise ValueError(f"Antes de concluir esta etapa, falta terminar: {faltam}.")

    update: dict[str, Any] = {"status": novo_status, "updated_at": _agora_iso()}
    if novo_status == "CONCLUIDA":
        update["data_conclusao"] = date.today().isoformat()
        if custo_real is not None:
            update["custo_real"] = int(custo_real)
    elif custo_real is not None:
        update["custo_real"] = int(custo_real)

    res = sb.table("tarefas").update(update).eq("id", tarefa_id).execute()
    _recalcular_contadores(sb, tarefa["playbook_id"])

    if novo_status == "CONCLUIDA":
        try:
            sb.table("auditoria_eventos").insert({
                "user_id": user_id,
                "projeto_id": tarefa.get("projeto_id"),
                "entidade": "tarefa",
                "entidade_id": tarefa_id,
                "evento": "CONCLUIR_TAREFA",
                "snapshot_antes": {"status": tarefa.get("status"), "custo_real": tarefa.get("custo_real")},
                "snapshot_depois": {"status": novo_status, "custo_real": update.get("custo_real")},
            }).execute()
        except Exception:
            logger.warning("auditoria CONCLUIR_TAREFA falhou (não bloqueia)", exc_info=True)

    atualizada = _enriquecer_tarefa(res.data[0]) if res.data else None
    liberadas: list[str] = []
    if novo_status == "CONCLUIDA" and atualizada:
        dependentes = (
            sb.table("tarefa_dependencias")
            .select("tarefa_id")
            .eq("depende_de_tarefa_id", tarefa_id)
            .eq("tipo", "TERMINA_PARA_COMECAR")
            .execute()
        ).data or []
        for dep in dependentes:
            if not _predecessoras_pendentes(sb, dep["tarefa_id"]):
                liberadas.append(dep["tarefa_id"])
    return {"tarefa": atualizada, "tarefas_liberadas": liberadas}


def marcar_checklist_item(sb, item_id: str, user_id: str, concluido: bool) -> dict[str, Any]:
    item = (
        sb.table("tarefa_checklist")
        .select("id, tarefa_id")
        .eq("id", item_id)
        .maybe_single()
        .execute()
    )
    if not item or not item.data:
        raise LookupError("Item não encontrado.")
    _tarefa_do_usuario(sb, item.data["tarefa_id"], user_id)
    res = (
        sb.table("tarefa_checklist")
        .update({"concluido": bool(concluido)})
        .eq("id", item_id)
        .execute()
    )
    return res.data[0] if res.data else {}
