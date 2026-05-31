# Telemetria de Tokens & Sanitização

> **Escopo:** Como o GymSite Intelligence mede consumo de LLM (tokens) e protege dados sensíveis (LGPD) na telemetria.
>
> **Status:** Documentação alinhada ao código em **2026-05-30**. Telemetria e sanitização LGPD **implementadas**; pendências menores em §6.

---

## 1. Telemetria de Tokens — Conceito

### Por que medir tokens?

Cada agente do pipeline chama o Gemini. O custo da API Google é proporcional ao número de tokens (input + output). Sem telemetria:

- Não sabemos qual agente é o mais caro
- Não conseguimos estimar custo por relatório
- Não detectamos anomalias (ex: loop com `finish_reason=MAX_TOKENS` ou `MALFORMED_FUNCTION_CALL`)

### O que é um "token"?

| Tipo | Definição | Exemplo |
|---|---|---|
| **Input (prompt)** | Tokens enviados para o LLM | Instruction + contexto de mercado + tool results |
| **Output (completion)** | Tokens gerados pelo LLM | Resposta em JSON, texto, function call |
| **Total** | Soma input + output | Usado para billing e quota |

### Pipeline atual (A0 → A9)

| Agente | Nome ADK | Papel |
|---|---|---|
| **A0** | ContextBuilder | Deep Research de mercado |
| **A1** | GeoScout | Zonas comerciais (Google Maps) |
| **A2** | DemoAnalyst | Demografia IBGE *(paralelo)* |
| **A3** | CompetitorIntel | Sub-pipeline **A3a → A3b → A3c** *(paralelo)* |
| **A4** | FinancialEstimator | Viabilidade financeira *(paralelo)* |
| **A5** | ContactHunter | Decisores e scripts |
| **A6** | ReportConsolidator | Relatório executivo |
| **A9** | PositioningStrategist | Posicionamento ERRC |
| **A7** | *(embutido no A3)* | Gemini Search Grounding — não é agente separado no grafo |

Telemetria é anexada via `_attach_telemetry()` em `gymsite_intelligence/agent.py` a todos os agentes acima (incluindo o sub-pipeline A3).

### Arquitetura da Telemetria

```
┌─────────────────┐     after_model_callback      ┌─────────────────┐
│   Agente ADK    │ ─────────────────────────────→│ token_telemetry │
│  (A0 → A9)      │    (llm_response + context)   │   (Python)      │
└─────────────────┘                               └─────────────────┘
         │                                                  │
         │ before/after_agent_callback                      ▼
         ▼                                        ┌─────────────────┐
┌─────────────────┐                               │ tokens_pipeline │
│ agent_telemetry │                               │     .csv        │
│  (OTel spans)   │                               └─────────────────┘
└─────────────────┘                                         │
                                                            ▼
                                                  ┌─────────────────┐
                                                  │ _agregar_e_     │
                                                  │ persistir_custos│
                                                  │ (api.py)        │
                                                  └─────────────────┘
                                                            │
                                                            ▼
                                                  ┌─────────────────┐
                                                  │ relatorio_      │
                                                  │ custos_agentes  │
                                                  │ (Supabase)      │
                                                  └─────────────────┘
                                                            │
                                                            ▼
                                                  ┌─────────────────┐
                                                  │  /custos        │
                                                  │  (frontend)     │
                                                  └─────────────────┘
```

**Fluxo resumido:**

1. Cada chamada LLM → linha em `metrics/tokens_pipeline.csv` (`after_model_callback`)
2. Ao final do pipeline → `api.py` agrega por `run_id` via `tools/pricing.py` e faz UPSERT em `relatorio_custos_agentes`
3. Dashboard admin lê Supabase via `GET /api/relatorios/{id}/custos-api`

> **LangCache** (`tools/langcache_client.py`) reduz chamadas Gemini repetidas (A0, A9, grounding), mas **não altera** a contagem de tokens no CSV — hits de cache simplesmente não geram nova linha.

### Dados Coletados (`metrics/tokens_pipeline.csv`)

| Coluna | Significado |
|---|---|
| `run_id` | ID da execução do pipeline (12 chars hex) |
| `timestamp` | ISO-8601 da chamada LLM |
| `agent_name` | Nome do agente (ContextBuilder, GeoScout, etc.) |
| `tokens_in` | Tokens de prompt |
| `tokens_out` | Tokens de resposta |
| `tokens_total` | Soma (fallback: in + out se API não retornar total) |
| `model` | Modelo usado (gemini-2.5-flash, gemini-2.5-pro, etc.) |
| `fonte_usage` | De onde veio o `usage_metadata` (debug de captura) |
| `finish_reason` | STOP / MAX_TOKENS / MALFORMED_FUNCTION_CALL / SAFETY / ERROR:* |

O CSV **não contém PII** — apenas metadados de consumo LLM.

### Por que `after_model_callback` e não `after_agent_callback`?

