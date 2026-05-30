"""
Engine — orquestração do módulo de prospecção.

Fluxo:
  1. fetch  → matcher.match_opportunities()
  2. enrich → enricher.enrich_opportunity()
  3. persist → UPSERT em oportunidades_prospeccao (idempotente por cnpj+cno)
  4. webhook → webhook.send_opportunity_webhook() para score >= threshold
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from supabase import create_client

from prospecting.config import Config
from prospecting.matcher import match_opportunities
from prospecting.enricher import enrich_opportunity
from prospecting.webhook import send_opportunity_webhook


def _get_client():
    if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios.")
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)


def run_prospeccao(
    *,
    cidade: str,
    uf: str = "CE",
    dias: int = 90,
    limit: int = 500,
    cno_dir: Path | None = None,
    org_id: str | None = None,
    webhook_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Executa o pipeline completo de prospecção para um município.

    Retorna dict com estatísticas da execução.
    """
    client = _get_client()
    oportunidades = match_opportunities(
        cidade=cidade,
        uf=uf,
        dias=dias,
        limit=limit,
        cno_dir=cno_dir,
    )

    stats = {
        "total_match": len(oportunidades),
        "qualificados": 0,
        "persistidos": 0,
        "webhooks_entregues": 0,
        "webhooks_falhos": 0,
        "webhooks_skipped": 0,
    }

    for opp in oportunidades:
        # Enriquecimento
        enrich_opportunity(opp)

        # Qualificação por score
        score = opp.get("score_match") or 0.0
        if score < Config.SCORE_MATCH_MIN:
            continue
        stats["qualificados"] += 1

        # Adiciona metadatas de execução
        opp["cidade"] = cidade
        opp["uf"] = uf
        opp["org_id"] = org_id
        if webhook_url:
            opp["webhook_url"] = webhook_url

        # Persistência (UPSERT por cnpj + cno)
        if not dry_run:
            persisted = _upsert_oportunidade(opp, client)
            if persisted:
                stats["persistidos"] += 1
                opp.update(persisted)  # injeta id, created_at, etc.

            # Webhook
            if opp.get("id"):
                result = send_opportunity_webhook(opp, client=client)
                status = result.get("status")
                if status == "entregue":
                    stats["webhooks_entregues"] += 1
                    _update_status(opp["id"], "webhook_enviado", client)
                elif status == "idempotente":
                    stats["webhooks_skipped"] += 1
                else:
                    stats["webhooks_falhos"] += 1
        else:
            stats["persistidos"] += 1

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf,
        "dry_run": dry_run,
        "stats": stats,
        "oportunidades": oportunidades if dry_run else None,
    }


def _upsert_oportunidade(opp: dict[str, Any], client) -> dict[str, Any] | None:
    """
    Insere ou atualiza oportunidade baseada em cnpj + cno.
    Retorna o registro completo (com id) se sucesso.
    """
    cnpj = opp.get("cnpj")
    cno = opp.get("cno")
    if not cnpj:
        return None

    try:
        # Verifica existente
        query = client.table("oportunidades_prospeccao").select("*").eq("cnpj", cnpj)
        if cno:
            query = query.eq("cno", cno)
        else:
            query = query.is_("cno", "null")

        existing = query.limit(1).execute()

        row = {
            "org_id": opp.get("org_id"),
            "cnpj": cnpj,
            "cno": cno,
            "municipio_codigo": opp.get("municipio_codigo"),
            "cidade": opp.get("cidade"),
            "uf": opp.get("uf"),
            "razao_social": opp.get("razao_social"),
            "nome_fantasia": opp.get("nome_fantasia"),
            "segmento_operacao": opp.get("segmento_operacao"),
            "data_inicio_atividade": opp.get("data_inicio_atividade"),
            "situacao_cadastral": opp.get("situacao_cadastral"),
            "endereco_cnpj": opp.get("endereco_cnpj"),
            "contato_cnpj": opp.get("contato_cnpj"),
            "nome_obra": opp.get("nome_obra"),
            "situacao_obra": opp.get("situacao_obra"),
            "area_total_m2": opp.get("area_total_m2"),
            "data_inicio_obra": opp.get("data_inicio_obra"),
            "data_situacao_obra": opp.get("data_situacao_obra"),
            "endereco_cno": opp.get("endereco_cno"),
            "score_match": opp.get("score_match"),
            "motivo_match": opp.get("motivo_match"),
            "status": "qualificado",
            "prioridade": opp.get("prioridade", "media"),
            "webhook_url": opp.get("webhook_url"),
        }

        if existing.data:
            record = existing.data[0]
            record_id = record["id"]
            # Atualiza preservando status avançado do pipeline
            if record.get("status") in ("engajado", "fechado", "descartado"):
                row.pop("status", None)
            client.table("oportunidades_prospeccao").update(row).eq("id", record_id).execute()
            return record
        else:
            result = client.table("oportunidades_prospeccao").insert(row).execute()
            if result.data:
                return result.data[0]
    except Exception as e:
        print(f"[prospeccao] Erro ao persistir oportunidade {cnpj}: {e}")

    return None


