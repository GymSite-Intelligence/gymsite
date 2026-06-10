# Agente de IA Especialista em Fitness — Estado Atual (As-Built)

> Documento de registro do que foi efetivamente implementado até 10/06/2026.  
> Para a especificação original do fluxo conversacional, ver `AGENTE_CONSULTOR_CONVERSACIONAL.md`.

---

## 1. Contexto do Projeto

O **Agente de IA Especialista em Fitness** é uma camada conversacional que substitui o formulário estático de geração de relatórios de viabilidade por um chat natural. O usuário informa cidade/bairro (e opcionalmente modelo, tamanho, público-alvo) via texto livre; o agente extrai os parâmetros (slot-filling), preenche o que falta perguntando de forma orientadora, e dispara o pipeline ADK A0–A9 quando todos os slots obrigatórios estão presentes.

**Escopo implementado:**
- Backend de inference com fallback Tinker → Gemini.
- Motor conversacional com classificação de intenção, extração de slots e slot-filling.
- Persistência de sessões (`sessions`) e mensagens (`messages`) no Supabase.
- UI de chat profissional (React, Tailwind, shadcn/ui) com múltiplas sessões, anexos, markdown e sidebar.
- Integração de navegação: rota `/assistente`, botão "Novo relatório" redireciona para o chat.

**O que ainda NÃO está implementado (vs. especificação original):**
- `UserProject` com contexto acumulativo (estados `EM_CONVERSA`, `PESQUISANDO`, etc.).
- Capabilities sob demanda (function calling para ferramentas isoladas A0–A4).
- Tela de status do projeto (`ProjetoDetailPage`).
- SSE/WebSocket para atualizações em tempo real.
- Cache inteligente por bairro.

---

## 2. Stack Real em Uso

| Categoria | Tecnologia | Observação |
|-----------|------------|------------|
| Frontend | React 18, TypeScript, Tailwind CSS, shadcn/ui | React 19 ainda não migrado |
| Roteamento | TanStack Router | — |
| Build | Vite | HMR ativo; reinício necessário para novos arquivos |
| Backend | Python 3.14, FastAPI (`api.py` ~2.142 linhas) | Monolítico |
| Orquestração | Google ADK A0–A9 (inalterado) | Pipeline pesado via RedisQueue |
| LLM Conversacional | Gemini 2.5 Flash | Fallback de Tinker (ver ADR-001) |
| LLM Pipeline | Gemini 2.5 Flash / Pro | A0–A9 conforme configuração |
| Banco de Dados | Supabase PostgreSQL | Tabelas `sessions`, `messages` |
| Cache | Redis | `competitor_cache`, fila de jobs |
| Filas | RedisQueue (`redis_queue.py`) | Worker síncrono |
| Inference Wrapper | `services/tinker_bot.py` | SamplingClient + fallback Gemini |

**Dependências adicionadas:**
- `tinker==0.22.3` (instalado, mas não em uso efetivo)
- `react-markdown`, `remark-gfm` (frontend)

---

## 3. Glossário do Domínio (Em Uso na UI)

| Termo | Uso |
|-------|-----|
| **Agente / GymSite Agent** | A própria IA na interface |
| **Análise de viabilidade** | O relatório formal gerado pelo pipeline A0–A9 |
| **Conversa** | Sessão de chat persistente |
| **Anexo** | PDF, foto ou planilha enviada pelo usuário |

### Termos Proibidos na UI (Acordo vigente)
"slot", "pipeline", "stub", "output_key", "session.state", "token", "payload", "entidade", "registro", "submeter", "tenant", "async", "worker", "queue".

---

## 4. Padrões Arquiteturais Aplicados

### P-001 — Linguagem do domínio, não do software
A UI fala na linguagem que o usuário fala no dia-a-dia. O agente se apresenta como "Especialista em franquias de academia", não como "sistema de slot-filling".

**Violação conhecida:** a mensagem de confirmação antes do pipeline usa linguagem de formulário:  
> *"Resumo do que entendi: • Tipo: Academia • Tamanho: M (800–1500 m²)"*  
Isso soa como pré-visualização de campos de banco de dados, não como consultoria. Ver BUG-001.

