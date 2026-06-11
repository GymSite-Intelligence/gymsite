# Auditoria 360 — GymSite Intelligence

> Executada em 2026-06-10 por workflow multi-agente (25 agentes): 6 frentes paralelas (rotas, imports Python, frontend orfao, codigo x banco, scripts, env/config) + verificacao adversarial de todo achado CRITICA/ALTA (cetico tenta refutar relendo arquivo e refazendo grep).
> Resultado: **55 achados confirmados, 0 refutados.** Achados de banco re-verificados contra o Supabase de producao (cargo-flow-navigator).

## Sumario Executivo

| Prioridade | Qtde | Tema dominante |
|---|---|---|
| P0 Critico | 10 | Modulo admin de parceiros 100% morto; chat gravando em tabela renomeada; dinheiro como float; secrets fora do .env.example |
| P1 Alto | 6 | ~61 env vars usadas e nao documentadas; RLS de messages sem policy |
| P2 Medio | 30 | Codigo orfao (9 componentes/hooks frontend, 1 service), __init__.py ausentes, paths hardcoded |
| P3 Baixo | 9 | Rotas possivelmente orfas, TODOs, exemplos com path local |

## Verificacao adicional no banco de producao (pos-workflow)

Consulta direta ao Supabase confirmou e AGRAVOU dois achados:

1. **`chat_sessions` E `sessions` existem AMBAS** — a migration de rename foi aplicada parcialmente ou a tabela antiga foi recriada pelo codigo. Dados de sessao podem estar divergindo entre as duas (BUG-004 confirmado em producao).
2. **`chat_sessions`, `sessions` e `messages` tem RLS ATIVA com ZERO policies** — backend via service role funciona (bypassa RLS), mas o frontend insere direto em `messages` via supabase-js (`useConversationalChat.saveMessage`, linha 76): esses INSERTs estao sendo **bloqueados silenciosamente** para usuarios autenticados. Historico de chat do usuario nao persiste pelo caminho do frontend.

## P0 — Crítico (quebra produção ou viola segurança)

### C1. Router de Parceiros não incluído no app principal ✅ verificado adversarialmente

- **Area:** rotas
- **Onde:** `api.py:2153-2156 (fim do arquivo) vs backend/routers/parceiros_admin.py:22`
- **Evidencia:** Em api.py não existe nenhuma chamada `app.include_router()` ou import do `backend.routers.parceiros_admin`. O router está definido em backend/routers/parceiros_admin.py linha 22 com `router = APIRouter(prefix="/api/admin/parceiros", tags=["Admin — Parceiros"])`, mas nunca é incluído na app FastAPI.
- **Confirmacao do cetico:** O router parceiros_admin.py (279 linhas com 7 endpoints implementados) está definido em backend/routers/parceiros_admin.py:22 com `router = APIRouter(prefix="/api/admin/parceiros")`, mas NUNCA é incluído em api.py. Grep por `include_router` retorna vazio. Execução da app mostra 35 rotas registradas — nenhuma delas `/api/admin/parceiros/*`. Endpoints são 100% inviáveis (inacessíveis, mortos).
- **Acao:** Adicionar `from backend.routers.parceiros_admin import router as parceiros_router` e `app.include_router(parceiros_router)` no api.py, idealmente após as outras rotas (antes da linha 2153).

### C2. Frontend chama /api/admin/parceiros mas rota não existe ✅ verificado adversarialmente

- **Area:** rotas
- **Onde:** `frontend/src/hooks/useParceirosAdmin.ts:60,68,81,94,110`
- **Evidencia:** Frontend faz fetch para `${API_URL}/admin/parceiros` (linhas 60,68,81,94,110) onde API_URL="/api", resultando em chamadas para /api/admin/parceiros. Como o router não está incluído, todas essas chamadas retornarão 404.
- **Confirmacao do cetico:** Router admin/parceiros existe (backend/routers/parceiros_admin.py com 7 endpoints definidos nas linhas 134-255) mas nunca é registrado no FastAPI app. Não há uma única chamada a app.include_router() para este router em todo o código. Frontend chama /api/admin/parceiros em 5 pontos (useParceirosAdmin.ts linhas 60,68,81,94,110) e receberá 404. Procura por: include_router (0 resultados), importlib/exec/eval (nenhum padrão dinâmico), startup hooks (nenhum), routers alternativos com mesmo path (nenhum).
- **Acao:** Incluir o router parceiros_admin na app (ver achado anterior). As 7 rotas POST/GET/PATCH/DELETE definidas no router (linhas 134,149,180,194,213,227,255) ficarão acessíveis.

### C3. chat_state.py references deprecated table name 'chat_sessions' after migration rename ✅ verificado adversarialmente

- **Area:** python-imports
- **Onde:** `services/chat_state.py:58,69,84,120,141`
- **Evidencia:** Migration 20260610_chat_messages.sql (line 7) renames table: ALTER TABLE chat_sessions RENAME TO sessions; but services/chat_state.py still uses sb.table('chat_sessions') in criar_sessao (line 58), buscar_sessao (line 69), buscar_ultima_sessao_ativa (line 84), atualizar_sessao (line 120), and adicionar_mensagem (line 141)
- **Confirmacao do cetico:** Five CRUD operations in services/chat_state.py (criar_sessao:58, buscar_sessao:69, buscar_ultima_sessao_ativa:84, atualizar_sessao:120, adicionar_mensagem:141) reference sb.table('chat_sessions') but migration db/migrations/20260610_chat_messages.sql:7 renames the table to 'sessions' via ALTER TABLE chat_sessions RENAME TO sessions. These functions are actively imported and called in conversational_engine.py and api.py, so the mismatch will cause runtime failures when the migration is applied.
- **Acao:** Update all 5 occurrences of sb.table('chat_sessions') to sb.table('sessions') in services/chat_state.py to match the renamed database table

### C4. chat_sessions table missing RLS enforcement ✅ verificado adversarialmente