```
Agente A3 pode fazer:
  LLM call 1 → tool call (buscar concorrentes)
  LLM call 2 → tool call (analisar reviews)
  LLM call 3 → resposta final

after_agent_callback:  1 registro por agente (perde calls 1 e 2)
after_model_callback:  3 registros (cada LLM call separada) ← correto
```

---

## 2. Sanitização — Conceito

### O que é sanitização?

**Sanitização** = remover, mascarar ou transformar dados sensíveis antes de gravar em logs, traces, métricas ou payloads externos.

### Por que sanitizar?

1. **LGPD (Lei 13.709/2018)** — CNPJ, endereço, telefone, email são dados pessoais/empresariais
2. **Segurança** — Chaves de API, tokens de autenticação, secrets
3. **Compliance** — Se um trace OTel vazar para Grafana Cloud, não pode levar PII
4. **Custo** — Dados sanitizados = menos bytes = spans mais leves

### O que sanitizar na telemetria do GymSite?

| Dado | Risco | Como sanitizar |
|---|---|---|
| **CNPJ completo** | LGPD — identifica empresa | `12.***.***/0001-99` (mascarar dígitos centrais) |
| **Endereço** | LGPD — localização precisa | Remover número; manter bairro + cidade |
| **Telefone/WhatsApp** | LGPD — contato direto | `+55 ** *****-9999` (últimos 4 dígitos) |
| **Email** | LGPD — contato direto | `jo***@academia.com.br` (2 primeiros chars + domínio) |
| **Chaves de API** | Segurança — vazamento de credenciais | Remover; substituir por `[REDACTED]` |
| **Nome fantasia** | LGPD — identificação indireta | Manter; não é pessoa natural |
| **Razão social** | LGPD — identificação empresarial | Manter; é dado público (RFB) |
| **Score / Tokens** | Sem risco | Não sanitizar |

### Regra de Ouro

> **"Se o dado não for essencial para debug/métrica, não grave. Se for sensível, mascare."**

---

## 3. Implementação — Estado Atual

### 3.1 `tools/sanitize.py` — ✅ Implementado

Funções: `mask_cnpj`, `mask_phone`, `mask_email`, `mask_address`, `redact`, `sanitize_dict`, `sanitize_state`, `safe_headers`, `safe_span_attribute`.

```python
from tools.sanitize import mask_cnpj, mask_phone, mask_email, mask_address, sanitize_state

safe = sanitize_state(state_adk)  # para spans OTel
endereco = mask_address(raw, cidade="Fortaleza", uf="CE")
headers = safe_headers(request.headers)  # logs de debug
```

### 3.2 OpenTelemetry (`tools/agent_telemetry.py`) — ✅ Implementado

- Span por agente (`before_agent_callback` / `after_agent_callback`)
- `sanitize_state()` antes de gravar atributos — **nunca** dump do state bruto
- Atributos whitelisted: `cnpj_masked`, `email_masked`, `phone_masked`, `endereco_masked`, `cidade`, `uf`, `bairro`, `contato.*_masked`
- Dicts/listas grandes viram placeholder (`<dict:N>`) — sem JSON completo no span

`tools/telemetry.py` (`span()` manual) usa `safe_span_attribute()` para mascarar PII passada como kwargs.

### 3.3 Webhook de prospecção (`prospecting/webhook.py`) — ✅ Implementado

**Em `_montar_payload`:**

- ✅ `cnpj` → `mask_cnpj`
- ✅ `contato.email` → `mask_email`
- ✅ `contato.whatsapp` → `mask_phone`
- ✅ `endereco` → `mask_address(endereco_cnpj, cidade, uf)`

Payload sanitizado também é persistido em `webhook_claw_log` / `webhook_payload`.

### 3.4 Logs da API (`api.py`) — ⚠️ Parcial

**Implementado:**

- JWT lido de `Authorization` sem logar o token
- Rate limit usa IP / bearer hash, não loga header completo
- Helper `safe_headers()` disponível em `tools/sanitize.py`

**Pendente:**

- Adotar `safe_headers()` nos pontos que passarem a logar request headers

```python
from tools.sanitize import safe_headers

logger.info("Headers: %s", safe_headers(request.headers))
```

### 3.5 Telemetria de tokens — ✅ Implementado

| Componente | Arquivo | Status |
|---|---|---|
| Coleta por LLM call | `tools/token_telemetry.py` | ✅ |
| Wiring nos agentes | `gymsite_intelligence/agent.py` → `_attach_telemetry` | ✅ |
| Agregação + pricing | `tools/pricing.py` + `api.py` → `_agregar_e_persistir_custos` | ✅ |
| Persistência Supabase | `relatorio_custos_agentes` | ✅ |
| CSV ignorado no git | `.gitignore` → `metrics/*.csv` | ✅ |
| Retenção CSV | `prune_tokens_csv()` no startup da API | ✅ |

---

## 4. Checklist de Sanitização & Telemetria

Legenda: ✅ feito · ⚠️ parcial · ❌ pendente

