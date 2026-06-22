# GymSite MVP PRD v1.1
Data: 2026-05-16 | Versão anterior: v1.0 (corrigida após auditoria dos repos)
Autor: Claude (revisão baseada em leitura direta de todos os repos)

---

## 1. Contexto e escopo

O GymSite já tem backend (FastAPI, pipeline A0-A6, 22 tools) e frontend (Vite+React,
12 rotas, 12 hooks, auth completo com senha+OTP) funcionais.
O MVP acrescenta UMA camada de captação de leads externa (via VectraCargo) com pipeline
automatizado de onboarding via VectraClaw (Morpheus -> Hermes -> CFN -> Navi).

**NÃO está em escopo:**
- Construir frontend do gymsite -- ele já existe e está completo
- Alterar agents/, tools/, db/supabase_writer.py
- Alterar o pipeline A0-A6

---

## 2. Estado real por repo (auditado em 2026-05-16)

### gymsite
- OK backend: api.py 472 linhas -- POST /api/relatorios, GET status, GET relatorio, list
- OK frontend/src/routes/: LoginPage (senha+OTP 404 linhas), NovoRelatorioPage (847 linhas),
  RelatorioAguardandoPage (298 linhas), RelatorioViewerPage (527 linhas),
  RelatoriosListPage, ComparadorPage, MapaRelatoriosPage, CustosPage, PerfilPage
- OK frontend/src/hooks/: 12 hooks (useRelatorios, useRelatorioDetail, useMembership, etc.)
- OK frontend/src/router.tsx: TanStack Router configurado, search params tipados, 231 linhas
- PENDENTE Dockerfile: nao existe
- PENDENTE CORS gymsite.vectracargo.com.br: nao confirmado como adicionado
- PENDENTE Campo access_code na tabela relatorios: nao existe
- PENDENTE Validacao ?access_code no GET /api/relatorios/{id}: nao implementada

### vectracargo
- OK landing page completa: Navbar, HeroSection, AboutSection, ServicesSection,
  ContactSection, Footer, FloatingWhatsApp
- PENDENTE GymSiteSection.tsx: nao existe (formulario de captacao de leads)

### vectraclaw-backend
- OK MorpheusDispatcher: src/services/morpheus_dispatcher.py
- OK HermesReporter: src/agents/hermes_reporter.py (407 linhas)
- OK api_routes/: 10 modulos de feature (prospects, workflows, athena, rag, etc.)
- PENDENTE POST /api/gymsite/lead: nao existe
- PENDENTE src/api_routes/gymsite.py: nao existe
- PENDENTE Tabela gymsite_leads no Supabase: nao existe
- PENDENTE routing_rule gymsite_lead_intake -> Morpheus: nao existe
- PENDENTE routing_rule email_lead -> Hermes: nao existe
- PENDENTE Template Hermes gymsite_lead_welcome: nao existe
- PENDENTE src/services/navi_client.py: nao existe

### <SUPABASE_PROJECT>
- OK useClients.tsx + BrasilAPI ja usados
- PENDENTE Colunas lead_source, lead_badge, gymsite_access_code na tabela clients: nao existem
- PENDENTE Badge visual GymSite Lead no componente de cliente: nao existe

### navi
- OK api.ts 1558 linhas -- pipeline CRM completo
- A CONFIRMAR POST /api/deals com campos source/tags/metadata: confirmar pelo Agente 5

---

## 3. Arquitetura do fluxo MVP

```
[VectraCargo -- GymSiteSection]
        |
        | POST /api/gymsite/lead {nome, cnpj, email, telefone}
        v
[vectraclaw-backend -- POST /api/gymsite/lead]
        |-- gera access_code (uuid)
        |-- INSERT gymsite_leads
        |-- cria task operation_type=gymsite_lead_intake
        |-- MorpheusDispatcher.dispatch(task_id)
        v
[Morpheus -- routing_rule gymsite_lead_intake]
        |-- child task email_lead -> Hermes Reporter
        |-- child task cfn_lead_write -> CFN Lead Writer (CMA)
        |-- child task navi_deal_create -> Navi Notifier (CMA)
        v
[Hermes Reporter -- email_lead]
        |-- envia email com template gymsite_lead_welcome
        |-- access_code em destaque + briefing 1 consulta + link gymsite
        |-- destino: GoDaddy mailbox 41229009 + email do lead
        v
[CFN Lead Writer -- CMA Anthropic]
        |-- busca CNPJ na Receita Federal (BrasilAPI)
        |-- UPSERT clients com lead_source=gymsite_form, lead_badge=GYMSITE_LEAD
        |-- persiste gymsite_access_code
        v
[Navi Notifier -- CMA Anthropic]
        |-- POST /api/deals no Navi
        |-- source=gymsite_lead_form, tags=[gymsite, lead], metadata={access_code}
        v
[Lead recebe email -> acessa gymsite.vectracargo.com.br?code=<uuid>]
        |
        v
[gymsite backend -- GET /api/relatorios/{id}?access_code=<uuid>]
        |-- valida access_code contra tabela relatorios
        |-- retorna relatorio se valido
```

