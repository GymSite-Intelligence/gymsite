# tools/redis_queue.py — Task Queue com Redis (Lists)
"""
Substitui BackgroundTasks por uma fila Redis persistente.
Jobs sobrevivem restart do container e podem ser reprocessados.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from typing import Any, Callable

from redis.exceptions import TimeoutError as RedisTimeoutError

from tools.redis_client import get_redis

logger = logging.getLogger("gymsite.api")
BRPOP_TIMEOUT_SEC = 30
QUEUE_KEY = "gymsite:queue"
PROCESSING_KEY = "gymsite:queue:processing"


class RedisQueue:
    """Fila simples com Redis + worker async."""

    def __init__(self, worker_func: Callable[[dict], Any], concurrency: int = 2):
        self.worker_func = worker_func
        self.concurrency = concurrency
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    async def enqueue(self, job: dict) -> str:
        """Adiciona job na fila."""
        r = await get_redis()
        job_id = f"job_{asyncio.get_event_loop().time()}_{id(job)}"
        payload = json.dumps({"id": job_id, **job})
        await r.lpush(QUEUE_KEY, payload)
        logger.info(f"Job enfileirado: {job_id} ({job.get('type', 'unknown')})")
        return job_id

    async def start_worker(self) -> None:
        """Inicia worker que consome a fila."""
        self._running = True
        logger.info("RedisQueue worker iniciado")
        while self._running:
            try:
                r = await get_redis()
                result = await r.brpop(QUEUE_KEY, timeout=BRPOP_TIMEOUT_SEC)
                if result is None:
                    continue
                _, payload = result
                job = json.loads(payload)

                # Move para processing (garantia de entrega)
                await r.hset(PROCESSING_KEY, job["id"], payload)

                # Processa
                task = asyncio.create_task(self._run_job(job))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

            except RedisTimeoutError:
                # Idle queue: socket read timeout before BRPOP returns (misconfig or legacy client)
                logger.debug("RedisQueue idle (BRPOP timeout)")
                continue
            except Exception as e:
                logger.error(f"RedisQueue error: {e}")
                await asyncio.sleep(1)

    async def _run_job(self, job: dict) -> None:
        try:
            await self.worker_func(job)
        except Exception:
            logger.error(f"Job {job['id']} falhou: {traceback.format_exc()}")
        finally:
            try:
                r = await get_redis()
                await r.hdel(PROCESSING_KEY, job["id"])
            except Exception:
                pass

    def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()


# ═══════════════════════════════════════════════════════════════════════════
# Worker específico pro GymSite
# ═══════════════════════════════════════════════════════════════════════════

async def gymsite_worker(job: dict) -> None:
    """Processa jobs da fila Redis."""
    job_type = job.get("type")

    if job_type == "pipeline":
        from api import _run_pipeline_async, NovoRelatorioInput
        payload = job["payload"]
        relatorio_id = job["relatorio_id"]
        # Reconstrói o input
        input_obj = NovoRelatorioInput(**payload)
        await _run_pipeline_async(relatorio_id, input_obj)
        logger.info(f"Pipeline {relatorio_id} concluído via RedisQueue")

    elif job_type == "site_conversar":
        # Turno do chat de degustação (N3). Roda o engine do consultor em modo_site;
        # conversar() persiste user+assistant em project_messages → o front faz polling.
        from services.consultor.consultor_engine import conversar
        await conversar(
            mensagem=job["mensagem"],
            usuario_id=job["usuario_id"],
            projeto_id=job["projeto_id"],
            modo_site=True,
            agente=job.get("agente", "degustacao"),
        )
        logger.info(f"site_conversar {job.get('projeto_id')} concluído via RedisQueue")

    elif job_type == "prospeccao":
        from prospecting.engine import run_prospeccao
        # run_prospeccao é síncrono e bloqueante — roda em thread pra não travar o
        # event loop (este worker já roda dentro de um loop, seja no RedisQueue ou
        # no fallback BackgroundTasks).
        result = await asyncio.to_thread(run_prospeccao, **job["kwargs"])
        logger.info(f"Prospecção {job['kwargs'].get('cidade')} concluída via RedisQueue")
        try:
            from tools.redis_pubsub import notify_prospeccao_pronta
            # await direto (NÃO asyncio.run — já há loop ativo).
            await notify_prospeccao_pronta(
                job["kwargs"].get("cidade", ""),
                oportunidades_count=result if isinstance(result, int) else 0,
            )
        except Exception:
            pass

    else:
        logger.warning(f"Job tipo desconhecido: {job_type}")
