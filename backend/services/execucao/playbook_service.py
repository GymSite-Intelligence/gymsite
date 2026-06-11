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


def _variacao_conclusao_dias(tarefa: dict[str, Any]) -> Optional[int]:
    """Concluída: dias entre previsto e real. Positivo = terminou atrasada,
    negativo = adiantada. None quando não concluída ou sem datas."""
    if tarefa.get("status") != "CONCLUIDA":
        return None
    prevista = tarefa.get("data_prevista_conclusao")
    real = tarefa.get("data_conclusao")
    if not prevista or not real:
        return None
    try:
        return (date.fromisoformat(str(real)[:10]) - date.fromisoformat(str(prevista)[:10])).days
    except ValueError:
        return None


def _enriquecer_tarefa(t: dict[str, Any]) -> dict[str, Any]:
    atraso = _dias_atraso(t)
    t["dias_atraso"] = atraso
    t["esta_atrasada"] = atraso > 0
    t["variacao_conclusao_dias"] = _variacao_conclusao_dias(t)
    return t


def listar_playbooks(sb, user_id: str) -> list[dict[str, Any]]:
    res = (
        sb.table("playbooks")
        .select("id, projeto_id, relatorio_id, nome, status, data_inicio, "
                "data_prevista_conclusao, custo_planejado_total, custo_real_total, "
                "total_tarefas, tarefas_concluidas, percentual_concluido, created_at, "
                "user_projects(nome)")
        .eq("user_id", user_id)
        .neq("status", "ARQUIVADO")
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )
    itens = res.data or []
    for p in itens:
        projeto = p.pop("user_projects", None) or {}
        p["projeto_nome"] = projeto.get("nome")
    return itens


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
            .select("id, tarefa_id, descricao, concluido, ordem, responsavel_pessoa_id")
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

    pessoas = (
        sb.table("projeto_pessoas")
        .select("id, nome, papel, email, telefone")
        .eq("projeto_id", pb.data["projeto_id"])
        .is_("deleted_at", "null")
        .order("nome")
        .execute()
    ).data or []

    okrs = (
        sb.table("okrs")
        .select("id, objetivo, descricao, status, "
                "kr1_descricao, kr1_target, kr1_atual, "
                "kr2_descricao, kr2_target, kr2_atual, "
                "kr3_descricao, kr3_target, kr3_atual")
        .eq("playbook_id", playbook_id)
        .is_("deleted_at", "null")
        .neq("status", "ARQUIVADO")
        .order("created_at")
        .execute()
    ).data or []

    # KRs espelho do plano: derivados em runtime (C-02), não digitados.
    # Casados pela descrição semeada pelo gerador.
    concluidas_runtime = sum(1 for t in lista if t["status"] == "CONCLUIDA")
    gasto_total_reais = sum(t.get("custo_real") or 0 for t in lista) / 100
    KR_AUTO = {
        "Etapas do plano concluídas": float(concluidas_runtime),
        "Investimento total (R$, máximo)": round(gasto_total_reais, 2),
    }
    for okr in okrs:
        for i in (1, 2, 3):
            desc = okr.get(f"kr{i}_descricao")
            if desc in KR_AUTO:
                okr[f"kr{i}_atual"] = KR_AUTO[desc]
                okr[f"kr{i}_auto"] = True

    out = dict(pb.data)
    concluidas = sum(1 for t in lista if t["status"] == "CONCLUIDA")
    contaveis = [t for t in lista if t["status"] != "CANCELADA"]
    out["pessoas"] = pessoas
    out["okrs"] = okrs
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


def _projeto_do_usuario(sb, projeto_id: str, user_id: str) -> dict[str, Any]:
    p = (
        sb.table("user_projects")
        .select("id, user_id")
        .eq("id", projeto_id)
        .maybe_single()
        .execute()
    )
    if not p or not p.data or p.data.get("user_id") != user_id:
        raise LookupError("Projeto não encontrado.")
    return p.data