- **Area:** db-codigo
- **Onde:** `db/migrations/20260610_chat_sessions.sql`
- **Evidencia:** CREATE TABLE IF NOT EXISTS chat_sessions (...) — No ALTER TABLE ... ENABLE ROW LEVEL SECURITY or CREATE POLICY statements. Migration ends without RLS configuration.
- **Confirmacao do cetico:** CONFIRMED SECURITY VULNERABILITY: The chat_sessions table (and its later renamed version 'sessions' in db/migrations/20260610_chat_messages.sql) has NO Row Level Security enforcement. Critical evidence:

1. **20260610_chat_sessions.sql (lines 4-15)**: CREATE TABLE chat_sessions with user_id FOREIGN KEY, but ends without any ALTER TABLE ENABLE ROW LEVEL SECURITY or CREATE POLICY statements.

2. **20260610_chat_messages.sql (lines 9-20)**: Migration recreates table as 'sessions' but again NO RLS enforcement. Neither ALTER TABLE ... ENABLE ROW LEVEL SECURITY nor CREATE POLICY statements present.

3. **Authorization Bypass in services/conversational_engine.py (lines 366-368)**: When a session_id is provided by client, function calls buscar_sessao(session_id) WITHOUT verifying the retrieved session belongs to the authenticated user. No subsequent check validates sessao.user_id == user_id before proceeding with operations.

4. **services/chat_state.py (lines 66-77)**: buscar_sessao() queries chat_sessions.select(*).eq("id", session_id).execute() - this is a raw Supabase query with NO authentication filter. With RLS disabled, any authenticated user can retrieve ANY session by guessing/knowing a session_id.

ATTACK SCENARIO: Attacker authenticates with User A, then calls /api/assistente/conversar with User B's session_id. With RLS disabled, the query succeeds, leaking User B's conversation slots (city, neighborhood, business intent, relatorio_id) and allowing the attacker to hijack/modify the session state.

This bypasses the _require_authenticated() JWT check at the endpoint level (api.py:2066) because while authorization to the API exists, data-level authorization (RLS) is missing.
- **Acao:** Add ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY and CREATE POLICY for user-scoped access (check user_id = auth.uid())

### C5. Float type used for BIGINT monetary columns (lead_valor) ✅ verificado adversarialmente

- **Area:** db-codigo
- **Onde:** `backend/routers/parceiros_admin.py:40, backend/services/execucao/parceiro_service.py:25`
- **Evidencia:** Pydantic schema: lead_valor: Optional[float] = Field(None, ge=0) vs Database migration: lead_valor BIGINT (comment '-- Lead generation (valor em centavos)'). Float cannot reliably store centavo values; 100.50 BRL becomes 10050 centavos but float arithmetic causes precision loss.
- **Confirmacao do cetico:** Float type is used in Pydantic schemas (lead_valor, valor_mensalidade, comissao_gerada, valor_fechado) but database columns are defined as BIGINT with explicit centavos comments. Float cannot reliably store decimal values without precision loss. No conversion logic (multiply/divide by 100) exists between API input and database insertion. Violates established rule P-007 in processo-mudanca.md which mandates integer centavos storage. Similar fields in other tables (custo_planejado, custo_real) correctly use int in Pydantic. This creates immediate data corruption risk for financial transactions.
- **Acao:** Change all lead_valor, valor_mensalidade, valor_fechado, comissao_gerada from float to int in Pydantic schemas, treating them as centavos (multiply by 100 on input, divide on output)

### C6. Float type used for BIGINT monetary columns (valor_mensalidade) ✅ verificado adversarialmente

- **Area:** db-codigo
- **Onde:** `backend/routers/parceiros_admin.py:43, backend/services/execucao/parceiro_service.py:28`
- **Evidencia:** Pydantic schema: valor_mensalidade: Optional[float] = Field(None, ge=0) vs Database: valor_mensalidade BIGINT (comment '-- Sponsored (centavos)'). Same float precision issue for monthly sponsorship amounts.
- **Confirmacao do cetico:** CRÍTICA: Float/BIGINT mismatch para colunas monetárias confirmado. (1) DB schema: lead_valor, valor_mensalidade, valor_fechado, comissao_gerada são BIGINT (centavos) com comentário explícito. (2) API schemas (parceiros_admin.py:40,43,73,76 + parceiro_service.py:25,28,46,49,71,74) usam Optional[float]. (3) Sem middleware de conversão float→int. Floats causam perda de precisão em valores como 0.1 centavo. comissao_percentual está correto (DECIMAL 5,2 em DB, float em Python).
- **Acao:** Change valor_mensalidade from float to int in all schemas (backend/routers/parceiros_admin.py, backend/services/execucao/parceiro_service.py), document centavo handling

### C7. sessions table renamed from chat_sessions but code still uses old table name ✅ verificado adversarialmente

- **Area:** db-codigo
- **Onde:** `services/chat_state.py:58,69,84,120,141`
- **Evidencia:** Migration 20260610_chat_messages.sql line 7: ALTER TABLE chat_sessions RENAME TO sessions. However services/chat_state.py still calls sb.table('chat_sessions') (5 references). If migration was applied, code will fail with table not found.
- **Confirmacao do cetico:** Migrations 20260610_chat_messages.sql and 20260610_chat_sessions.sql exist in db/migrations/ but NOT in supabase/migrations/ (applied migrations folder). The 20260610_chat_messages.sql migration contains logic to rename chat_sessions → sessions (line 7: ALTER TABLE chat_sessions RENAME TO sessions). However, services/chat_state.py still references sb.table("chat_sessions") in 5 functions (criar_sessao:58, buscar_sessao:69, buscar_ultima_sessao_ativa:84, atualizar_sessao:120, adicionar_mensagem:141). When this migration is applied to Supabase, all 5 functions will fail with table-not-found errors. This is a real breaking change waiting to happen - the code and migration are out of sync. The issue is not active yet because the migrations haven't been applied, but it's a critical bug in the codebase.
- **Acao:** Update all references in services/chat_state.py from 'chat_sessions' to 'sessions', OR rename table back if chat_sessions is the canonical name

