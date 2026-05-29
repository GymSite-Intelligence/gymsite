# GymSite MVP PRD v1.1 — Issues

**Data:** 2026-05-16
**Origem:** PRD v1.1 (validado contra auditoria dos 5 repos)
**Linear:** [GymSite Intelligence](https://linear.app/vectra-cargo/project/gymsite-intelligence-5f167f4eafcd/overview) (milestones M1–M4 já criados; issues nesse arquivo por limitação do plano free)

## Escopo MVP

Camada de **captação de leads** sobre o GymSite (que já roda end-to-end).
Fluxo: VectraCargo (form) → VectraClaw (POST /api/gymsite/lead) → Morpheus (rota) → Hermes (e-mail) + CFN (cliente com badge) + Navi (deal) → Lead acessa `gymsite.vectracargo.com.br?code=<uuid>`.

**Não está em escopo:** reescrever o frontend gymsite do zero, alterar pipeline A0–A6.

**Exceção M4 (frontend mínimo):** rotas públicas de lead (`?code=`), viewer guest e vínculo `access_code` lead ↔ relatório — issues **GYM-21..23**. O viewer autenticado (12 seções A0–A6) já existe; não refatorar em massa no MVP.

**Mockup visual (estilo [kimi.page](https://fmz5gctopgu4k.kimi.page)):** [`docs/mockups/frontend-mvp-preview.html`](./mockups/frontend-mvp-preview.html) · análise: [`REFATORACAO-FRONTEND-INSPIRACAO-KIMI.md`](./REFATORACAO-FRONTEND-INSPIRACAO-KIMI.md)

## Convenções

- **Owner:** quem executa (`agente-1` gymsite, `agente-2` vectracargo, `agente-3` vectraclaw-backend, `agente-4` cargo-flow-navigator, `agente-5` navi, `humano` Marcelo).
- **Blocked by:** issues que precisam fechar antes desta começar.
- **Estado:** `[ ]` pendente, `[~]` em progresso, `[x]` concluído.

## Dependency graph

```
M1 (infra) ─┬─ GYM-01 ─┐
            ├─ GYM-02 ─┼─→ M2 (endpoint testável via URL pública)
            ├─ GYM-03 ─┤
            ├─ GYM-04 ─┤
            └─ GYM-05 ─┘

M2 (captação) ─┬─ GYM-06 ─┐
               ├─ GYM-07 ─┼─→ GYM-08 ──→ GYM-09 ──┐
               ├─ GYM-10 ─┘                       ├─→ M3 + M4
               ├─ GYM-11 (← GYM-08) ─→ GYM-12 ─┘
               └─ GYM-12 (← GYM-11)

M3 (onboarding) ─┬─ GYM-13 (← GYM-08, SMTP em GYM-04)
                 ├─ GYM-14
                 ├─ GYM-15 ─→ GYM-16
                 └─ GYM-17 (← GYM-14)

M4 (access_code) ─┬─ GYM-18 ─→ GYM-19 ─→ GYM-21
                  ├─ GYM-08 + GYM-18 ─→ GYM-22
                  ├─ GYM-23 (pós-MVP, UI consórcio)
                  └─ GYM-20 (← GYM-01..22) — e2e
```

---

## M1 — Infraestrutura (bloqueadora)

**Estimativa:** 1–2h. **Bloqueia:** todos os outros milestones.

### [ ] GYM-01 — Dockerfile do gymsite (Python 3.11 + Playwright + uvicorn)

- **Owner:** `agente-1`
- **Labels:** `gymsite` `devops` `deploy`
- **Arquivos:** `Dockerfile`, `.dockerignore`
- **Blocked by:** —

**Spec:**

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    fonts-liberation libnss3 libxss1 libasound2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**.dockerignore:**

```
.env
__pycache__
.git
*.pyc
frontend/node_modules
frontend/dist
competitor_cache/
debug/
metrics/
```

**Aceite:**
- `docker build -t gymsite .` sem erros
- `docker run -p 8000:8000 --env-file .env gymsite` sobe API em http://localhost:8000
- GET /docs responde 200
- Playwright Chromium funcional dentro do container

**Restrições (CLAUDE.md gymsite):** não alterar `agents/`, `tools/`, `db/supabase_writer.py`, `frontend/`. Não commitar credenciais.

---

### [ ] GYM-02 — Cloudflare Tunnel: gymsite-api.vectracargo.com.br → localhost:8000

- **Owner:** `humano`
- **Labels:** `gymsite` `devops` `deploy`
- **Recurso:** Cloudflare Tunnel
- **Blocked by:** —

**Spec:**
- Criar tunnel apontando `gymsite-api.vectracargo.com.br` → `localhost:8000`
- Validar com `curl https://gymsite-api.vectracargo.com.br/docs` → 200
- Compartilhar URL exata para GYM-04 e GYM-12

**Aceite:**
- URL pública responde com OpenAPI docs
- Latência aceitável (< 500ms p50 do Brasil)

**Bloqueia:** M2 inteiro, GYM-12.

---

### [ ] GYM-03 — Cloudflare Pages: gymsite.vectracargo.com.br → frontend/dist

- **Owner:** `humano`
- **Labels:** `gymsite` `devops` `deploy` `CI/CD`
- **Recurso:** Cloudflare Pages
- **Blocked by:** —

**Spec:**
- Repositório: `Marcelo-Rosas/gymsite`
- Branch: `main`
- Build: `cd frontend && npm install && npm run build`
- Output: `frontend/dist`
- Projeto: `gymsite`
- Custom domain: `gymsite.vectracargo.com.br`

**Env de build (frontend):**
```
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_API_BASE_URL=https://gymsite-api.vectracargo.com.br
VITE_USE_MOCKS=false
```

**Aceite:**
- https://gymsite.vectracargo.com.br carrega LoginPage
- Build verde (GitHub Actions / Cloudflare)
- SPA fallback (todas rotas → index.html)

---

### [ ] GYM-04 — Env vars do servidor (gymsite + vectraclaw)

- **Owner:** `humano`
- **Labels:** `devops` `config`
- **Arquivos:** `.env` no servidor de cada serviço
- **Blocked by:** —

**gymsite/.env (acrescentar):**
```
CORS_ORIGINS=https://gymsite.vectracargo.com.br,https://www.vectracargo.com.br,http://localhost:5174
```

**vectraclaw-backend/.env (acrescentar):**
```
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
SMTP_FROM=...
NAVI_API_BASE=...
NAVI_API_TOKEN=...
```

**Aceite:**
- Variáveis carregadas após restart
- Smoke test: `curl` no endpoint com Origin header validado
- SMTP testado (`swaks` ou similar) antes de GYM-13
- NUNCA commitar — `.env` gitignored

---

### [ ] GYM-05 — CORS: adicionar gymsite.vectracargo.com.br + vectracargo.com.br

- **Owner:** `agente-1`
- **Labels:** `gymsite` `config`
- **Arquivo:** `api.py`
- **Blocked by:** GYM-04 (env var `CORS_ORIGINS`)

**Spec:**
Middleware CORS lê `CORS_ORIGINS` do `.env` e inclui:
- `https://gymsite.vectracargo.com.br`
- `https://www.vectracargo.com.br`
- `http://localhost:5174` (dev landing)

Preservar origens existentes (dev local gymsite).

**Aceite:**
- OPTIONS preflight do vectracargo.com.br responde 200
- Headers `Access-Control-Allow-Origin` corretos
- Sem regressão para origens existentes

**Restrições:** não alterar rotas existentes; não tocar em `agents/`, `tools/`, `db/supabase_writer.py`.

---

## M2 — Captação de Leads

**Estimativa:** 3–4h. **Depende de:** GYM-02 (URL do endpoint pública).

### [ ] GYM-06 — Migration gymsite_leads

- **Owner:** `agente-3` (vectraclaw-backend)
- **Labels:** `OpenClaw` `Supabase`
- **Arquivo:** `supabase/migrations/2026-05-16T000000_gymsite_leads.sql`
- **Blocked by:** —

**Spec:**

```sql
CREATE TABLE IF NOT EXISTS gymsite_leads (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome        text NOT NULL,
  cnpj        text NOT NULL,
  email       text NOT NULL,
  telefone    text NOT NULL,
  access_code uuid NOT NULL DEFAULT gen_random_uuid(),
  status      text NOT NULL DEFAULT 'pending',
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT gymsite_leads_cnpj_unique UNIQUE (cnpj)
);
ALTER TABLE gymsite_leads ENABLE ROW LEVEL SECURITY;
```

**Aceite:** migration aplicada sem erro; INSERT de teste via SQL editor funciona; UNIQUE(cnpj) bloqueia duplicata.

---

### [ ] GYM-07 — Router + GymSiteLeadInput model

- **Owner:** `agente-3`
- **Labels:** `OpenClaw` `Feature`
- **Arquivo:** `src/api_routes/gymsite.py` (novo)
- **Blocked by:** —

**Spec:**
- Criar APIRouter
- Pydantic `GymSiteLeadInput`: `nome: str`, `cnpj: str`, `email: EmailStr`, `telefone: str`
- Validador para CNPJ (normaliza para 14 dígitos)

**Restrições:** novos endpoints sempre em `src/api_routes/<feature>.py`, nunca direto em `api.py`.

---

### [ ] GYM-08 — POST /api/gymsite/lead (público, sem JWT)

- **Owner:** `agente-3`
- **Labels:** `OpenClaw` `Feature` `integração`
- **Arquivo:** `src/api_routes/gymsite.py`
- **Blocked by:** GYM-06, GYM-07

**Spec:**
- Endpoint público — adicionar em `_OPENAPI_PUBLIC_PATHS`
- Normaliza CNPJ → 14 dígitos
- Gera `access_code = str(uuid.uuid4())`
- INSERT em `gymsite_leads`; duplicata → HTTP 409 `{"detail": "CNPJ já cadastrado"}`
- Cria task `{title, description=json, operation_type="gymsite_lead_intake", status="pending"}`
- `asyncio.create_task(MorpheusDispatcher().dispatch(task_id))` — best-effort
- Retorna HTTP 201 `{"access_code": access_code, "message": "Lead recebido com sucesso"}`

**Aceite:** POST válido → 201 com access_code; POST com CNPJ duplicado → 409; task aparece em `tasks` com `operation_type=gymsite_lead_intake`.

**Restrições:** mutações fail-loud (raise HTTPException); side-effects best-effort (Morpheus dispatch não derruba a request).

---

### [ ] GYM-09 — Registrar _gymsite_routes + _OPENAPI_PUBLIC_PATHS

- **Owner:** `agente-3`
- **Labels:** `OpenClaw` `config`
- **Arquivo:** `src/api.py`
- **Blocked by:** GYM-07

**Spec:**
- `from src.api_routes.gymsite import router as _gymsite_routes`
- `app.include_router(_gymsite_routes)`
- Adicionar `"/api/gymsite/lead"` em `_OPENAPI_PUBLIC_PATHS`
- Import lazy se houver risco circular

**Aceite:** rota aparece em `/docs`; sem warning de OpenAPI sobre missing auth.

---

### [ ] GYM-10 — Migration routing_rules (gymsite_lead_intake + email_lead)

- **Owner:** `agente-3`
- **Labels:** `OpenClaw` `Supabase`
- **Arquivo:** `supabase/migrations/2026-05-16T000001_gymsite_routing.sql`
- **Blocked by:** —

**Spec:**

```sql
INSERT INTO routing_rules (operation_type, agent_id, priority, is_active)
VALUES
  ('gymsite_lead_intake',
   (SELECT id FROM agents WHERE slug = 'morpheus' LIMIT 1), 100, true),
  ('email_lead',
   (SELECT id FROM agents WHERE id = '360a96cb-b1c3-4b65-b9fa-2b9cbb59dac1'), 100, true)
ON CONFLICT (operation_type) DO UPDATE SET agent_id = EXCLUDED.agent_id, is_active = true;
```

**Plus agentes Supabase-only (sem .py novo):**

```sql
INSERT INTO agents (name, slug, role, system_prompt, execution_mode)
VALUES (
  'CFN Lead Writer', 'cfn-lead-writer', 'specialist',
  'Você recebe dados de um lead gymsite {nome, cnpj, email, telefone, access_code}.
   1. Consulte BrasilAPI GET /api/cnpj/v1/{cnpj} para obter dados da Receita Federal.
   2. Faça UPSERT na tabela clients do CFN com lead_source=gymsite_form,
      lead_badge=GYMSITE_LEAD, gymsite_access_code={access_code}.
   3. Use apenas telefone e email do formulário — demais dados vêm da Receita Federal.',
  'cma'
);

INSERT INTO agents (name, slug, role, system_prompt, execution_mode)
VALUES (
  'Navi Notifier', 'navi-notifier', 'specialist',
  'Você recebe dados de um lead gymsite {nome, cnpj, email, telefone, access_code}.
   Chame navi_client.create_gymsite_deal() para criar o deal no CRM Navi.
   Este é um side-effect best-effort — não falhe a task se o Navi estiver indisponível.',
  'cma'
);
```

**Aceite:** SELECT na `routing_rules` mostra as 2 linhas; SELECT em `agents` mostra os 2 novos slugs.

---

### [ ] GYM-11 — GymSiteSection.tsx (form Nome/CNPJ/email/telefone + BrasilAPI)

- **Owner:** `agente-2` (vectracargo)
- **Labels:** `vectracargo` `Feature` `ui`
- **Arquivo:** `src/components/GymSiteSection.tsx` (novo)
- **Blocked by:** GYM-08 (endpoint funcional via GYM-02)

**Spec:**
- React Hook Form + Zod
- Campos:
  - `nome` (string)
  - `cnpj` (máscara `XX.XXX.XXX/XXXX-XX`)
  - `email`
  - `telefone` (máscara `(XX) XXXXX-XXXX`)
- Ao preencher CNPJ válido (14 dígitos): `GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}` → preenche nome se vazio (loading state visível)
- Submit: `POST import.meta.env.VITE_GYMSITE_API_URL/api/gymsite/lead`
- Sucesso → "Acesso enviado! Verifique seu e-mail." + reset form
- Erro 409 → "CNPJ já cadastrado. Verifique seu e-mail anterior."

**Restrições (CLAUDE.md vectracargo):** não alterar Navbar, HeroSection, AboutSection, ServicesSection, ContactSection, Footer. Variáveis via `import.meta.env.VITE_*`.

---

### [ ] GYM-12 — Index.tsx + .env.example (adicionar GymSiteSection)

- **Owner:** `agente-2`
- **Labels:** `vectracargo` `config`
- **Arquivos:** `src/pages/Index.tsx`, `.env.example`
- **Blocked by:** GYM-11

**Spec:**
- Import + render `<GymSiteSection />` antes de `<ContactSection />`
- `.env.example`: adicionar `VITE_GYMSITE_API_URL=https://gymsite-api.vectracargo.com.br`

**Aceite:** seção visível no layout sem quebrar componentes vizinhos.

---

## M3 — Pipeline de Onboarding

**Estimativa:** 2–3h. **Depende de:** M2 (endpoint ativo, task sendo criada).

### [ ] GYM-13 — Template Hermes gymsite_lead_welcome

- **Owner:** `agente-3`
- **Labels:** `OpenClaw` `integração`
- **Arquivo:** `src/agents/hermes_reporter.py` (apenas adicionar template)
- **Blocked by:** GYM-04 (SMTP config), GYM-08 (gera o access_code)

**Spec:**
- **Assunto:** `Seu acesso ao GymSite chegou — {access_code}`
- **Saudação:** `Olá, {nome}!`
- **access_code** em box monospace destacada
- **Aviso:** "Este código dá direito a apenas 1 consulta completa. Não compartilhe."
- **3 bullets:**
  - Análise de concorrência e raio de influência por geolocalização
  - Projeção financeira e ponto de equilíbrio do negócio
  - Relatório PDF completo gerado por IA em minutos
- **CTA:** botão "Acessar Meu Relatório" → `https://gymsite.vectracargo.com.br?code={access_code}`
- **Footer:** "VectraCargo — Inteligência de dados para o seu negócio"
- **Destinatários:** e-mail do lead + GoDaddy mailbox 41229009

**Restrições:** não alterar `src/agents/` existentes — apenas acrescentar template.

---

### [ ] GYM-14 — navi_client.py (HTTP client best-effort para Navi)

- **Owner:** `agente-3`
- **Labels:** `OpenClaw` `NAVI` `integração`
- **Arquivo:** `src/services/navi_client.py` (novo)
- **Blocked by:** GYM-04 (env vars NAVI_API_*)

**Spec:**

```python
import os, httpx, logging
logger = logging.getLogger("VectraClawAPI")
NAVI_API_BASE = os.getenv("NAVI_API_BASE", "")
NAVI_API_TOKEN = os.getenv("NAVI_API_TOKEN", "")

async def create_gymsite_deal(nome, cnpj, email, telefone, access_code) -> dict:
    """Best-effort — nunca raise."""
    if not NAVI_API_BASE or not NAVI_API_TOKEN:
        logger.warning("NAVI vars ausentes — deal não criado")
        return {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{NAVI_API_BASE}/api/deals",
                json={"title": f"GymSite Lead — {cnpj}", "contact_name": nome,
                      "contact_email": email, "contact_phone": telefone,
                      "source": "gymsite_lead_form", "tags": ["gymsite", "lead"],
                      "metadata": {"access_code": access_code}},
                headers={"Authorization": f"Bearer {NAVI_API_TOKEN}"}
            )
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.warning("Navi deal failed (best-effort): %s", exc)
        return {}
```

**Aceite:** import sem erro; chamada com NAVI vars ausentes retorna `{}` e loga warning.

---

### [ ] GYM-15 — Migration CFN (clients.lead_source, lead_badge, gymsite_access_code)

- **Owner:** `agente-4` (cargo-flow-navigator)
- **Labels:** `CFN` `Supabase`
- **Arquivo:** `supabase/migrations/2026-05-16T000000_gymsite_badge.sql`
- **Blocked by:** —

**Spec:**

```sql
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS lead_source text,
  ADD COLUMN IF NOT EXISTS lead_badge  text,
  ADD COLUMN IF NOT EXISTS gymsite_access_code uuid;
COMMENT ON COLUMN clients.lead_source IS 'gymsite_form | manual | import';
COMMENT ON COLUMN clients.lead_badge IS 'GYMSITE_LEAD | INDICACAO | null';
COMMENT ON COLUMN clients.gymsite_access_code IS 'UUID do GymSite (1 consulta)';
```

**Restrições:** não alterar `useClients.tsx`.

---

### [ ] GYM-16 — Badge visual "GymSite Lead" no componente de cliente

- **Owner:** `agente-4`
- **Labels:** `CFN` `ui`
- **Arquivos:** `src/components/clients/*`
- **Blocked by:** GYM-15

**Spec:**
- Quando `client.lead_badge === 'GYMSITE_LEAD'` renderizar badge visual
- Apenas visual — sem alterar lógica de negócio existente

**Aceite:** clientes seed com `lead_badge=GYMSITE_LEAD` mostram badge; demais não regridem.

---

### [ ] GYM-17 — Confirmar/adaptar POST /api/deals no navi

- **Owner:** `agente-5` (navi)
- **Labels:** `NAVI` `integração` `docs`
- **Arquivo:** `api.ts` (leitura) + `GYMSITE_INTEGRATION.md` (novo)
- **Blocked by:** GYM-14

**Spec:**
- Ler `api.ts` (1558 linhas) e validar que `POST /api/deals` aceita: `source`, `tags[]`, `metadata{}`, `contact_name`, `contact_email`, `contact_phone`
- Se compatível: documentar contrato em `GYMSITE_INTEGRATION.md` — **não alterar código**
- Se incompatível: adicionar campos faltantes mantendo retrocompatibilidade

**Restrições:** não alterar pipeline de cotação nem outras features; preservar `api.ts` se já compatível.

---

## M4 — Acesso via access_code (gymsite + frontend guest)

**Estimativa:** 4–6h (backend + frontend). **Depende de:** M2 (access_code armazenado).

### [ ] GYM-18 — Migration relatorios.access_code

- **Owner:** `agente-1` (gymsite)
- **Labels:** `gymsite` `Supabase`
- **Arquivo:** `supabase/migrations/2026-05-16T000000_relatorios_access_code.sql`
- **Blocked by:** —

**Spec:**

```sql
ALTER TABLE relatorios
  ADD COLUMN IF NOT EXISTS access_code uuid,
  ADD COLUMN IF NOT EXISTS access_code_used_at timestamptz;
COMMENT ON COLUMN relatorios.access_code IS 'UUID enviado ao lead — acesso sem login';
COMMENT ON COLUMN relatorios.access_code_used_at IS 'Timestamp da primeira utilização';
```

**Restrições:** filename com timestamp ISO.

---

### [ ] GYM-19 — Validação ?access_code no GET /api/relatorios/{id}

- **Owner:** `agente-1`
- **Labels:** `gymsite` `Feature` `security`
- **Arquivo:** `api.py`
- **Blocked by:** GYM-18

**Spec:**
- `GET /api/relatorios/{id}?access_code=<uuid>`
- Se relatório tem `access_code NOT NULL` e query param presente:
  - código não bate → HTTP 403 `{"detail": "access_code inválido ou expirado"}`
  - código bate → `UPDATE access_code_used_at = now()` (best-effort) → retorna relatório
- Se relatório **não** tem `access_code` (user autenticado normal): comportamento atual **inalterado**

**Aceite:** chamada autenticada normal segue funcionando; chamada com `?access_code` válido retorna 200 + atualiza `access_code_used_at`; chamada com código errado → 403.

**Restrições:** NÃO alterar `create_relatorio`, `get_status`, `list_relatorios` existentes (apenas o GET por id).

---

### [ ] GYM-21 — Rota pública lead: `/acesso` + `?code=` + viewer guest

- **Owner:** `agente-1` (gymsite)
- **Labels:** `gymsite` `frontend` `security`
- **Arquivos:** `frontend/src/router.tsx`, `frontend/src/hooks/useRelatorioDetail.ts`, `frontend/src/routes/LeadAccessPage.tsx` (novo)
- **Blocked by:** GYM-19, GYM-03 (deploy Pages)

**Spec:**
- Adicionar `/acesso` em `PUBLIC_PATHS` (sem `RequireAuth` / `AppShell`)
- `validateSearch`: `code?: string` (uuid), `id?: string` (relatorio_id)
- Redirect opcional: `/?code=<uuid>` → `/acesso?code=<uuid>&id=<id>` quando `id` conhecido
- `useRelatorioDetail(relatorioId, { accessCode })`: se `accessCode` presente, `GET /api/relatorios/{id}?access_code=` **sem** JWT Supabase
- Estados UI:
  - loading → skeleton
  - `status !== done` → tela aguardando (reutilizar padrão `RelatorioAguardandoPage`, layout guest)
  - `403` → “Link inválido ou expirado” + CTA VectraCargo
  - `200` → `RelatorioViewerPage` em **modo guest** (header mínimo: logo + “Análise exclusiva”, sem nav Relatórios/Mapa/Custos)
- Polling de status permitido com `access_code` no query (se GYM-19 estender `/status` — senão só GET detail)

**Aceite:** GYM-20 passo 6 funciona sem login; deep-link do e-mail abre relatório ou estado pendente.

**Restrições:** não duplicar lógica A4 no client; consumir JSON A6 existente. Ver mockup tela “Acesso Lead”.

---

### [ ] GYM-22 — Vincular `gymsite_leads.access_code` → `relatorios`

- **Owner:** `agente-3` + `agente-1`
- **Labels:** `gymsite` `OpenClaw` `integração`
- **Arquivos:** migration ou lógica Morpheus/Hermes; doc `docs/GYMSITE_LEAD_ACCESS.md` (novo)
- **Blocked by:** GYM-08, GYM-18

**Spec (escolher uma estratégia e documentar):**
- **A)** Ao processar `gymsite_lead_intake`, criar `relatorios` stub com **mesmo** `access_code` do lead + `input_canonico` mínimo (cidade do CNPJ ou default)
- **B)** Tabela ponte `gymsite_lead_relatorios(lead_id, relatorio_id, access_code)` com UNIQUE em `access_code`
- E-mail Hermes (GYM-13) deve incluir link: `https://gymsite.vectracargo.com.br/acesso?code={access_code}&id={relatorio_id}`

**Aceite:** um único `access_code` abre o relatório correto no frontend; Morpheus consegue resolver id sem login.

**Gap que fecha:** GYM-06 grava code em `gymsite_leads`; GYM-18 em `relatorios` — hoje sem join no plano.

---

### [ ] GYM-23 — Card Consórcio + gráfico CAPEX (UI, pós-MVP hardening)

- **Owner:** `agente-1` (gymsite frontend)
- **Labels:** `gymsite` `frontend` `ui`
- **Arquivos:** `frontend/src/components/domain/ConsorcioCard.tsx`, `CapexBreakdownChart.tsx` (novos); `RelatorioViewerPage.tsx`
- **Blocked by:** — (recomendado após GYM-21; dados podem vir de regra A4 futura)

**Spec:**
- Card “Consórcio recomendado” quando `capex_mid` (ou campo A4) > threshold — carta sugerida, parcela estimada, CTA “Falar com Vectra”
- Gráfico barras empilhadas: obra / equipamentos / contingência nos 3 cenários (Recharts)
- KPI strip (4 cards) acima da seção financeira: área, aluguel total, CAPEX mid, payback
- **Não** implementar probabilidade de contemplação por sorteio no client sem modelo validado

**Aceite:** mockup `frontend-mvp-preview.html` tela “Viewer autenticado” refletida no React.

**Inspiração:** protótipo Kimi `ReportView.tsx` — ver `REFATORACAO-FRONTEND-INSPIRACAO-KIMI.md`.

---

### [ ] GYM-20 — Teste e2e completo (acceptance criteria)

- **Owner:** `humano`
- **Labels:** `teste` `integração`
- **Blocked by:** GYM-01..22

**Roteiro:**

1. Preencher form em vectracargo.com.br: Nome, CNPJ, email, telefone
2. CNPJ válido → BrasilAPI preenche nome automaticamente (loading visível)
3. Submit → POST `/api/gymsite/lead` retorna HTTP 201 com `access_code`
4. UI exibe "Acesso enviado! Verifique seu e-mail."
5. Em até 5 min: e-mail chega com `access_code` em destaque + link gymsite
6. Acessar `https://gymsite.vectracargo.com.br/acesso?code=<uuid>&id=<relatorio_id>` → gymsite valida (GYM-21) e exibe relatório guest ou tela aguardando (GYM-22)
7. CFN mostra novo cliente com badge "GymSite Lead"
8. Navi mostra deal com `source=gymsite_lead_form` e tag `gymsite`
9. CNPJ duplicado no form → mensagem 409 amigável, sem crash

---

## Checklist de execução

### Semana 1 (paralelo)
- [ ] **Humano:** GYM-02, GYM-03, GYM-04
- [ ] **Agente 1:** GYM-01, GYM-05, GYM-18, GYM-19, GYM-21, GYM-22 (doc)
- [ ] **Agente 3:** GYM-06..10, GYM-13, GYM-14

### Semana 2 (após Agente 3 commit)
- [ ] **Agente 2:** GYM-11, GYM-12
- [ ] **Agente 4:** GYM-15, GYM-16
- [ ] **Agente 5:** GYM-17

### Semana 3
- [ ] **Agente 1:** GYM-21 (após GYM-19 + GYM-03), GYM-23 se sobrar tempo
- [ ] **Agente 3:** GYM-22 (vínculo lead ↔ relatório no Morpheus/Hermes)
- [ ] **Humano:** GYM-20 (e2e)

---

## Env vars consolidadas

### gymsite_intelligence/.env (raiz, runtime local e Cloudflare Tunnel)
```
SUPABASE_URL=https://epgedaiukjippepujuzc.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
GEMINI_API_KEY=...
GOOGLE_API_KEY=...
MAPS_API_KEY=...
CORS_ORIGINS=https://vectracargo.com.br,https://gymsite.vectracargo.com.br
```

> O regex `http://localhost:\d+` em `api.py` cobre dev local — não precisa estar em `CORS_ORIGINS`.

### gymsite/frontend/.env.local
```
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_API_BASE_URL=https://gymsite-api.vectracargo.com.br
VITE_USE_MOCKS=false
```

### vectraclaw-backend/.env (M2/M3)
```
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
SMTP_FROM=...
NAVI_API_BASE=...
NAVI_API_TOKEN=...
```

### vectracargo/.env.local
```
VITE_GYMSITE_API_URL=https://gymsite-api.vectracargo.com.br
```
