"""
Webhook client — envia oportunidades qualificadas para o Claw/Vectra.

Features:
- Retry exponencial (até 3 tentativas)
- Idempotência: verifica webhook_claw_log antes de reenviar
- Log estruturado em webhook_claw_log
- Timeout configurável
"""
from __future__ import annotations

import json
import time
from typing import Any

import requests

from prospecting.config import Config
from tools.telemetry import span
from tools.sanitize import mask_cnpj, mask_phone, mask_email


@span("prospeccao.webhook.send")
def send_opportunity_webhook(
    oportunidade: dict[str, Any],
    client=None,
) -> dict[str, Any]:
    """
    Envia webhook para o Claw. Retorna dict com status, http_status, resposta.
    """
    url = oportunidade.get("webhook_url") or Config.CLAW_WEBHOOK_URL
    if not url:
        return {
            "status": "skipped",
            "motivo": "CLAW_WEBHOOK_URL não configurado",
        }

    opp_id = oportunidade.get("id")
    evento = "prospeccao.oportunidade.qualificada"

    # Idempotência — verifica se já enviou com sucesso recente
    if _ja_enviado_com_sucesso(opp_id, evento, client):
        return {
            "status": "idempotente",
            "motivo": "Webhook já entregue com sucesso",
        }

    payload = _montar_payload(oportunidade)

    headers = {"Content-Type": "application/json"}
    if Config.CLAW_WEBHOOK_SECRET:
        headers["X-Claw-Secret"] = Config.CLAW_WEBHOOK_SECRET

    max_retries = Config.WEBHOOK_MAX_RETRIES
    timeout = Config.WEBHOOK_TIMEOUT_SECONDS

    last_error = None
    for tentativa in range(1, max_retries + 1):
        inicio = time.time()
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            duracao_ms = int((time.time() - inicio) * 1000)

            _log_webhook(
                oportunidade_id=opp_id,
                evento=evento,
                payload=payload,
                http_status=resp.status_code,
                resposta=resp.text[:2000],
                duracao_ms=duracao_ms,
                client=client,
            )

            # Persiste os detalhes da tentativa diretamente na oportunidade
            if client and opp_id:
                updates: dict[str, Any] = {
                    "webhook_resposta_http": resp.status_code,
                    "webhook_tentativas": tentativa,
                    "webhook_payload": payload,
                }
                if resp.status_code < 300:
                    from datetime import datetime, timezone
                    updates["webhook_enviado_at"] = datetime.now(timezone.utc).isoformat()
                try:
                    client.table("oportunidades_prospeccao").update(updates).eq("id", opp_id).execute()
                except Exception as db_err:
                    print(f"[webhook] Erro ao atualizar oportunidade {opp_id}: {db_err}")

            if resp.status_code < 300:
                return {
                    "status": "entregue",
                    "http_status": resp.status_code,
                    "tentativas": tentativa,
                }

            last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
            if tentativa < max_retries:
                time.sleep(2 ** tentativa)  # backoff exponencial

        except Exception as e:
            duracao_ms = int((time.time() - inicio) * 1000)
            last_error = str(e)
            _log_webhook(
                oportunidade_id=opp_id,
                evento=evento,
                payload=payload,
                http_status=None,
                resposta=last_error,
                duracao_ms=duracao_ms,
                client=client,
            )
            if client and opp_id:
                try:
                    client.table("oportunidades_prospeccao").update({
                        "webhook_resposta_http": None,
                        "webhook_tentativas": tentativa,
                        "webhook_payload": payload,
                    }).eq("id", opp_id).execute()
                except Exception as db_err:
                    print(f"[webhook] Erro ao atualizar oportunidade {opp_id}: {db_err}")
            if tentativa < max_retries:
                time.sleep(2 ** tentativa)

    return {
        "status": "falhou",
        "motivo": last_error,
        "tentativas": max_retries,
    }


def _montar_payload(opp: dict[str, Any]) -> dict[str, Any]:
    """Monta o payload canônico do webhook com sanitização LGPD."""
    contato = opp.get("contato_cnpj") or {}
    return {
        "event": "prospeccao.oportunidade.qualificada",
        "version": "1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": {
            "oportunidade_id": opp.get("id"),
            "cnpj": mask_cnpj(opp.get("cnpj")),
            "cno": opp.get("cno"),
            "razao_social": opp.get("razao_social"),
            "nome_fantasia": opp.get("nome_fantasia"),
            "nome_exibicao": opp.get("nome_exibicao"),
            "segmento": opp.get("segmento_operacao"),
            "cidade": opp.get("cidade"),
            "uf": opp.get("uf"),
            "endereco": opp.get("endereco_cnpj"),
            "obra": {
                "nome": opp.get("nome_obra"),
                "situacao": opp.get("situacao_obra"),
                "area_m2": opp.get("area_total_m2"),
                "data_inicio": opp.get("data_inicio_obra"),
                "data_situacao": opp.get("data_situacao_obra"),
            },
            "score_match": opp.get("score_match"),
            "motivo_match": opp.get("motivo_match"),
            "prioridade": opp.get("prioridade"),
            "contato": {
                "decision_maker": contato.get("decision_maker"),
                "cargo": contato.get("cargo"),
                "email": mask_email(contato.get("email")),
                "whatsapp": mask_phone(contato.get("whatsapp")),
                "linkedin": contato.get("linkedin"),
            },
            "projecao_receita": opp.get("projecao_receita"),
            "capacidade_matriculas": opp.get("capacidade_matriculas"),
        },
    }


def _ja_enviado_com_sucesso(
    oportunidade_id: str | None,
    evento: str,
    client=None,
) -> bool:
    """Verifica no Supabase se já houve entrega HTTP 2xx."""
    if not oportunidade_id or not client:
        return False
    try:
        res = (
            client.table("webhook_claw_log")
            .select("id")
            .eq("oportunidade_id", oportunidade_id)
            .eq("evento", evento)
            .not_.is_("http_status", "null")
            .gte("http_status", 200)
            .lt("http_status", 300)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def _log_webhook(
    *,
    oportunidade_id: str | None,
    evento: str,
    payload: dict[str, Any],
    http_status: int | None,
    resposta: str,
    duracao_ms: int,
    client=None,
) -> None:
    """Grava linha em webhook_claw_log."""
    if not client:
        return
    try:
        client.table("webhook_claw_log").insert(
            {
                "oportunidade_id": oportunidade_id,
                "evento": evento,
                "payload": payload,
                "http_status": http_status,
                "resposta": resposta,
                "duracao_ms": duracao_ms,
            }
        ).execute()
    except Exception:
        pass
