"""
Enriquecimento de entrantes CNPJ: razão social, bairro, e-mail/telefone da PJ e QSA.

Fontes (ordem):
1. Colunas já gravadas em cnpj_fitness_estabelecimentos (RFB)
2. cache Supabase cnpj_contato_cache
3. ReceitaWS (3 req/min) — cartão CNPJ + QSA
4. ViaCEP — bairro quando CEP existe e bairro vazio
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from tools.contact_tools import buscar_cnpj

RECEITA_MIN_INTERVAL_SEC = 21.0  # ~3 req/min
_last_receita_call: float = 0.0

_ADMIN_QUAL_PATTERNS = (
    "administrador",
    "socio-administrador",
    "sócio-administrador",
    "49-socio",
    "49-",
)


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _pick_socio_administrador(socios: list[dict]) -> dict | None:
    if not socios:
        return None
    for s in socios:
        qual = (s.get("qualificacao") or s.get("qual") or "").lower()
        if any(p in qual for p in _ADMIN_QUAL_PATTERNS):
            return {
                "nome": (s.get("nome") or "").strip() or None,
                "qualificacao": (s.get("qualificacao") or s.get("qual") or "").strip() or None,
                "email": (s.get("email") or "").strip() or None,
                "telefone": (s.get("telefone") or "").strip() or None,
            }
    first = socios[0]
    return {
        "nome": (first.get("nome") or "").strip() or None,
        "qualificacao": (first.get("qualificacao") or first.get("qual") or "").strip() or None,
        "email": (first.get("email") or "").strip() or None,
        "telefone": (first.get("telefone") or "").strip() or None,
    }


def _supabase_client():
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _cache_get(cnpj: str) -> dict | None:
    sb = _supabase_client()
    if not sb:
        return None
    cnpj_limpo = _digits(cnpj)
    try:
        res = (
            sb.table("cnpj_contato_cache")
            .select("*")
            .eq("cnpj", cnpj_limpo)
            .maybe_single()
            .execute()
        )
        row = res.data
        if not isinstance(row, dict):
            return None
        exp = row.get("expires_at")
        if exp:
            exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if exp_dt < datetime.now(timezone.utc):
                return None
        return row
    except Exception:
        return None


def _cache_put(cnpj: str, payload: dict) -> None:
    sb = _supabase_client()
    if not sb:
        return
    cnpj_limpo = _digits(cnpj)
    ttl_days = int(os.getenv("CNPJ_CONTATO_CACHE_TTL_DIAS", "90") or "90")
    expires = datetime.now(timezone.utc) + timedelta(days=max(ttl_days, 7))
    row = {
        "cnpj": cnpj_limpo,
        "razao_social": payload.get("razao_social"),
        "nome_fantasia": payload.get("nome_fantasia"),
        "email": payload.get("email"),
        "telefone": payload.get("telefone"),
        "bairro": payload.get("bairro"),
        "municipio": payload.get("municipio"),
        "uf": payload.get("uf"),
        "qsa": payload.get("qsa") or [],
        "socio_administrador": payload.get("socio_administrador"),
        "fonte": payload.get("fonte") or "receitaws",
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires.isoformat(),
    }
    try:
        sb.table("cnpj_contato_cache").upsert(row, on_conflict="cnpj").execute()
    except Exception:
        pass


def _throttle_receita() -> None:
    global _last_receita_call
    now = time.monotonic()
    wait = RECEITA_MIN_INTERVAL_SEC - (now - _last_receita_call)
    if wait > 0:
        time.sleep(wait)
    _last_receita_call = time.monotonic()


def _fetch_receita(cnpj: str) -> dict:
    _throttle_receita()
    return buscar_cnpj(cnpj)


def _viacep_bairro(cep: str) -> str | None:
    cep8 = _digits(cep)[:8]
    if len(cep8) != 8:
        return None
    try:
        with httpx.Client(timeout=8) as c:
            r = c.get(f"https://viacep.com.br/ws/{cep8}/json/").json()
        if r.get("erro"):
            return None
        b = (r.get("bairro") or "").strip()
        return b or None
    except Exception:
        return None


def _normalize_telefone_estabelecimento(ddd: str, tel: str) -> str | None:
    d = _digits(ddd)
    t = _digits(tel)
    if not t:
        return None
    if d and not t.startswith(d):
        full = d + t
    else:
        full = t
    if len(full) >= 10:
        return full
    return None


def enriquecimento_habilitado() -> bool:
    return os.getenv("CNPJ_ENRIQUECER_QSA", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def apollo_no_pipeline_habilitado() -> bool:
    """Apollo só no pipeline se APOLLO_ENRICH_ON_PIPELINE=1 (default: desligado)."""
    return os.getenv("APOLLO_ENRICH_ON_PIPELINE", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _aplicar_apollo_no_socio(
    socio_adm: dict,
    apollo_data: dict,
) -> None:
    """Mescla resultado Apollo no bloco socio_administrador."""
    if apollo_data.get("nome"):
        socio_adm.setdefault("nome", apollo_data.get("nome"))
    if apollo_data.get("email_direto"):
        socio_adm["email_direto"] = apollo_data.get("email_direto")
    if apollo_data.get("telefone_direto"):
        socio_adm["telefone"] = apollo_data.get("telefone_direto")
    if apollo_data.get("linkedin_url"):
        socio_adm["linkedin_url"] = apollo_data.get("linkedin_url")
    if apollo_data.get("empresa_match"):
        socio_adm["empresa_match_apollo"] = apollo_data.get("empresa_match")
    if apollo_data.get("fonte_apollo"):
        socio_adm["fonte_apollo"] = apollo_data.get("fonte_apollo")
    socio_adm["contato_individual_disponivel"] = bool(
        socio_adm.get("email_direto")
        or socio_adm.get("telefone")
        or socio_adm.get("linkedin_url")
    )


def _apollo_tem_contato(data: dict | None) -> bool:
    if not data:
        return False
    return bool(
        data.get("email_direto")
        or data.get("linkedin_url")
        or data.get("telefone_direto")
    )


def _chamar_apollo_para_entrante(
    razao: str,
    socio_adm: dict,
    *,
    cidade: str | None = None,
) -> dict | None:
    import inspect

    from tools.apollo_enrichment import (
        enriquecer_empresa_com_apollo,
        enriquecer_socio_qsa_com_apollo,
    )

    nome_qsa = (socio_adm.get("nome") or "").strip() or None
    sig = inspect.signature(enriquecer_empresa_com_apollo)
    if "nome_socio_qsa" in sig.parameters:
        return enriquecer_empresa_com_apollo(
            razao,
            cidade=cidade,
            nome_socio_qsa=nome_qsa,
        )

    out = enriquecer_empresa_com_apollo(razao, cidade=cidade)
    if nome_qsa and not _apollo_tem_contato(out):
        qsa_out = enriquecer_socio_qsa_com_apollo(razao.strip(), nome_qsa, cidade)
        if _apollo_tem_contato(qsa_out):
            return qsa_out
    return out


def max_enriquecimentos_por_lista() -> int:
    try:
        return max(0, min(int(os.getenv("CNPJ_ENRIQUECER_MAX", "20") or "20"), 50))
    except ValueError:
        return 20


def fetch_cartao_cnpj(
    cnpj: str,
    *,
    use_cache: bool = True,
    usar_apollo: bool | None = None,
) -> dict:
    """Cartão CNPJ + QSA (cache → ReceitaWS)."""
    cached = _cache_get(cnpj) if use_cache else None
    if cached:
        return {
            "status": "ok",
            "fonte": cached.get("fonte") or "cache",
            "razao_social": cached.get("razao_social"),
            "nome_fantasia": cached.get("nome_fantasia"),
            "email": cached.get("email"),
            "telefone": cached.get("telefone"),
            "bairro": cached.get("bairro"),
            "municipio": cached.get("municipio"),
            "uf": cached.get("uf"),
            "qsa": cached.get("qsa") or [],
            "socio_administrador": cached.get("socio_administrador"),
        }

    data = _fetch_receita(cnpj)
    if data.get("erro"):
        return {"status": "erro", "motivo": data.get("erro")}

    socios = data.get("socios") or []
    socio_adm = _pick_socio_administrador(socios)
    # ReceitaWS não expõe e-mail/telefone por sócio — lacuna explícita
    if socio_adm and not socio_adm.get("email") and not socio_adm.get("telefone"):
        socio_adm["contato_individual_disponivel"] = False

    parts = (data.get("endereco") or "").split(" - ")
    bairro_rs = None
    if len(parts) >= 2:
        bairro_rs = parts[0].split(",")[-1].strip() if "," in parts[0] else None

    payload = {
        "status": "ok",
        "fonte": "receitaws",
        "razao_social": (data.get("razao_social") or "").strip() or None,
        "nome_fantasia": (data.get("nome_fantasia") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "telefone": (data.get("telefone") or "").strip() or None,
        "bairro": bairro_rs,
        "qsa": socios,
        "socio_administrador": socio_adm,
    }

    # Apollo: só com flag explícita (UI) ou APOLLO_ENRICH_ON_PIPELINE=1
    do_apollo = usar_apollo if usar_apollo is not None else apollo_no_pipeline_habilitado()
    if do_apollo and os.getenv("APOLLO_API_KEY") and socio_adm:
        razao = payload.get("razao_social") or payload.get("nome_fantasia")
        if razao:
            try:
                apollo_data = _chamar_apollo_para_entrante(razao, socio_adm)
                if apollo_data:
                    _aplicar_apollo_no_socio(socio_adm, apollo_data)
            except Exception as e:
                print(f"[Apollo Enrichment Error] {e}")

    _cache_put(cnpj, payload)
    return payload


def aplicar_enriquecimento_entrante(
    ent: dict[str, Any],
    *,
    cartao: dict | None = None,
    viacep: bool = True,
) -> dict[str, Any]:
    """
    Garante razão social, bairro, nome de exibição e bloco de contato/QSA.
    Não remove campos existentes; preenche lacunas.
    """
    out = dict(ent)
    cnpj = out.get("cnpj") or ""

    razao = (out.get("razao_social") or "").strip()
    fantasia = (out.get("nome_fantasia") or "").strip()
    bairro = (out.get("bairro") or "").strip()

    if cartao and cartao.get("status") == "ok":
        razao = razao or (cartao.get("razao_social") or "").strip()
        fantasia = fantasia or (cartao.get("nome_fantasia") or "").strip()
        bairro = bairro or (cartao.get("bairro") or "").strip()
        out.setdefault("email_empresa", (cartao.get("email") or "").strip() or None)
        out.setdefault("telefone_empresa", (cartao.get("telefone") or "").strip() or None)
        out["qsa"] = cartao.get("qsa") or out.get("qsa") or []
        socio = cartao.get("socio_administrador")
        if socio:
            out["socio_administrador"] = socio
            out.setdefault(
                "email_socio_administrador",
                socio.get("email_direto") or socio.get("email") or None,
            )
            out.setdefault(
                "telefone_socio_administrador",
                socio.get("telefone") or None,
            )
            out.setdefault(
                "linkedin_url",
                socio.get("linkedin_url") or None,
            )

    if viacep and not bairro and out.get("cep"):
        bairro_v = _viacep_bairro(str(out.get("cep")))
        if bairro_v:
            bairro = bairro_v
            out["bairro_fonte"] = out.get("bairro_fonte") or "viacep"

    from tools.cnpj_fitness_tools import nome_exibicao_cnpj

    nome_exib, fantasia_out, inferido_de = nome_exibicao_cnpj(fantasia, razao)
    if inferido_de:
        out["nome_fantasia_inferido_de"] = inferido_de

    out["razao_social"] = razao or None
    out["nome_fantasia"] = fantasia_out
    out["nome_exibicao"] = nome_exib
    out["bairro"] = bairro or None
    out["dados_completos"] = bool(razao and bairro and out.get("nome_exibicao"))
    out.setdefault("contato_validado", False)
    out.setdefault("contato_validado_em", None)
    out.setdefault("contato_validado_por", None)
    # legado: mantém campo para mocks antigos
    out["razao_social_indisponivel"] = not bool(razao)

    lacunas: list[str] = []
    if not razao:
        lacunas.append("razao_social")
    if not bairro:
        lacunas.append("bairro")
    if not out.get("email_empresa"):
        lacunas.append("email_empresa")
    if not out.get("telefone_empresa"):
        lacunas.append("telefone_empresa")
    if not out.get("email_socio_administrador"):
        lacunas.append("email_socio_administrador")
    if not out.get("telefone_socio_administrador"):
        lacunas.append("telefone_socio_administrador")
    if lacunas:
        out["lacunas_contato"] = lacunas

    return out


def enriquecer_entrante_unico(
    ent: dict[str, Any],
    *,
    usar_apollo: bool = True,
    max_receita: int | None = 1,
    forcar_receita: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Enriquece um entrante (Receita + Apollo opcional). Uso: ação manual na UI."""
    lista, meta = enriquecer_entrantes(
        [ent],
        max_receita=max_receita,
        usar_apollo=usar_apollo,
        forcar_receita=forcar_receita,
    )
    return (lista[0] if lista else ent), meta