### P-002 — Mobile-first
O chat foi construído responsivo: touch targets amplos, drawer no mobile (`ChatSidebarMobile`), layout fluido, textarea auto-resize.

### P-003 — Defaults inteligentes e auto-save
Os defaults existem (`tamanho_preset: "m"`, `publico_alvo: "25-40"`, etc.), mas a **decisão consciente única** do usuário não está implementada. O agente aplica defaults silenciosamente e dispara o pipeline sem confirmação. Ver BUG-001.

### P-004 — Filtragem proativa
Não implementado. O agente não oferece opções elegíveis antes de executar a ação pesada (pipeline A0–A9). Ele escolhe sozinho.

### P-005 — Validação no backend
Requests passam por schemas Pydantic (`ConversarInput`, `ConversarOutput`). Regras de negócio re-validadas no `api.py`.

---

## 5. Estrutura de Pastas e Arquivos (Real)

```
services/
  tinker_bot.py              # Wrapper Tinker SamplingClient + fallback Gemini
  tinker_context.py          # Builder de contexto RAG sobre relatórios do usuário
  conversational_engine.py   # Motor de conversação: intenção, slots, slot-filling, dispatcher
  chat_state.py              # CRUD Supabase para chat_sessions (legacy) e sessions/messages

frontend/src/
  hooks/
    useConversationalChat.ts # Estado do chat, conversa com /api/assistente/conversar
  components/chat/
    ChatLayout.tsx           # Estrutura flex principal (header, messages, input)
    ChatMessage.tsx          # Bubbles, ReactMarkdown, syntax highlight, anexos, ações
    ChatInput.tsx            # Textarea auto-resize, upload file, previews, envio
    ChatSidebar.tsx          # Lista de sessões, drawer mobile
  routes/
    AssistentePage.tsx       # Página do chat (integra hook + componentes)

db/migrations/
  20260610_chat_sessions.sql    # Migration original (cria chat_sessions)
  20260610_chat_messages.sql    # Migration final (renomeia para sessions, cria messages)

api.py                         # Endpoint POST /api/assistente/conversar
```

---

## 6. Modelo de Dados (Supabase)

### 6.1 Tabela `sessions`

Criada pela migration `20260610_chat_messages.sql`. Renomeia `chat_sessions` se existir.

```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  intencao TEXT,
  slots JSONB DEFAULT '{}',
  relatorio_id UUID REFERENCES relatorios(id),
  status TEXT DEFAULT 'coletando_slots'
    CHECK (status IN ('coletando_slots', 'pipeline_rodando', 'respondendo', 'encerrado')),
  messages JSONB DEFAULT '[]',        -- LEGADO: histórico inline (será descontinuado)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions(user_id, updated_at DESC);
CREATE INDEX idx_sessions_relatorio ON sessions(relatorio_id);
```

**Observação:** o campo `messages` JSONB é legado. O histórico real persiste na tabela `messages` (abaixo). O `chat_state.py` ainda lê/escreve `messages` inline por compatibilidade, mas o frontend usa a tabela `messages`.

### 6.2 Tabela `messages`

```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  attachments JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id, timestamp DESC);
```

### 6.3 Risco: duplicidade de tabelas

A migration `20260610_chat_sessions.sql` criou `chat_sessions`. A migration posterior `20260610_chat_messages.sql` renomeia `chat_sessions` → `sessions` via `DO $$ ... ALTER TABLE ... RENAME`.  
Se ambas as migrations rodarem em ordem diferente ou se `chat_sessions` já tiver sido criado manualmente, pode haver conflito de schema. A tabela `sessions` é a fonte de verdade atual.

---

## 7. Endpoints da API

### 7.1 Conversação Principal

```http
POST /api/assistente/conversar
Authorization: Bearer <jwt>
Content-Type: application/json
```

