"""Runner ADK — site (degustação) + consultor logado.

Motor único: `agents_site.root_agent`. Tier em session.state:
  - degustacao: gate antifatiamento (landing)
  - consultor: sem gate; marca pesquisas + custo após tools
"""
from __future__ import annotations

import logging

from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents_site.agent import root_agent
from agents_site.catalog import ESPECIALISTAS
from agents_site.carimbo import extrair_citacoes, pack_citacoes_tool_results
from agents_site.llm_route import (
    mensagem_falha_turno,
    site_chat_developer_api,
)
from services.consultor.project_messages import carregar_historico, salvar_mensagem
from services.consultor.project_state import (
    atualizar_campo_projeto,
    carregar_projeto,
    marcar_pesquisa_realizada,
)

logger = logging.getLogger("gymsite.site_adk")

_FALLBACK_RESPOSTA = (
    "Tive um problema ao gerar a resposta agora. Pode reformular a pergunta ou tentar de novo?"
)

_APP_SITE = "gymsite_site"
_APP_CONSULTOR = "gymsite_consultor"

_PINADOS = {
    _id: sub.model_copy(
        update={
            "parent_agent": None,
            "disallow_transfer_to_parent": True,
            "disallow_transfer_to_peers": True,
        }
    )
    for _id, _nome in ESPECIALISTAS.items()
    for sub in root_agent.sub_agents
    if sub.name == _nome
}

_AMOSTRA_TOOLS = frozenset(
    {"buscar_concorrentes", "analisar_demografia", "pesquisar_contexto_mercado",
     "analisar_reviews_e_dores"}
)

_TOOL_TO_PESQUISA: dict[str, str] = {
    "pesquisar_contexto_mercado": "mercado",
    "buscar_pontos_comerciais": "pontos_comerciais",
    "analisar_demografia": "demografia",
    "buscar_concorrentes": "concorrentes",
    "pesquisar_concorrentes": "concorrentes",
    "analisar_reviews_e_dores": "reviews",
    "mapear_oferta_e_servicos": "oferta_concorrentes",
    "estimar_investimento": "investimento",
}

_CUSTO_BRL_POR_TOOL: dict[str, float] = {
    "pesquisar_contexto_mercado": 0.35,
    "buscar_concorrentes": 0.45,
    "pesquisar_concorrentes": 0.45,
    "analisar_demografia": 0.25,
    "buscar_pontos_comerciais": 0.30,
    "analisar_reviews_e_dores": 0.40,
    "mapear_oferta_e_servicos": 0.35,
    "estimar_investimento": 0.50,
}


def _resolver_agente(agente: str):
    return _PINADOS.get(agente, root_agent)


def _derivar_amostras(historico: list[dict]) -> int:
    n = 0
    for m in historico:
        for tc in m.get("tool_calls") or []:
            nome = (tc or {}).get("ferramenta") or (tc or {}).get("name") or (tc or {}).get("tool")
            if nome in _AMOSTRA_TOOLS:
                n += 1
    return n


def _historico_para_eventos(historico: list[dict]) -> list[Event]:
    eventos: list[Event] = []
    for m in historico:
        texto = (m.get("content") or "").strip()
        if not texto:
            continue
        eh_user = m.get("role") == "user"
        eventos.append(
            Event(
                author="user" if eh_user else "model",
                content=Content(
                    role="user" if eh_user else "model",
                    parts=[Part(text=texto)],
                ),
            )
        )
    return eventos


def _extrair_resposta(event) -> str:
    if getattr(event, "partial", False):
        return ""
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return ""
    if getattr(content, "role", None) == "user":
        return ""
    return "".join(p.text for p in content.parts if getattr(p, "text", None))