def _entrante_precisa_fetch_receita(ent: dict[str, Any]) -> bool:
    precisa_rs = not (ent.get("razao_social") or "").strip()
    precisa_contato = not ent.get("email_empresa") and not ent.get("telefone_empresa")
    qsa = ent.get("qsa")
    precisa_qsa = not qsa or (isinstance(qsa, list) and len(qsa) == 0)
    precisa_socio = not ent.get("socio_administrador")
    precisa_email_socio = not (ent.get("email_socio_administrador") or "").strip()
    return bool(
        ent.get("cnpj")
        and (
            precisa_rs
            or precisa_contato
            or precisa_qsa
            or precisa_socio
            or precisa_email_socio
        )
    )


def enriquecer_entrantes(
    entrantes: list[dict[str, Any]],
    *,
    max_receita: int | None = None,
    usar_apollo: bool | None = None,
    forcar_receita: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Enriquece lista de entrantes. Respeita limite de chamadas ReceitaWS.
    Retorna (lista, meta).
    """
    if not enriquecimento_habilitado():
        return [
            aplicar_enriquecimento_entrante(e, cartao=None, viacep=True) for e in entrantes
        ], {"enriquecimento": "desligado"}

    limite = max_receita if max_receita is not None else max_enriquecimentos_por_lista()
    receita_calls = 0
    cache_hits = 0
    apollo_tentado = False
    apollo_ok = False
    receita_fonte: str | None = None
    receita_motivo: str | None = None
    out_list: list[dict] = []

    do_apollo = usar_apollo if usar_apollo is not None else apollo_no_pipeline_habilitado()
    apollo_key = bool((os.getenv("APOLLO_API_KEY") or "").strip())

    for ent in entrantes:
        cnpj = ent.get("cnpj") or ""
        cartao: dict | None = None
        deve_buscar = forcar_receita or _entrante_precisa_fetch_receita(ent)

        if deve_buscar and cnpj:
            cached = _cache_get(cnpj)
            if cached:
                cache_hits += 1
                receita_fonte = "cache"
                cartao = {
                    "status": "ok",
                    "fonte": "cache",
                    "razao_social": cached.get("razao_social"),
                    "nome_fantasia": cached.get("nome_fantasia"),
                    "email": cached.get("email"),
                    "telefone": cached.get("telefone"),
                    "bairro": cached.get("bairro"),
                    "qsa": cached.get("qsa"),
                    "socio_administrador": cached.get("socio_administrador"),
                }
                socio = cartao.get("socio_administrador") or {}
                razao = (cartao.get("razao_social") or cartao.get("nome_fantasia") or "").strip()
                if (
                    forcar_receita
                    and do_apollo
                    and apollo_key
                    and razao
                    and socio
                    and not socio.get("email_direto")
                    and not socio.get("linkedin_url")
                    and not socio.get("telefone")
                ):
                    apollo_tentado = True
                    try:
                        apollo_data = _chamar_apollo_para_entrante(razao, socio)
                        if apollo_data:
                            apollo_ok = True
                            _aplicar_apollo_no_socio(socio, apollo_data)
                            cartao["socio_administrador"] = socio
                    except Exception as exc:
                        receita_motivo = f"apollo_erro:{exc}"
            elif receita_calls < limite:
                cartao = fetch_cartao_cnpj(cnpj, usar_apollo=usar_apollo)
                if cartao.get("status") == "ok":
                    receita_calls += 1
                    receita_fonte = cartao.get("fonte") or "receitaws"
                    socio = cartao.get("socio_administrador") or {}
                    if do_apollo and apollo_key and socio:
                        apollo_tentado = True
                        apollo_ok = bool(
                            socio.get("email_direto")
                            or socio.get("linkedin_url")
                            or socio.get("telefone")
                        )
                else:
                    receita_motivo = cartao.get("motivo") or cartao.get("erro") or "receita_falhou"
            else:
                receita_motivo = "limite_receita_atingido"
        elif not cnpj:
            receita_motivo = "cnpj_ausente"
        else:
            receita_motivo = "dados_ja_presentes"

        out_list.append(
            aplicar_enriquecimento_entrante(ent, cartao=cartao, viacep=True)
        )

    meta: dict[str, Any] = {
        "enriquecimento": "ok",
        "receita_chamadas": receita_calls,
        "cache_hits": cache_hits,
        "limite_receita": limite,
        "receita_fonte": receita_fonte,
        "receita_motivo": receita_motivo,
        "apollo_habilitado": do_apollo and apollo_key,
        "apollo_tentado": apollo_tentado,
        "apollo_ok": apollo_ok,
        "forcar_receita": forcar_receita,
    }
    return out_list, meta