**Request:**
```json
{
  "mensagem": "Quero abrir uma academia em João Pessoa no Bairro Cabo Branco...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "intencao": "novo_relatorio",
  "slots": {
    "cidade": "João Pessoa",
    "bairro": "Cabo Branco",
    "uf": "PB",
    "tamanho_preset": "m",
    "publico_alvo": "25-40",
    "tipo_negocio": "academia"
  },
  "slots_faltando": [],
  "resposta": "Perfeito! Estou preparando sua análise...",
  "relatorio_id": null,
  "status": "pronto_para_pipeline"
}
```

**Status possíveis:**
- `coletando_slots` — faltam dados obrigatórios ou opcionais
- `pronto_para_pipeline` — todos os slots preenchidos (o backend cria stub e enfileira)
- `pipeline_rodando` — stub criado, job enfileirado no RedisQueue
- `encerrado` — usuário disse "tchau" ou equivalente

### 7.2 Chat Q&A (Fallback)

```http
POST /api/assistente/chat
Authorization: Bearer <jwt>
Content-Type: application/json
```

Usado quando a intenção classificada é `pergunta_simples` ou `status_relatorio`. Chama `services/tinker_bot.chat_async()` que faz fallback automático para Gemini.

---

## 8. Fluxo Conversacional (Implementado)

```
┌─────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│   Usuário envia │────▶│ classificar_intencao│────▶│  encerrar / ajuda│
│   mensagem      │     │   (Gemini Flash)    │     │  pergunta_simples│
└─────────────────┘     └────────────────────┘     └──────────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │  novo_relatorio /  │
                    │  clarificacao      │
                    └────────┬───────────┘
                             ▼
                    ┌────────────────────┐
                    │  extrair_slots     │
                    │  (Gemini Flash)    │
                    └────────┬───────────┘
                             ▼
                    ┌────────────────────┐
                    │  _aplicar_defaults  │
                    │  (silencioso!)      │
                    └────────┬───────────┘
                             ▼
                    ┌────────────────────┐
                    │  _slots_a_perguntar │
                    └────────┬───────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │  Faltam slots   │           │  Todos ok       │
    │  → gerar_pergunta│          │  → pronto_para_ │
    │     _follow_up   │           │     pipeline    │
    └─────────────────┘           └─────────────────┘
                                          │
                                          ▼
                              ┌─────────────────────┐
                              │  api.py cria stub   │
                              │  + enqueue no Redis │
                              │  → pipeline_rodando │
                              └─────────────────────┘
```

### 8.1 Slots Obrigatórios

| Slot | Descrição |
|------|-----------|
| `cidade` | Cidade da nova unidade |
| `bairro` | Bairro da nova unidade |

### 8.2 Slots Opcionais (com Defaults)

| Slot | Default | Descrição |
|------|---------|-----------|
| `tamanho_preset` | `"m"` | pp (200–500m²), p (500–800), m (800–1500), g (1500–2500), gg (2500–5000) |
| `publico_alvo` | `"25-40"` | 18-25, 25-40, 30-50, 40+ |
| `genero_alvo` | `"misto"` | misto, predom_fem, predom_masc, excl_fem, excl_masc |
| `tipo_negocio` | `"academia"` | academia, crossfit_box, studio_pilates, studio_funcional, outro |
| `estacionamento_obrigatorio` | `true` | boolean |
| `uf` | inferido da cidade | estado |
| `area_m2_min`, `area_m2_max` | inferido do preset | área em m² |

---

## 9. Componentes de UI

### 9.1 ChatLayout
- Estrutura flex principal: sidebar (desktop) / drawer (mobile), header, área de mensagens, input.
- Auto-scroll para a última mensagem.
- Estado vazio com CTA de boas-vindas.
- Indicador "Analisando..." quando `isLoading`.

### 9.2 ChatMessage
- Bubbles com avatar (usuário vs. agente).
- `ReactMarkdown` + `remarkGfm` para renderização rica.
- Syntax highlight para blocos de código.
- Anexos com preview de imagem ou ícone de arquivo.
- Ações: Copiar, Regenerar (hover, desktop).