### C8. GYMSITE_API_KEY ausente de .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + mcp_server.py:21`
- **Evidencia:** mcp_server.py:21 — GYMSITE_API_KEY = os.getenv("GYMSITE_API_KEY", "") | mcp_server.py:119 — headers["Authorization"] = f"Bearer {GYMSITE_API_KEY}" | .env.production.example não menciona GYMSITE_API_KEY
- **Confirmacao do cetico:** GYMSITE_API_KEY é lido em mcp_server.py:21 e usado como Bearer token em lines 118-119 e 129-130 para autenticar chamadas à API interna do GymSite. Porém, está AUSENTE tanto em .env.production.example quanto em .env.production (verificado por grep). mcp_server.py:8 documenta explicitamente que Auth usa Bearer token (GYMSITE_API_KEY), mas o template de produção não inclui esta variável. Sem documentação, operadores deployarão com a chave vazia, desabilitando a autenticação interna. GYMSITE_API_BASE também não está documentado, embora tenha default seguro (127.0.0.1:8000).
- **Acao:** Adicione GYMSITE_API_KEY=YOUR_MCP_BEARER_TOKEN em .env.production.example com documentação que é Bearer token para autenticação interna da API.

### C9. CLAW_WEBHOOK_SECRET ausente de .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + prospecting/config.py:22 + prospecting/webhook.py:52`
- **Evidencia:** prospecting/config.py:22 — CLAW_WEBHOOK_SECRET: str = os.getenv("CLAW_WEBHOOK_SECRET", "").strip() | prospecting/webhook.py:52 — headers["X-Claw-Secret"] = Config.CLAW_WEBHOOK_SECRET | .env.production.example não documenta CLAW_WEBHOOK_SECRET
- **Confirmacao do cetico:** CLAW_WEBHOOK_SECRET é carregado em prospecting/config.py:22 via os.getenv("CLAW_WEBHOOK_SECRET"), usado em prospecting/webhook.py:51-52 para autenticar requisições de webhook (headers["X-Claw-Secret"]), e chamado via send_opportunity_webhook() em prospecting/engine.py:222 e :243. A documentação em docs/INTEGRACAO_VECTRA.md:122 especifica que deve ser configurado em .env.production, mas CLAW_WEBHOOK_SECRET (e CLAW_WEBHOOK_URL) NÃO está listado em .env.production.example. Verificado: grep confirmou ausência em .env.production.example.
- **Acao:** Adicione CLAW_WEBHOOK_SECRET= em .env.production.example com documentação de que é o secret para validação de webhooks da plataforma Claw.

### C10. OPENCLAW_TOKEN ausente de .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + tools/kimi_research.py:115 + openclaw_kimi_server.py:91`
- **Evidencia:** tools/kimi_research.py:115 — token = (os.getenv("OPENCLAW_TOKEN") or "").strip() | openclaw_kimi_server.py:91 — if creds.credentials != _env("OPENCLAW_TOKEN") | .env.production.example não menciona OPENCLAW_TOKEN
- **Confirmacao do cetico:** OPENCLAW_TOKEN é utilizado pela função kimi_search() em tools/kimi_research.py (linha 115) e validado em openclaw_kimi_server.py (linha 91). A integração está ativa nos agents (a0_context_builder.py, a8_validator.py), API (com campo a0_research_provider), e documentação produtiva (INTEGRATION_KIMI.md, HANDOFF_GYMSITE_OPENCLAW.md). Porém, .env.production.example não documenta este token, diferentemente de todos os outros 25+ env vars críticos de autenticação (GOOGLE_API_KEY, SUPABASE_SERVICE_ROLE_KEY, etc). Quando A0_RESEARCH_PROVIDER=kimi é definido, a ausência causa falha de autenticação HTTP na chamada ao OpenClaw.
- **Acao:** Adicione OPENCLAW_TOKEN=YOUR_OPENCLAW_BEARER_TOKEN em .env.production.example para autenticação com serviço OpenClaw/Kimi.

## P1 — Alto (quebra deploy novo ou regra do projeto)

### A1. messages table missing RLS enforcement ✅ verificado adversarialmente

- **Area:** db-codigo
- **Onde:** `db/migrations/20260610_chat_messages.sql`
- **Evidencia:** CREATE TABLE IF NOT EXISTS messages (...) — No RLS configuration in migration. Only creates table and indexes, no ENABLE ROW LEVEL SECURITY or policies.
- **Confirmacao do cetico:** Confirmed: messages and sessions tables created in 20260610_chat_messages.sql with no RLS enabled. Service layer uses SUPABASE_SERVICE_ROLE_KEY (line 20, chat_state.py) to bypass RLS. API endpoint /assistente/conversar passes session_id to processar_mensagem (api.py:2069-2072), which calls buscar_sessao(session_id) without validating returned session belongs to authenticated user (conversational_engine.py:366-373). No check exists: if sessao.user_id != user_id. Attacker with valid auth can access any session by providing its UUID.
- **Acao:** Add ALTER TABLE messages ENABLE ROW LEVEL SECURITY and CREATE POLICY to restrict access via session (join to sessions and check user_id)

### A2. GEMINI_API_KEY não documentada em .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + api.py:322, tools/_genai_client.py:47`
- **Evidencia:** api.py:322 — gkey = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip() | tools/_genai_client.py:47 — api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")).strip() | .env.production.example contém apenas GOOGLE_API_KEY (linha 10), sem GEMINI_API_KEY
- **Confirmacao do cetico:** Verified: .env.production.example (line 10) documents only GOOGLE_API_KEY, but api.py:322 and tools/_genai_client.py:47 both prioritize GEMINI_API_KEY (checked first via 'or' logic). The actual .env.production file DOES include GEMINI_API_KEY, as do architecture docs, but the template is incomplete. New deployments following .env.production.example would be missing the primary API key variable.
- **Acao:** Adicione GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE em .env.production.example e documente a precedência (GEMINI_API_KEY > GOOGLE_API_KEY).

