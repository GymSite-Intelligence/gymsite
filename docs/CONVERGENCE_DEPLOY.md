# Convergência GymSite — Guia de Implementação e Deploy

Este documento registra a convergência entre o site de marketing
(`gym-insight-hub`, Cloudflare Pages) e o produto (`gymsite`, FastAPI + Google ADK).
Ele descreve o que foi implementado em código e os passos manuais de
configuração/infra que precisam ser aplicados pelo responsável.

## Visão geral das quatro frentes

| Frente | Descrição | Status do código |
|--------|-----------|------------------|
| 1 | Endpoints `/api/chat` e `/api/leads` no backend, persistindo em `chat_interacoes` e `leads` | Implementado |
| 2 | Sincronização de leads com o Apollo via API | Implementado (requer chave) |
| 3 | Subdomínios `app.` e `api.` em getgymsite.com.br | Pendente (ação manual de DNS) |
| 4 | Formulário da landing enviando para `POST /api/leads` (substitui mock) | Implementado |

## Frente 1 — Endpoints do backend

Arquivos adicionados:

- `backend/routers/leads.py` — rota `POST /api/leads` (pública). Valida a
  entrada com Pydantic (`LeadInput`, e-mail validado), persiste na tabela
  `leads` via service client e dispara o sync com o Apollo em background.
- `backend/routers/chat.py` — rota `POST /api/chat`. Classifica a intenção,
  responde a partir da base de conhecimento, delega pesquisa de mercado ao
  agente A7 (com fallback seguro) e persiste a conversa em `chat_interacoes`.

Integração:

- `api.py` foi atualizado para importar e registrar ambos os routers
  (`include_router`), seguindo o padrão dos routers existentes.

Migração de banco:

- `db/migrations/0001_leads.sql` — cria a tabela `leads`, índices, trigger de
  `updated_at`, habilita RLS, política de leitura por organização e escrita
  restrita ao `service_role`.

## Frente 2 — Sincronização com o Apollo

Arquivo adicionado:

- `tools/apollo_client.py` — `sync_lead_to_apollo` faz upsert do contato via
  `httpx` e, opcionalmente, adiciona o contato a uma sequência. Toda a
  configuração vem de variáveis de ambiente; nenhum segredo fica no código.

Variáveis de ambiente necessárias:

- `APOLLO_API_KEY` — chave da API do Apollo (obrigatória para ativar).
- `APOLLO_BASE_URL` — opcional, padrão para a API pública do Apollo.
- `APOLLO_SEQUENCE_ID` — sequence/campanha nurture pós-lead (obrigatório pro enrollment).
- `APOLLO_EMAIL_ACCOUNT_ID` — caixa remetente Apollo (obrigatório pro enrollment; sem ela só upsert contact).
- `APOLLO_SYNC_ENABLED` — liga/desliga o sync sem remover a chave.
- `GYMSITE_SCHEMA_SEP=1` / `SHARED_SCHEMA_SEP=1` — roteamento `tbl()` (obrigatório em prod).

## Frente 3 — Subdomínios (ação manual)

Esta frente NÃO foi executada automaticamente porque envolve alterações de DNS
e configuração de conta, que devem ser feitas pelo responsável.

Registros a adicionar no Cloudflare (zona getgymsite.com.br):

- `app` → CNAME para `gymsite.pages.dev` (Proxied) — front-end do produto.
- `api` → CNAME para o domínio do backend (Cloud Run) ou via Cloudflare
  Tunnel (Proxied) — origem da API.

## Frente 4 — Formulário da landing

Arquivo alterado:

- `gym-insight-hub/src/components/site/ChatAgent.tsx` — o `handleSubmit`
  (antes apenas um mock que marcava `submitted`) agora envia um `POST` para
  `${API_BASE}/api/leads` com nome, e-mail, telefone, mensagem, cidade,
  bairro, perfil e parâmetros de UTM.
- `API_BASE` vem de `import.meta.env.VITE_API_BASE` com fallback para
  `https://api.getgymsite.com.br`.

## Checklist de configuração manual

1. Rodar a migração `db/migrations/0001_leads.sql` no Supabase.
2. Definir no backend: `APOLLO_API_KEY` (e opcionalmente `APOLLO_SEQUENCE_ID`),
   `SUPABASE_GYMSITE_ORG_ID`.
3. Adicionar `https://getgymsite.com.br` a `CORS_ORIGINS` no backend.
4. Definir `VITE_API_BASE` nas variáveis de ambiente do Cloudflare Pages
   (projeto gym-insight-hub).
5. Confirmar que `httpx` está em `requirements.txt`.
6. Criar os subdomínios `app.` e `api.` (ver Frente 3).
7. Fazer deploy do backend (Cloud Run) para que `api.getgymsite.com.br`
   tenha origem.

## Degustação pública 100% Cloudflare (jul/2026)

A landing `gymsite.com.br/degustacao` (repo `gym-insight-hub`) pode rodar **sem
Cloud Run** no caminho crítico:

| Componente | Onde |
|------------|------|
| Front | Cloudflare Pages (`gym-insight-hub`) |
| API `/api/site-agent/*` | Worker `gymsite-degustacao` |
| Chat LLM | Sakana Fugu |
| Concorrentes | SearchAPI |
| Mini-relatório | CF Queue + Gemini (narrativa) + Supabase |
| Caps chat | CF KV (fail-closed) |
| Caps análise | Supabase `analise_gratuita` |

Cutover:

1. Deploy Worker (`gym-insight-hub/workers/degustacao`) com secrets Supabase/SearchAPI/Fugu/Turnstile/Gemini.
2. Criar KV namespace e atualizar `wrangler.jsonc`.
3. Routes: `gymsite.com.br/api/site-agent/*` → Worker.
4. Pages `public/_routes.json` exclui `/api/site-agent/*`.
5. `VITE_DEGUSTACAO_PROVIDER=cloudflare` + `VITE_API_BASE=` (same-origin).

O pipeline ADK A0–A9 Python permanece no produto pago; o mini-relatório free usa
**DegustacaoEngine** TS (subset determinístico + narrativa Gemini).

**Rotação:** `SAKANA_API_KEY` vazou no histórico git — rotacionar no Sakana Console
e atualizar secrets Pages + Worker.

## Histórico de commits relacionados

- `backend/routers/leads.py` (00f2e17)
- `backend/routers/chat.py`
- `tools/apollo_client.py` (ad7873b)
- `db/migrations/0001_leads.sql`
- `api.py` — registro dos routers (bc9ec64)
- `ChatAgent.tsx` — formulário real (14c6d64, repo gym-insight-hub)