def _coletar_acoes(event) -> list[dict]:
    """Extrai function_call e function_response (com `resultado` JSON da tool)."""
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return []
    acoes: list[dict] = []
    for p in content.parts:
        fc = getattr(p, "function_call", None)
        if fc:
            nome = getattr(fc, "name", "") or ""
            if nome:
                acoes.append({"ferramenta": nome, "status": "sucesso", "resumo": nome})
            continue
        fr = getattr(p, "function_response", None)
        if not fr:
            continue
        nome = getattr(fr, "name", "") or ""
        if not nome:
            continue
        resp = getattr(fr, "response", None)
        if resp is not None and hasattr(resp, "model_dump"):
            try:
                resp = resp.model_dump()
            except Exception:  # noqa: BLE001
                pass
        if not isinstance(resp, dict):
            resp = {"valor": resp} if resp is not None else {}
        status = "erro" if resp.get("erro") else "sucesso"
        acoes.append({
            "ferramenta": nome,
            "status": status,
            "resumo": nome,
            "resultado": resp,
        })
    return acoes


def _normalizar_tool_calls(acoes: list[dict]) -> list[dict]:
    """Dedup por ferramenta; preserva `resultado` quando a response chegou."""
    ordem: list[str] = []
    por_nome: dict[str, dict] = {}
    for a in acoes:
        nome = (a.get("ferramenta") or a.get("name") or "").strip()
        if not nome:
            continue
        if nome not in por_nome:
            ordem.append(nome)
            por_nome[nome] = {
                "ferramenta": nome,
                "status": a.get("status") or "sucesso",
                "resumo": a.get("resumo") or nome,
            }
        cur = por_nome[nome]
        if a.get("status"):
            cur["status"] = a["status"]
        if a.get("resumo"):
            cur["resumo"] = a["resumo"]
        if a.get("resultado") is not None:
            cur["resultado"] = a["resultado"]
    return [por_nome[n] for n in ordem]


async def _rodar_turno(
    agente_obj,
    historico: list[dict],
    mensagem: str,
    projeto_id: str,
    *,
    tier: str = "degustacao",
    app_name: str = _APP_SITE,
):
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=app_name,
        user_id=projeto_id,
        session_id=projeto_id,
        state={
            "tier": tier,
            "agente": getattr(agente_obj, "name", "degustacao"),
            "amostras": _derivar_amostras(historico),
        },
    )
    session = await session_service.get_session(
        app_name=app_name, user_id=projeto_id, session_id=projeto_id
    )
    for ev in _historico_para_eventos(historico):
        await session_service.append_event(session, ev)

    runner = Runner(agent=agente_obj, app_name=app_name, session_service=session_service)
    partes: list[str] = []
    autor: str | None = None
    alvo: str | None = None
    acoes: list[dict] = []
    async for event in runner.run_async(
        user_id=projeto_id,
        session_id=projeto_id,
        new_message=Content(role="user", parts=[Part(text=mensagem)]),
    ):
        acts = getattr(event, "actions", None)
        destino = getattr(acts, "transfer_to_agent", None) if acts else None
        if destino:
            alvo = destino
        acoes.extend(_coletar_acoes(event))
        texto = _extrair_resposta(event)
        if texto:
            autor = event.author
        partes.append(texto)
    return "".join(partes).strip(), autor, alvo, _normalizar_tool_calls(acoes)


async def _retry_pos_transfer(
    resposta: str,
    alvo: str | None,
    historico: list[dict],
    mensagem: str,
    projeto_id: str,
    *,
    tier: str,
    app_name: str,
):
    if resposta or not alvo:
        return resposta, None, []
    pin = next((p for p in _PINADOS.values() if getattr(p, "name", None) == alvo), None)
    if pin is None:
        return resposta, None, []
    logger.warning("adk vazio pós-transfer pra %s; re-rodando fixo", alvo)
    return await _rodar_turno(pin, historico, mensagem, projeto_id, tier=tier, app_name=app_name)