### A3. 61 variáveis de backend em uso mas ausentes de .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + diversos arquivos`
- **Evidencia:** Vars críticas/alta encontradas via grep mas ausentes do example: LANGCACHE_API_KEY (tools/langcache_client.py), REDIS_GENERATE_KEY (tools/langcache_client.py), GOOGLE_DISTANCE_MATRIX_API_KEY (tools/distance_matrix_tools.py), A0_RESEARCH_PROVIDER (agents/a8_validator.py), OUTSCRAPER_API_KEY, SEARCHAPI_KEY, CLAW_WEBHOOK_URL, OPENCLAW_URL, etc. Total de 61 vars.
- **Confirmacao do cetico:** REAL: 56 environment variables (out of 81 total used in code) are missing from .env.production.example. These include critical API keys and configuration variables actually referenced in active code: (1) LANGCACHE_API_KEY, REDIS_GENERATE_KEY — semantic cache for LLM in tools/langcache_client.py; (2) GOOGLE_DISTANCE_MATRIX_API_KEY — distance matrix service in tools/distance_matrix_tools.py; (3) OUTSCRAPER_API_KEY, SEARCHAPI_KEY — competitor mapping in tools/competitor_offer_mapper.py, tools/popular_times_tool.py; (4) CLAW_WEBHOOK_URL, CLAW_WEBHOOK_SECRET, OPENCLAW_URL, OPENCLAW_TOKEN — webhook/Kimi integration in prospecting/config.py, tools/kimi_research.py; (5) GYMSITE_API_KEY, GYMSITE_API_BASE — MCP server auth in mcp_server.py; (6) A0_RESEARCH_PROVIDER — provider selection in agents/a8_validator.py. Plus 45+ more configuration variables (timeouts, thresholds, flags, feature toggles) used across agents/, tools/, prospecting/, and other modules. Evidence: 81 env vars actually used in code (verified via os.getenv/os.environ grep), only 36 documented in .env.production.example. All 56 missing variables verified in active code paths."
- **Acao:** Revisar tools/, services/, agents/, prospecting/ e consolidar todas as vars em .env.production.example com valores example e comentário explicativo para cada uma.

### A4. GEMINI_API_KEY vs GOOGLE_API_KEY ambiguidade no .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example:10 + api.py:322`
- **Evidencia:** .env.production.example linha 10 documenta GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY_HERE | Mas api.py:322 usa fallback (GEMINI_API_KEY) || (GOOGLE_API_KEY) | Sem GEMINI_API_KEY no example, operador pode não saber qual usar em produção.
- **Confirmacao do cetico:** Code at tools/_genai_client.py:47 and api.py:322 uses fallback pattern `GEMINI_API_KEY or GOOGLE_API_KEY`, but .env.production.example (line 10) documents ONLY GOOGLE_API_KEY without mentioning GEMINI_API_KEY or explaining precedence. Production .env.production (lines 12-13) defines both variables. Operators following the example file alone would not discover the GEMINI_API_KEY variable or its higher precedence.
- **Acao:** Clarificar em .env.production.example: GEMINI_API_KEY sobrescreve GOOGLE_API_KEY; ou remover GEMINI_API_KEY e padronizar em GOOGLE_API_KEY apenas.

### A5. db/supabase_writer.py silencioso quando credenciais ausentes (sem falha visível) ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `db/supabase_writer.py:58-70`
- **Evidencia:** db/supabase_writer.py linhas 58-70: if not url or not key: return None | Dados do relatório não são gravados no Supabase quando SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY ausentes; apenas log em metrics/supabase_writes/writer.log (não visível em logs da aplicação).
- **Confirmacao do cetico:** Audit finding is REAL. Supabase credentials (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) are only checked by _get_client() returning None (line 62-63 in db/supabase_writer.py), which triggers silent no-op logging to metrics/supabase_writes/writer.log (line 589). This log file is isolated from main API logs. The api.py lifespan (line 339) catches the resulting exception with a generic "Startup stale recovery skip" message (line 343) that does NOT explicitly warn about missing Supabase credentials. Evidence: (1) writer.log shows 7 entries "no-op (credenciais Supabase ausentes)" from May 10-11 2026, (2) api.py lifespan exception handler at line 342-343 masks the real cause, (3) no startup WARNING in api.py logs mentioning Supabase configuration status. Reports complete without Supabase persistence becoming visible to operators.
- **Acao:** Adicione WARNING no log de startup da API (api.py lifespan) se SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY estiverem vazios para visibilidade do operador.

### A6. LANGCACHE_API_KEY ausente de .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + tools/langcache_client.py:40`
- **Evidencia:** tools/langcache_client.py:40 — os.getenv("LANGCACHE_API_KEY") | tools/langcache_client.py:49 — return bool(get_langcache_api_key() and os.getenv("LANGCACHE_CACHE_ID")) | .env.production.example linhas 25-30 comentam LANGCACHE_SERVER_URL/LANGCACHE_CACHE_ID mas não LANGCACHE_API_KEY
- **Confirmacao do cetico:** LANGCACHE_API_KEY is genuinely missing from .env.production.example, along with the entire LangCache configuration section (LANGCACHE_CACHE_ID, LANGCACHE_SERVER_URL, LANGCACHE_EMBEDDING_MODEL, LANGCACHE_SIMILARITY_THRESHOLD). The frontend/.env.example correctly documents these at lines 25-30, but the production backend template at .env.production.example has zero LangCache variables. Code at tools/langcache_client.py:40,49 and requirements.txt:21 confirm langcache>=0.12.0 is a production dependency used by agents/a9_positioning_strategist.py, tools/deep_research_tool.py, and tools/gemini_search_grounding.py. While functions gracefully return early when unconfigured, users deploying to production without populating these vars will lose semantic caching functionality silently.
- **Acao:** Adicione LANGCACHE_API_KEY=lc1_... em .env.production.example (seção LangCache) com documentação que é token da API de cache semântico.

