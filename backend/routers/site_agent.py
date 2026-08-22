"""
Router /api/site-agent — Análise Gratuita PÚBLICA da landing (N3).

Conecta o ChatAgent (gym-insight-hub) ao pipeline determinístico de viabilidade:
visitante anônimo tem direito a 1 análise gratuita (mini-relatório).

Fluxo:
  POST /analise  → Turnstile + entitlement (1/email) + caps (IP/dia, global/dia)
                   + allowance SearchAPI → cria stub `relatorios` (user_id NULL,
                   org ANON, access_token) → enfileira o MESMO pipeline ADK.
  GET  /analise/{id} + header X-Access-Token → polling; 'done' → SUBSET free.
                   Token UUID + TTL (SITE_ANALISE_TOKEN_TTL_HOURS, default 48).
                   Query ?token= rejeitada (evita Referer / logs de URL).

Aluguel no mini-relatório (`aluguel_m2` em `_extras_teaser`) vem do A4 Tier 0 MRLR
(`tools/aluguel_mrlr.py`), não de SearchAPI. Inputs mínimos MRLR no stub:
  cidade + bairro (lookup `renda_bairro` → `municipio_pib`); área via default
  area_m2_min/max 300–1500 preset "m" (visitante não informa área hoje).
Ver `.agent/rules/conferencia-fontes-pipeline.md` §3.

Segurança: endpoint público (sem JWT). Escrita/leitura via backend service_role
(RLS bloqueia anon). A leitura do resultado exige o access_token não-adivinhável.
Reusa, via import LAZY (evita circular com api.py): create_relatorio_stub,
_enqueue_ou_background, NovoRelatorioInput, _supabase_client.
"""
from __future__ import annotations

import hmac
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from agents_site.catalog import AGENTES_VALIDOS, id_publico  # sem dependência do ADK (import barato)
from tools.turnstile import verificar_turnstile
from tools.db_schema import tbl  # roteia gymsite/shared (flags ON em prod; tbl(sb,) cru = public)

logger = logging.getLogger("gymsite.site_agent")

router_site_agent = APIRouter(prefix="/api/site-agent", tags=["site-agent — landing"])

_ANON_ORG_ID = "00000000-0000-0000-0000-0000000000a0"
_FONTE = "landing-getgymsite"
_CAP_IP_DIA = int(os.getenv("SITE_AGENT_CAP_IP_DIA") or "5")
_CAP_GLOBAL_DIA = int(os.getenv("SITE_AGENT_CAP_GLOBAL_DIA") or "100")
_ETA_MIN = 5
_TOKEN_TTL_HOURS = int(os.getenv("SITE_ANALISE_TOKEN_TTL_HOURS") or "48")
_CHAT_SESSOES_IP_DIA = int(os.getenv("SITE_CHAT_SESSOES_IP_DIA") or "2")
_CHAT_TURNOS_PROJETO = int(os.getenv("SITE_CHAT_TURNOS_PROJETO") or "10")
_CHAT_MODO_DEGUSTACAO = (os.getenv("SITE_CHAT_MODO_DEGUSTACAO") or "0").strip().lower() in ("1", "true", "yes")
_CHAT_BYPASS_TOKEN = (os.getenv("SITE_CHAT_BYPASS_TOKEN") or "").strip()
_EMAILS_BYPASS_ANALISE = {
    e.strip().lower()
    for e in (os.getenv("SITE_ANALISE_EMAIL_BYPASS") or "teste@gymsite.com.br").split(",")
    if e.strip()
}


def _email_com_bypass(email: str) -> bool:
    return email.lower().strip() in _EMAILS_BYPASS_ANALISE


def _ip_na_allowlist(ip: str | None) -> bool:
    allow = {x.strip() for x in (os.getenv("SITE_CHAT_IP_ALLOWLIST") or "").split(",") if x.strip()}
    return bool(ip and ip in allow)


def _bypass_autorizado(request: Request, dev_token: str | None, ip: str | None) -> bool:
    if _ip_na_allowlist(ip):
        return True
    if not _CHAT_BYPASS_TOKEN:
        return False
    candidato = (request.headers.get("x-site-chat-token") or dev_token or "").strip()
    return bool(candidato) and hmac.compare_digest(candidato, _CHAT_BYPASS_TOKEN)


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _access_token_expirado(row: dict) -> bool:
    """True se capability token passou do TTL.

    Prefer access_token_expires_at (migration 20260822); senão created_at + SITE_ANALISE_TOKEN_TTL_HOURS.
    Sem âncora temporal → trata como expirado (fail-closed).
    """
    now = datetime.now(timezone.utc)
    exp = _parse_ts(row.get("access_token_expires_at"))
    if exp is not None:
        return now >= exp
    created = _parse_ts(row.get("created_at"))
    if created is None:
        return True
    return now >= created + timedelta(hours=_TOKEN_TTL_HOURS)


