# HANDOFF — Apollo (landing leads) + Marketing

> Atualizado 2026-07-13. Alinhado a `.agent/rules/P-000_REGRA_MESTRA_MUDANCA.md`.
> **Dois funis Apollo distintos — não misturar.**

## 1. Dois funis (P-000 §2 — ler fonte antes de mexer)

| Funil | Entrada | Código | Apollo |
|-------|---------|--------|--------|
| **Landing / análise grátis** | Form, `/api/leads`, `site_agent._capturar_lead` | `tools/apollo_client.py` | Contact upsert + **sequence** (nurture) |
| **Scout CNPJ×CNO** | `oportunidades_prospeccao` | `services/apollo_crm_sync.py` | Person/Account CRM enrichment |

`sequence-load` (MCP/skill) = passos manuais do funil **landing** já codificados em `apollo_client._add_to_sequence`.

## 2. E2E landing → sequence (checklist pré-teste)

**Banco (Supabase `epgedaiukjippepujuzc`):**
- `gymsite.analise_gratuita` existe + Cloud Run com `GYMSITE_SCHEMA_SEP=1`
- `leads` via `tbl(sb, "leads")` — ver `tools/db_schema.py`

**Cloud Run `gymsite-api` — três envs Apollo obrigatórias pro E2E completo:**

| Env | Função | Estado jul/13 |
|-----|--------|---------------|
| `APOLLO_API_KEY` | auth | ✅ setada |
| `APOLLO_SEQUENCE_ID` | campanha (`6a4ab3f5…`) | ✅ setada |
| `APOLLO_SENDER_EMAIL` | `suporte@gymsite.com.br` — lookup → account_id | ✅ Cloud Run jul/13 |

Sem `APOLLO_EMAIL_ACCOUNT_ID`, status no banco fica `sincronizado_sem_sequencia` (não `sincronizado_sequencia`).

**Obter account_id:** vincular `suporte@gymsite.com.br` no Apollo (Settings → Mailboxes), depois `GET /api/v1/email_accounts` com **master API key** ou setar `APOLLO_EMAIL_ACCOUNT_ID` direto.

**Rerun leads pendentes (únicos por email):**
```powershell
.venv\Scripts\python.exe tools/resync_leads_apollo.py
```

**Apollo conta:** jul/13 API retorna `401 Invalid access credentials` em `/contacts` — conferir billing/plano Apollo antes do teste real.

## 3. Fluxo código (normalizado jul/13)

```
POST /api/leads  ou  site_agent._capturar_lead
  → leads._persistir_lead (tbl)
  → BackgroundTasks._sync_apollo_bg
  → apollo_client.sync_lead_to_apollo
       POST /api/v1/contacts (run_dedupe=true)
       POST /api/v1/emailer_campaigns/{APOLLO_SEQUENCE_ID}/add_contact_ids
  → leads.apollo_sync_status:
       sincronizado_sequencia | sincronizado_sem_sequencia | erro
```

Base URL canônica: `https://api.apollo.io/api/v1` (igual `apollo_crm_sync.py`).

## 4. Artefatos

| Arquivo | Papel |
|---------|-------|
| `tools/apollo_client.py` | Landing → Contact + Sequence |
| `backend/routers/leads.py` | POST `/api/leads` + status sequence |
| `backend/routers/site_agent.py` | `_capturar_lead` reusa `leads._persistir_lead` |
| `services/apollo_crm_sync.py` | Scout — **outro funil** |
| `tools/test_apollo_client.py` | Mock httpx — rodar antes de commit |
| `.env.production.example` | `APOLLO_*` documentado |

## 5. Regras P-000 que mordem aqui

- Segredos só `.env` / Cloud Run — nunca commit
- Teste: `.venv\Scripts\python.exe -m pytest tools/test_apollo_client.py`
- Schema: `tbl()` + flags `GYMSITE_SCHEMA_SEP` / `SHARED_SCHEMA_SEP`
- Sequence: **nunca ativar envio** sem OK explícito Marcelo — campanha nasce pausada/rascunho
- Deploy API: Cloud Run `gen-lang-client-0106729343` us-central1 (não southamerica)

## 6. Próximo passo operacional

1. Resolver billing Apollo (401)
2. Setar `APOLLO_EMAIL_ACCOUNT_ID` no Cloud Run api + worker
3. Teste E2E: form landing → lead `sincronizado_sequencia` no Supabase
4. Scout/marketing: inventário `apollo_crm_sync` + `docs/marketing/` (frente paralela)

## 7. Log

- 2026-07-13: Normalizado `apollo_client` (base `/api/v1`, run_dedupe, sequence status). Handoff alinhado P-000. Bloqueador: EMAIL_ACCOUNT_ID + 401 Apollo.
