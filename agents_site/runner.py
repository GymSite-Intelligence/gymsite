"""Runner ADK da degustação do site — Fase 3a da migração consultor_engine → agents_site.

Roda `agents_site.root_agent` (5 especialistas ADK) como motor da landing, no lugar
de `conversar(modo_site=True)`. Ativado pela flag `SITE_AGENT_ENGINE=adk` (default
`legacy`); ver `escolher_motor_site` em tools/redis_queue.py e
docs/arquitetura/PLANO_MIGRACAO_ADK_FASE_3A.md.

Contrato preservado: persiste user+assistant em `project_messages` (mesmo formato do
`conversar`) → o polling do front funciona sem alteração.

Nó de design (Opção 1 do plano): o worker é stateless entre turnos (cada mensagem é
um job), então a sessão ADK é RECONSTRUÍDA a cada turno a partir do histórico
`project_messages` — via `append_event` — e o contador do gate (K) é re-hidratado no
`session.state`.

⚠️ VALIDAÇÃO PENDENTE (antes de ligar o canário — Fase 3a parte 2):
smoke contra o ADK real (`adk web` / staging). Pontos a confirmar no ambiente ADK:
  1. coleta da resposta final (filtro de eventos `partial`);
  2. assinatura de `Event(author=..., content=...)` na versão instalada (google-adk 2.3.0);
  3. re-hidratação via `append_event` reproduz o histórico pro agente;
  4. latência/custo dos 2 hops (roteador + especialista) vs o motor legacy.
Os testes unitários cobrem só o wire e a derivação de estado — não a integração ADK.
"""
from __future__ import annotations

import logging

from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents_site.agent import root_agent
from services.consultor.project_messages import carregar_historico, salvar_mensagem

logger = logging.getLogger("gymsite.site_adk")

_APP = "gymsite_site"

# Tools de amostra que o gate_degustacao conta pro corte K=2. Usadas para re-hidratar
# o contador a partir do histórico (o state ADK não sobrevive entre jobs do worker).
_AMOSTRA_TOOLS = frozenset(
    {"buscar_concorrentes", "analisar_demografia", "pesquisar_contexto_mercado"}
)


def _derivar_amostras(historico: list[dict]) -> int:
    """Conta amostras já entregues, lendo tool_calls do histórico persistido."""
    n = 0
    for m in historico:
        for tc in m.get("tool_calls") or []:
            nome = (tc or {}).get("name") or (tc or {}).get("tool")
            if nome in _AMOSTRA_TOOLS:
                n += 1
    return n


def _historico_para_eventos(historico: list[dict]) -> list[Event]:
    """Converte project_messages em eventos ADK pra re-hidratar a sessão."""
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
    """Texto de um evento final (ignora eventos parciais de streaming)."""
    if getattr(event, "partial", False):
        return ""
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return ""
    # Só respostas do modelo/agente — nunca o eco da mensagem do user.
    if getattr(content, "role", None) == "user":
        return ""
    return "".join(p.text for p in content.parts if getattr(p, "text", None))


async def run_site_agent_adk(
    projeto_id: str, mensagem: str, agente: str = "degustacao"
) -> str:
    """Roda um turno da degustação via ADK. Persiste user+assistant em
    project_messages (contrato do conversar). Retorna a resposta do agente."""
    historico = await carregar_historico(projeto_id, limite=20)
    await salvar_mensagem(projeto_id, role="user", content=mensagem)

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=_APP,
        user_id=projeto_id,
        session_id=projeto_id,
        state={
            "tier": "degustacao",
            "agente": agente,
            "amostras_dadas": _derivar_amostras(historico),
        },
    )
    # Re-hidrata o histórico (worker stateless entre turnos).
    session = await session_service.get_session(
        app_name=_APP, user_id=projeto_id, session_id=projeto_id
    )
    for ev in _historico_para_eventos(historico):
        await session_service.append_event(session, ev)

    runner = Runner(agent=root_agent, app_name=_APP, session_service=session_service)
    partes: list[str] = []
    async for event in runner.run_async(
        user_id=projeto_id,
        session_id=projeto_id,
        new_message=Content(role="user", parts=[Part(text=mensagem)]),
    ):
        partes.append(_extrair_resposta(event))

    resposta = "".join(partes).strip() or "Desculpe, não consegui responder agora."
    await salvar_mensagem(projeto_id, role="assistant", content=resposta)
    logger.info(
        "site_agent_adk turno OK projeto=%s len_resp=%d",
        projeto_id,
        len(resposta),
        extra={"agent": "SITE_ADK"},
    )
    return resposta
