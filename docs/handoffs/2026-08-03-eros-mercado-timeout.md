# Handoff — GymSite → Eros: grupo Mercado timeout no `knowledge-ask`

**Data:** 2026-08-03  
**De:** sessão Cursor no repo `C:\Users\marce\gymsite` (consultor ADK + NVIDIA)  
**Para:** agente / sessão no repo **`C:\Users\marce\assistent-control`** (Eros / projeto Supabase *controle de assistente*)  
**Humano:** Marcelo  

---

## 1. Pedido

Destravar RAG do grupo **Mercado Fitness** no Edge `knowledge-ask`.  
GymSite já aponta certo pro projeto Eros; **Regulatório e Engenharia respondem 200**. Só **Mercado** estoura.

---

## 2. Contexto (o que GymSite já fez)

- Chat consultor usa `LLM_PROVIDER=nvidia` (LiteLLM) — **não** Vertex.
- Vertex Discovery no chat: `VERTEX_RAG_ENABLED=0` (stub).
- Tools Eros em `gymsite/agents_site/tools.py` agora usam:
  - `EROS_SUPABASE_URL=https://gxmaxbjgdrqdcizvdojp.supabase.co`
  - `EROS_SUPABASE_SERVICE_ROLE_KEY` (do `.env.local` do assistent-control)
  - `EROS_GROUP_ID_MERCADO` / `REGULATORIO` / `ENGENHARIA`
- Antes: 404 em `epgedaiukjippepujuzc` (Supabase GymSite/cargo-flow) — função inexistente lá. **Corrigido.**

---

## 3. Evidência do bug (reproduzível)

### Projeto

| Campo | Valor |
|---|---|
| Supabase ref | `gxmaxbjgdrqdcizvdojp` |
| Nome | controle de assistente |
| Edge | `knowledge-ask` (ACTIVE, verify_jwt=false) |
| Código | `assistent-control/supabase/functions/knowledge-ask/index.ts` |

### Grupos (SQL 2026-08-03)

```sql
select g.id, g.name,
       count(c.id) as chunks,
       count(c.embedding) filter (where c.embedding is not null) as with_embed
from eros_knowledge_groups g
left join eros_knowledge_chunks c on c.group_id = g.id
where g.id in (
  'b2bce16f-3695-4d93-94c5-4bd77bdb92d6',  -- Mercado
  'b7dad505-2d2a-49a9-bbaf-d4b9c4929dea',  -- Regulatório
  'f087bfc8-ad2b-434c-bc18-a38608be183d'   -- Engenharia
)
group by g.id, g.name;
```

| Grupo | UUID | Chunks | Embed |
|---|---|---:|---:|
| **Mercado Fitness** | `b2bce16f-3695-4d93-94c5-4bd77bdb92d6` | **58 495** | 58 495 |
| Regulatório CONFEF/CREF | `b7dad505-2d2a-49a9-bbaf-d4b9c4929dea` | 93 | 93 |
| Engenharia de Obra | `f087bfc8-ad2b-434c-bc18-a38608be183d` | 33 | 33 |

### HTTP smoke (mesmo payload GymSite)

```http
POST https://gxmaxbjgdrqdcizvdojp.supabase.co/functions/v1/knowledge-ask
Authorization: Bearer <service_role>
apikey: <service_role>
Content-Type: application/json

{"groupId":"<uuid>","messages":[{"role":"user","content":"CREF academia"}]}
```

| groupId | HTTP | Corpo |
|---|---|---|
| Regulatório | **200** | texto + `chunk_count` ~15 |
| Engenharia | **200** | ok (0 chunks p/ pergunta CREF — esperado) |
| **Mercado** | **500** | `{"error":"retrieval_failed","details":"canceling statement due to statement timeout"}` |

Log Edge (MCP): `POST | 500 | .../knowledge-ask` · `execution_time_ms` ~10–27s.

**Hipótese forte:** `match_chunks` / hybrid no grupo de **~58k** chunks estoura statement timeout. Embed **existe** (não é “sem ingestão”). Problema = **escala / índice / timeout / filtro**, não ausência de dado.

Comentário no próprio `knowledge-ask`:

> Nunca use `.select().limit(80)` em `eros_knowledge_chunks`.

---

## 4. O que o agente Eros deve fazer

1. **Reproduzir** o 500 só no Mercado (curl acima).
2. **Diagnosticar** `callMatchChunks` / RPC `match_chunks` com `group_id = Mercado`:
   - índice HNSW/IVF no embedding?
   - filtro `group_id` aplica **antes** do ANN?
   - `statement_timeout` do role da Edge?
3. **Corrigir** (uma ou combinação):
   - timeout maior só no path RAG; **ou**
   - índice / stats / `match_chunks` com filtro barato; **ou**
   - curadoria: Mercado Fitness não deveria ter 58k chunks de listing (TotalPass/Wellhub?) misturados com metodologia GymSite — se for lixo de agregador, **separar grupo** (metodologia leve vs catálogo gigante).
4. **Aceite:** mesma pergunta `"tendencia academias"` ou `"como medir saturacao de academias no bairro"` → **HTTP 200** em &lt; ~8s, `sources`/`text` não vazios **ou** 200 honesto “base não cobre” (não 500).
5. Avisar GymSite quando verde — consultor já chama `consultar_base_mercado` → Eros Mercado.

### Fora de escopo deste handoff

- Trocar NVIDIA/Gemini no GymSite.
- Reativar Vertex Discovery.
- Pipeline A0–A9.
- Deploy Cloud Run.