def _update_status(opp_id: str, status: str, client) -> None:
    try:
        client.table("oportunidades_prospeccao").update({"status": status}).eq("id", opp_id).execute()
    except Exception:
        pass


def list_oportunidades(
    *,
    cidade: str | None = None,
    uf: str | None = None,
    status: str | None = None,
    prioridade: str | None = None,
    score_min: float | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Lista oportunidades persistidas com filtros."""
    client = _get_client()
    query = client.table("oportunidades_prospeccao").select("*")

    if cidade:
        query = query.eq("cidade", cidade)
    if uf:
        query = query.eq("uf", uf)
    if status:
        query = query.eq("status", status)
    if prioridade:
        query = query.eq("prioridade", prioridade)
    if score_min is not None:
        query = query.gte("score_match", score_min)

    query = query.order("score_match", desc=True).limit(limit).offset(offset)
    result = query.execute()
    return result.data or []


def get_oportunidade(id: str) -> dict[str, Any] | None:
    """Retorna uma oportunidade pelo UUID."""
    client = _get_client()
    result = client.table("oportunidades_prospeccao").select("*").eq("id", id).limit(1).execute()
    return result.data[0] if result.data else None


class OportunidadeNotFoundError(Exception):
    pass


class WebhookDeliveryError(Exception):
    pass


def update_status(id: str, status: str) -> bool:
    """Atualiza status do pipeline. Se for webhook_enviado, dispara o webhook.

    Raises:
        OportunidadeNotFoundError: Oportunidade não existe.
        WebhookDeliveryError: Falha no envio do webhook.
    """
    client = _get_client()
    opp = get_oportunidade(id)
    if not opp:
        raise OportunidadeNotFoundError("Oportunidade não encontrada")

    if status == "webhook_enviado":
        res = send_opportunity_webhook(opp, client=client)
        if res.get("status") == "skipped":
            raise WebhookDeliveryError(res.get("motivo", "URL do webhook não configurada"))
        elif res.get("status") == "falhou":
            raise WebhookDeliveryError(f"Falha ao entregar webhook: {res.get('motivo')}")

    try:
        client.table("oportunidades_prospeccao").update({"status": status}).eq("id", id).execute()
        return True
    except Exception as e:
        print(f"[prospeccao] Erro ao atualizar status de {id}: {e}")
        return False



def reenviar_webhook(id: str) -> dict[str, Any]:
    """Reenvia webhook manualmente para uma oportunidade."""
    client = _get_client()
    opp = get_oportunidade(id)
    if not opp:
        return {"status": "erro", "motivo": "Oportunidade não encontrada"}
    return send_opportunity_webhook(opp, client=client)