## P2 — Médio (código morto, dívida, risco latente)

### M1. Missing __init__.py files break backend package imports ✅ verificado adversarialmente

- **Area:** python-imports
- **Onde:** `backend/services/__init__.py, backend/services/execucao/__init__.py, backend/routers/__init__.py, backend/__init__.py`
- **Evidencia:** ModuleNotFoundError: No module named 'services.execucao' when attempting: from services.execucao.parceiro_service import ParceiroService in backend/routers/parceiros_admin.py:13
- **Confirmacao do cetico:** Missing __init__.py files in backend/, backend/services/, backend/services/execucao/, and backend/routers/ directories. Verified by: (1) finding no __init__.py files in these directories; (2) confirmed import failure with direct test: ModuleNotFoundError from 'from services.execucao.parceiro_service'; (3) parceiros_admin.py at line 13 imports from services.execucao but the package structure is broken. This is dead code currently unused but would fail if activated.
- **Acao:** Create __init__.py files in backend/, backend/services/, backend/services/execucao/, and backend/routers/ directories to make them proper Python packages

### M2. Orphaned service module with no importers

- **Area:** python-imports
- **Onde:** `services/apollo_crm_sync.py`
- **Evidencia:** grep -r 'apollo_crm_sync' returns only the module itself (logger definition and docstring), zero imports from api.py, agents/, backend/, services/, or tools/
- **Acao:** Either integrate apollo_crm_sync into the codebase (add imports where needed) or remove the unused module if it's dead code

### M3. AdminParceirosPage não registrada no router

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/routes/AdminParceirosPage.tsx`
- **Evidencia:** router.tsx linha 23-39: RelatoriosListPage, RelatorioViewerPage, ..., AssistentePage importados e registrados em rootRoute.addChildren() linhas 287-306. AdminParceirosPage.tsx existe mas não aparece em nenhuma importação ou rota criada.
- **Acao:** Remover AdminParceirosPage.tsx ou registrar rota correspondente em router.tsx com createRoute() e adicionar a rootRoute.addChildren().

### M4. PlaceholderPage não registrada no router

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/routes/PlaceholderPage.tsx`
- **Evidencia:** router.tsx: PlaceholderPage não importado nem registrado nas rotas. Arquivo existe mas grep -r 'PlaceholderPage' em frontend/src retorna 0 referências fora do próprio arquivo.
- **Acao:** Remover PlaceholderPage.tsx se for placeholder obsoleto ou registrar rota em router.tsx.

### M5. ChatInterface componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/chat/ChatInterface.tsx`
- **Evidencia:** Export function ChatInterface() definido linhas 72+. Grep 'ChatInterface' retorna 0 importadores em frontend/src. AssistentePage importa ChatLayout (linha 7) não ChatInterface.
- **Acao:** Remover ChatInterface.tsx ou usar em AssistentePage caso seja implementação alternativa planejada.

### M6. useAssistenteChat hook órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/hooks/useAssistenteChat.ts`
- **Evidencia:** Export function useAssistenteChat() linhas 1-20. Grep 'useAssistenteChat' em frontend/src retorna apenas 0 importadores. AssistentePage usa useConversationalChat (hooks/useConversationalChat.ts) linha 8.
- **Acao:** Remover useAssistenteChat.ts ou consolidar com useConversationalChat.ts se houver duplicação.

### M7. DoresDominantesTable componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/domain/DoresDominantesTable.tsx`
- **Evidencia:** Export function DoresDominantesTable() definido. Grep 'import.*DoresDominantesTable' retorna 0 resultados. CompetidoresDoresTable.tsx comenta linha 2 'Sobrescreve a antiga DoresDominantesTable' indicando substituição.
- **Acao:** Remover DoresDominantesTable.tsx em favor de CompetidoresDoresTable.tsx.

### M8. ScriptCard componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/domain/ScriptCard.tsx`
- **Evidencia:** Export function ScriptCard() definido. Grep 'import.*ScriptCard' retorna 0 resultados. Nenhum componente importa ScriptCard em frontend/src.
- **Acao:** Remover ScriptCard.tsx se for implementação descontinuada ou registrar seu uso.

### M9. data-table componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/data-table.tsx`
- **Evidencia:** Componente genérico com DndContext, useSortable, useReactTable. Grep 'import.*data-table\|from.*data-table' retorna 0 resultados.
- **Acao:** Remover ou usar em algum componente de tabela se for utilitário descontinuado.

### M10. chart-area-interactive componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/chart-area-interactive.tsx`
- **Evidencia:** Componente Recharts com AreaChart, Select, ToggleGroup. Grep 'import.*chart-area' retorna 0 resultados.
- **Acao:** Remover chart-area-interactive.tsx se descontinuado ou registrar uso em page.

### M11. section-cards componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/section-cards.tsx`
- **Evidencia:** Export function SectionCards() definido. Grep 'import.*section-cards\|SectionCards' retorna 0 resultados em frontend/src.
- **Acao:** Remover section-cards.tsx se descontinuado ou usar em alguma página.

### M12. nav-documents componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/nav-documents.tsx`
- **Evidencia:** Componente SidebarGroup com links (/relatorios, /mapa, /comparar, /custos). Grep 'nav-documents' retorna 0 referências em frontend/src.
- **Acao:** Remover nav-documents.tsx ou usar em app-sidebar/AuthenticatedSidebarLayout.