---

## 4. Milestones e Issues

### M1 -- Infraestrutura (bloqueadora)
Responsavel: voce (humano) + Agente 1
Estimativa: 1-2h
Bloqueadora para: todos os outros milestones

| Issue | Resp. | Arquivo/Recurso | Descricao |
|-------|-------|-----------------|-----------|
| GYM-01 | Agente 1 | gymsite/Dockerfile | Dockerfile: python:3.11-slim + Playwright + uvicorn |
| GYM-02 | Voce | Cloudflare Tunnel | gymsite-api.vectracargo.com.br -> localhost:8000 |
| GYM-03 | Voce | Cloudflare Pages | gymsite.vectracargo.com.br -> frontend/dist |
| GYM-04 | Voce | .env do servidor | CORS_ORIGINS, SMTP_*, NAVI_BASE_URL, NAVI_SERVICE_KEY |
| GYM-05 | Agente 1 | gymsite/api.py | CORS: adicionar gymsite.vectracargo.com.br + vectracargo.com.br |

**Spec GYM-01 -- Dockerfile:**

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

Criar tambem `.dockerignore`:
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

**Spec GYM-03 -- Cloudflare Pages:**
- Repositorio: Marcelo-Rosas/gymsite
- Branch: main
- Build command: cd frontend && npm install && npm run build
- Build output: frontend/dist
- Nome do projeto: gymsite
- Custom domain: gymsite.vectracargo.com.br

---

### M2 -- Captacao de Leads
Responsavel: Agente 2 (vectracargo) + Agente 3 (vectraclaw-backend) -- paralelo
Estimativa: 3-4h
Depende de: GYM-02 (URL do endpoint disponivel para testar)

| Issue | Resp. | Arquivo | Descricao |
|-------|-------|---------|-----------|
| GYM-06 | Agente 3 | supabase/migrations/2026-05-16T000000_gymsite_leads.sql | Tabela gymsite_leads |
| GYM-07 | Agente 3 | src/api_routes/gymsite.py | Router + GymSiteLeadInput model |
| GYM-08 | Agente 3 | src/api_routes/gymsite.py | POST /api/gymsite/lead (publico, sem JWT) |
| GYM-09 | Agente 3 | src/api.py | Registrar _gymsite_routes + _OPENAPI_PUBLIC_PATHS |
| GYM-10 | Agente 3 | supabase/migrations/2026-05-16T000001_gymsite_routing.sql | routing_rules gymsite_lead_intake + email_lead |
| GYM-11 | Agente 2 | src/components/GymSiteSection.tsx | Form Nome/CNPJ/email/telefone + BrasilAPI + POST |
| GYM-12 | Agente 2 | src/pages/Index.tsx + .env.example | Adicionar GymSiteSection + VITE_GYMSITE_API_URL |

**Spec GYM-06 -- gymsite_leads:**
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

**Spec GYM-08 -- POST /api/gymsite/lead:**
- Endpoint publico (sem JWT) -- adicionar em _OPENAPI_PUBLIC_PATHS
- Normaliza CNPJ: remove pontuacao -> 14 digitos
- Gera access_code = str(uuid.uuid4())
- INSERT gymsite_leads -- se CNPJ duplicado -> HTTP 409 {"detail": "CNPJ ja cadastrado"}
- Cria task {title, description=json, operation_type=gymsite_lead_intake, status=pending}
- asyncio.create_task(MorpheusDispatcher().dispatch(task_id)) -- best-effort
- Retorna HTTP 201 {"access_code": access_code, "message": "Lead recebido com sucesso"}

