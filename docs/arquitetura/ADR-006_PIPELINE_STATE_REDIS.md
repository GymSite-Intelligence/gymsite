# ADR-006 — Estado vivo do pipeline (Living Map / progresso) via Redis

| Campo | Valor |
|---|---|
| Status | **Accepted** (2026-07-16) |
| Decisores | GymSite / Marcelo |
| Relacionados | `SPEC_PROGRESSO_PIPELINE.md` (Fase 2 SSE), `tools/redis_pubsub.py`, `tools/redis_queue.py`, `api.py` (`_pipeline_state`, `/ws/pipeline`), Cloud Run `gymsite-api` + `gymsite-worker` |

## Contexto

O pipeline A0–A9 roda via `RedisQueue` (`gymsite:queue`). API e worker já são serviços Cloud Run separados (`RUN_QUEUE_WORKER`). O “Living Agent Map” e qualquer stream em tempo real hoje dependem de `_pipeline_state: dict` **em memória do processo** + WebSocket `/ws/pipeline` na API.

Quando o job é consumido no **worker**, o dict da API fica vazio ou atrasado. Com autoscaling (>1 revisão/instância), o cliente WS pode cair numa instância que nunca viu o run. `tools/redis_pubsub.py` já publica `relatorio.pronto` / `prospeccao.pronta` no canal `gymsite:events` — o caminho está meio aberto.

Progresso de produto para o usuário (stepper) já tem fonte durável: `relatorios.etapa_atual` + `etapas_concluidas` + `GET /api/relatorios/{id}/status` (SPEC Fase 1). Este ADR trata do **canal quente** (mapa / SSE / micro-eventos), não substitui o banco.

## Checklist Redis (2026-07-16) — pré-requisito F0

| Check | Resultado |
|---|---|
| Secret Cloud Run `redis-url` | Presente em api e worker |
| Host | Upstash `intense-sloth-41040.upstash.io:6379` (`rediss://`) |
| Ping | OK |
| Fila `gymsite:queue` | Operacional (jobs enfileiram e concluem “via RedisQueue”) |
| Memorystore GCP | Não usado (API Redis GCP desligada); broker = Upstash |
| `/health` | **Não** inclui Redis (ponto cego — ver consequências) |
| `RUN_QUEUE_WORKER` na API | Ausente → default código `"1"` → API **também** consome a fila |
| `gymsite:queue:processing` | Hash com jobs órfãos (crash sem `hdel`) — limpeza operacional |

**Conclusão F0:** Redis compartilhado **está online**. ADR pode implementar sem provisionar Memorystore.

## Decisão

**Opção B — Redis como barramento do estado vivo do pipeline.**

1. **Fonte durável (stepper / status HTTP):** continua Supabase (`etapa_atual` / `etapas_concluidas`) — inalterada.
2. **Fonte quente (Living Map, SSE Fase 2, micro-narrativa):** Redis
   - Pub/Sub: canal `gymsite:pipeline:{relatorio_id}` (ou campo `relatorio_id` em `gymsite:events` versionado).
   - Snapshot opcional: hash `gymsite:pipeline:state:{relatorio_id}` TTL ~1h (`HSET` agent_id → JSON `{status, tokens, latency_ms, ts}`).
3. **Publicadores:** callbacks de telemetria / `pipeline_progress` no processo que **roda o agente** (hoje api e/ou worker).
4. **Consumidores:** API (`/ws/pipeline` ou `GET /api/relatorios/{id}/events` SSE) faz `SUBSCRIBE` + lê snapshot inicial; se Redis cair, responde `degraded` e o front cai no polling HTTP já existente.
5. **`_pipeline_state` in-memory:** deixa de ser fonte de verdade; no máximo cache local da instância.

### Opções rejeitadas

| Opção | Motivo |
|---|---|
| A — Manter só dict + WS | Quebra com api≠worker e N instâncias |
| C — Só Supabase Realtime pro mapa | Mistura telemetria quente com DB; latência/custo; Redis já paga a fila |
| D — Só polling, sem canal quente | Suficiente pro stepper; insuficiente pro Living Map / SPEC Fase 2 |

## Consequências

### Positivas

- Living Map e SSE veem o mesmo run independente de qual serviço executa o agent.
- Alinha SPEC Fase 2 (SSE via Redis) com o WS existente — um contrato de evento.
- Degradação já conhecida (`_enqueue_ou_background` → BackgroundTasks) espelhada no stream (`degraded`).

### Negativas / trabalho

- Implementar publish nos callbacks + subscribe no WS/SSE.
- Incluir `redis` em `/health` (`tools/redis_client.redis_health`) — senão F0 volta a ficar cego.
- Decidir operação: `RUN_QUEUE_WORKER=0` na **api** (só enfileira) vs default atual (api também worker). Recomendação operacional: `0` na api, `1` no worker — reduz BRPOP duplo e concentra CPU de pipeline no worker.
- Limpar órfãos em `gymsite:queue:processing` (ops) e, se desejável, TTL/`HEXPIRE` por campo.

### Fora de escopo (ADRs / tickets separados)

- Checkpoint por agente pós-429 (não reprocessar A0–A(n-1)).
- `asyncio.to_thread` em chamadas sync supabase-py.
- Extrair pipeline/WS de `api.py` para router.
- Rotação de `REDIS_MEMORY_API_KEY` (produto Memory API ≠ fila; vazou em checklist — rotacionar se log compartilhado).

## Contrato de evento (v1)

```json
{
  "v": 1,
  "type": "agent.progress",
  "relatorio_id": "uuid",
  "agent_id": "A3a",
  "status": "running|completed|failed",
  "tokens": 0,
  "latency_ms": 0,
  "ts": "ISO-8601"
}
```

Publicação: best-effort (falha de publish não derruba o pipeline).  
WS/SSE: snapshot hash no connect, depois só deltas pub/sub.

## Plano de implementação (ordem)

1. Health: componente `redis` em `health_payload`.
2. Estender `tools/redis_pubsub.py` (`publish_pipeline_progress` + helpers de snapshot hash).
3. Hook em `pipeline_progress` / telemetria → publish (worker e api, se ambos rodarem agentes).
4. `/ws/pipeline` (e depois SSE SPEC Fase 2) → subscribe + degraded fallback.
5. Teste local: api `RUN_QUEUE_WORKER=0`, worker `=1`, Redis Upstash/local — WS na api vê A0→A6 do worker.
6. Ops: setar `RUN_QUEUE_WORKER=0` na revisão `gymsite-api` quando (5) estiver verde.

## Verificação

- [x] `GET /health` → `components.redis` (código; ok com Upstash no ar)
- [x] Publish sync em `pipeline_progress` + snapshot hash + WS subscribe (código)
- [ ] Run com api≠worker: WS/SSE na api reflete agentes do worker (smoke prod)
- [ ] Redis down: enqueue degrada; stream sinaliza `degraded`; stepper via polling OK
- [ ] Sem regressão: job ainda “concluído via RedisQueue” nos logs
- [ ] Ops: `RUN_QUEUE_WORKER=0` na API