def listar_pessoas(sb, projeto_id: str, user_id: str) -> list[dict[str, Any]]:
    _projeto_do_usuario(sb, projeto_id, user_id)
    res = (
        sb.table("projeto_pessoas")
        .select("id, nome, papel, email, telefone")
        .eq("projeto_id", projeto_id)
        .is_("deleted_at", "null")
        .order("nome")
        .execute()
    )
    return res.data or []


def criar_pessoa(
    sb, projeto_id: str, user_id: str, *, nome: str,
    papel: Optional[str] = None, email: Optional[str] = None, telefone: Optional[str] = None,
) -> dict[str, Any]:
    if not nome or not nome.strip():
        raise ValueError("Informe o nome da pessoa.")
    _projeto_do_usuario(sb, projeto_id, user_id)
    res = sb.table("projeto_pessoas").insert({
        "projeto_id": projeto_id,
        "nome": nome.strip(),
        "papel": (papel or "").strip() or None,
        "email": (email or "").strip() or None,
        "telefone": (telefone or "").strip() or None,
    }).execute()
    return res.data[0] if res.data else {}


def _pessoa_do_usuario(sb, pessoa_id: str, user_id: str) -> dict[str, Any]:
    p = (
        sb.table("projeto_pessoas")
        .select("*, user_projects!inner(user_id)")
        .eq("id", pessoa_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not p or not p.data or (p.data.get("user_projects") or {}).get("user_id") != user_id:
        raise LookupError("Pessoa não encontrada.")
    return p.data


def atualizar_pessoa(sb, pessoa_id: str, user_id: str, campos: dict[str, Any]) -> dict[str, Any]:
    _pessoa_do_usuario(sb, pessoa_id, user_id)
    update = {
        k: (str(v).strip() or None if v is not None else None)
        for k, v in campos.items()
        if k in ("nome", "papel", "email", "telefone")
    }
    if "nome" in update and not update["nome"]:
        raise ValueError("O nome da pessoa não pode ficar vazio.")
    if not update:
        raise ValueError("Nada para atualizar.")
    res = sb.table("projeto_pessoas").update(update).eq("id", pessoa_id).execute()
    return res.data[0] if res.data else {}


def remover_pessoa(sb, pessoa_id: str, user_id: str) -> None:
    _pessoa_do_usuario(sb, pessoa_id, user_id)
    sb.table("projeto_pessoas").update({"deleted_at": _agora_iso()}).eq("id", pessoa_id).execute()
    sb.table("tarefas").update({"responsavel_pessoa_id": None}).eq("responsavel_pessoa_id", pessoa_id).execute()
    sb.table("tarefa_checklist").update({"responsavel_pessoa_id": None}).eq("responsavel_pessoa_id", pessoa_id).execute()


CATEGORIAS_VALIDAS = {
    "IMOBILIARIO", "LEGAL", "OBRAS", "EQUIPAMENTOS", "TECNOLOGIA",
    "RH", "MARKETING", "FINANCEIRO", "OPERACIONAL", "OUTRO",
}


def _playbook_do_usuario(sb, playbook_id: str, user_id: str) -> dict[str, Any]:
    pb = (
        sb.table("playbooks")
        .select("id, projeto_id, user_id")
        .eq("id", playbook_id)
        .eq("user_id", user_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not pb or not pb.data:
        raise LookupError("Plano não encontrado.")
    return pb.data


def criar_tarefa(sb, playbook_id: str, user_id: str, campos: dict[str, Any]) -> dict[str, Any]:
    pb = _playbook_do_usuario(sb, playbook_id, user_id)
    titulo = (campos.get("titulo") or "").strip()
    if not titulo:
        raise ValueError("Dê um nome para a etapa.")
    categoria = campos.get("categoria") or "OUTRO"
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValueError("Área inválida para a etapa.")

    ultima = (
        sb.table("tarefas")
        .select("ordem")
        .eq("playbook_id", playbook_id)
        .order("ordem", desc=True)
        .limit(1)
        .execute()
    )
    ordem = ((ultima.data[0]["ordem"] if ultima.data else 0) or 0) + 10

    row = {
        "playbook_id": playbook_id,
        "projeto_id": pb["projeto_id"],
        "titulo": titulo,
        "descricao": (campos.get("descricao") or "").strip() or None,
        "categoria": categoria,
        "status": "A_FAZER",
        "ordem": ordem,
        "custo_planejado": int(campos["custo_planejado"]) if campos.get("custo_planejado") is not None else None,
        "data_inicio": campos.get("data_inicio"),
        "data_prevista_conclusao": campos.get("data_prevista_conclusao"),
        "responsavel_nome": (campos.get("responsavel_nome") or "").strip() or None,
        "sugerida_pela_ia": False,
        "aceita_pelo_usuario": True,
    }
    res = sb.table("tarefas").insert(row).execute()
    _recalcular_contadores(sb, playbook_id)
    try:
        sb.table("auditoria_eventos").insert({
            "user_id": user_id,
            "projeto_id": pb["projeto_id"],
            "entidade": "tarefa",
            "entidade_id": res.data[0]["id"] if res.data else None,
            "evento": "CRIAR_TAREFA",
            "snapshot_depois": {"titulo": titulo, "categoria": categoria},
        }).execute()
    except Exception:
        logger.warning("auditoria CRIAR_TAREFA falhou (não bloqueia)", exc_info=True)
    return _enriquecer_tarefa(res.data[0]) if res.data else {}


def editar_tarefa(sb, tarefa_id: str, user_id: str, campos: dict[str, Any]) -> dict[str, Any]:
    tarefa = _tarefa_do_usuario(sb, tarefa_id, user_id)
    permitidos = {
        "titulo", "descricao", "categoria", "custo_planejado",
        "data_inicio", "data_prevista_conclusao", "responsavel_nome",
    }
    update: dict[str, Any] = {}
    for k, v in campos.items():
        if k not in permitidos:
            continue
        if k == "titulo":
            if not (v or "").strip():
                raise ValueError("O nome da etapa não pode ficar vazio.")
            update[k] = v.strip()
        elif k == "categoria":
            if v not in CATEGORIAS_VALIDAS:
                raise ValueError("Área inválida para a etapa.")
            update[k] = v
        elif k == "custo_planejado":
            update[k] = int(v) if v is not None else None
        elif k in ("descricao", "responsavel_nome"):
            update[k] = (v or "").strip() or None
        else:
            update[k] = v
    if not update:
        raise ValueError("Nada para atualizar.")
    update["updated_at"] = _agora_iso()
    res = sb.table("tarefas").update(update).eq("id", tarefa["id"]).execute()
    _recalcular_contadores(sb, tarefa["playbook_id"])
    try:
        sb.table("auditoria_eventos").insert({
            "user_id": user_id,
            "projeto_id": tarefa.get("projeto_id"),
            "entidade": "tarefa",
            "entidade_id": tarefa_id,
            "evento": "EDITAR_TAREFA",
            "snapshot_antes": {k: tarefa.get(k) for k in update if k != "updated_at"},
            "snapshot_depois": {k: v for k, v in update.items() if k != "updated_at"},
        }).execute()
    except Exception:
        logger.warning("auditoria EDITAR_TAREFA falhou (não bloqueia)", exc_info=True)
    return _enriquecer_tarefa(res.data[0]) if res.data else {}


def excluir_tarefa(sb, tarefa_id: str, user_id: str) -> None:
    """Soft delete (P-007). Dependências de quem dependia dela deixam de
    travar a conclusão: _predecessoras_pendentes só olha tarefas vivas."""
    tarefa = _tarefa_do_usuario(sb, tarefa_id, user_id)
    sb.table("tarefas").update({"deleted_at": _agora_iso()}).eq("id", tarefa["id"]).execute()
    _recalcular_contadores(sb, tarefa["playbook_id"])
    try:
        sb.table("auditoria_eventos").insert({
            "user_id": user_id,
            "projeto_id": tarefa.get("projeto_id"),
            "entidade": "tarefa",
            "entidade_id": tarefa_id,
            "evento": "EXCLUIR_TAREFA",
            "snapshot_antes": {"titulo": tarefa.get("titulo"), "status": tarefa.get("status")},
        }).execute()
    except Exception:
        logger.warning("auditoria EXCLUIR_TAREFA falhou (não bloqueia)", exc_info=True)


def adicionar_checklist_item(sb, tarefa_id: str, user_id: str, descricao: str) -> dict[str, Any]:
    if not descricao or not descricao.strip():
        raise ValueError("Escreva o passo antes de adicionar.")
    _tarefa_do_usuario(sb, tarefa_id, user_id)
    ultimo = (
        sb.table("tarefa_checklist")
        .select("ordem")
        .eq("tarefa_id", tarefa_id)
        .order("ordem", desc=True)
        .limit(1)
        .execute()
    )
    ordem = ((ultimo.data[0]["ordem"] if ultimo.data else 0) or 0) + 1
    res = sb.table("tarefa_checklist").insert({
        "tarefa_id": tarefa_id,
        "descricao": descricao.strip(),
        "ordem": ordem,
    }).execute()
    return res.data[0] if res.data else {}


def excluir_checklist_item(sb, item_id: str, user_id: str) -> None:
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
    sb.table("tarefa_checklist").update({"deleted_at": _agora_iso()}).eq("id", item_id).execute()


def criar_okr(sb, playbook_id: str, user_id: str, campos: dict[str, Any]) -> dict[str, Any]:
    pb = _playbook_do_usuario(sb, playbook_id, user_id)
    objetivo = (campos.get("objetivo") or "").strip()
    if not objetivo:
        raise ValueError("Dê um nome para a meta.")
    row: dict[str, Any] = {
        "playbook_id": playbook_id,
        "projeto_id": pb["projeto_id"],
        "objetivo": objetivo,
        "descricao": (campos.get("descricao") or "").strip() or None,
    }
    for i in (1, 2, 3):
        desc = (campos.get(f"kr{i}_descricao") or "").strip()
        target = campos.get(f"kr{i}_target")
        if desc and target is not None:
            row[f"kr{i}_descricao"] = desc
            row[f"kr{i}_target"] = float(target)
            row[f"kr{i}_atual"] = float(campos.get(f"kr{i}_atual") or 0)
    res = sb.table("okrs").insert(row).execute()
    try:
        sb.table("auditoria_eventos").insert({
            "user_id": user_id,
            "projeto_id": pb["projeto_id"],
            "entidade": "okr",
            "entidade_id": res.data[0]["id"] if res.data else None,
            "evento": "CRIAR_OKR",
            "snapshot_depois": {"objetivo": objetivo},
        }).execute()
    except Exception:
        logger.warning("auditoria CRIAR_OKR falhou (não bloqueia)", exc_info=True)
    return res.data[0] if res.data else {}


def excluir_okr(sb, okr_id: str, user_id: str) -> None:
    okr = (
        sb.table("okrs")
        .select("id, projeto_id, playbooks!inner(user_id)")
        .eq("id", okr_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not okr or not okr.data or (okr.data.get("playbooks") or {}).get("user_id") != user_id:
        raise LookupError("Meta não encontrada.")
    sb.table("okrs").update({"deleted_at": _agora_iso()}).eq("id", okr_id).execute()
    try:
        sb.table("auditoria_eventos").insert({
            "user_id": user_id,
            "projeto_id": okr.data.get("projeto_id"),
            "entidade": "okr",
            "entidade_id": okr_id,
            "evento": "EXCLUIR_OKR",
        }).execute()
    except Exception:
        logger.warning("auditoria EXCLUIR_OKR falhou (não bloqueia)", exc_info=True)


def registrar_custo_real(sb, tarefa_id: str, user_id: str, custo_real: int) -> dict[str, Any]:
    """Lança o gasto realizado da etapa em qualquer situação (sinal pago,
    parcela da obra) — não só na conclusão. Centavos, sempre."""
    if custo_real < 0:
        raise ValueError("O gasto não pode ser negativo.")
    tarefa = _tarefa_do_usuario(sb, tarefa_id, user_id)
    res = (
        sb.table("tarefas")
        .update({"custo_real": int(custo_real), "updated_at": _agora_iso()})
        .eq("id", tarefa["id"])
        .execute()
    )
    _recalcular_contadores(sb, tarefa["playbook_id"])
    try:
        sb.table("auditoria_eventos").insert({
            "user_id": user_id,
            "projeto_id": tarefa.get("projeto_id"),
            "entidade": "tarefa",
            "entidade_id": tarefa_id,
            "evento": "REGISTRAR_GASTO",
            "snapshot_antes": {"custo_real": tarefa.get("custo_real")},
            "snapshot_depois": {"custo_real": int(custo_real)},
        }).execute()
    except Exception:
        logger.warning("auditoria REGISTRAR_GASTO falhou (não bloqueia)", exc_info=True)
    return _enriquecer_tarefa(res.data[0]) if res.data else {}


def atribuir_responsavel_tarefa(
    sb, tarefa_id: str, user_id: str, pessoa_id: Optional[str]
) -> dict[str, Any]:
    tarefa = _tarefa_do_usuario(sb, tarefa_id, user_id)
    update: dict[str, Any] = {"responsavel_pessoa_id": pessoa_id, "updated_at": _agora_iso()}
    if pessoa_id:
        pessoa = _pessoa_do_usuario(sb, pessoa_id, user_id)
        update["responsavel_nome"] = pessoa["nome"]
    res = sb.table("tarefas").update(update).eq("id", tarefa["id"]).execute()
    return _enriquecer_tarefa(res.data[0]) if res.data else {}


def atribuir_responsavel_checklist(
    sb, item_id: str, user_id: str, pessoa_id: Optional[str]
) -> dict[str, Any]:
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
    if pessoa_id:
        _pessoa_do_usuario(sb, pessoa_id, user_id)
    res = (
        sb.table("tarefa_checklist")
        .update({"responsavel_pessoa_id": pessoa_id})
        .eq("id", item_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def listar_notas(sb, tarefa_id: str, user_id: str) -> list[dict[str, Any]]:
    _tarefa_do_usuario(sb, tarefa_id, user_id)
    res = (
        sb.table("tarefa_notas")
        .select("id, tarefa_id, autor_nome, origem, texto, criado_em")
        .eq("tarefa_id", tarefa_id)
        .is_("deleted_at", "null")
        .order("criado_em", desc=True)
        .execute()
    )
    return res.data or []


def adicionar_nota(
    sb, tarefa_id: str, user_id: str, texto: str, *, autor_nome: str, origem: str = "DONO"
) -> dict[str, Any]:
    if not texto or not texto.strip():
        raise ValueError("Escreva o que aconteceu antes de salvar a anotação.")
    if origem not in ("DONO", "EXTERNO", "IA"):
        raise ValueError("Origem inválida para a anotação.")
    _tarefa_do_usuario(sb, tarefa_id, user_id)
    res = sb.table("tarefa_notas").insert({
        "tarefa_id": tarefa_id,
        "autor_user_id": user_id,
        "autor_nome": autor_nome or "Você",
        "origem": origem,
        "texto": texto.strip(),
    }).execute()
    return res.data[0] if res.data else {}


def atualizar_okr(sb, okr_id: str, user_id: str, campos: dict[str, Any]) -> dict[str, Any]:
    okr = (
        sb.table("okrs")
        .select("id, playbook_id, playbooks!inner(user_id)")
        .eq("id", okr_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not okr or not okr.data or (okr.data.get("playbooks") or {}).get("user_id") != user_id:
        raise LookupError("Meta não encontrada.")

    numericos = {
        "kr1_atual", "kr2_atual", "kr3_atual",
        "kr1_target", "kr2_target", "kr3_target",
    }
    textos = {
        "objetivo", "descricao",
        "kr1_descricao", "kr2_descricao", "kr3_descricao",
    }
    update: dict[str, Any] = {}
    for k, v in campos.items():
        if k == "status":
            if v not in ("ATIVO", "CONCLUIDO", "ARQUIVADO"):
                raise ValueError("Situação inválida para a meta.")
            update[k] = v
        elif k in numericos:
            if v is None:
                update[k] = None
            else:
                try:
                    update[k] = float(v)
                except (TypeError, ValueError):
                    raise ValueError("Valor numérico inválido para a meta.")
        elif k in textos:
            if k == "objetivo" and not (v or "").strip():
                raise ValueError("O nome da meta não pode ficar vazio.")
            update[k] = (v or "").strip() or None
    if not update:
        raise ValueError("Nada para atualizar.")
    update["updated_at"] = _agora_iso()
    res = sb.table("okrs").update(update).eq("id", okr_id).execute()
    return res.data[0] if res.data else {}


BUCKET_ANEXOS = "execucao-anexos"


def listar_anexos(sb, tarefa_id: str, user_id: str) -> list[dict[str, Any]]:
    _tarefa_do_usuario(sb, tarefa_id, user_id)
    res = (
        sb.table("tarefa_anexos")
        .select("id, tarefa_id, nota_id, nome_arquivo, content_type, tamanho_bytes, criado_em")
        .eq("tarefa_id", tarefa_id)
        .is_("deleted_at", "null")
        .order("criado_em", desc=True)
        .execute()
    )
    return res.data or []


def registrar_anexo(
    sb, tarefa_id: str, user_id: str, *, nome_arquivo: str, storage_path: str,
    content_type: Optional[str], tamanho_bytes: int, nota_id: Optional[str] = None,
) -> dict[str, Any]:
    res = sb.table("tarefa_anexos").insert({
        "tarefa_id": tarefa_id,
        "nota_id": nota_id,
        "nome_arquivo": nome_arquivo,
        "storage_path": storage_path,
        "content_type": content_type,
        "tamanho_bytes": tamanho_bytes,
    }).execute()
    return res.data[0] if res.data else {}


def _anexo_do_usuario(sb, anexo_id: str, user_id: str) -> dict[str, Any]:
    a = (
        sb.table("tarefa_anexos")
        .select("*")
        .eq("id", anexo_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not a or not a.data:
        raise LookupError("Anexo não encontrado.")
    _tarefa_do_usuario(sb, a.data["tarefa_id"], user_id)
    return a.data


def url_download_anexo(sb, anexo_id: str, user_id: str, *, validade_s: int = 300) -> str:
    anexo = _anexo_do_usuario(sb, anexo_id, user_id)
    signed = sb.storage.from_(BUCKET_ANEXOS).create_signed_url(anexo["storage_path"], validade_s)
    url = (signed or {}).get("signedURL") or (signed or {}).get("signedUrl")
    if not url:
        raise ValueError("Não foi possível gerar o link do arquivo.")
    return url


def remover_anexo(sb, anexo_id: str, user_id: str) -> None:
    _anexo_do_usuario(sb, anexo_id, user_id)
    sb.table("tarefa_anexos").update({"deleted_at": _agora_iso()}).eq("id", anexo_id).execute()


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