---

## 5. Arquivos úteis (Eros)

| Path | Por quê |
|---|---|
| `supabase/functions/knowledge-ask/index.ts` | Entry ask |
| `supabase/functions/_shared/matchChunks.ts` | RPC retrieval |
| `supabase/functions/_shared/embed.ts` | embed query |
| Tabelas `eros_knowledge_groups` / `eros_knowledge_chunks` | volume Mercado |

## 6. Arquivos úteis (GymSite — só referência)

| Path | Por quê |
|---|---|
| `agents_site/tools.py` → `criar_tool_consultar_eros` | Cliente HTTP + `EROS_SUPABASE_*` |
| `agents_site/tools.py` → `consultar_base_mercado` | Facade Mercado → Eros → stub |
| `.env` | `EROS_SUPABASE_URL`, `EROS_GROUP_ID_MERCADO=b2bce16f-…` |

---

## 7. Critério de pronto

- [ ] `knowledge-ask` + `groupId=b2bce16f-3695-4d93-94c5-4bd77bdb92d6` → **200** estável  
- [ ] Sem `statement timeout` no detalhe  
- [ ] Decisão documentada: índice/timeout **ou** split do grupo 58k  
- [ ] Smoke do lado GymSite: `consultar_eros_mercado("tendencia academias")` → `n_docs>0` ou texto útil  

---

## 8. Mensagem curta pro humano

> GymSite já fala com o Supabase certo do Eros. Regulatório OK. Mercado Fitness tem **58 mil** chunks embedados e o `knowledge-ask` morre em **timeout SQL** — não é falta de embed. Precisa o time Eros otimizar retrieval ou separar esse grupo.

---

## 9. Confirmado pelo agente Eros (2026-08-03) — hipótese bate

### Causa raiz (plano SQL)

RPC `match_chunks` (`20260729_match_chunks_materialized_filter.sql`):

```sql
with filtered as MATERIALIZED (
  select ... from eros_knowledge_chunks c
  where c.group_id = match_group_id and c.embedding is not null ...
),
nearest as (
  select ... from filtered f
  order by f.embedding <=> query_embedding
  limit overfetch
)
```

Sem filtro `municipio`/`bairro`/`modalidade` → CTE materializa **os 58k do grupo**, depois sort `<=>` linear.  
**HNSW global (`eros_knowledge_chunks_embedding_hnsw_idx`) não entra** nesse plano (distância em CTE, não na tabela base).  
→ statement timeout → `retrieval_failed`.

Grupos pequenos (93 / 33): mesmo plano, barato → 200.  
Smoke Fortaleza “quantas abriram…” pode passar via path **aggregate** (pula `match_chunks`). Pergunta metodologia (`"tendencia academias"`, `"CREF academia"` no Mercado) → path vetorial → 500.

### Mix no grupo Mercado Fitness

| kind | n |
|------|--:|
| `receita_cnpj_estabelecimento` | 57 676 |
| `md_upload` + `pdf_upload` + `json` | ~819 |

Consultor GymSite (tendência / saturação / metodologia) precisa dos **~800 docs**.  
Catálogo Receita = census → já existe RPC `aggregate_*`.

### Correção recomendada (prioridade Eros)

1. **Split de grupo (melhor p/ GymSite)**  
   - Grupo leve = só md/pdf/json (~800) → novo UUID vira `EROS_GROUP_ID_MERCADO` no GymSite  
   - Receita fica em grupo/catálogo separado **ou** só via `aggregate_*`

2. **Reescrever `match_chunks` (se 58k ficar no mesmo group)**  
   - kNN **na tabela** com `WHERE group_id = …` (sem `MATERIALIZED` full-group)  
   - ou partial HNSW `WHERE group_id = Mercado`  
   - baixar `overfetch`; `SET LOCAL statement_timeout` só como cinto  
   - Só subir timeout sem mudar plano = bandaid

3. **Roteamento no ask**  
   - Metodologia → grupo leve  
   - Census → aggregate (já existe)

### Aceite (atualizado)

| Check | Como |
|-------|------|
| Grupo leve (pós-split) **ou** `b2bce16f-…` pós-RPC + `"tendencia academias"` | HTTP **200**, &lt;~8s, sem timeout |
| `"CREF academia"` no Mercado | 200 (metodologia ou “não cobre”) — **não** 500 |
| Reg/Eng | continuam 200 |
| GymSite `consultar_base_mercado` | `n_docs>0` ou texto útil |

## 10. Resolve (2026-08-03) — Eros fechou split + RPC

**Decisão:** split + rewrite `match_chunks` (sem `MATERIALIZED` full-group).

| Uso | Nome | UUID | Chunks |
|-----|------|------|-------:|
| **GymSite `EROS_GROUP_ID_MERCADO`** | Mercado Metodologia | `7b471b98-bfc8-4c7e-a58f-a0e95edede7b` | 819 |
| Aggregate / Receita | Mercado Receita CNAE | `b2bce16f-3695-4d93-94c5-4bd77bdb92d6` | 57 676 |

**GymSite:** `.env` aponta Metodologia. Restart API + smoke.

**Eros doc:** `Docs/ops/mercado-split-2026-08-03.md`  
**RPC:** `20260803_match_chunks_no_materialized_fullgroup.sql`

### Aceite

- [x] Split feito (819 vs 57 676)
- [x] Smoke GymSite `consultar_eros_mercado("tendencia academias")` → 200 / texto útil
- [x] Fortaleza aggregate Receita PASS (lado Eros)