### 9.3 ChatInput
- Textarea auto-resize (max 200px).
- Upload de arquivos via `<input type="file">` (imagem, PDF, doc, planilha, txt, csv).
- Preview de anexos com remoção.
- Envio com `Enter` (Shift+Enter para nova linha).
- Validação: não envia se vazio e sem anexos.

### 9.4 ChatSidebar
- Desktop: aside fixo de 260px.
- Mobile: Sheet/drawer deslizante (280px).
- Lista de sessões com título truncado, status e botão "Nova".
- Suporte a delete (prop opcional).

### 9.5 useConversationalChat
- Estado: `messages`, `sessions`, `state` (`ConversationalState`), `isLoading`, `error`.
- `sendMessage`: POST para `/api/assistente/conversar`, persiste mensagens no Supabase.
- `newSession`: reseta estado para nova conversa.
- `selectSession`: carrega mensagens históricas da sessão.
- Títulos de sessão gerados a partir da cidade ou truncamento da primeira mensagem.

---

## 10. Decisões Arquiteturais (ADRs)

| Código | Decisão | Justificativa | Status |
|--------|---------|---------------|--------|
| **ADR-001** | Fallback Tinker → Gemini automático | Tinker retorna 402 (sem créditos). Fallback transparente para não quebrar UX. | Ativo. Tinker inativo até billing adicionado. |
| **ADR-002** | Pipeline A0–A9 inalterado | O agente conversacional é apenas uma nova camada de coleta que produz o mesmo `NovoRelatorioInput`. Reutiliza `create_relatorio_stub()` + RedisQueue. | Ativo. |
| **ADR-003** | Tabelas separadas `sessions` + `messages` | `chat_sessions` com `messages` JSONB inline não escala para busca/histórico. Nova tabela `messages` normalizada com JSONB `attachments`. | Ativo. Migration renomeia `chat_sessions` → `sessions`. |
| **ADR-004** | Slot-filling via LLM (Gemini Flash) em vez de regex/NER | Maior flexibilidade para linguagem natural, inferência de UF, sinônimos ("pequena" → "p"). | Ativo. |
| **ADR-005** | Anexos no chat input mas não processados | A UI permite anexar arquivos, mas o backend ainda não extrai entidades de anexos no fluxo conversacional. | Parcial. UI pronta, backend pendente. |

---

## 11. Bugs e Problemas Conhecidos

### ✅ BUG-001 — Slot-filling ignora incerteza do usuário (CORRIGIDO 2026-06-10)
**Severidade:** Alta. **Status:** Corrigido em `services/conversational_engine.py`.

**Comportamento (antes):** quando o usuário dizia *"Ainda não sei o modelo e o tamanho da nova unidade"*, o agente aplicava os defaults (`tamanho_preset: "m"`, `tipo_negocio: "academia"`) silenciosamente e disparava o pipeline.

**Causa raiz:** `processar_mensagem` aplicava `_aplicar_defaults` ANTES de verificar slots faltantes, mascarando o que ainda precisava ser perguntado. Não havia estado intermediário de confirmação.

**Correção aplicada:**
1. Prompt de extração agora retorna `incerto: string[]` quando o usuário declara não saber ("não sei", "tanto faz", "você decide"). Slots incertos ficam em `slots._incertos` na sessão (sem migration).
2. Defaults NÃO são mais aplicados durante a coleta — apenas após confirmação explícita. Slots incertos não são re-perguntados.
3. Novo estado `aguardando_confirmacao`: quando nada resta a perguntar, o agente apresenta proposta com cada valor assumido marcado como *(sugestão)* e pergunta "Posso seguir?". `_detectar_confirmacao` classifica a resposta em confirmar/ajustar/cancelar. Pipeline só dispara em `pronto_para_pipeline`, emitido exclusivamente após "confirmar".
4. Fluxo validado por testes de integração com LLM mockado (5 cenários: coleta com incerteza, proposta, ajuste, confirmação, cancelamento). `api.py` e frontend não precisaram de mudança (status é string passante).

### ✅ BUG-002 — Playwright `NotImplementedError` no Windows (CORRIGIDO 2026-06-10)
**Severidade:** Média. **Status:** Corrigido em `tools/listing_tools.py`.