async def _sync_consultor_pos_turno(
    projeto_id: str,
    usuario_id: str,
    acoes: list[dict],
) -> None:
    if not acoes:
        return
    projeto = await carregar_projeto(projeto_id, usuario_id)
    custo = sum(_CUSTO_BRL_POR_TOOL.get(a["ferramenta"], 0.10) for a in acoes)
    if custo:
        total = round((projeto.custo_brl_ate_agora or 0.0) + custo + 0.02, 2)
        await atualizar_campo_projeto(projeto_id, "custo_brl_ate_agora", total, usuario_id)
    for acao in acoes:
        pesq = _TOOL_TO_PESQUISA.get(acao["ferramenta"])
        if pesq:
            await marcar_pesquisa_realizada(projeto_id, pesq, usuario_id)


async def _persistir_falha_turno(projeto_id: str, exc: BaseException) -> str:
    msg = mensagem_falha_turno(exc)
    logger.exception(
        "adk turno falhou projeto=%s — persistindo assistant de erro",
        projeto_id,
        extra={"agent": "SITE_ADK"},
    )
    try:
        await salvar_mensagem(
            projeto_id,
            role="assistant",
            content=msg,
            agente="sistema",
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "falha ao persistir mensagem de erro projeto=%s",
            projeto_id,
        )
    return msg


async def _executar_turno_site(
    projeto_id: str,
    mensagem_efetiva: str,
    historico: list[dict],
    agente: str,
) -> tuple[str, str | None, list[dict]]:
    escolhido = _resolver_agente(agente)
    with site_chat_developer_api(escolhido):
        resposta, autor, alvo, acoes = await _rodar_turno(
            escolhido,
            historico,
            mensagem_efetiva,
            projeto_id,
            tier="degustacao",
            app_name=_APP_SITE,
        )
        resposta, autor_retry, acoes_retry = await _retry_pos_transfer(
            resposta,
            alvo,
            historico,
            mensagem_efetiva,
            projeto_id,
            tier="degustacao",
            app_name=_APP_SITE,
        )
    if autor_retry:
        autor = autor_retry
    if acoes_retry:
        acoes = acoes_retry
    if not resposta:
        resposta = _FALLBACK_RESPOSTA
    return resposta, autor, acoes


async def completar_turno_orfao_site(projeto_id: str, agente: str = "degustacao") -> bool:
    """Completa turno quando user já foi persistido mas assistant não (worker caiu)."""
    historico = await carregar_historico(projeto_id, limite=20)
    if not historico or historico[-1].get("role") != "user":
        return False
    mensagem = (historico[-1].get("content") or "").strip()
    if not mensagem:
        return False
    historico_turno = historico[:-1]
    mensagem_efetiva = mensagem
    try:
        resposta, autor, acoes = await _executar_turno_site(
            projeto_id, mensagem_efetiva, historico_turno, agente
        )
    except Exception as exc:  # noqa: BLE001
        await _persistir_falha_turno(projeto_id, exc)
        return True
    resposta, citacoes = extrair_citacoes(resposta)
    await salvar_mensagem(
        projeto_id,
        role="assistant",
        content=resposta,
        tool_calls=acoes or None,
        tool_results=pack_citacoes_tool_results(citacoes),
        agente=autor,
    )
    logger.info(
        "site_agent_adk órfão recuperado projeto=%s respondeu=%s",
        projeto_id,
        autor,
        extra={"agent": "SITE_ADK"},
    )
    return True