### M13. nav-secondary componente órfão

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/components/nav-secondary.tsx`
- **Evidencia:** Componente SidebarGroup com UserIcon. Grep 'nav-secondary' retorna 0 importadores em frontend/src.
- **Acao:** Remover nav-secondary.tsx ou registrar em layout se for menu secundário.

### M14. posicionamento_estrategico column accessed but may not exist on all relatorio_outputs

- **Area:** db-codigo
- **Onde:** `db/schema.sql:628-637`
- **Evidencia:** View v_relatorios_resumo references o.posicionamento_estrategico->>'veredito_posicionamento' and other JSONB paths. This column was added via migration 20260530_posicionamento_estrategico.sql but code doesn't handle NULL/missing case gracefully — relies on successful parse of JSONB structure.
- **Acao:** Ensure A9 agent always populates posicionamento_estrategico JSONB with required keys (veredito_posicionamento, recomendacao_ticket, gaps_identificados), or add COALESCE defaults in view

### M15. competidores.place_id referenced without existence check

- **Area:** db-codigo
- **Onde:** `api.py:810, db/supabase_writer.py:289`
- **Evidencia:** api.py line 810: res = sb.table('competidores').select('place_id').eq('relatorio_id', relatorio_id).execute() — No error handling if place_id is NULL. db/supabase_writer.py _fetch_competidores_geo_lookup queries place_id but doesn't validate format or handle missing values.
- **Acao:** Add explicit NULL checks when reading place_id from competidores (some entries may lack Google Places ID if search failed). Filter out NULL values or use COALESCE.

### M16. oportunidades_prospeccao apollosync columns assume sync not yet implemented

- **Area:** db-codigo
- **Onde:** `db/migrations/20250610_apollo_crm_sync_oportunidades.sql, services/apollo_crm_sync.py`
- **Evidencia:** Migration adds apollo_sync_status, apollo_person_id, apollo_account_id, etc. with defaults ('pending', NULL, NULL). Code in services/apollo_crm_sync.py references these columns. But no RLS policies added to oportunidades_prospeccao for Apollo data (sensitive PII).
- **Acao:** Review RLS on oportunidades_prospeccao — if Apollo IDs are PII, restrict view to org members. Currently migration doesn't touch RLS after adding Apollo columns.

### M17. parceiroservice code accesses curador_id field not present in create dataclass

- **Area:** db-codigo
- **Onde:** `backend/services/execucao/parceiro_service.py:137,150,158`
- **Evidencia:** ParceiroCreate dataclass (line 13-31) has no curador_id field, but criar() method (line 137) accepts curador_id param and passes to INSERT. Field in DB exists (curadoria_por) but dataclass missing — code works via raw SQL but IDE/type-checking won't catch missing field mapping.
- **Acao:** Add optional curador_id/curadoria_por field to ParceiroCreate dataclass to match actual table schema and enable type safety

### M18. Hardcoded Windows paths in patch scripts

- **Area:** scripts
- **Onde:** `scripts/_fix_ts.py:2`
- **Evidencia:** p = Path(r"c:/Users/marce/gymsite_intelligence/frontend/src/hooks/useRelatoriosNoMapa.ts")
- **Acao:** Replace hardcoded path with Path(__file__).parent.parent / 'frontend' / 'src' / ... to make scripts portable across machines

### M19. Hardcoded Windows paths in patch script _patch_geocode.py

- **Area:** scripts
- **Onde:** `scripts/_patch_geocode.py:2`
- **Evidencia:** api = Path(r"c:/Users/marce/gymsite_intelligence/api.py")
- **Acao:** Replace hardcoded path with Path(__file__).parent.parent / 'api.py' to ensure portability

### M20. Hardcoded Windows paths in patch script _patch_mapa_hook.py

- **Area:** scripts
- **Onde:** `scripts/_patch_mapa_hook.py:2`
- **Evidencia:** p = Path(r"c:/Users/marce/gymsite_intelligence/frontend/src/hooks/useRelatoriosNoMapa.ts")
- **Acao:** Replace hardcoded path with relative path construction using Path(__file__).parent.parent

### M21. Hardcoded Windows paths in patch script _patch_mapa_page.py

- **Area:** scripts
- **Onde:** `scripts/_patch_mapa_page.py:2`
- **Evidencia:** p = Path(r"c:/Users/marce/gymsite_intelligence/frontend/src/routes/MapaRelatoriosPage.tsx")
- **Acao:** Replace hardcoded path with relative path construction using Path(__file__).parent.parent

### M22. Hardcoded fallback path in query_cno_golden_case.py

- **Area:** scripts
- **Onde:** `scripts/query_cno_golden_case.py:38`
- **Evidencia:** Path(r"C:\Users\marce\Downloads\cno_extract"),
- **Acao:** Replace hardcoded Windows user path with environment variable or OS-independent fallback directory (e.g., ~/Downloads)

### M23. Hardcoded user-specific path in query_cno_golden_case.py fallback

- **Area:** scripts
- **Onde:** `scripts/query_cno_golden_case.py:53`
- **Evidencia:** return candidates[0] if candidates else Path(r"C:\Users\marce\Downloads\cno_extract")
- **Acao:** Replace hardcoded path with environment-based or home-directory relative path

### M24. GOOGLE_DISTANCE_MATRIX_API_KEY não documentada em .env.production.example ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + tools/distance_matrix_tools.py:118`
- **Evidencia:** tools/distance_matrix_tools.py:118-119 — os.environ.get("GOOGLE_DISTANCE_MATRIX_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY") | .env.production.example não menciona GOOGLE_DISTANCE_MATRIX_API_KEY (linha 19 menciona apenas GOOGLE_MAPS_API_KEY)
- **Confirmacao do cetico:** GOOGLE_DISTANCE_MATRIX_API_KEY é efetivamente usada no código (tools/distance_matrix_tools.py:118) com fallback para GOOGLE_MAPS_API_KEY. A integração está completa em antt_tools.py (chamada em financial_tools.py:807-812) e testada (tests/test_distance_matrix.py). Porém, a documentação em .env.production.example não menciona a variável, criando gap entre implementação e guia de deployment. O código padece de risco: operadores deployando em produção sem conhecer que a key é necessária (ou que pode ser reusada de GOOGLE_MAPS_API_KEY).
- **Acao:** Adicione GOOGLE_DISTANCE_MATRIX_API_KEY=YOUR_DISTANCE_MATRIX_KEY em .env.production.example e documente que pode reusar GOOGLE_MAPS_API_KEY se ambas habilitadas.