**Comportamento (antes):** `fetch_commercial_listings_async` (A1 — listings OLX/ImovelWeb via `playwright.async_api`) falhava com `NotImplementedError` em `create_subprocess_exec`.

**Causa raiz:** no Windows, o loop principal (ADK/uvicorn) é `SelectorEventLoop`, que não implementa subprocess. Playwright precisa de `ProactorEventLoop`.

**Correção aplicada:** em vez de trocar a policy global (arriscado — ADK depende do Selector), os scrapes rodam num `ProactorEventLoop` próprio em thread dedicada (`_gather_scrapes_em_proactor` + `asyncio.to_thread`), só no `win32`. Mesma estratégia já usada em `tools/playwright_enrichment.py`. Mecanismo validado: subprocess executa na thread Proactor enquanto o loop principal Selector reproduz o erro original. BUG-003 (`listing_tools: fonte falhou`) deve sumir junto — monitorar logs do próximo pipeline.

### 🟡 BUG-003 — `listing_tools: fonte falhou`
**Severidade:** Média. **Status:** Aberto.

**Comportamento:** logs repetidos de `listing_tools: fonte falhou —` durante execução do pipeline.

**Causa raiz:** provavelmente A3 tentando buscar listings de academias e falhando (fonte indisponível, timeout, ou Playwright quebrado).

**Correção:** resolver BUG-002 primeiro; se persistir, investigar robustez do scraper.

### 🟡 BUG-004 — Duplicidade potencial de tabelas
**Severidade:** Baixa. **Status:** Monitorado.

**Causa raiz:** migration `20260610_chat_sessions.sql` criou `chat_sessions`; migration `20260610_chat_messages.sql` tenta renomear para `sessions`. Se `chat_sessions` foi criado fora da migration (manualmente), pode haver conflito.

**Correção:** verificar em produção se existem ambas as tabelas. Se sim, migrar dados e dropar `chat_sessions`.

### 🟡 BUG-005 — Vite não detecta novos arquivos sem reinício
**Severidade:** Baixa. **Status:** Conhecido.

**Comportamento:** ao criar novos componentes (ex: `ChatSidebar.tsx`), o HMR do Vite não os detecta até reiniciar `npm run dev`.

**Correção:** reiniciar o dev server após criar arquivos novos. Não afeta builds de produção.

---

## 12. Variáveis de Ambiente Críticas

| Variável | Descrição | Status |
|----------|-----------|--------|
| `TINKER_API_KEY` | Prefixo `tml-`, conta Thinking Machines | Inativa (sem billing) |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Gemini via google-genai | Ativa |
| `TINKER_FALLBACK_MODEL` | Modelo Gemini de fallback | `gemini-2.5-flash` |
| `SUPABASE_URL` | Endpoint Supabase | Ativa |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave de serviço Supabase | Ativa |

---

## 13. Próximos Passos (Prioridade)

1. ~~**Corrigir BUG-001 (slot-filling + incerteza)**~~ — ✅ feito 2026-06-10 (ver §11).
2. ~~**Corrigir BUG-002 (Playwright no Windows)**~~ — ✅ feito 2026-06-10 via thread Proactor isolada (ver §11).
3. **Remover campo `messages` JSONB legado** de `sessions` — usar apenas tabela `messages`.
4. **Implementar extração de anexos** — conectar `ChatInput` uploads ao backend (Gemini Vision para imagens/PDFs).
5. **Adicionar billing no Tinker** — para voltar a usar o modelo primário (Qwen3-8B) em vez de Gemini fallback.
6. **Implementar `UserProject` com contexto acumulativo** — evoluir de sessão de chat para projeto com estados `EM_CONVERSA`, `PESQUISANDO`, etc.
7. **Capabilities sob demanda** — desacoplar A0–A4 em ferramentas independentes acessíveis via function calling.

---

## 14. Histórico de Mudanças

| Data | Autor | Mudança |
|------|-------|---------|
| 2026-06-10 | Kimi Code CLI | Criação do documento as-built com registro do estado atual do Agente de IA Especialista em Fitness. |