**Spec GYM-10 -- routing_rules:**
```sql
INSERT INTO routing_rules (operation_type, agent_id, priority, is_active)
VALUES
  ('gymsite_lead_intake',
   (SELECT id FROM agents WHERE slug = 'morpheus' LIMIT 1), 100, true),
  ('email_lead',
   (SELECT id FROM agents WHERE id = '360a96cb-b1c3-4b65-b9fa-2b9cbb59dac1'), 100, true)
ON CONFLICT (operation_type) DO UPDATE SET agent_id = EXCLUDED.agent_id, is_active = true;
```

**Spec GYM-11 -- GymSiteSection.tsx:**
- React Hook Form + Zod
- Campos: nome (string), cnpj (mascara XX.XXX.XXX/XXXX-XX), email, telefone (mascara (XX) XXXXX-XXXX)
- Ao preencher CNPJ valido (14 digitos): GET https://brasilapi.com.br/api/cnpj/v1/{cnpj} -> preenche nome se vazio
- Submit: POST import.meta.env.VITE_GYMSITE_API_URL/api/gymsite/lead
- Sucesso: "Acesso enviado! Verifique seu e-mail." + reset form
- Erro 409: "CNPJ ja cadastrado. Verifique seu e-mail anterior."
- Posicao em Index.tsx: antes de <ContactSection />

---

### M3 -- Pipeline de Onboarding
Responsavel: Agente 3 + Agente 4 + Agente 5
Estimativa: 2-3h
Depende de: M2 (endpoint ativo, task sendo criada)