| # | Item | Status | Notas |
|---|---|---|---|
| 1 | Nenhum CNPJ completo em spans OTel | ✅ | `sanitize_state` + `cnpj_masked` |
| 2 | Nenhum CNPJ completo no CSV de tokens | ✅ | CSV não grava PII |
| 3 | Nenhum CNPJ completo no webhook | ✅ | `mask_cnpj` em `_montar_payload` |
| 4 | Nenhuma chave de API em spans/logs | ⚠️ | `safe_span_attribute` + `safe_headers`; falta auditoria Grafana |
| 5 | Telefones mascarados no webhook | ✅ | `mask_phone` em contato |
| 6 | Emails mascarados no webhook | ✅ | `mask_email` em contato |
| 7 | Endereços sem número de porta/prédio | ✅ | `mask_address` no webhook + OTel |
| 8 | Tokens de auth redacted em traces | ⚠️ | API não loga Bearer; usar `safe_headers` se expandir logs |
| 9 | CSV de telemetria fora do git | ✅ | `metrics/*.csv` no `.gitignore` |
| 10 | Retenção de CSVs (> 90 dias) | ✅ | `prune_tokens_csv()` no startup; env `TELEMETRY_CSV_RETENTION_DAYS` |
| 11 | Custos persistidos por relatório | ✅ | `relatorio_custos_agentes` + migration 20260530 |
| 12 | Dashboard admin de custos | ✅ | `/custos` (owner/admin only) |
| 13 | Sanitização OTel completa no state | ✅ | `agent_telemetry._apply_sanitized_state_to_span` |
| 14 | LangCache configurado (redução de custo) | ✅ | A0, A9, grounding — ver `tools/langcache_client.py` |

---

## 5. Dashboard de Custos (Frontend)

**Rota:** `/custos` — **não** `/telemetria`.

**Acesso:** apenas `owner` / `admin` (`useMembership().isOwnerOrAdmin`).

**Implementado em:** `frontend/src/routes/CustosPage.tsx`

```
┌─────────────────────────────────────────┐
│  Custos — Período: Este mês             │
├─────────────────────────────────────────┤
│  Total período    │ Médio/relatório     │
│  R$ 124,50        │ R$ 12,45            │
├─────────────────────────────────────────┤
│  Relatório        │ Tokens │ Custo │ ▶  │
│  ────────────────┼────────┼───────┼────│
│  Fortaleza/CE     │ 145k   │ R$12  │ ▶  │  ← expande breakdown
│  Anápolis/GO      │ 98k    │ R$8   │ ▶  │
└─────────────────────────────────────────┘
         ▼ (expandido)
┌─────────────────────────────────────────┐
│  Agente              │ Tokens │ Custo  │
│  ContextBuilder (A0) │ 8.351  │ R$0,42 │
│  GeoScout (A1)       │ 94.590 │ R$4,80 │ ← mais caro
│  Positioning (A9)    │ 5.595  │ R$0,28 │
└─────────────────────────────────────────┘
```

### Endpoints da API

| Método | Rota | Uso |
|---|---|---|
| `GET` | `/api/relatorios/{id}/custos-api` | Breakdown LLM + APIs externas de um relatório |
| `GET` | `/api/custos/optimizations?dias=30` | Sugestões de otimização agregadas |
| `GET/POST/PATCH` | `/api/custos/propostas` | Propostas de otimização (backlog interno) |

**Fonte primária:** Supabase `relatorio_custos_agentes` (populado a partir de `tokens_pipeline.csv` ao concluir o pipeline).

Relatórios gerados **antes** da telemetria exibem: *"Sem telemetria registrada para este relatório"*.

---

## 6. Pendências recomendadas

Itens restantes (baixa prioridade):

1. **Auditoria OTel export** — revisar spans no Grafana Cloud e confirmar zero PII
2. **Adotar `safe_headers()`** nos logs de debug da API quando forem expandidos
3. **Cron dedicado** (opcional) — se a API ficar offline por longos períodos, rodar `prune_tokens_csv()` via cron externo

```python
# Retenção manual / cron
from tools.token_telemetry import prune_tokens_csv
print(prune_tokens_csv())  # default 90 dias via TELEMETRY_CSV_RETENTION_DAYS
```

---

> **Referências**
>
> | Arquivo | Papel |
> |---|---|
> | `tools/token_telemetry.py` | Coleta por LLM call → CSV |
> | `tools/agent_telemetry.py` | Spans OTel por agente |
> | `tools/sanitize.py` | Funções de mascaramento LGPD |
> | `tools/pricing.py` | Cálculo BRL por modelo |
> | `api.py` | `_agregar_e_persistir_custos`, endpoints `/custos*` |
> | `prospecting/webhook.py` | Payload sanitizado para Claw |
> | `metrics/tokens_pipeline.csv` | Dados brutos locais (gitignored) |
> | `supabase/migrations/20260530_relatorio_custos_agentes.sql` | Schema Supabase |
> | LGPD Art. 7º, 9º, 46º | Tratamento de dados empresariais |