def _gravar_access_token(sb, relatorio_id: str, access_token: str) -> datetime:
    """Persiste token + expires_at. Se coluna expires ainda não existir, só token."""
    expires = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)
    payload = {
        "access_token": access_token,
        "access_token_expires_at": expires.isoformat(),
    }
    try:
        tbl(sb, "relatorios").update(payload).eq("id", relatorio_id).execute()
    except Exception:
        logger.warning(
            "access_token_expires_at indisponível — gravando só token (aplique db/migrations/20260822_access_token_expires_at.sql)"
        )
        tbl(sb, "relatorios").update({"access_token": access_token}).eq("id", relatorio_id).execute()
    return expires


async def _cap_chat_estourado(ip: str | None, projeto_id: str | None, nova_sessao: bool, agente: str) -> str | None:
    # Fail-CLOSED: sem Redis não há teto, e o mesmo evento faz `_enqueue_ou_background`
    # degradar pra BackgroundTasks — o turno roda dentro da api (maxScale=20), não no
    # worker. Sem cap + execução inline = gasto de Gemini sem teto. O /analise capeia
    # via Supabase, então o funil de lead sobrevive a uma queda do Redis; só o chat cai.
    try:
        from tools.redis_client import get_redis
        r = await get_redis()
    except Exception:
        logger.exception("cap de chat indisponível (redis inacessível) — bloqueando")
        return "indisponivel"
    try:
        hoje = datetime.now(timezone.utc).strftime("%Y%m%d")
        if nova_sessao and ip:
            chave = f"site_chat:sessoes:{ip}:{hoje}"
            n = await r.incr(chave)
            if n == 1:
                await r.expire(chave, 86400)
            if n > _CHAT_SESSOES_IP_DIA:
                logger.warning("cap sessoes chat/dia atingido ip=%s (%s)", ip, _CHAT_SESSOES_IP_DIA)
                return "sessoes"
        # 1 DEGUSTAÇÃO (conversa) por especialista/dia — só conta na ABERTURA (nova_sessao).
        # A clarificação (usuário responde a pergunta do agente) é parte da MESMA pergunta,
        # não uma nova — não pode queimar a cota. Continuação já é limitada pelo cap `turnos`.
        if _CHAT_MODO_DEGUSTACAO and nova_sessao and ip:
            chave = f"site_chat:agente:{ip}:{agente}:{hoje}"
            n = await r.incr(chave)
            if n == 1:
                await r.expire(chave, 86400)
            if n > 1:
                logger.warning("degustacao: pergunta extra bloqueada ip=%s agente=%s", ip, agente)
                return "agente"
        if not nova_sessao and projeto_id:
            chave = f"site_chat:turnos:{projeto_id}"
            n = await r.incr(chave)
            if n == 1:
                await r.expire(chave, 86400)
            if n > _CHAT_TURNOS_PROJETO:
                logger.warning("cap turnos chat atingido projeto=%s (%s)", projeto_id, _CHAT_TURNOS_PROJETO)
                return "turnos"
    except Exception:
        logger.exception("cap de chat falhou no meio (redis) — bloqueando")
        return "indisponivel"
    return None


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AnaliseInput(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    telefone: Optional[str] = Field(default=None, max_length=40)
    cidade: str = Field(min_length=2, max_length=120)
    bairro: str = Field(min_length=2, max_length=120)
    uf: Optional[str] = Field(default=None, max_length=2)
    perfil: Optional[str] = Field(default=None, max_length=40)        # vou_abrir | ja_opero
    tipo_negocio: str = Field(default="academia", max_length=40)
    turnstile_token: Optional[str] = None
    dev_token: Optional[str] = Field(default=None, max_length=120)
    utm_source: Optional[str] = Field(default=None, max_length=120)
    utm_medium: Optional[str] = Field(default=None, max_length=120)
    utm_campaign: Optional[str] = Field(default=None, max_length=160)


class AnaliseResposta(BaseModel):
    status: str                       # processando | quota_used | fila
    relatorio_id: Optional[str] = None
    access_token: Optional[str] = None
    eta_min: Optional[int] = None
    mensagem: str


class ConversarSiteInput(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    projeto_id: Optional[str] = None          # None = nova sessão (exige Turnstile)
    turnstile_token: Optional[str] = None      # obrigatório só na 1ª mensagem
    agente: Optional[str] = None               # None/degustacao = roteador; senão, id de agents_site/catalog.py
    # Hint opcional do front (gym-insight-hub): evita reperguntar bairro/cidade.
    localizacao: Optional[dict] = None         # {bairro, cidade, uf} — validado no runner
    dev_token: Optional[str] = Field(default=None, max_length=120)

    @field_validator("agente")
    @classmethod
    def _agente_conhecido(cls, v: Optional[str]) -> Optional[str]:
        # P-005: string livre aqui entra CRUA na chave do cap por especialista
        # (`site_chat:agente:{ip}:{agente}:{dia}`). Sem whitelist, mandar um `agente`
        # diferente a cada request zera o contador e o cap nunca estoura — e `:` no
        # valor forja a chave. Fonte única das chaves: agents_site/catalog.py.
        if v is not None and v not in AGENTES_VALIDOS:
            raise ValueError(f"agente desconhecido: {v!r}")
        return v

    @field_validator("localizacao")
    @classmethod
    def _localizacao_shape(cls, v: Optional[dict]) -> Optional[dict]:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("localizacao deve ser objeto")
        out: dict = {}
        for k in ("bairro", "cidade", "uf", "bairro_ascii", "tipo_negocio"):
            raw = v.get(k)
            if raw is None:
                continue
            s = str(raw).strip()
            if not s:
                continue
            if k == "uf":
                s = s.upper()[:2]
            elif len(s) > 120:
                s = s[:120]
            out[k] = s
        return out or None


class ConversarSiteResposta(BaseModel):
    projeto_id: str
    mensagem: str
    sugestoes: list[str] = []
    pode_gerar_relatorio: bool = False
    dados_faltantes: list[str] = []
    # Dados coletados no chat (server-side) → prefill do form Tier 2 (POST /analise),
    # pra não re-perguntar cidade/bairro/tipo que o visitante já disse conversando.
    localizacao: dict = {}        # {cidade, bairro, uf}
    modelo_negocio: dict = {}     # {tipo, ...} — sem campos internos


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sb():
    from api import _supabase_client
    return _supabase_client()


def _client_ip(request: Request) -> str | None:
    # Atrás da Cloudflare: CF-Connecting-IP é o IP real do visitante.
    return (
        request.headers.get("cf-connecting-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )


def _hoje_inicio_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _email_ja_usou(sb, email: str) -> bool:
    res = (
        tbl(sb,"analise_gratuita")
        .select("id")
        .eq("email", email.lower().strip())
        .limit(1)
        .execute()
    )
    return bool(res.data)


def _cap_estourado(sb, ip: str | None) -> bool:
    inicio = _hoje_inicio_iso()
    glob = tbl(sb,"analise_gratuita").select("id", count="exact").gte("created_at", inicio).execute()
    if (glob.count or 0) >= _CAP_GLOBAL_DIA:
        logger.warning("cap global/dia atingido (%s)", _CAP_GLOBAL_DIA)
        return True
    if ip:
        per_ip = (
            tbl(sb,"analise_gratuita").select("id", count="exact")
            .eq("ip", ip).gte("created_at", inicio).execute()
        )
        if (per_ip.count or 0) >= _CAP_IP_DIA:
            logger.warning("cap IP/dia atingido ip=%s (%s)", ip, _CAP_IP_DIA)
            return True
    return False


def _capturar_lead(sb, data: "AnaliseInput", background) -> None:
    """Persiste o lead (best-effort, não bloqueia). Usado no fluxo normal E no
    overflow 'fila' — senão a promessa de 'enviamos por e-mail' descartaria o
    contato. NÃO consome o entitlement (analise_gratuita): o email segue elegível."""
    try:
        from backend.routers.leads import LeadInput, _persistir_lead, _sync_apollo_bg
        lead = LeadInput(
            nome=data.nome, email=data.email, telefone=data.telefone,
            cidade=data.cidade, bairro=data.bairro, perfil=data.perfil,
            utm_source=data.utm_source, utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign, fonte=_FONTE,
        )
        reg = _persistir_lead(sb, lead)
        background.add_task(_sync_apollo_bg, reg["id"], lead)
    except Exception as e:  # noqa: BLE001
        logger.warning("captura de lead falhou (segue): %s", e)


def _searchapi_sem_folga() -> bool:
    """True se a allowance do SearchAPI está no nível crítico (best-effort)."""
    try:
        from tools.searchapi_account import resumo_orcamento
        orc = resumo_orcamento()
        if orc.get("status") == "critico":
            return True
        return int(orc.get("restante") or 0) <= 0 and int(orc.get("remaining_credits_pagos") or 0) <= 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("checagem allowance SearchAPI falhou (segue): %s", exc)
        return False


# ─── POST /api/site-agent/analise ─────────────────────────────────────────────

@router_site_agent.post("/analise", response_model=AnaliseResposta)
async def criar_analise(data: AnaliseInput, request: Request, background: BackgroundTasks):
    from api import NovoRelatorioInput, create_relatorio_stub, _enqueue_ou_background

    ip = _client_ip(request)

    # 1. Anti-bot (fail-closed — o run gasta dinheiro). Dev/owner pula via
    #    allowlist de IP ou token (mesmo mecanismo do chat).
    if not _bypass_autorizado(request, data.dev_token, ip):
        if not await verificar_turnstile(data.turnstile_token, ip):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Verificação anti-bot falhou.")

    sb = _sb()
    # Token/IP de dono = mesmo bypass do e-mail allowlist: sem entitlement, sem
    # cap IP/global, sem gate SearchAPI. Leads sem token seguem o funil normal.
    token_bypass = _bypass_autorizado(request, data.dev_token, ip)
    bypass = token_bypass or _email_com_bypass(data.email)
    if bypass:
        logger.info(
            "analise gratuita com bypass entitlement token=%s email=%s",
            token_bypass,
            data.email,
        )

    # 2. Entitlement: 1 grátis por email.
    if not bypass and _email_ja_usou(sb, data.email):
        return AnaliseResposta(
            status="quota_used",
            mensagem="Você já usou sua análise gratuita. Fale com nosso time para o relatório completo.",
        )

    # 3. Caps (IP/dia, global/dia) e 4. allowance SearchAPI → overflow.
    if not bypass and (_cap_estourado(sb, ip) or _searchapi_sem_folga()):
        # Captura o lead ANTES de retornar — a mensagem promete follow-up por
        # e-mail; sem isso o contato se perderia. Não consome o entitlement.
        _capturar_lead(sb, data, background)
        return AnaliseResposta(
            status="fila",
            mensagem="Estamos com alta demanda agora. Deixe seus dados que enviamos sua análise por e-mail em breve.",
        )

    # 5. Cria stub do relatório (run anônimo) + access_token.
    payload = NovoRelatorioInput(
        cidade=data.cidade,
        uf=(data.uf or None),
        bairro=data.bairro,
        area_m2_min=300,
        area_m2_max=1500,
        tamanho_preset="m",
        tipo_negocio=(data.tipo_negocio or "academia"),
        org_id=_ANON_ORG_ID,
    )
    try:
        relatorio_id, _created = create_relatorio_stub(payload, org_id=_ANON_ORG_ID, user_id=None)
    except Exception as e:  # noqa: BLE001
        logger.error("falha ao criar stub anônimo: %s", e)
        raise HTTPException(status_code=500, detail="Falha ao iniciar a análise.") from e

    access_token = str(uuid.uuid4())
    _gravar_access_token(sb, relatorio_id, access_token)

    # 6. Grava entitlement (unique(email) é o guard duro contra corrida).
    if not bypass:
        try:
            tbl(sb,"analise_gratuita").insert({
                "email": data.email.lower().strip(),
                "ip": ip,
                "relatorio_id": relatorio_id,
                "user_agent": request.headers.get("user-agent"),
                "utm": {"source": data.utm_source, "medium": data.utm_medium, "campaign": data.utm_campaign},
            }).execute()
        except Exception:  # corrida: outro request do mesmo email ganhou
            return AnaliseResposta(
                status="quota_used",
                mensagem="Você já usou sua análise gratuita. Fale com nosso time para o relatório completo.",
            )

    # 7. Lead pro CRM/Apollo (best-effort, não bloqueia).
    if not bypass:
        _capturar_lead(sb, data, background)

    # 8. Enfileira o MESMO pipeline.
    await _enqueue_ou_background({
        "type": "pipeline",
        "relatorio_id": relatorio_id,
        "payload": payload.model_dump(),
    }, background)

    logger.info("análise grátis iniciada id=%s email=%s ip=%s", relatorio_id, data.email, ip)
    return AnaliseResposta(
        status="processando",
        relatorio_id=relatorio_id,
        access_token=access_token,
        eta_min=_ETA_MIN,
        mensagem=f"Estamos gerando sua análise (~{_ETA_MIN} min). Você pode aguardar aqui ou receber por e-mail.",
    )


# ─── POST /api/site-agent/conversar (degustação — Tier 1) ─────────────────────

@router_site_agent.post("/conversar")
async def conversar_site(data: ConversarSiteInput, request: Request, background: BackgroundTasks):
    """Chat de degustação ASSÍNCRONO via ADK (`agents_site`). POST enfileira o turno;
    resposta vem por GET /conversar/{projeto_id}/mensagens.

    Blueprint genérico (history→LLM→sendText) mapeia aqui para:
    enqueue `site_conversar` → `run_site_agent_adk` → salvar_mensagem + poll.
    Sem Evolution/WhatsApp (sandbox = HTTP).

    Caps chat: Turnstile em nova sessão + Redis `_cap_chat_estourado`
    (sessoes/IP/dia, turnos/projeto, degustação agente). Fail-closed se Redis cair.
    """
    from services.consultor.consultor_engine import _ANON_SITE_USER_ID
    from services.consultor.project_state import criar_projeto
    from api import _enqueue_ou_background

    ip = _client_ip(request)
    nova_sessao = not data.projeto_id

    # Anti-bot na 1ª msg (fail-closed). Dev/owner pula via allowlist de IP ou token
    # (x-site-chat-token / dev_token) — mesmo mecanismo do /analise.
    if (nova_sessao
            and not _bypass_autorizado(request, data.dev_token, ip)
            and not await verificar_turnstile(data.turnstile_token, ip)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Verificação anti-bot falhou.")

    if not _bypass_autorizado(request, data.dev_token, ip):
        motivo = await _cap_chat_estourado(ip, data.projeto_id, nova_sessao, data.agente or "degustacao")
        if motivo == "indisponivel":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="O chat está indisponível no momento. Tente de novo em alguns minutos — ou peça a análise gratuita do seu ponto.",
            )
        if motivo == "sessoes":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Você já usou a degustação de hoje. Peça a análise gratuita do seu ponto — é bem mais completa.",
            )
        if motivo == "agente":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Você já fez sua pergunta pra esse especialista hoje. Escolha outro agente — ou peça a análise gratuita do seu ponto.",
            )
        if motivo == "turnos":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Essa conversa chegou ao limite da degustação. Peça a análise gratuita do seu ponto pra ir mais fundo.",
            )

    try:
        projeto_id = data.projeto_id
        if nova_sessao:
            projeto = await criar_projeto(_ANON_SITE_USER_ID)
            projeto_id = projeto.id
    except Exception as e:  # noqa: BLE001
        logger.exception("conversar_site: falha ao criar projeto anon")
        raise HTTPException(status_code=500, detail="Falha ao iniciar a conversa.") from e

    # Enfileira o turno (worker roda o engine e salva a resposta). Com REDIS_URL +
    # RUN_QUEUE_WORKER=0 na api, vai pro gymsite-worker; senão BackgroundTasks fallback.
    await _enqueue_ou_background({
        "type": "site_conversar",
        "projeto_id": projeto_id,
        "mensagem": data.mensagem,
        "usuario_id": _ANON_SITE_USER_ID,
        "agente": data.agente or "degustacao",
        "localizacao": data.localizacao,
    }, background)

    logger.info("site_conversar enfileirado projeto=%s ip=%s", projeto_id, ip)
    return {"projeto_id": projeto_id, "status": "analisando"}


# ─── GET /api/site-agent/conversar/{id}/mensagens (polling) ───────────────────

@router_site_agent.get("/conversar/{projeto_id}/mensagens")
async def conversar_mensagens(projeto_id: str, desde: Optional[str] = None):
    """Polling do chat. Devolve mensagens APÓS `desde` (ISO) + estado do projeto
    (localizacao/modelo_negocio p/ prefill do Tier 2). O projeto_id (uuid não-
    adivinhável) é o token da sessão; só serve projetos do user anon do site."""
    from services.consultor.consultor_engine import _ANON_SITE_USER_ID
    sb = _sb()

    proj = (
        tbl(sb, "user_projects")
        .select("localizacao, modelo_negocio, status, user_id")
        .eq("id", projeto_id).maybe_single().execute()
    ).data or {}
    if not proj or proj.get("user_id") != _ANON_SITE_USER_ID:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    q = tbl(sb, "project_messages").select(
        "role, content, created_at, agente, tool_calls, tool_results"
    ).eq("projeto_id", projeto_id)
    if desde:
        q = q.gt("created_at", desde)
    msgs = q.order("created_at").execute().data or []
    # A coluna guarda o nome ADK (Event.author); a API fala id público nos dois sentidos.
    # É este campo que acende o crachá do especialista em cada balão — com o roteador,
    # quem respondeu só se sabe DEPOIS do turno.
    from agents_site.carimbo import unpack_citacoes_from_msg
    from tools.floor_plan_layout import sanitize_tool_calls_planta

    for m in msgs:
        m["agente"] = id_publico(m.get("agente"))
        m["citacoes"] = unpack_citacoes_from_msg(m)
        m.pop("tool_results", None)
        sanitize_tool_calls_planta(m.get("tool_calls"))

        # RAG Eros: injeta fontes recuperadas via tools consultar_eros_* no polling.
        # O frontend (siteAgent.ts → PollMsg.sources) renderiza no chat público.
        fontes_eros = []
        for tc in (m.get("tool_calls") or []):
            nome = tc.get("ferramenta") or tc.get("name") or ""
            if nome.startswith("consultar_eros_"):
                resultado = tc.get("resultado") or tc.get("result") or {}
                if isinstance(resultado, dict):
                    fontes = resultado.get("fontes") or resultado.get("sources") or []
                    if isinstance(fontes, list) and fontes:
                        # Pega apenas as fontes da tool mais recente (última chamada)
                        fontes_eros = fontes
        if fontes_eros:
            m["sources"] = fontes_eros

        # RAG Eros: injeta fontes recuperadas via tools consultar_eros_* no polling.
        # O frontend (siteAgent.ts → PollMsg.sources) renderiza no chat público.
        fontes_eros = []
        for tc in (m.get("tool_calls") or []):
            nome = tc.get("ferramenta") or tc.get("name") or ""
            if nome.startswith("consultar_eros_"):
                resultado = tc.get("resultado") or tc.get("result") or {}
                if isinstance(resultado, dict):
                    fontes = resultado.get("fontes") or resultado.get("sources") or []
                    if isinstance(fontes, list) and fontes:
                        # Pega apenas as fontes da tool mais recente (última chamada)
                        fontes_eros = fontes
        if fontes_eros:
            m["sources"] = fontes_eros

    mn = dict(proj.get("modelo_negocio") or {})
    mn.pop("_site", None)
    loc = proj.get("localizacao") or {}
    return {
        "mensagens": msgs,
        "status": proj.get("status"),
        "pode_gerar_relatorio": bool(loc.get("cidade") and loc.get("bairro")),
        "localizacao": loc,
        "modelo_negocio": mn,
    }


# ─── GET /api/site-agent/analise/{id} ─────────────────────────────────────────

@router_site_agent.get("/analise/{relatorio_id}")
async def status_analise(
    relatorio_id: str,
    request: Request,
    x_access_token: str | None = Header(None, alias="X-Access-Token"),
):
    """Polling do status + entrega do mini-relatório (subset free) quando 'done'.

    Exige header X-Access-Token (capability UUID). Sem JWT — leitura via service_role.
    Query ?token= não é aceita (evita vazamento via Referer / logs de URL).
    """
    token = (x_access_token or "").strip()
    if not token:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    sb = _sb()
    # created_at ancora o TTL sem exigir migration; expires_at opcional (20260822).
    try:
        rel = (
            tbl(sb, "relatorios")
            .select("id, status, access_token, created_at, access_token_expires_at")
            .eq("id", relatorio_id)
            .maybe_single()
            .execute()
        )
        row = rel.data
    except Exception:
        rel = (
            tbl(sb, "relatorios")
            .select("id, status, access_token, created_at")
            .eq("id", relatorio_id)
            .maybe_single()
            .execute()
        )
        row = rel.data

    if not row or str(row.get("access_token") or "") != token:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    if _access_token_expirado(row):
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    st = row.get("status")
    if st != "done":
        # queued | running → ainda processando; failed/cancelled → erro amigável.
        if st in ("failed", "cancelled"):
            try:
                tbl(sb, "analise_gratuita").delete().eq("relatorio_id", relatorio_id).execute()
                logger.info("entitlement liberado no polling de falha rel=%s", relatorio_id)
            except Exception as e:
                logger.warning("liberação de entitlement no polling falhou (segue) rel=%s: %s", relatorio_id, e)
            return {"status": "erro", "mensagem": "Não conseguimos concluir sua análise. Você pode tentar de novo com o mesmo e-mail — ou nosso time te contata."}
        return {"status": "processando", "eta_min": _ETA_MIN}

    # SUBSET free (gateia A9/concorrentes completos/financeiro/PDF — só no pago).
    out = (
        tbl(sb,"relatorio_outputs")
        .select("*")
        .eq("relatorio_id", relatorio_id).maybe_single().execute()
    ).data or {}

    comp = (
        tbl(sb,"competidores")
        .select("nome, bairro_concorrente, rating_oficial")
        .eq("relatorio_id", relatorio_id)
        .order("rating_oficial", desc=True)
        .limit(3).execute()
    ).data or []

    rel_meta = (
        tbl(sb,"relatorios").select("bairro")
        .eq("id", relatorio_id).maybe_single().execute()
    ).data or {}

    return {
        "status": "pronto",
        "mini_relatorio": {
            "veredito": out.get("veredito"),
            "resumo_executivo": out.get("resumo_executivo"),
            "nivel_saturacao": out.get("nivel_saturacao"),
            "score_bairro": out.get("score_bairro"),
            "total_concorrentes": out.get("total_concorrentes_analisados"),
            "rating_medio_concorrentes": out.get("rating_medio_concorrentes"),
            "modelo_recomendado": out.get("modelo_recomendado"),
            "top_concorrentes": comp,
            "extras": _extras_teaser(out, rel_meta.get("bairro")),
        },
        "upsell": "Veja o relatório completo: concorrência detalhada, planos/preços, cenários financeiros e posicionamento.",
    }


def _extras_teaser(out: dict, bairro_analisado: str | None) -> dict:
    def _lista(v):
        return v if isinstance(v, list) else []

    dores = _lista(out.get("dores_dominantes"))
    dor_top = dores[0] if dores and isinstance(dores[0], dict) else {}

    brechas = [s for s in _lista(out.get("servicos_nao_oferecidos")) if isinstance(s, str)]

    entrantes = out.get("entrantes_cnpj_90d")
    entrantes_total = None
    if isinstance(entrantes, dict):
        entrantes_total = (
            entrantes.get("total")
            or entrantes.get("count")
            or (
                len(empresas) if (empresas := entrantes.get("empresas")) and isinstance(empresas, list) else None
            )
        )
    elif isinstance(entrantes, list):
        entrantes_total = len(entrantes)

    alternativos = _lista(out.get("bairros_alternativos"))
    alt_motivo = None
    if alternativos and isinstance(alternativos[0], dict):
        alt_motivo = alternativos[0].get("motivo")

    cenarios = out.get("viabilidade_3_cenarios")
    payback_mid = None
    if isinstance(cenarios, dict) and isinstance(cenarios.get("mid"), dict):
        payback_mid = cenarios["mid"].get("payback_meses") or cenarios["mid"].get("payback")

    return {
        "bairro_analisado": bairro_analisado,
        "dor_top": {"dor": dor_top.get("dor"), "mencoes": dor_top.get("mencoes")} if dor_top else None,
        "dores_total": len(dores) or None,
        "brechas_amostra": brechas[:2] or None,
        "brechas_total": len(brechas) or None,
        "entrantes_90d_total": entrantes_total,
        "aluguel_m2": {
            "min": out.get("aluguel_min_m2"),
            "max": out.get("aluguel_max_m2"),
            "mediana": out.get("aluguel_mediana_m2"),
        } if out.get("aluguel_mediana_m2") or out.get("aluguel_min_m2") else None,
        "bairro_alternativo_motivo": alt_motivo,
        "payback_mid_meses": payback_mid,
    }


# Montar em api.py:
#   from backend.routers.site_agent import router_site_agent
#   app.include_router(router_site_agent)