| Issue | Resp. | Arquivo | Descricao |
|-------|-------|---------|-----------|
| GYM-13 | Agente 3 | src/agents/hermes_reporter.py | Template gymsite_lead_welcome |
| GYM-14 | Agente 3 | src/services/navi_client.py | HTTP client best-effort para Navi |
| GYM-15 | Agente 4 | supabase/migrations/2026-05-16T000000_gymsite_badge.sql | Colunas lead_source, lead_badge, gymsite_access_code em clients |
| GYM-16 | Agente 4 | src/components/clients/* | Badge visual GymSite Lead (apenas visual) |
| GYM-17 | Agente 5 | -- | Confirmar/adaptar POST /api/deals no navi |

**Spec GYM-13 -- Template Hermes gymsite_lead_welcome:**
- Assunto: Seu acesso ao GymSite chegou -- {access_code}
- Saudacao: Ola, {nome}!
- access_code em box monospace destacada
- Aviso: Este codigo da direito a apenas 1 consulta completa. Nao compartilhe.
- 3 bullets do que o GymSite entrega:
  - Analise de concorrencia e raio de influencia por geolocalizacao
  - Projecao financeira e ponto de equilibrio do negocio
  - Relatorio PDF completo gerado por IA em minutos
- CTA: botao Acessar Meu Relatorio -> https://gymsite.vectracargo.com.br?code={access_code}
- Footer: VectraCargo -- Inteligencia de dados para o seu negocio
- Destinatarios: email do lead + GoDaddy mailbox 41229009

**Spec GYM-14 -- navi_client.py:**
```python
# src/services/navi_client.py
import os, httpx, logging
logger = logging.getLogger("VectraClawAPI")
NAVI_BASE_URL = os.getenv("NAVI_BASE_URL", "")
NAVI_SERVICE_KEY = os.getenv("NAVI_SERVICE_KEY", "")

async def create_gymsite_deal(nome, cnpj, email, telefone, access_code) -> dict:
    """Best-effort -- nunca raise."""
    if not NAVI_BASE_URL or not NAVI_SERVICE_KEY:
        logger.warning("NAVI vars ausentes -- deal nao criado")
        return {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{NAVI_BASE_URL}/api/deals",
                json={"title": f"GymSite Lead -- {cnpj}", "contact_name": nome,
                      "contact_email": email, "contact_phone": telefone,
                      "source": "gymsite_lead_form", "tags": ["gymsite", "lead"],
                      "metadata": {"access_code": access_code}},
                headers={"Authorization": f"Bearer {NAVI_SERVICE_KEY}"}
            )
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        logger.warning("Navi deal failed (best-effort): %s", exc)
        return {}
```

**Spec GYM-15 -- Migration CFN:**
```sql
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS lead_source text,
  ADD COLUMN IF NOT EXISTS lead_badge  text,
  ADD COLUMN IF NOT EXISTS gymsite_access_code uuid;
COMMENT ON COLUMN clients.lead_source IS 'gymsite_form | manual | import';
COMMENT ON COLUMN clients.lead_badge IS 'GYMSITE_LEAD | INDICACAO | null';
COMMENT ON COLUMN clients.gymsite_access_code IS 'UUID do GymSite (1 consulta)';
```

---

### M4 -- Acesso via access_code (gymsite)
Responsavel: Agente 1
Estimativa: 1h
Depende de: M2 (access_code gerado pelo VectraClaw e armazenado)

| Issue | Resp. | Arquivo | Descricao |
|-------|-------|---------|-----------|
| GYM-18 | Agente 1 | supabase/migrations/2026-05-16T000000_relatorios_access_code.sql | Coluna access_code na tabela relatorios |
| GYM-19 | Agente 1 | gymsite/api.py | GET /api/relatorios/{id}: validar ?access_code se presente |
| GYM-20 | Voce | -- | e2e completo: form -> email -> acesso gymsite com code |

**Spec GYM-18 -- Migration relatorios:**
```sql
ALTER TABLE relatorios
  ADD COLUMN IF NOT EXISTS access_code uuid,
  ADD COLUMN IF NOT EXISTS access_code_used_at timestamptz;
COMMENT ON COLUMN relatorios.access_code IS 'UUID enviado ao lead -- acesso sem login';
COMMENT ON COLUMN relatorios.access_code_used_at IS 'Timestamp da primeira utilizacao';
```

**Spec GYM-19 -- Validacao access_code:**
- GET /api/relatorios/{id}?access_code=<uuid>
- Se relatorio tem access_code NOT NULL e query param presente:
  - access_code nao bate -> HTTP 403 {"detail": "access_code invalido ou expirado"}
  - access_code bate -> UPDATE access_code_used_at = now() (best-effort) -> retornar relatorio
- Se relatorio NAO tem access_code (usuario normal autenticado): comportamento atual inalterado

---

## 5. CLAUDE.md rules por repo (imutaveis)

### gymsite (Agente 1)
- NAO altere agents/, tools/, db/supabase_writer.py
- NAO altere frontend/ -- esta completo e funcional
- NAO altere rotas existentes de api.py (create_relatorio, get_status, list_relatorios)
- Migrations SQL em supabase/migrations/ com timestamp ISO no nome do arquivo
- Qualquer novo endpoint publico -> adicionar em _OPENAPI_PUBLIC_PATHS
- NUNCA commite credenciais -- todas as chaves ficam em .env (gitignored)

### vectraclaw-backend (Agente 3)
- Novos endpoints de feature -> src/api_routes/<feature>.py (nunca direto em api.py)
- NAO altere src/agents/ existentes
- Logger: logging.getLogger("VectraClawAPI") na API
- Import lazy entre api.py e outros modulos para evitar circular import
- Heartbeats e side-effects: best-effort (nao raise em falha)
- Mutacoes de dados: fail-loud (raise HTTPException)
- Novos operation_types SEMPRE com routing_rule SQL correspondente
- NUNCA commite credenciais

### vectracargo (Agente 2)
- NAO altere Navbar, HeroSection, AboutSection, ServicesSection, ContactSection, Footer
- NAO altere Index.tsx alem de adicionar import + GymSiteSection antes de ContactSection
- Use React Hook Form + Zod
- Variaveis de ambiente via import.meta.env.VITE_*
- NUNCA commite credenciais

### <SUPABASE_PROJECT> (Agente 4)
- NAO altere useClients.tsx
- Novos campos apenas via migration SQL
- Badge visual apenas -- sem alterar logica de negocio existente
- NUNCA commite credenciais

### navi (Agente 5)
- NAO altere pipeline de cotacao nem outras features existentes
- NAO altere api.ts -- apenas leia para entender a interface
- Se POST /api/deals ja e compativel: documente em GYMSITE_INTEGRATION.md, nao altere nada
- NUNCA commite credenciais

---

## 6. Env vars checklist

### gymsite -- backend (.env na raiz, gitignored)
```
SUPABASE_URL=...              # ja existe
SUPABASE_KEY=...              # ja existe (service role)
GOOGLE_MAPS_API_KEY=...       # ja existe
VERTEX_AI_PROJECT=...         # ja existe
CORS_ORIGINS=https://gymsite.vectracargo.com.br,https://www.vectracargo.com.br,http://localhost:5174
```

### gymsite -- frontend (.env.local em frontend/, gitignored)
```
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_API_BASE_URL=https://gymsite-api.vectracargo.com.br
VITE_USE_MOCKS=false
```

### vectraclaw-backend (.env, gitignored)
```
SMTP_HOST=smtpout.secureserver.net
SMTP_PORT=465
SMTP_USER=<email-godaddy>
SMTP_PASS=<senha-mailbox-41229009>
NAVI_BASE_URL=https://<url-do-navi>
NAVI_SERVICE_KEY=<service-key-do-navi>
```

### vectracargo (.env.local, gitignored)
```
VITE_GYMSITE_API_URL=https://gymsite-api.vectracargo.com.br
```

---

## 7. Agentes VectraClaw -- Supabase DB (sem novo .py)

Os dois agentes abaixo NAO precisam de novo arquivo em src/agents/.
Sao registrados como linhas na tabela agents do Supabase e executados
pelo agent_daemon.py via CMA (Anthropic) com score >= 50.

### CFN Lead Writer
```sql
INSERT INTO agents (name, slug, role, system_prompt, execution_mode)
VALUES (
  'CFN Lead Writer', 'cfn-lead-writer', 'specialist',
  'Voce recebe dados de um lead gymsite {nome, cnpj, email, telefone, access_code}.
   1. Consulte BrasilAPI GET /api/cnpj/v1/{cnpj} para obter dados da Receita Federal.
   2. Faca UPSERT na tabela clients do CFN com lead_source=gymsite_form,
      lead_badge=GYMSITE_LEAD, gymsite_access_code={access_code}.
   3. Use apenas telefone e email do formulario -- os demais dados vem da Receita Federal.',
  'cma'
);
```

### Navi Notifier
```sql
INSERT INTO agents (name, slug, role, system_prompt, execution_mode)
VALUES (
  'Navi Notifier', 'navi-notifier', 'specialist',
  'Voce recebe dados de um lead gymsite {nome, cnpj, email, telefone, access_code}.
   Chame navi_client.create_gymsite_deal() para criar o deal no CRM Navi.
   Este e um side-effect best-effort -- nao falhe a task se o Navi estiver indisponivel.',
  'cma'
);
```

---

## 8. Ordem de execucao

```
Semana 1 -- Paralelo:
  Voce       -> GYM-02 (Tunnel), GYM-03 (Pages), GYM-04 (env vars)
  Agente 1   -> GYM-01 (Dockerfile), GYM-05 (CORS), GYM-18/19 (access_code)
  Agente 3   -> GYM-06 a GYM-14 (endpoint + migrations + Hermes + Navi client)

Semana 2 -- Apos Agente 3 commit:
  Agente 2   -> GYM-11, GYM-12 (GymSiteSection no vectracargo)
  Agente 4   -> GYM-15, GYM-16 (migration CFN + badge)
  Agente 5   -> GYM-17 (confirmar/criar deal navi)

Semana 3:
  Voce       -> GYM-20 e2e completo
```

---

## 9. Acceptance criteria e2e (GYM-20)

1. Usuario preenche form em vectracargo.com.br: Nome, CNPJ, email, telefone
2. CNPJ valido -> BrasilAPI preenche nome automaticamente (loading state visivel)
3. Submit -> POST /api/gymsite/lead retorna HTTP 201 com access_code
4. UI exibe "Acesso enviado! Verifique seu e-mail."
5. Em ate 5 minutos: email chega com access_code em destaque + link gymsite
6. Acessar URL com ?code= -> gymsite valida e exibe relatorio (ou form de solicitacao)
7. CFN mostra novo cliente com badge "GymSite Lead"
8. Navi mostra deal com source "gymsite_lead_form" e tag "gymsite"
9. CNPJ duplicado no form -> mensagem de erro 409 amigavel, sem crash

---

## 10. Mudancas em relacao ao PRD v1.0

| Item | v1.0 (errado) | v1.1 (correto) |
|------|---------------|----------------|
| Frontend gymsite | "a construir" | Ja existe completo -- nao tocar |
| TanStack Router | "proxima fase" | Ja configurado (router.tsx 231 linhas) |
| Auth (Login+OTP) | Nao mencionado | Ja existe (LoginPage 404 linhas) |
| Telas Viewer/Aguardando/Lista | Nao mencionadas | Ja existem e funcionam |
| Agente 1 escopo | frontend + Dockerfile + CORS | APENAS Dockerfile + CORS + access_code |
| Total de issues | GYM-01 a GYM-23 (23 issues) | GYM-01 a GYM-20 (20 issues, sem buracos) |
| GYM access_code | "validar no get_relatorio" | Migration + validacao no endpoint existente |
| api_routes/gymsite.py | Nao mencionado | Padrao correto (nao adicionar direto em api.py) |
