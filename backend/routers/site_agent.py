"""
Router /api/site-agent — Análise Gratuita PÚBLICA da landing (N3).

Conecta o ChatAgent (gym-insight-hub) ao pipeline determinístico de viabilidade:
visitante anônimo tem direito a 1 análise gratuita (mini-relatório).

Fluxo:
  POST /analise  → Turnstile + entitlement (1/email) + caps (IP/dia, global/dia)
                   + allowance SearchAPI → cria stub `relatorios` (user_id NULL,
                   org ANON, access_token) → enfileira o MESMO pipeline ADK.
  GET  /analise/{id}?token=  → polling; quando status='done' devolve o SUBSET free.

Segurança: endpoint público (sem JWT). Escrita/leitura via backend service_role
(RLS bloqueia anon). A leitura do resultado exige o access_token não-adivinhável.
Reusa, via import LAZY (evita circular com api.py): create_relatorio_stub,
_enqueue_ou_background, NovoRelatorioInput, _supabase_client.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from tools.turnstile import verificar_turnstile
from tools.db_schema import tbl  # roteia gymsite/shared (flags ON em prod; tbl(sb,) cru = public)

logger = logging.getLogger("gymsite.site_agent")

router_site_agent = APIRouter(prefix="/api/site-agent", tags=["site-agent — landing"])

_ANON_ORG_ID = "00000000-0000-0000-0000-0000000000a0"
_FONTE = "landing-getgymsite"
_CAP_IP_DIA = int(os.getenv("SITE_AGENT_CAP_IP_DIA") or "5")
_CAP_GLOBAL_DIA = int(os.getenv("SITE_AGENT_CAP_GLOBAL_DIA") or "100")
_ETA_MIN = 5


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


class ConversarSiteResposta(BaseModel):
    projeto_id: str
    mensagem: str
    sugestoes: list[str] = []
    pode_gerar_relatorio: bool = False
    dados_faltantes: list[str] = []


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

    # 1. Anti-bot (fail-closed — o run gasta dinheiro).
    if not await verificar_turnstile(data.turnstile_token, ip):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Verificação anti-bot falhou.")

    sb = _sb()

    # 2. Entitlement: 1 grátis por email.
    if _email_ja_usou(sb, data.email):
        return AnaliseResposta(
            status="quota_used",
            mensagem="Você já usou sua análise gratuita. Fale com nosso time para o relatório completo.",
        )

    # 3. Caps (IP/dia, global/dia) e 4. allowance SearchAPI → overflow.
    if _cap_estourado(sb, ip) or _searchapi_sem_folga():
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
    tbl(sb,"relatorios").update({"access_token": access_token}).eq("id", relatorio_id).execute()

    # 6. Grava entitlement (unique(email) é o guard duro contra corrida).
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

@router_site_agent.post("/conversar", response_model=ConversarSiteResposta)
async def conversar_site(data: ConversarSiteInput, request: Request):
    """Chat de degustação da landing. Roda o MESMO engine do /consultor em
    modo_site (persona de captação + base de conhecimento + whitelist Tier 1 +
    antifatiamento hard). NÃO gera relatório — o release Tier 2 é o POST /analise
    (com entitlement 1/email), chamado pelo frontend quando o gate de formulário
    fecha. Turnstile (fail-closed) só na 1ª mensagem (criação da sessão).

    NOTA: cap de novas sessões por IP/dia ainda não enforced aqui (Turnstile +
    antifatiamento K=2 do engine + entitlement 1/email no /analise já limitam o
    custo). Follow-up: contador por IP na criação de sessão.
    """
    from services.consultor.consultor_engine import conversar, _ANON_SITE_USER_ID

    ip = _client_ip(request)
    nova_sessao = not data.projeto_id

    if nova_sessao and not await verificar_turnstile(data.turnstile_token, ip):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Verificação anti-bot falhou.")

    try:
        r = await conversar(
            mensagem=data.mensagem,
            usuario_id=_ANON_SITE_USER_ID,
            projeto_id=data.projeto_id,
            modo_site=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("conversar_site falhou")
        raise HTTPException(status_code=500, detail="Falha ao processar a conversa.") from e

    return ConversarSiteResposta(
        projeto_id=r["projeto_id"],
        mensagem=r["mensagem"],
        sugestoes=r.get("sugestoes", []),
        pode_gerar_relatorio=r.get("pode_gerar_relatorio", False),
        dados_faltantes=r.get("dados_faltantes", []),
    )


# ─── GET /api/site-agent/analise/{id} ─────────────────────────────────────────

@router_site_agent.get("/analise/{relatorio_id}")
async def status_analise(relatorio_id: str, token: str, request: Request):
    """Polling do status + entrega do mini-relatório (subset free) quando 'done'.

    Exige o access_token (não-adivinhável). Sem JWT — leitura via service_role.
    """
    sb = _sb()
    rel = (
        tbl(sb,"relatorios").select("id, status, access_token")
        .eq("id", relatorio_id).maybe_single().execute()
    )
    row = rel.data
    if not row or row.get("access_token") != token:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    st = row.get("status")
    if st != "done":
        # queued | running → ainda processando; failed/cancelled → erro amigável.
        if st in ("failed", "cancelled"):
            return {"status": "erro", "mensagem": "Não conseguimos concluir sua análise. Nosso time vai te contatar."}
        return {"status": "processando", "eta_min": _ETA_MIN}

    # SUBSET free (gateia A9/concorrentes completos/financeiro/PDF — só no pago).
    out = (
        tbl(sb,"relatorio_outputs")
        .select("veredito, resumo_executivo, nivel_saturacao, score_bairro, "
                "total_concorrentes_analisados, rating_medio_concorrentes, modelo_recomendado")
        .eq("relatorio_id", relatorio_id).maybe_single().execute()
    ).data or {}

    comp = (
        tbl(sb,"competidores")
        .select("nome, bairro_concorrente, rating_oficial")
        .eq("relatorio_id", relatorio_id)
        .order("rating_oficial", desc=True)
        .limit(3).execute()
    ).data or []

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
        },
        "upsell": "Veja o relatório completo: concorrência detalhada, planos/preços, cenários financeiros e posicionamento.",
    }


# Montar em api.py:
#   from backend.routers.site_agent import router_site_agent
#   app.include_router(router_site_agent)