async def run_site_agent_adk(
    projeto_id: str,
    mensagem: str,
    agente: str = "degustacao",
    localizacao_hint: dict | None = None,
) -> str:
    from agents_site.localizacao import injetar_contexto_localizacao, resolver_localizacao
    from services.consultor.consultor_engine import _ANON_SITE_USER_ID
    from services.consultor.project_state import atualizar_campo_projeto, carregar_projeto

    previa: dict = {}
    modelo_atual: dict = {}
    try:
        proj = await carregar_projeto(projeto_id, _ANON_SITE_USER_ID)
        previa = dict(proj.localizacao or {})
        modelo_atual = dict(proj.modelo_negocio or {})
        if modelo_atual.get("tipo") and "tipo_negocio" not in previa:
            previa = {**previa, "tipo_negocio": modelo_atual.get("tipo")}
    except Exception:  # noqa: BLE001
        logger.debug("site_adk: sem prévia de localização projeto=%s", projeto_id)

    loc = resolver_localizacao(mensagem, hint=localizacao_hint, previa=previa)
    mensagem_efetiva = injetar_contexto_localizacao(mensagem, loc)

    if loc.completa or (loc.bairro or loc.cidade):
        try:
            payload_loc = {
                k: v for k, v in {
                    "bairro": loc.bairro,
                    "cidade": loc.cidade,
                    "uf": loc.uf,
                }.items() if v
            }
            if payload_loc:
                await atualizar_campo_projeto(
                    projeto_id, "localizacao", {**previa, **payload_loc}, _ANON_SITE_USER_ID
                )
            if loc.tipo_negocio:
                mn = {**modelo_atual, "tipo": loc.tipo_negocio}
                await atualizar_campo_projeto(
                    projeto_id, "modelo_negocio", mn, _ANON_SITE_USER_ID
                )
        except Exception:  # noqa: BLE001
            logger.exception("site_adk: falha ao persistir localizacao projeto=%s", projeto_id)

    historico = await carregar_historico(projeto_id, limite=20)
    await salvar_mensagem(projeto_id, role="user", content=mensagem)

    try:
        resposta, autor, acoes = await _executar_turno_site(
            projeto_id, mensagem_efetiva, historico, agente
        )
    except Exception as exc:  # noqa: BLE001
        return await _persistir_falha_turno(projeto_id, exc)

    resposta, citacoes = extrair_citacoes(resposta)

    await salvar_mensagem(
        projeto_id,
        role="assistant",
        content=resposta,
        tool_calls=acoes or None,
        tool_results=pack_citacoes_tool_results(citacoes),
        agente=autor,
    )
    logger.info(
        "site_agent_adk turno OK projeto=%s pedido=%s respondeu=%s len_resp=%d loc=%s citacoes=%d",
        projeto_id,
        agente,
        autor,
        len(resposta),
        loc.origem or "-",
        len(citacoes),
        extra={"agent": "SITE_ADK"},
    )
    return resposta


async def run_consultor_adk(
    projeto_id: str,
    mensagem: str,
    usuario_id: str,
    agente: str = "degustacao",
) -> str:
    historico = await carregar_historico(projeto_id, limite=20)
    await salvar_mensagem(projeto_id, role="user", content=mensagem)

    escolhido = _resolver_agente(agente)
    try:
        with site_chat_developer_api(escolhido):
            resposta, autor, alvo, acoes = await _rodar_turno(
                escolhido,
                historico,
                mensagem,
                projeto_id,
                tier="consultor",
                app_name=_APP_CONSULTOR,
            )
            resposta, autor_retry, acoes_retry = await _retry_pos_transfer(
                resposta,
                alvo,
                historico,
                mensagem,
                projeto_id,
                tier="consultor",
                app_name=_APP_CONSULTOR,
            )
        if autor_retry:
            autor = autor_retry
        if acoes_retry:
            acoes = acoes_retry
    except Exception as exc:  # noqa: BLE001
        return await _persistir_falha_turno(projeto_id, exc)

    if not resposta:
        resposta = "Tive um problema ao gerar a resposta agora. Pode reformular a pergunta ou tentar de novo?"

    await _sync_consultor_pos_turno(projeto_id, usuario_id, acoes)

    resposta, citacoes = extrair_citacoes(resposta)

    await salvar_mensagem(
        projeto_id,
        role="assistant",
        content=resposta,
        tool_calls=acoes or None,
        tool_results=pack_citacoes_tool_results(citacoes),
        agente=autor,
    )
    logger.info(
        "consultor_adk turno OK projeto=%s pedido=%s respondeu=%s tools=%d citacoes=%d",
        projeto_id,
        agente,
        autor,
        len(acoes),
        len(citacoes),
        extra={"agent": "CONSULTOR_ADK"},
    )
    return resposta
