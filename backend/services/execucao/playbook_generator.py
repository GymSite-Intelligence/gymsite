"""
Playbook Generator — transforma Relatório de Viabilidade em plano de abertura.

Fase 1 (determinística, sem LLM): template por tipo de negócio + personalização
por regras a partir do relatório real (capex do cenário recomendado, candidato
top-1, alertas financeiros, gaps do posicionamento A9). Geração em < 5s e sem
risco de MALFORMED — enriquecimento por LLM entra como camada opcional depois.

Decisões:
- Cria o `user_project` container quando o relatório ainda não tem um — é o
  primeiro degrau da ponte sessions→UserProject (schema já em produção).
- Idempotente: relatório com playbook ATIVO retorna o existente; `force=True`
  arquiva o antigo e gera novo.
- Valores monetários SEMPRE em centavos (int). Relatório guarda reais → x100.
- Auditoria append-only: evento GERAR_PLAYBOOK em auditoria_eventos (P-007).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from backend.services.execucao.playbook_templates import (
    TarefaTemplate,
    get_template_por_tipo_negocio,
)
from backend.services.execucao.playbook_dependencias import (
    get_dependencias_por_tipo,
    ordenar_tarefas_por_dependencias,
)

logger = logging.getLogger("gymsite.playbook_generator")

TIPOS_VALIDOS = {"academia", "crossfit_box", "studio_pilates", "studio_funcional", "outro"}

# Distribuição do CAPEX do relatório (cenário recomendado) em tarefas-âncora.
# Percentuais da POLITICA_CUSTOS.md; aplica-se apenas quando o título existe
# no template do tipo de negócio — sobras ficam nos defaults do template.
_DISTRIBUICAO_CAPEX_DETALHADO = {
    # chave do capex_detalhado (schema v2) → [(titulo_tarefa, fração)]
    "equipamentos": [
        ("Comprar aparelhos de musculação", 0.60),
        ("Comprar equipamentos de cardio", 0.27),
        ("Comprar acessórios e halteres", 0.13),
    ],
    "obra_adaptacao": [("Executar obra civil", 1.0)],
    "projeto_arquitetonico": [("Contratar arquiteto e aprovar projeto", 1.0)],
    "alvara_e_taxas": [("Obter Alvará de Funcionamento", 1.0)],
}

# Fallback quando só existe capex_estimado total (schema v1)
_DISTRIBUICAO_CAPEX_TOTAL = [
    ("Comprar aparelhos de musculação", 0.28),
    ("Comprar equipamentos de cardio", 0.13),
    ("Comprar acessórios e halteres", 0.06),
    ("Executar obra civil", 0.27),
    ("Contratar arquiteto e aprovar projeto", 0.016),
    ("Obter Alvará de Funcionamento", 0.009),
]


def _reais_para_centavos(valor: Any) -> Optional[int]:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return int(round(v * 100))


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_contexto_relatorio(sb, relatorio_id: str) -> dict[str, Any]:
    """Carrega relatório + inputs + outputs + candidato top-1. Levanta ValueError
    com mensagem em linguagem do domínio quando algo impede a geração."""
    rel = (
        sb.table("relatorios")
        .select("id, user_id, org_id, status, deleted_at")
        .eq("id", relatorio_id)
        .maybe_single()
        .execute()
    )
    if not rel or not rel.data or rel.data.get("deleted_at"):
        raise ValueError("Relatório não encontrado.")
    if rel.data.get("status") != "done":
        raise ValueError("O relatório ainda não está pronto — gere o plano quando a análise terminar.")

    inputs = (
        sb.table("relatorio_inputs").select("*").eq("relatorio_id", relatorio_id).maybe_single().execute()
    )
    outputs = (
        sb.table("relatorio_outputs").select("*").eq("relatorio_id", relatorio_id).maybe_single().execute()
    )
    cenarios = (
        sb.table("cenarios_financeiros").select("*").eq("relatorio_id", relatorio_id).execute()
    )
    top1 = (
        sb.table("candidatos")
        .select("nome, endereco, area_estimada_m2, listing_url, price_raw")
        .eq("relatorio_id", relatorio_id)
        .order("posicao")
        .limit(1)
        .execute()
    )
    return {
        "relatorio": rel.data,
        "inputs": (inputs.data if inputs else None) or {},
        "outputs": (outputs.data if outputs else None) or {},
        "cenarios": (cenarios.data if cenarios else None) or [],
        "top1": (top1.data[0] if top1 and top1.data else None),
    }


def _garantir_user_project(sb, ctx: dict[str, Any]) -> str:
    """Retorna o user_project do relatório, criando o container se necessário."""
    relatorio = ctx["relatorio"]
    existente = (
        sb.table("user_projects")
        .select("id")
        .eq("relatorio_id", relatorio["id"])
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    if existente.data:
        return existente.data[0]["id"]

    inputs = ctx["inputs"]
    payload = {
        "user_id": relatorio["user_id"],
        "org_id": relatorio.get("org_id"),
        "status": "RELATORIO_GERADO",
        "nome": f"Abertura — {inputs.get('bairro') or ''}, {inputs.get('cidade') or ''}".strip(" —,"),
        "intencao_principal": "abrir_academia",
        "localizacao": {
            "cidade": inputs.get("cidade"),
            "uf": inputs.get("uf"),
            "bairro": inputs.get("bairro"),
        },
        "modelo_negocio": {
            "tipo_negocio": inputs.get("tipo_negocio") or "academia",
            "area_m2_min": inputs.get("area_m2_min"),
            "area_m2_max": inputs.get("area_m2_max"),
            "publico_alvo": inputs.get("publico_alvo"),
        },
        "relatorio_id": relatorio["id"],
    }
    res = sb.table("user_projects").insert(payload).execute()
    return res.data[0]["id"]


def _custos_personalizados(ctx: dict[str, Any]) -> dict[str, int]:
    """titulo → custo em centavos, derivado do cenário recomendado (CST-001).

    cenarios_financeiros é colunar: modelo ('Low Cost'|'Mid Market'|'Premium'),
    capex_equipamentos/obra_adaptacao/projeto_arquitetonico/alvara_e_taxas (v2)
    ou capex_estimado/capex_total (v1)."""
    outputs = ctx["outputs"]
    modelo_rec = (outputs.get("modelo_recomendado") or "").strip().lower()
    cenarios = ctx["cenarios"]
    alvo = None
    for c in cenarios:
        if str(c.get("modelo") or "").strip().lower() == modelo_rec:
            alvo = c
            break
    if alvo is None and cenarios:
        alvo = cenarios[0]
    if not alvo:
        return {}

    custos: dict[str, int] = {}
    capex_det = {
        "equipamentos": alvo.get("capex_equipamentos"),
        "obra_adaptacao": alvo.get("capex_obra_adaptacao"),
        "projeto_arquitetonico": alvo.get("capex_projeto_arquitetonico"),
        "alvara_e_taxas": alvo.get("capex_alvara_e_taxas"),
    }
    if any(_reais_para_centavos(v) for v in capex_det.values()):
        for chave_capex, distribuicao in _DISTRIBUICAO_CAPEX_DETALHADO.items():
            total = _reais_para_centavos(capex_det.get(chave_capex))
            if not total:
                continue
            for titulo, fracao in distribuicao:
                custos[titulo] = int(total * fracao)
        return custos

    capex_total = _reais_para_centavos(alvo.get("capex_total") or alvo.get("capex_estimado"))
    if capex_total:
        for titulo, fracao in _DISTRIBUICAO_CAPEX_TOTAL:
            custos[titulo] = int(capex_total * fracao)
    return custos


def _personalizar_descricao(t: TarefaTemplate, ctx: dict[str, Any]) -> tuple[str, Optional[str], Optional[str]]:
    """Retorna (descricao, origem_secao, origem_insight) com contexto do relatório."""
    outputs = ctx["outputs"]
    inputs = ctx["inputs"]
    top1 = ctx["top1"]
    descricao = t.descricao
    origem_secao = None
    origem_insight = None

    if t.titulo == "Buscar e avaliar pontos comerciais" and top1:
        local = top1.get("endereco") or top1.get("nome") or ""
        extra = f" Candidato apontado pela análise: {local}"
        if top1.get("price_raw"):
            extra += f" ({top1['price_raw']})"
        if top1.get("listing_url"):
            extra += f" — anúncio: {top1['listing_url']}"
        descricao = (descricao + "." if not descricao.endswith(".") else descricao) + extra
        origem_secao = "candidatos"
        origem_insight = f"Top 1 da análise: {local}"

    if t.categoria == "FINANCEIRO":
        alertas = outputs.get("alertas") or []
        if isinstance(alertas, list) and alertas:
            origem_secao = origem_secao or "financeiro"
            origem_insight = str(alertas[0])[:300]

    if t.titulo.startswith("Negociar e assinar contrato") and outputs.get("aluguel_mensal"):
        descricao += f" Aluguel de referência na análise: R$ {float(outputs['aluguel_mensal']):,.0f}/mês."
        origem_secao = origem_secao or "financeiro"

    if t.categoria == "MARKETING":
        bairro = inputs.get("bairro") or ""
        if bairro and "{bairro}" not in descricao:
            descricao += f" Foco geográfico: {bairro} e entorno."

    return descricao, origem_secao, origem_insight


def _tarefas_de_gaps(ctx: dict[str, Any], ordem_base: int) -> list[dict[str, Any]]:
    """Gaps do posicionamento A9 viram tarefas extras (marcadas como IA)."""
    pos = ctx["outputs"].get("posicionamento_estrategico") or {}
    gaps = pos.get("gaps_identificados") if isinstance(pos, dict) else None
    extras: list[dict[str, Any]] = []
    if not isinstance(gaps, list):
        return extras
    for i, gap in enumerate(gaps[:3]):
        if not isinstance(gap, dict):
            continue
        nome_gap = str(gap.get("gap") or "").strip()
        if not nome_gap:
            continue
        inicio = date.today()
        extras.append({
            "titulo": f"Preparar diferencial: {nome_gap}"[:200],
            "descricao": (str(gap.get("descricao") or "") +
                          (f" Potencial de mensalidade: {gap.get('potencial_ticket')}." if gap.get("potencial_ticket") else ""))[:1000],
            "categoria": "MARKETING",
            "prioridade": "ALTA",
            "ordem": ordem_base + i * 10,
            "custo_planejado": None,
            "data_inicio": inicio.isoformat(),
            "data_prevista_conclusao": (inicio + timedelta(days=14)).isoformat(),
            "responsavel_nome": "Empreendedor",
            "checklist": [],
            "sugerida_pela_ia": True,
            "origem_relatorio_secao": "posicionamento",
            "origem_relatorio_insight": nome_gap[:300],
        })
    return extras


def gerar_playbook_para_relatorio(
    sb,
    relatorio_id: str,
    *,
    user_id: Optional[str] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Gera (ou retorna) o playbook de abertura de um relatório concluído.

    user_id: dono efetivo quando o relatório não tem (relatórios gerados via
    CLI/batch têm user_id NULL) — o endpoint passa o usuário autenticado."""
    ctx = _fetch_contexto_relatorio(sb, relatorio_id)
    relatorio = ctx["relatorio"]
    dono = relatorio.get("user_id") or user_id
    if not dono:
        raise ValueError("Não foi possível identificar o dono do plano — entre pela sua conta e tente de novo.")
    relatorio["user_id"] = dono

    ativo = (
        sb.table("playbooks")
        .select("id")
        .eq("relatorio_id", relatorio_id)
        .eq("status", "ATIVO")
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    if ativo.data and not force:
        return {"playbook_id": ativo.data[0]["id"], "ja_existia": True}
    if ativo.data and force:
        sb.table("playbooks").update({"status": "ARQUIVADO", "updated_at": _agora_iso()}).eq(
            "id", ativo.data[0]["id"]
        ).execute()

    projeto_id = _garantir_user_project(sb, ctx)

    tipo = (ctx["inputs"].get("tipo_negocio") or "academia").strip().lower()
    if tipo not in TIPOS_VALIDOS:
        tipo = "outro"
    template = get_template_por_tipo_negocio(tipo)
    deps_template = get_dependencias_por_tipo(tipo)

    titulos = [t.titulo for t in template]
    deps_aplicaveis = [
        d for d in deps_template
        if d.tarefa_origem_titulo in set(titulos) and d.tarefa_destino_titulo in set(titulos)
    ]
    ordem_execucao = ordenar_tarefas_por_dependencias(titulos, deps_aplicaveis)
    posicao_topologica = {titulo: i for i, titulo in enumerate(ordem_execucao)}

    custos_override = _custos_personalizados(ctx)

    # Datas por cadeia: início de cada tarefa = max(hoje, fim das predecessoras TPC)
    predecessoras: dict[str, list[str]] = {}
    for d in deps_aplicaveis:
        if d.tipo == "TERMINA_PARA_COMECAR":
            predecessoras.setdefault(d.tarefa_destino_titulo, []).append(d.tarefa_origem_titulo)

    hoje = date.today()
    fim_por_titulo: dict[str, date] = {}
    datas: dict[str, tuple[date, date]] = {}
    for titulo in ordem_execucao:
        t = next(t for t in template if t.titulo == titulo)
        inicio = hoje
        for pred in predecessoras.get(titulo, []):
            if pred in fim_por_titulo and fim_por_titulo[pred] > inicio:
                inicio = fim_por_titulo[pred]
        fim = inicio + timedelta(days=max(int(t.dias_duracao_default or 7), 1))
        datas[titulo] = (inicio, fim)
        fim_por_titulo[titulo] = fim

    data_prevista_conclusao = max(f for _, f in datas.values()) if datas else hoje

    # Monta linhas de tarefas (template + extras de gaps)
    linhas: list[dict[str, Any]] = []
    for t in sorted(template, key=lambda x: posicao_topologica.get(x.titulo, 999)):
        descricao, origem_secao, origem_insight = _personalizar_descricao(t, ctx)
        inicio, fim = datas[t.titulo]
        custo = custos_override.get(t.titulo, t.custo_planejado_default or None)
        linhas.append({
            "titulo": t.titulo,
            "descricao": descricao,
            "categoria": t.categoria,
            "prioridade": t.prioridade,
            "ordem": posicao_topologica.get(t.titulo, 999) * 10,
            "custo_planejado": custo if custo else None,
            "data_inicio": inicio.isoformat(),
            "data_prevista_conclusao": fim.isoformat(),
            "responsavel_nome": t.responsavel_sugestao,
            "checklist": list(t.checklist or ()),
            "sugerida_pela_ia": False,
            "origem_relatorio_secao": origem_secao,
            "origem_relatorio_insight": origem_insight,
        })
    linhas.extend(_tarefas_de_gaps(ctx, ordem_base=(len(linhas) + 1) * 10))

    custo_total = sum(l["custo_planejado"] or 0 for l in linhas)

    pb = sb.table("playbooks").insert({
        "projeto_id": projeto_id,
        "relatorio_id": relatorio_id,
        "user_id": relatorio["user_id"],
        "org_id": relatorio.get("org_id"),
        "nome": "Plano de Abertura",
        "status": "ATIVO",
        "data_inicio": hoje.isoformat(),
        "data_prevista_conclusao": data_prevista_conclusao.isoformat(),
        "custo_planejado_total": custo_total or None,
        "total_tarefas": len(linhas),
        "tarefas_concluidas": 0,
    }).execute()
    playbook_id = pb.data[0]["id"]

    rows_tarefas = []
    for l in linhas:
        rows_tarefas.append({
            "playbook_id": playbook_id,
            "projeto_id": projeto_id,
            "titulo": l["titulo"],
            "descricao": l["descricao"],
            "categoria": l["categoria"],
            "status": "A_FAZER",
            "prioridade": l["prioridade"],
            "ordem": l["ordem"],
            "custo_planejado": l["custo_planejado"],
            "data_inicio": l["data_inicio"],
            "data_prevista_conclusao": l["data_prevista_conclusao"],
            "responsavel_nome": l["responsavel_nome"],
            "sugerida_pela_ia": l["sugerida_pela_ia"],
            "aceita_pelo_usuario": True,
            "origem_relatorio_secao": l["origem_relatorio_secao"],
            "origem_relatorio_insight": l["origem_relatorio_insight"],
        })
    inseridas = sb.table("tarefas").insert(rows_tarefas).execute()
    id_por_titulo = {row["titulo"]: row["id"] for row in inseridas.data}

    rows_deps = []
    for d in deps_aplicaveis:
        origem_id = id_por_titulo.get(d.tarefa_origem_titulo)
        destino_id = id_por_titulo.get(d.tarefa_destino_titulo)
        if origem_id and destino_id:
            rows_deps.append({
                "tarefa_id": destino_id,
                "depende_de_tarefa_id": origem_id,
                "tipo": d.tipo,
            })
    if rows_deps:
        sb.table("tarefa_dependencias").insert(rows_deps).execute()

    rows_checklist = []
    for l in linhas:
        tarefa_id = id_por_titulo.get(l["titulo"])
        if not tarefa_id:
            continue
        for i, item in enumerate(l["checklist"]):
            rows_checklist.append({
                "tarefa_id": tarefa_id,
                "descricao": item,
                "ordem": i,
            })
    if rows_checklist:
        sb.table("tarefa_checklist").insert(rows_checklist).execute()

    try:
        sb.table("auditoria_eventos").insert({
            "user_id": relatorio["user_id"],
            "projeto_id": projeto_id,
            "entidade": "playbook",
            "entidade_id": playbook_id,
            "evento": "GERAR_PLAYBOOK",
            "snapshot_depois": {
                "relatorio_id": relatorio_id,
                "tipo_negocio": tipo,
                "total_tarefas": len(linhas),
                "custo_planejado_total_centavos": custo_total,
                "tarefas_ia": sum(1 for l in linhas if l["sugerida_pela_ia"]),
            },
        }).execute()
    except Exception:
        logger.warning("auditoria GERAR_PLAYBOOK falhou (não bloqueia)", exc_info=True)

    por_categoria: dict[str, int] = {}
    for l in linhas:
        por_categoria[l["categoria"]] = por_categoria.get(l["categoria"], 0) + 1

    logger.info(
        "playbook gerado relatorio=%s playbook=%s tarefas=%d custo_total=%d",
        relatorio_id, playbook_id, len(linhas), custo_total,
    )
    return {
        "playbook_id": playbook_id,
        "projeto_id": projeto_id,
        "ja_existia": False,
        "tarefas_geradas": len(linhas),
        "tarefas_por_categoria": por_categoria,
        "custo_planejado_total": custo_total,
        "data_prevista_conclusao": data_prevista_conclusao.isoformat(),
    }
