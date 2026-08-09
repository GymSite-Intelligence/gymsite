"""Router /api/explorar — mapa-first light Absorção + SearchAPI + OSM (W1).

Degustação do site: Turnstile + 1 pesquisa/e-mail (`explorar_gratuita`).
Não compartilha entitlement com especialistas (`analise_gratuita`).
Logado (JWT) pula cap. Sem score 0–10.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from tools.db_schema import tbl
from tools.explorar_analise import run_explorar_analise
from tools.maps_fallback import suggest_nominatim
from tools.turnstile import verificar_turnstile

logger = logging.getLogger("gymsite.explorar")

router = APIRouter(prefix="/api/explorar", tags=["explorar"])

_CAP_IP_DIA = int(os.getenv("SITE_AGENT_CAP_IP_DIA") or "5")
_CAP_GLOBAL_DIA = int(os.getenv("SITE_AGENT_CAP_GLOBAL_DIA") or "100")
_MSG_QUOTA = (
    "Você já usou a pesquisa grátis neste e-mail. "
    "Te avisamos por e-mail quando tiver novidade neste recorte."
)
_MSG_FILA = (
    "Estamos com alta demanda agora. Deixamos seu e-mail e falamos com você em breve."
)

Lente = Literal["500m", "1km", "bairro"]
TipoNegocio = Literal[
    "academia", "crossfit_box", "studio_pilates", "studio_funcional", "outro"
]


class ExplorarAnalisarInput(BaseModel):
    lat: float
    lng: float
    lente: Lente = "1km"
    tipo_negocio: TipoNegocio = "academia"
    cidade: Optional[str] = Field(default=None, max_length=120)
    bairro: Optional[str] = Field(default=None, max_length=120)
    uf: Optional[str] = Field(default=None, max_length=2)
    email: Optional[EmailStr] = None
    turnstile_token: Optional[str] = None
    endereco: Optional[str] = Field(default=None, max_length=240)
    publico_alvo: Optional[str] = Field(default=None, max_length=32)
    area_m2: Optional[float] = Field(default=None, ge=50, le=20000)
    idade_min: Optional[int] = Field(default=None, ge=0, le=120)
    idade_max: Optional[int] = Field(default=None, ge=0, le=120)


class ExplorarGeocodeInput(BaseModel):
    endereco: str = Field(min_length=3, max_length=240)


class ExplorarAutocompleteInput(BaseModel):
    q: str = Field(min_length=2, max_length=160)
    lat: Optional[float] = None
    lng: Optional[float] = None


class ExplorarIsocronasInput(BaseModel):
    lat: float
    lng: float
    modo: Literal["pe", "carro"] = "pe"


def _user_id_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        from api import _supabase_client

        sb = _supabase_client()
        user_resp = sb.auth.get_user(token)
        user = getattr(user_resp, "user", None)
        uid = getattr(user, "id", None) if user else None
        return str(uid) if uid else None
    except Exception:
        return None


def _email_ja_usou_explorar(email: str) -> bool:
    from backend.routers.site_agent import _sb

    res = (
        tbl(_sb(), "explorar_gratuita")
        .select("id")
        .eq("email", email.lower().strip())
        .limit(1)
        .execute()
    )
    return bool(res.data)


def _cap_explorar_estourado(ip: str | None) -> bool:
    from backend.routers.site_agent import _hoje_inicio_iso, _sb

    sb = _sb()
    inicio = _hoje_inicio_iso()
    glob = (
        tbl(sb, "explorar_gratuita")
        .select("id", count="exact")
        .gte("created_at", inicio)
        .execute()
    )
    if (glob.count or 0) >= _CAP_GLOBAL_DIA:
        logger.warning("cap explorar global/dia atingido (%s)", _CAP_GLOBAL_DIA)
        return True
    if ip:
        per_ip = (
            tbl(sb, "explorar_gratuita")
            .select("id", count="exact")
            .eq("ip", ip)
            .gte("created_at", inicio)
            .execute()
        )
        if (per_ip.count or 0) >= _CAP_IP_DIA:
            logger.warning("cap explorar IP/dia atingido ip=%s (%s)", ip, _CAP_IP_DIA)
            return True
    return False


def _gravar_entitlement(
    request: Request,
    email: str,
    ip: str | None,
    cidade: str | None,
    bairro: str | None,
    uf: str | None,
) -> None:
    from backend.routers.site_agent import _sb

    tbl(_sb(), "explorar_gratuita").insert(
        {
            "email": email.lower().strip(),
            "ip": ip,
            "user_agent": request.headers.get("user-agent"),
            "cidade": cidade,
            "bairro": bairro,
            "uf": uf,
        }
    ).execute()


def _liberar_entitlement(email: str) -> None:
    try:
        from backend.routers.site_agent import _sb

        tbl(_sb(), "explorar_gratuita").delete().eq(
            "email", email.lower().strip()
        ).execute()
    except Exception:
        logger.warning("liberar explorar_gratuita falhou", exc_info=True)


def _resumo_email_explorar(out: dict[str, Any], cidade: str | None, bairro: str | None) -> dict[str, Any]:
    absb = out.get("absorcao_margem_fresca") if isinstance(out.get("absorcao_margem_fresca"), dict) else {}
    rivais = out.get("concorrentes") if isinstance(out.get("concorrentes"), list) else []
    return {
        "cidade": cidade or out.get("cidade"),
        "bairro": bairro or out.get("bairro"),
        "label": out.get("base_espacial_label"),
        "leituras": absb.get("leituras") if isinstance(absb, dict) else {},
        "rivais": [
            {"nome": r.get("nome"), "dist_m": r.get("dist_m")}
            for r in rivais[:8]
            if isinstance(r, dict)
        ],
    }


def _enroll_resend_bg(
    email: str,
    cidade: str | None,
    bairro: str | None,
    resumo: dict[str, Any] | None = None,
) -> None:
    try:
        from tools.resend_client import enroll_explorar_lead

        enroll_explorar_lead(email, cidade, bairro, resumo=resumo)
    except Exception:
        logger.warning("resend explorar falhou (segue)", exc_info=True)


def _capturar_lead_explorar(
    email: str,
    cidade: str | None,
    bairro: str | None,
    background: BackgroundTasks | None = None,
    resumo: dict[str, Any] | None = None,
) -> None:
    try:
        from backend.routers.leads import LeadInput, _persistir_lead
        from backend.routers.site_agent import _sb

        lead = LeadInput(
            nome="Explorar mapa",
            email=email,
            cidade=cidade,
            bairro=bairro,
            fonte="explorar-site",
            utm_source="explorar",
        )
        _persistir_lead(_sb(), lead)
    except Exception:
        logger.warning("lead explorar não gravou (segue)", exc_info=True)
    if background is not None:
        background.add_task(_enroll_resend_bg, email, cidade, bairro, resumo)
    else:
        _enroll_resend_bg(email, cidade, bairro, resumo)


@router.post("/analisar")
async def explorar_analisar(
    data: ExplorarAnalisarInput,
    request: Request,
    background: BackgroundTasks,
) -> dict[str, Any]:
    from backend.routers.site_agent import _bypass_autorizado, _client_ip, _searchapi_sem_folga

    ip = _client_ip(request)
    user_id = _user_id_from_request(request)
    bypass = _bypass_autorizado(request, None, ip)
    email = str(data.email).lower().strip() if data.email else None
    reserved = False

    if not user_id and not bypass:
        if not await verificar_turnstile(data.turnstile_token, ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verificação anti-bot falhou.",
            )
        if not email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="E-mail obrigatório na degustação.",
            )
        if _email_ja_usou_explorar(email):
            _capturar_lead_explorar(email, data.cidade, data.bairro, background)
            return {"status": "quota_used", "mensagem": _MSG_QUOTA}
        if _cap_explorar_estourado(ip) or _searchapi_sem_folga():
            _capturar_lead_explorar(email, data.cidade, data.bairro, background)
            return {"status": "fila", "mensagem": _MSG_FILA}
        try:
            _gravar_entitlement(
                request, email, ip, data.cidade, data.bairro, data.uf
            )
            reserved = True
        except Exception:
            return {"status": "quota_used", "mensagem": _MSG_QUOTA}

    logger.info(
        "explorar analisar lente=%s user=%s ip=%s",
        data.lente,
        bool(user_id) or bypass,
        ip,
    )
    try:
        out = run_explorar_analise(
            lat=data.lat,
            lng=data.lng,
            lente=data.lente,
            tipo_negocio=data.tipo_negocio,
            cidade=data.cidade,
            bairro=data.bairro,
            uf=(data.uf.upper() if data.uf else None),
            endereco=data.endereco,
            publico_alvo=data.publico_alvo,
            area_candidato_m2=data.area_m2,
            idade_min=data.idade_min,
            idade_max=data.idade_max,
        )
    except Exception:
        if reserved and email:
            _liberar_entitlement(email)
        raise
    if reserved and email:
        _capturar_lead_explorar(
            email,
            data.cidade,
            data.bairro,
            background,
            resumo=_resumo_email_explorar(out, data.cidade, data.bairro),
        )
    out["status"] = "ok"
    return out


@router.post("/autocomplete")
async def explorar_autocomplete(data: ExplorarAutocompleteInput) -> dict[str, Any]:
    from tools.explorar_pin import filtrar_pins_nominatim

    q = data.q.strip()
    osm = filtrar_pins_nominatim(suggest_nominatim(q, data.lat, data.lng), q)
    if osm:
        return {"suggestions": osm, "fonte": "nominatim"}
    return {"suggestions": [], "fonte": "none"}


@router.post("/isocronas")
async def explorar_isocronas(data: ExplorarIsocronasInput) -> dict[str, Any]:
    from tools.osm_isocronas import fetch_isocronas

    try:
        return fetch_isocronas(data.lat, data.lng, data.modo)
    except Exception:
        logger.warning("isócrona real falhou", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Não deu para calcular o tempo a pé/carro neste ponto.",
        )


@router.post("/geocode")
async def explorar_geocode(data: ExplorarGeocodeInput) -> dict[str, Any]:
    from tools.explorar_pin import parse_lugar_explorar, resolver_explorar_pin
    from tools.maps_fallback import geocode_nominatim

    lugar = parse_lugar_explorar(data.endereco)
    pin = resolver_explorar_pin(data.endereco)
    if pin and pin.get("lat") is not None:
        return {
            "lat": pin["lat"],
            "lng": pin["lng"],
            "fonte": pin.get("fonte"),
            **lugar,
        }
    geo = geocode_nominatim(data.endereco)
    if not isinstance(geo, dict) or geo.get("error") or geo.get("lat") is None:
        raise HTTPException(status_code=404, detail="Endereço não encontrado.")
    return {
        "lat": float(geo["lat"]),
        "lng": float(geo["lng"]),
        "fonte": geo.get("fonte_geocode") or "nominatim",
        **lugar,
    }
