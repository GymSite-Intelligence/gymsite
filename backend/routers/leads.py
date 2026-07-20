"""
Router /api/leads — captura de leads da landing page (gym-insight-hub).

Recebe os dados do formulario "Analise gratuita" / agente "Diagnostico GymSite",
persiste em `leads` (Supabase) e dispara o sync com o Apollo de forma assincrona
(best-effort, nunca bloqueia a resposta ao visitante).

Este endpoint e PUBLICO (sem JWT) por design: a landing e anonima. A protecao
contra abuso fica a cargo do RateLimitMiddleware (api.py) + validacao Pydantic.

Tabela `leads` — ver db/migrations/0001_leads.sql.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from supabase import create_client

from tools.db_schema import tbl

logger = logging.getLogger("gymsite.leads")

router = APIRouter(prefix="/api/leads", tags=["Leads — Landing"])

_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"
_FONTE_DEFAULT = "landing-getgymsite"


def _sb():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase nao configurado")
    return create_client(url, key)


def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


class LeadInput(BaseModel):
    """Payload do formulario da landing. Campos espelham o modal do agente."""

    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    telefone: Optional[str] = Field(default=None, max_length=40)
    cidade: Optional[str] = Field(default=None, max_length=120)
    bairro: Optional[str] = Field(default=None, max_length=120)
    # "vou_abrir" | "ja_opero" — etapa do funil capturada pelo agente
    perfil: Optional[str] = Field(default=None, max_length=40)
    empresa: Optional[str] = Field(default=None, max_length=160)
    mensagem: Optional[str] = Field(default=None, max_length=2000)
    # rastreio de campanha (preenchido pelo front via querystring utm_*)
    utm_source: Optional[str] = Field(default=None, max_length=120)
    utm_medium: Optional[str] = Field(default=None, max_length=120)
    utm_campaign: Optional[str] = Field(default=None, max_length=160)
    fonte: str = Field(default=_FONTE_DEFAULT, max_length=80)


class LeadResposta(BaseModel):
    id: str
    status: str = "recebido"


def _persistir_lead(sb, data: LeadInput) -> dict:
    registro = {
        "org_id": os.getenv("SUPABASE_GYMSITE_ORG_ID", _DEFAULT_ORG_ID),
        "nome": data.nome.strip(),
        "email": str(data.email).lower().strip(),
        "telefone": _digits(data.telefone) or None,
        "cidade": (data.cidade or "").strip() or None,
        "bairro": (data.bairro or "").strip() or None,
        "perfil": data.perfil,
        "empresa": (data.empresa or "").strip() or None,
        "mensagem": (data.mensagem or "").strip() or None,
        "utm_source": data.utm_source,
        "utm_medium": data.utm_medium,
        "utm_campaign": data.utm_campaign,
        "fonte": data.fonte,
        "apollo_sync_status": "pendente",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = tbl(sb, "leads").insert(registro).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Falha ao gravar lead")
    return res.data[0]


def _sync_apollo_bg(lead_id: str, data: LeadInput) -> None:
    """Roda no BackgroundTasks — best-effort, isolado de falhas."""
    try:
        from tools.apollo_client import sync_lead_to_apollo

        resultado = sync_lead_to_apollo(
            nome=data.nome,
            email=str(data.email),
            telefone=_digits(data.telefone) or None,
            empresa=data.empresa,
            cidade=data.cidade,
            bairro=data.bairro,
            perfil=data.perfil,
            fonte=data.fonte,
        )
        if resultado.get("ok"):
            if resultado.get("sequence_enrolled"):
                status = "sincronizado_sequencia"
            elif resultado.get("sequence_id"):
                status = "sincronizado_sem_sequencia"
            else:
                status = "sincronizado"
        else:
            status = "erro"
        try:
            tbl(_sb(), "leads").update({
                "apollo_sync_status": status,
                "apollo_contact_id": resultado.get("contact_id"),
                "apollo_synced_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", lead_id).execute()
        except Exception as e:  # noqa: BLE001
            logger.warning("lead %s: falha ao gravar status Apollo: %s", lead_id, e)
    except Exception as e:  # noqa: BLE001
        logger.warning("lead %s: sync Apollo falhou (segue): %s", lead_id, e)
        try:
            tbl(_sb(), "leads").update(
                {"apollo_sync_status": "erro"}
            ).eq("id", lead_id).execute()
        except Exception:
            pass


@router.post("", response_model=LeadResposta, status_code=201)
async def criar_lead(
    data: LeadInput,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Captura um lead da landing e agenda o sync com o Apollo."""
    sb = _sb()
    registro = _persistir_lead(sb, data)
    lead_id = registro["id"]

    background_tasks.add_task(_sync_apollo_bg, lead_id, data)

    logger.info(
        "lead recebido id=%s email=%s perfil=%s fonte=%s",
        lead_id, registro.get("email"), data.perfil, data.fonte,
    )
    return LeadResposta(id=lead_id, status="recebido")