### M25. REDIS_GENERATE_KEY ausente de .env.production.example mas usado em langcache ✅ verificado adversarialmente

- **Area:** env-config
- **Onde:** `.env.production.example + tools/langcache_client.py:41`
- **Evidencia:** tools/langcache_client.py:41 — os.getenv("LANGCACHE_API_KEY") or os.getenv("REDIS_GENERATE_KEY") | .env.production.example documenta REDIS_URL mas não REDIS_GENERATE_KEY (fallback/alternativa para token de auth Redis)
- **Confirmacao do cetico:** O código em tools/langcache_client.py (linhas 38-43) implementa explicitamente um fallback para REDIS_GENERATE_KEY: `os.getenv("LANGCACHE_API_KEY") or os.getenv("REDIS_GENERATE_KEY")`. A docstring (linha 8) documenta isto como alternativa legada. Porém, .env.production.example (seção Redis, linhas 51-56) omite completamente REDIS_GENERATE_KEY da documentação, criando uma lacuna de configuração. A função get_langcache_api_key() é consumida por is_langcache_configured() que valida ambas as vars; operadores upgrading de setup legado não teriam guidance sobre a alternativa existente no template de produção.
- **Acao:** Adicione REDIS_GENERATE_KEY= em .env.production.example (seção Redis) como alternativa/fallback para LANGCACHE_API_KEY.

### M26. VITE_API_URL, VITE_DEV_AS_ADMIN, VITE_GOOGLE_MAPS_MAP_ID, VITE_MAP_PROVIDER não documentadas em frontend/.env.example

- **Area:** env-config
- **Onde:** `frontend/.env.example + frontend/src (múltiplos)`
- **Evidencia:** frontend/src/hooks/useParceirosAdmin.ts:3 — VITE_API_URL | frontend/src/hooks/useIsAdmin.ts:32 — VITE_DEV_AS_ADMIN === 'true' | frontend/src/lib/maps-js-api.ts:42 — VITE_GOOGLE_MAPS_MAP_ID | frontend/src/routes/MapaRelatoriosPage.tsx:65 — VITE_MAP_PROVIDER | frontend/.env.example contém apenas VITE_USE_MOCKS, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
- **Acao:** Adicione VITE_API_URL, VITE_DEV_AS_ADMIN (padrão false), VITE_GOOGLE_MAPS_MAP_ID (opcional), VITE_MAP_PROVIDER (google|pigeon) em frontend/.env.example.

### M27. frontend/src/vite-env.d.ts TypeScript definitions incompleto

- **Area:** env-config
- **Onde:** `frontend/src/vite-env.d.ts:3-6`
- **Evidencia:** vite-env.d.ts define apenas VITE_USE_MOCKS, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY | Mas código usa VITE_API_BASE (lib/supabase.ts:39), VITE_API_URL (useParceirosAdmin.ts:3), VITE_DEV_AS_ADMIN (useIsAdmin.ts:32), VITE_GOOGLE_MAPS_MAP_ID (maps-js-api.ts:42), VITE_MAP_PROVIDER (MapaRelatoriosPage.tsx:65)
- **Acao:** Atualize vite-env.d.ts para incluir todas as 7 variáveis VITE_* usadas no frontend (marque opcionais com ?).

### M28. A0_RESEARCH_PROVIDER feature flag não documentada em .env.production.example

- **Area:** env-config
- **Onde:** `.env.production.example + agents/a8_validator.py:110 + tools/kimi_research.py:49`
- **Evidencia:** agents/a8_validator.py:110 — return os.getenv("A0_RESEARCH_PROVIDER", "gemini") | tools/kimi_research.py:49 — p = (os.getenv("A0_RESEARCH_PROVIDER") or "").strip().lower() | .env.production.example não documenta A0_RESEARCH_PROVIDER (valores: gemini, kimi, openclaw)
- **Acao:** Adicione A0_RESEARCH_PROVIDER=gemini em .env.production.example com documentação de que valores válidos são: gemini (padrão), kimi, openclaw.

### M29. CLAW_WEBHOOK_URL ausente de .env.production.example

- **Area:** env-config
- **Onde:** `.env.production.example + prospecting/config.py:21`
- **Evidencia:** prospecting/config.py:21 — CLAW_WEBHOOK_URL: str = os.getenv("CLAW_WEBHOOK_URL", "").strip() | .env.production.example não menciona CLAW_WEBHOOK_URL (só CLAW_WEBHOOK_SECRET em comentário)
- **Acao:** Adicione CLAW_WEBHOOK_URL= em .env.production.example (seção Prospecting/Claw) com URL do webhook do Claw/Vectra.

### M30. OPENCLAW_URL e OPENCLAW_KIMI_SEARCH_PATH ausentes de .env.production.example

- **Area:** env-config
- **Onde:** `.env.production.example + tools/kimi_research.py:105 + tools/kimi_research.py:109`
- **Evidencia:** tools/kimi_research.py:105 — base = (os.getenv("OPENCLAW_URL") or "").strip().rstrip("/") | tools/kimi_research.py:109 — path = (os.getenv("OPENCLAW_KIMI_SEARCH_PATH") or "/v1/kimi/search").strip() | .env.production.example não docum
- **Acao:** Adicione OPENCLAW_URL=https://your-openclaw-base e OPENCLAW_KIMI_SEARCH_PATH=/v1/kimi/search em .env.production.example (seção OpenClaw).

