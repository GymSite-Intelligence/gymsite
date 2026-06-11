"""
apollo_crm_sync.py

Serviço de sincronização entre oportunidades_prospeccao (GymSite) e Apollo.io.

Responsabilidades:
  1. Enriquecer contato da oportunidade via Apollo People API
  2. Criar/atualizar Person + Account na plataforma Apollo
  3. Atualizar status de sync no banco (apollo_sync_status, apollo_person_id, etc.)
  4. Suportar sync unitário e bulk

Fluxo:
  oportunidade_prospeccao → enriquecimento Apollo → criação Person/Account Apollo
  → atualização Supabase → disponível para Apollo CRM Enrichment → CRM (SF/HubSpot)
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("gymsite.apollo_crm_sync")

_APOLLO_BASE = "https://api.apollo.io/api/v1"


def _apollo_headers() -> dict[str, str]:
    api_key = os.getenv("APOLLO_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("APOLLO_API_KEY não configurado")
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "x-api-key": api_key,
    }


def _apollo_post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST com JSON body para a API Apollo."""
    url = f"{_APOLLO_BASE}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers=_apollo_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _apollo_post_query(path: str, query_pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """POST com parâmetros na query string (padrão Apollo REST)."""
    qs = urllib.parse.urlencode(query_pairs)
    url = f"{_APOLLO_BASE}{path}?{qs}"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers=_apollo_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_http_error_body(e: urllib.error.HTTPError) -> str:
    try:
        return e.read().decode("utf-8", errors="replace")[:500]
    except Exception:
        return str(e.reason or e)


# ── Enriquecimento (reutiliza tools/apollo_enrichment) ──────────────────────


def _enriquecer_oportunidade(
    oportunidade: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """
    Enriquece contato da oportunidade usando Apollo Enrichment.
    Retorna (dados_enriquecidos, meta).
    """
    from tools.apollo_enrichment import enriquecer_empresa_com_apollo

    razao = oportunidade.get("razao_social") or oportunidade.get("nome_fantasia")
    cidade = oportunidade.get("cidade")
    contato_cnpj = oportunidade.get("contato_cnpj") or {}
    socio_nome = None
    if isinstance(contato_cnpj, dict):
        socio_nome = contato_cnpj.get("decision_maker")

    meta: dict[str, Any] = {"razao_social": razao, "cidade": cidade, "socio_nome": socio_nome}

    if not razao:
        meta["erro"] = "Razão social ausente"
        return None, meta

    try:
        enriched = enriquecer_empresa_com_apollo(
            organization_name=razao,
            cidade=cidade,
            nome_socio_qsa=socio_nome,
        )
        if enriched:
            meta["encontrado"] = True
            meta["campos"] = [k for k, v in enriched.items() if v is not None]
            return enriched, meta
        else:
            meta["encontrado"] = False
            meta["erro"] = "Apollo não encontrou contato"
            return None, meta
    except Exception as e:
        meta["encontrado"] = False
        meta["erro"] = str(e)
        return None, meta


# ── Criação/Atualização no Apollo ───────────────────────────────────────────


def _criar_ou_atualizar_account(
    oportunidade: dict[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    """
    Cria ou localiza Account na plataforma Apollo.
    Retorna (account_id, meta).
    """
    razao = oportunidade.get("razao_social") or oportunidade.get("nome_fantasia")
    cnpj = oportunidade.get("cnpj")
    cidade = oportunidade.get("cidade")
    uf = oportunidade.get("uf")
    segmento = oportunidade.get("segmento_operacao")

    if not razao:
        return None, {"erro": "Razão social ausente para criar account"}

    # Primeiro tenta encontrar account existente
    try:
        search_res = _apollo_post_query(
            "/organizations/search",
            [
                ("q_organization_name", razao),
                ("per_page", "5"),
            ],
        )
        orgs = search_res.get("organizations") or []
        if orgs:
            # Usa a primeira match
            account_id = str(orgs[0].get("id"))
            return account_id, {"acao": "encontrada", "account_id": account_id}
    except urllib.error.HTTPError as e:
        body = _read_http_error_body(e)
        logger.warning("Apollo org search falhou: %s %s", e.code, body[:200])
    except Exception as e:
        logger.warning("Apollo org search erro: %s", e)

    # Tenta criar nova account
    payload: dict[str, Any] = {
        "name": razao,
        "custom_fields": {
            "gymsite_cnpj": cnpj,
            "gymsite_fonte": "GymSite Intelligence",
        },
    }
    if cidade:
        payload["city"] = cidade
    if uf:
        payload["state"] = uf
    if segmento:
        payload["industry"] = segmento

    try:
        create_res = _apollo_post_json("/organizations", payload)
        account_id = str(create_res.get("organization", {}).get("id"))
        if account_id and account_id != "None":
            return account_id, {"acao": "criada", "account_id": account_id}
    except urllib.error.HTTPError as e:
        body = _read_http_error_body(e)
        logger.warning("Apollo org create falhou: %s %s", e.code, body[:200])
        # Se 422 (já existe), tenta search novamente com variação
        if e.code == 422:
            return None, {"erro": f"Account já existe ou inválida: {body[:200]}"}
    except Exception as e:
        logger.warning("Apollo org create erro: %s", e)

    return None, {"erro": "Não foi possível criar ou encontrar account"}


def _criar_ou_atualizar_person(
    oportunidade: dict[str, Any],
    enriched: dict[str, Any] | None,
    account_id: str | None,
) -> tuple[str | None, dict[str, Any]]:
    """
    Cria ou localiza Person na plataforma Apollo.
    Retorna (person_id, meta).
    """
    contato_cnpj = oportunidade.get("contato_cnpj") or {}
    if not isinstance(contato_cnpj, dict):
        contato_cnpj = {}

    nome = (enriched or {}).get("nome") or contato_cnpj.get("decision_maker")
    email = (enriched or {}).get("email_direto") or contato_cnpj.get("email")
    telefone = (enriched or {}).get("telefone_direto") or contato_cnpj.get("telefone")
    linkedin = (enriched or {}).get("linkedin_url")
    cargo = (enriched or {}).get("cargo") or contato_cnpj.get("cargo") or "Sócio-administrador"

    if not nome:
        return None, {"erro": "Nome do contato ausente para criar person"}

    # Dados do GymSite para custom fields
    score = oportunidade.get("score_match")
    motivo = oportunidade.get("motivo_match")
    cidade = oportunidade.get("cidade")
    cnpj = oportunidade.get("cnpj")

    payload: dict[str, Any] = {
        "name": nome,
        "title": cargo,
        "custom_fields": {
            "gymsite_fonte": "GymSite Intelligence",
            "gymsite_cnpj": cnpj,
        },
    }

    if email:
        payload["email"] = email
    if telefone:
        payload["phone"] = telefone
    if linkedin:
        payload["linkedin_url"] = linkedin
    if account_id:
        payload["organization_id"] = account_id
    if score is not None:
        payload["custom_fields"]["gymsite_score"] = str(score)
    if motivo:
        payload["custom_fields"]["gymsite_motivo"] = motivo
    if cidade:
        payload["custom_fields"]["gymsite_cidade_analisada"] = cidade

    try:
        create_res = _apollo_post_json("/people", payload)
        person_id = str(create_res.get("person", {}).get("id"))
        if person_id and person_id != "None":
            return person_id, {"acao": "criada", "person_id": person_id}
    except urllib.error.HTTPError as e:
        body = _read_http_error_body(e)
        logger.warning("Apollo person create falhou: %s %s", e.code, body[:200])
        if e.code == 422:
            return None, {"erro": f"Person já existe ou inválida: {body[:200]}"}
    except Exception as e:
        logger.warning("Apollo person create erro: %s", e)

    # Fallback: tenta buscar person existente por email
    if email:
        try:
            search_res = _apollo_post_query(
                "/mixed_people/api_search",
                [
                    ("q_keywords", email),
                    ("per_page", "5"),
                ],
            )
            people = search_res.get("people") or []
            if people:
                person_id = str(people[0].get("id"))
                return person_id, {"acao": "encontrada_por_email", "person_id": person_id}
        except Exception:
            pass

    return None, {"erro": "Não foi possível criar ou encontrar person"}


# ── Sync principal ──────────────────────────────────────────────────────────


def sync_oportunidade(
    oportunidade: dict[str, Any],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """
    Sincroniza uma única oportunidade com Apollo.io.

    Args:
        oportunidade: dict com os campos da tabela oportunidades_prospeccao
        force: se True, refaz sync mesmo se já estiver 'synced'

    Returns:
        dict com ok, apollo_person_id, apollo_account_id, sync_status, enriched, meta
    """
    current_status = oportunidade.get("apollo_sync_status")
    if current_status == "synced" and not force:
        return {
            "ok": True,
            "skipped": True,
            "motivo": "Já sincronizado",
            "apollo_person_id": oportunidade.get("apollo_person_id"),
            "apollo_account_id": oportunidade.get("apollo_account_id"),
        }

    if not os.getenv("APOLLO_API_KEY"):
        return {"ok": False, "erro": "APOLLO_API_KEY não configurado"}

    # 1. Enriquecer contato
    enriched, meta_enrich = _enriquecer_oportunidade(oportunidade)

    # 2. Criar/Encontrar Account
    account_id, meta_account = _criar_ou_atualizar_account(oportunidade)

    # 3. Criar/Encontrar Person
    person_id, meta_person = _criar_ou_atualizar_person(oportunidade, enriched, account_id)

    # 4. Montar resultado
    result: dict[str, Any] = {
        "ok": bool(person_id),
        "apollo_person_id": person_id,
        "apollo_account_id": account_id,
        "enriched": enriched,
        "meta_enrich": meta_enrich,
        "meta_account": meta_account,
        "meta_person": meta_person,
    }

    if person_id:
        result["sync_status"] = "synced"
    elif account_id:
        result["sync_status"] = "failed"
        result["erro"] = meta_person.get("erro", "Person não criado")
    else:
        result["sync_status"] = "failed"
        result["erro"] = meta_account.get("erro", "Account e Person não criados")

    return result


def sync_batch(
    oportunidades: list[dict[str, Any]],
    *,
    force: bool = False,
    max_retry: int = 3,
    retry_delay_sec: int = 5,
) -> dict[str, Any]:
    """
    Sincroniza um lote de oportunidades com Apollo.io.

    Returns:
        dict com total, synced, failed, skipped, errors
    """
    total = len(oportunidades)
    synced = 0
    failed = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for opp in oportunidades:
        cnpj = opp.get("cnpj", "desconhecido")
        attempt = 0
        success = False

        while attempt < max_retry and not success:
            try:
                result = sync_oportunidade(opp, force=force)
                if result.get("skipped"):
                    skipped += 1
                elif result.get("ok"):
                    synced += 1
                else:
                    failed += 1
                    errors.append({"cnpj": cnpj, "motivo": result.get("erro", "Erro desconhecido")})
                success = True
            except Exception as e:
                attempt += 1
                logger.warning("Sync Apollo erro (tentativa %d/%d) para CNPJ %s: %s", attempt, max_retry, cnpj, e)
                if attempt < max_retry:
                    time.sleep(retry_delay_sec)
                else:
                    failed += 1
                    errors.append({"cnpj": cnpj, "motivo": str(e)})

    return {
        "total": total,
        "synced": synced,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
    }