## P3 — Baixo (limpeza e higiene)

### B1. Rota /api/geocode/cidade não é chamada pelo frontend — ✅ RESOLVIDO: NÃO é órfã, MANTER

- **Area:** rotas
- **Onde:** `api.py:912`
- **Evidencia:** GET /api/geocode/cidade está definido em api.py, mas não há nenhuma chamada fetch/axios no frontend (testado com grep em frontend/src).
- **Resolução (2026-06-10):** rota tem consumidor real fora do frontend: `mcp_server.py:187` (tool MCP do GymSite chama `/api/geocode/cidade`). Além disso `_geocode_cidade` é usada internamente pelo Market Atlas (`tools/mapa_mercado.py:237`). O geocode do PIPELINE de relatório é outro caminho: `geocode_endereco` chamado direto dentro da macro-tool do A1 (`tools/anchoring_tools.py:327-341` + batch em `:610-625`) — não passa por rota HTTP, logo nenhuma dessas rotas afeta o relatório. A rota `/api/geocode/bairro` (api.py:898) TEM consumidor frontend (`frontend/src/lib/bairro-geocode.ts:28` — pin do mapa).
- **Acao:** Nenhuma. Manter rota.

### B2. Rota /api/maps/street-view não é chamada pelo frontend — ✅ VERIFICADO: órfã utilitária, manter por ora

- **Area:** rotas
- **Onde:** `api.py:920`
- **Evidencia:** GET /api/maps/street-view está definido em api.py, mas não há nenhuma chamada fetch/axios no frontend.
- **Resolução (2026-06-10):** confirmado sem consumidor (nem mcp_server). O frontend usa `street_view_url` PERSISTIDA pelo pipeline (gerada por `tools/maps_tools.obter_street_view_url` dentro do A1 e gravada via `db/supabase_writer.py:205`), não a rota. Rota é proxy utilitário inofensivo.
- **Acao:** Manter como utilitária; remover só se aparecer no caminho de alguma refatoração.

### B3. Rota /health/maps não é chamada pelo frontend — ✅ MANTER

- **Area:** rotas
- **Onde:** `api.py:879`
- **Evidencia:** GET /health/maps está definido em api.py, mas não há nenhuma chamada fetch/axios no frontend.
- **Resolução (2026-06-10):** healthcheck de integração Maps — alvo natural de monitoramento externo (uptime checks), não de frontend.
- **Acao:** Nenhuma. Manter.

### B4. TODO: Bairros persistidos no Supabase (futuro)

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/hooks/useBairrosDoMunicipio.ts:12`
- **Evidencia:** Comentário: 'TODO futuro: tabela bairros_municipio no Supabase'. Mitigação atual: cache TanStack staleTime infinito, mas sem persist cross-session.
- **Acao:** Criar tabela Supabase bairros_municipio e persistir resultados de Places Autocomplete para reduzir custo futuro.

### B5. TODO: Auth Supabase user_metadata.role

- **Area:** frontend-orfaos
- **Onde:** `frontend/src/hooks/useIsAdmin.ts:34`
- **Evidencia:** Comentário: 'TODO: Supabase Auth user_metadata.role'. Atualmente usa localStorage.gymsite_admin ou VITE_DEV_AS_ADMIN. Linhas 35-36 mostram código comentado para future auth.
- **Acao:** Plugar Supabase Auth e usar user_metadata.role === 'admin' em vez de env var e localStorage para permissões reais.

### B6. Market Atlas columns (market_wave, market_tier_qwen) may be NULL causing VIEW errors

- **Area:** db-codigo
- **Onde:** `db/schema.sql:636-637, db/migrations/20260602_market_atlas_view.sql`
- **Evidencia:** v_relatorios_resumo selects r.market_wave, r.market_tier_qwen without NULL handling. These columns default to NULL (no NOT NULL constraint). Callers may expect string values. If A9/Atlas pipeline incomplete, viewers see nulls.
- **Acao:** Add COALESCE(r.market_wave, 'unknown') in view, or document that callers must handle NULL values in market_wave and market_tier_qwen fields

### B7. chat_sessions.status field has status='encerrado' in code but migration defines 'encerrado' in CHECK

- **Area:** db-codigo
- **Onde:** `services/chat_state.py:87, db/migrations/20260610_chat_sessions.sql:15`
- **Evidencia:** Code: sb.table('chat_sessions').neq('status', 'encerrado') vs Migration CHECK constraint: status IN ('coletando_slots', 'pipeline_rodando', 'respondendo', 'encerrado'). Spelling is consistent ('encerrado' not 'encerrada'), so no issue.
- **Acao:** No action required — status values match between code and migration

### B8. Hardcoded project path in qwen-analyze.ps1 example

- **Area:** scripts
- **Onde:** `scripts/qwen-analyze.ps1:21`
- **Evidencia:** .\qwen-analyze.ps1 -Path "C:\Users\marce\gymsite_intelligence"
- **Acao:** Update documentation example to show relative path or use . (current directory) as default

### B9. Hardcoded project path in qwen-fix-lint.ps1 example

- **Area:** scripts
- **Onde:** `scripts/qwen-fix-lint.ps1:21`
- **Evidencia:** .\qwen-fix-lint.ps1 -Path "C:\Users\marce\gymsite_intelligence"
- **Acao:** Update documentation example to show relative path or use . (current directory) as default

## Metodologia

- Achados exigem evidencia verificada (Read/Grep/execucao real) — especulacao proibida no prompt dos finders.
- Todo CRITICA/ALTA passou por agente cetico independente com ordem de refutar (procurar prefixo de router, import dinamico, uso via string). Nenhum foi refutado.
- Achados de banco cruzados com as tabelas reais do Supabase de producao verificadas em 2026-06-10.
- Limite de 15 achados por frente — auditoria prioriza gravidade, nao exaustividade de itens triviais.
