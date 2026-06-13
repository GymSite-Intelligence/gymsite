# TASKS.md — Tarefas Atômicas: Ferramenta de Auditoria AI-Driven

> **Baseado em:** SPEC.md `spec-audit-001` + PLAN.md `plan-audit-001`  
> **Metodologia:** Spec-Driven Development (SDD) — Formação DEV AI Driven Development  
> **Versão:** 1.0  
> **Status:** Draft → Review → Approved → Ready for Implementation  
> **Sprint:** `Sprint 1-3` (6 semanas)

---

## 📋 VISÃO GERAL

| Campo | Valor |
|-------|-------|
| **Tasks ID** | `tasks-audit-001` |
| **Plan ID** | `plan-audit-001` |
| **Feature ID** | `spec-audit-001` |
| **Total de Tasks** | `24` |
| **Sprints** | `3 sprints (6 semanas)` |
| **Equipe** | `1 Arquiteto + 2 Devs Senior + 1 Security Engineer + 1 DevOps` |
| **Status** | `Ready for Implementation` |

---

## 🗂️ ESTRUTURA DAS SPRINTS

| Sprint | Foco | Tasks | Semanas |
|--------|------|-------|---------|
| **Sprint 1** | Foundation — Core Domain, DB, API, Infra | T01-T08 | 1-2 |
| **Sprint 2** | Plugins & Scanning — SAST, SCA, Secrets, AI-Detect | T09-T16 | 3-4 |
| **Sprint 3** | Orchestration, Reporting, UI, CI/CD, Hardening | T17-T24 | 5-6 |

---

## 🏗️ SPRINT 1 — FOUNDATION (Semanas 1-2)

### T01: Setup de Infraestrutura e Ambiente
**Descrição:** Configurar ambiente de desenvolvimento com Docker Compose, PostgreSQL, Redis, MinIO, e estrutura de pastas do projeto.

**Dependências:** Nenhuma

**Critérios de Aceite:**
- [ ] `docker-compose.yml` funcional com: API, Worker, Web, PostgreSQL, Redis, MinIO
- [ ] Migrations iniciais executam sem erro
- [ ] Health checks de todos os serviços passam
- [ ] Documentação de setup no `README.md`
- [ ] `.env.example` com todas as variáveis necessárias

**Estimativa:** `4h`

**Agente:** DevOps

---

### T02: Modelo de Dados e Migrations
**Descrição:** Implementar schema de banco de dados (PostgreSQL) para Audit, Finding, ScorecardConfig, ComplianceMapping, ControlDetail. Criar migrations versionadas.

**Dependências:** T01

**Critérios de Aceite:**
- [ ] Tabelas criadas: `audits`, `findings`, `scorecard_configs`, `compliance_mappings`, `control_details`
- [ ] Índices otimizados para queries frequentes (por projeto, por data, por severidade)
- [ ] Constraints de integridade referencial (FKs, NOT NULL, CHECK)
- [ ] Migration rollback testado
- [ ] Seed data para desenvolvimento (exemplo de audit e findings)

**Estimativa:** `6h`

**Agente:** Dev Senior

---

### T03: Domain Model — Entidades Core
**Descrição:** Implementar entidades de domínio (Audit, Finding, Scorecard, Dimension) com regras de negócio puras, sem dependência de frameworks.

**Dependências:** T02

**Critérios de Aceite:**
- [ ] Classes/entidades: `Audit`, `Finding`, `ScorecardConfig`, `Dimension`, `Severity`, `Status`
- [ ] Validações de domínio: score entre 0-10, pesos somam 1.0, severidade válida
- [ ] Métodos de domínio: `calculateOverallScore()`, `determineStatus()`, `addFinding()`
- [ ] 100% cobertura de testes unitários nestas entidades
- [ ] Sem imports de infraestrutura (DB, HTTP, etc.) no domínio

**Estimativa:** `8h`

**Agente:** Dev Senior

---

### T04: Plugin Interface e Registry
**Descrição:** Definir e implementar a interface comum `ScannerPlugin` e o sistema de registro/descoberta de plugins.

**Dependências:** T03

**Critérios de Aceite:**
- [ ] Interface `ScannerPlugin` definida com: `name`, `version`, `category`, `execute()`, `parseOutput()`, `validateConfig()`
- [ ] Registry de plugins: carregamento dinâmico de plugins em `src/plugins/`
- [ ] Validação de configuração por plugin (Zod schemas)
- [ ] Testes unitários: registry carrega plugins, valida configs, rejeita plugins inválidos
- [ ] Documentação de como criar um novo plugin (`docs/PLUGIN_DEVELOPMENT.md`)

**Estimativa:** `6h`

**Agente:** Dev Senior

---

### T05: API Gateway — Auth, Rate Limiting, Validation
**Descrição:** Implementar API Gateway com autenticação (JWT + API Key), rate limiting (Redis), e validação de requests (Zod).

**Dependências:** T01

**Critérios de Aceite:**
- [ ] Endpoints protegidos: JWT para usuários, API Key para CI/CD
- [ ] Rate limiting: por IP (100 req/min), por API key (1000 req/h), por user (500 req/h)
- [ ] RBAC: roles Admin, Auditor, Developer, Viewer, CI_CD
- [ ] Request validation com Zod em todos os endpoints
- [ ] Response DTOs que não expõem dados internos (evidence apenas via hash)
- [ ] Testes de integração para auth e rate limiting

**Estimativa:** `8h`

**Agente:** Dev Senior

---

### T06: Audit Engine — Workflow e State Machine
**Descrição:** Implementar o motor de auditoria com workflow de 5 fases (Initialize → Scan → Analyze → Score → Report) e state machine.

**Dependências:** T03, T04, T05

**Critérios de Aceite:**
- [ ] State machine: `PENDING → RUNNING → COMPLETED` / `FAILED` / `ABORTED`
- [ ] Checkpointing: estado persistido em PostgreSQL a cada transição
- [ ] Retry policy: 3 tentativas com exponential backoff para falhas transitórias
- [ ] Circuit breaker: desabilita plugin após 3 falhas consecutivas
- [ ] Timeout: 10 min para scanners síncronos, 30 min para assíncronos
- [ ] Testes unitários: todas as transições de estado, retry, circuit breaker, timeout

**Estimativa:** `10h`

**Agente:** Dev Senior

---

### T07: S3/MinIO Integration — Evidências Imutáveis
**Descrição:** Implementar upload de evidências para S3/MinIO com versioning, hash SHA-256, e lifecycle policy.

**Dependências:** T01

**Critérios de Aceite:**
- [ ] Upload de arquivos (logs, screenshots) para S3/MinIO com metadata
- [ ] Hash SHA-256 calculado no upload e armazenado em PostgreSQL
- [ ] Versioning habilitado no bucket (não sobrescreve)
- [ ] Lifecycle policy: arquivar para Glacier após 1 ano (nunca deletar)
- [ ] Acesso apenas via API (não direto)
- [ ] Redaction automática de PII/secrets antes de upload
- [ ] Testes de integração: upload, download, hash verification, versioning

**Estimativa:** `6h`

**Agente:** DevOps

---

### T08: Redis Integration — Cache e Filas
**Descrição:** Configurar Redis para cache de resultados de scan, sessões de auditoria, rate limiting, e fila de workers (BullMQ).

**Dependências:** T01

**Critérios de Aceite:**
- [ ] Cache de resultados de scan: TTL 1h, invalidação por chave
- [ ] Sessões de auditoria: TTL 30 min, armazena estado intermediário
- [ ] Rate limiting: implementado com Redis (sliding window)
- [ ] Fila BullMQ: jobs de scan com prioridade, retry, e dead letter queue
- [ ] Pub/sub para notificações de progresso de auditoria
- [ ] Testes de integração: cache hit/miss, fila, pub/sub

**Estimativa:** `6h`

**Agente:** DevOps

---

## 🔌 SPRINT 2 — PLUGINS & SCANNING (Semanas 3-4)

### T09: Semgrep Plugin (SAST)
**Descrição:** Implementar plugin que executa Semgrep em um repositório e parseia os resultados para o formato `Finding`.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Plugin executa `semgrep --config=auto --json` no repo
- [ ] Parseia output JSON para array de `Finding[]`
- [ ] Mapeia regras Semgrep para checks do SPEC (OWASP ASVS refs)
- [ ] Configuração: regras customizáveis via `.semgrep.yml`
- [ ] Testes de integração: repo de exemplo com vulnerabilidades conhecidas
- [ ] Testes unitários: parsing de output JSON válido e inválido

**Estimativa:** `8h`

**Agente:** Dev Senior

---

### T10: SonarQube Plugin (SAST)
**Descrição:** Implementar plugin que consome API REST do SonarQube para buscar issues de um projeto.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Plugin consome API `/api/issues/search` do SonarQube
- [ ] Parseia issues SonarQube para `Finding[]`
- [ ] Mapeia severidade SonarQube (BLOCKER, CRITICAL, MAJOR, MINOR) para Severity do domínio
- [ ] Suporta autenticação via token SonarQube
- [ ] Testes de integração: mock server SonarQube (WireMock/TestContainers)
- [ ] Testes unitários: parsing de resposta API

**Estimativa:** `6h`

**Agente:** Dev Senior

---

### T11: Snyk Plugin (SCA)
**Descrição:** Implementar plugin que executa `snyk test --json` e parseia resultados de vulnerabilidades e licenças.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Plugin executa `snyk test --json` no repo
- [ ] Parseia vulnerabilidades (CVE, CVSS, severity) para `Finding[]`
- [ ] Parseia licenças conflitantes (GPL/AGPL) para `Finding[]`
- [ ] Detecta typosquatting (compara nomes de pacotes com registry)
- [ ] Testes de integração: repo com dependências vulneráveis conhecidas
- [ ] Testes unitários: parsing de output JSON

**Estimativa:** `8h`

**Agente:** Security Engineer

---

### T12: GitLeaks Plugin (Secrets Scanning)
**Descrição:** Implementar plugin que executa `gitleaks detect --source . --report-format json` e parseia findings.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Plugin executa `gitleaks detect` no repo
- [ ] Parseia secrets encontrados para `Finding[]` (sem expor o secret em si)
- [ ] Mapeia para check `5.3` (Secrets scanning) do SPEC
- [ ] Verifica histórico git (não só working directory)
- [ ] Testes de integração: repo com secrets hardcoded (fictícios)
- [ ] Testes unitários: parsing de output JSON

**Estimativa:** `6h`

**Agente:** Security Engineer

---

### T13: TruffleHog Plugin (Secrets History Scanning)
**Descrição:** Implementar plugin que executa `trufflehog filesystem --json` para detectar secrets em todo o histórico.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Plugin executa `trufflehog filesystem` no repo
- [ ] Parseia findings para `Finding[]`
- [ ] Verifica histórico completo (git log)
- [ ] Deduplica com GitLeaks (mesmo secret não aparece 2x)
- [ ] Testes de integração: repo com secrets em commits antigos
- [ ] Testes unitários: parsing de output JSON

**Estimativa:** `6h`

**Agente:** Security Engineer

---

### T14: AI-Generated Code Detector (Custom Plugin)
**Descrição:** Implementar plugin heurístico que detecta código AI-generated via análise de git history, padrões de commit, e heurísticas de código.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Analisa git history: commits com prefixo `[AI]`, `ai-generated`, ou tag `co-authored-by: ai-agent`
- [ ] Heurísticas de código: padrões comuns de AI (comentários genéricos, estruturas repetitivas)
- [ ] Calcula `% de código AI-generated` por arquivo e por feature
- [ ] Rastreabilidade: modelo, data, prompt ref (quando disponível)
- [ ] Precision > 90%, Recall > 85% (validado com dataset anotado)
- [ ] Testes unitários: heurísticas em repos de exemplo

**Estimativa:** `10h`

**Agente:** Dev Senior

---

### T15: SDD Validator Plugin (Custom Plugin)
**Descrição:** Implementar plugin que verifica existência e qualidade de SPEC.md, PLAN.md, TASKS.md no repositório.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Verifica existência de `specs/` ou diretório equivalente
- [ ] Verifica se cada feature recente tem SPEC.md + PLAN.md + TASKS.md
- [ ] Valida qualidade dos specs: critérios de aceite, regras de negócio, copy
- [ ] Verifica se specs têm seção "Contexto para IA"
- [ ] Compara git diff vs spec (alerta se código mudou sem spec atualizado)
- [ ] Testes de integração: repos com e sem SDD

**Estimativa:** `8h`

**Agente:** Dev Senior

---

### T16: Context Engineering Check Plugin (Custom Plugin)
**Descrição:** Implementar plugin que verifica rules, skills, MCPs, e CONSTITUTION.md.

**Dependências:** T04, T06

**Critérios de Aceite:**
- [ ] Verifica `.cursor/rules/`, `CLAUDE.md`, `copilot-instructions.md`
- [ ] Verifica `CONSTITUTION.md` com não-negociáveis
- [ ] Verifica `mcp/` com configurações de MCPs
- [ ] Verifica progressive disclosure (ordem numérica 01-, 02-)
- [ ] Verifica versionamento de rules (não em .gitignore)
- [ ] Testes de integração: repos com e sem context engineering

**Estimativa:** `6h`

**Agente:** Dev Senior

---

## 🎛️ SPRINT 3 — ORCHESTRATION, REPORTING, UI, HARDENING (Semanas 5-6)

### T17: Analyzer Agent — Consolidação e Deduplicação de Findings
**Descrição:** Implementar agente que consolida findings de múltiplos plugins, remove duplicatas, e classifica severidade final.

**Dependências:** T09-T16

**Critérios de Aceite:**
- [ ] Recebe findings de todos os plugins e consolida em lista única
- [ ] Deduplicação: mesmo arquivo + linha + tipo = 1 finding (mantém o mais severo)
- [ ] Classificação de severidade: regras de override (ex: SAST + SCA = CRITICAL)
- [ ] Enriquecimento: adiciona frameworkRef, recommendation, evidenceHash
- [ ] Testes unitários: deduplicação, classificação, enriquecimento
- [ ] Testes de integração: 3 plugins retornando findings sobrepostos

**Estimativa:** `8h`

**Agente:** Dev Senior

---

### T18: Scorer Agent — Cálculo de Scorecard
**Descrição:** Implementar agente que calcula scorecard por dimensão com pesos configuráveis e thresholds.

**Dependências:** T17

**Critérios de Aceite:**
- [ ] Calcula score por dimensão (0-10) baseado em findings PASS/FAIL/N/A
- [ ] Aplica pesos configuráveis (default do SPEC, override por org)
- [ ] Calcula overall score: média ponderada das dimensões
- [ ] Determina status: APPROVED / CONDITIONAL / REJECTED baseado em thresholds
- [ ] Validação: pesos somam 1.0, scores entre 0-10, status consistente
- [ ] Testes unitários: todas as combinações de pesos e findings
- [ ] Testes de integração: scorecard real de repo de exemplo

**Estimativa:** `8h`

**Agente:** Dev Senior

---

### T19: Reporter Agent — Geração de Relatórios
**Descrição:** Implementar agente que gera relatório em JSON, Markdown, e PDF.

**Dependências:** T18

**Critérios de Aceite:**
- [ ] JSON: schema validado, completo, com todos os findings e scorecard
- [ ] Markdown: formato legível, com emojis, tabelas, e links para evidências
- [ ] PDF: gerado a partir de Markdown (via Puppeteer/Playwright), com header/footer
- [ ] Compliance Mapping: seção com % de controles atendidos por framework
- [ ] Plano de Remediação: gerado automaticamente a partir de findings 🔴 e 🟡
- [ ] Hash SHA-256 do relatório calculado e armazenado
- [ ] Testes unitários: geração de cada formato
- [ ] Testes de integração: relatório completo de repo real

**Estimativa:** `10h`

**Agente:** Dev Senior

---

### T20: Web UI — Dashboard de Auditorias
**Descrição:** Implementar dashboard Next.js para visualizar auditorias, scorecards, findings, e tendências.

**Dependências:** T05, T19

**Critérios de Aceite:**
- [ ] Dashboard: lista de auditorias com filtros (projeto, data, status, score)
- [ ] Scorecard visual: gráfico de radar ou barras por dimensão
- [ ] Findings: lista paginada com filtros (severidade, dimensão, status)
- [ ] Relatório: visualização inline do Markdown + download PDF
- [ ] Tendências: gráfico de evolução de score ao longo do tempo
- [ ] Responsivo: funciona em desktop e mobile
- [ ] Testes E2E: Playwright — 5 fluxos principais (login, executar audit, ver scorecard, ver findings, download report)

**Estimativa:** `12h`

**Agente:** Dev Senior

---

### T21: CLI Tool — Auditoria Local
**Descrição:** Implementar CLI tool em Node.js/TypeScript para executar auditoria localmente e gerar relatório.

**Dependências:** T06, T19

**Critérios de Aceite:**
- [ ] Comando: `audit-cli run --repo /path/to/repo --config config.yml`
- [ ] Output: relatório em JSON/Markdown/PDF no diretório atual
- [ ] Configuração: arquivo YAML com plugins, pesos, thresholds
- [ ] Progresso: barra de progresso no terminal
- [ ] Verbose mode: logs detalhados de cada plugin
- [ ] Testes E2E: execução em repos de exemplo
- [ ] Publicação: npm package `@company/audit-cli`

**Estimativa:** `8h`

**Agente:** Dev Senior

---

### T22: CI/CD Integration — GitHub Actions
**Descrição:** Implementar GitHub Action que executa auditoria em PRs e bloqueia merge se reprovado.

**Dependências:** T21

**Critérios de Aceite:**
- [ ] Action YAML: `.github/actions/ai-audit/action.yml`
- [ ] Executa auditoria no código do PR (não no base)
- [ ] Posta comentário no PR com scorecard e findings 🔴
- [ ] Bloqueia merge se status = REJECTED (via branch protection)
- [ ] Permite merge condicional se status = CONDITIONAL (com warning)
- [ ] Configuração: pesos e thresholds via `ai-audit.yml` no repo
- [ ] Testes: action testada em repo de exemplo

**Estimativa:** `6h`

**Agente:** DevOps

---

### T23: Observabilidade — Tracing, Metrics, Logging
**Descrição:** Implementar observabilidade completa: OpenTelemetry tracing, Prometheus metrics, structured logging.

**Dependências:** T01, T06

**Critérios de Aceite:**
- [ ] Tracing distribuído: trace ID propagado entre API, workers, plugins
- [ ] Metrics Prometheus: tempo de scan, count de findings, score distribution
- [ ] Logging estruturado: JSON, com trace ID, nível, componente
- [ ] Dashboard Grafana: visualização de métricas de auditoria
- [ ] Alertas: tempo de scan > 30 min, error rate > 1%, critical findings > 0
- [ ] Testes: verificar que traces e logs são emitidos corretamente

**Estimativa:** `8h`

**Agente:** DevOps

---

### T24: Hardening, Docs, e Self-Audit
**Descrição:** Hardening de segurança, documentação completa, e execução de self-audit (a ferramenta se audita).

**Dependências:** T01-T23

**Critérios de Aceite:**
- [ ] Hardening: SAST passando (Semgrep), SCA passando (Snyk), secrets scan passando (GitLeaks)
- [ ] Self-audit: a ferramenta executa auditoria no próprio código
- [ ] Score de self-audit > 7.0 (meta: comer o próprio dog food)
- [ ] Documentação: `README.md`, `ARCHITECTURE.md`, `PLUGIN_DEVELOPMENT.md`, `API.md`
- [ ] Runbooks: `docs/runbooks/ONCALL.md`, `docs/runbooks/DEBUGGING.md`
- [ ] ADRs: decisões arquiteturais documentadas em `docs/architecture-decisions/`
- [ ] Handoff: documentação para equipe de operações manter a ferramenta

**Estimativa:** `10h`

**Agente:** Arquiteto + DevOps + Security Engineer

---

## 📊 RESUMO DE ESTIMATIVAS

| Sprint | Tasks | Horas Totais | Horas/Dev | Risco |
|--------|-------|-------------|-----------|-------|
| **Sprint 1** | T01-T08 | 54h | 27h (2 devs) | Baixo — foundation é previsível |
| **Sprint 2** | T09-T16 | 58h | 29h (2 devs) | Médio — plugins externos podem variar |
| **Sprint 3** | T17-T24 | 62h | 31h (2 devs) | Médio — UI e reporting são complexos |
| **TOTAL** | T01-T24 | **174h** | **87h/dev** | — |

**Buffer recomendado:** +20% = **35h** → **209h totais** (~6 semanas com 2 devs full-time)

---

## 🔗 DEPENDÊNCIAS ENTRE TASKS

```
T01 ─┬─► T02 ──► T03 ──► T04 ──► T06
     │                      │
     ├─► T05 ───────────────┤
     │                      │
     ├─► T07 ───────────────┤
     │                      │
     └─► T08 ───────────────┘
                          │
                          ▼
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
            T09-T16 (Plugins) ──► T17 (Analyzer)
                                      │
                                      ▼
                                    T18 (Scorer)
                                      │
                                      ▼
                                    T19 (Reporter)
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                          ▼                       ▼
                        T20 (Web UI)            T21 (CLI)
                          │                       │
                          │                       ▼
                          │                     T22 (CI/CD)
                          │                       │
                          └───────────┬───────────┘
                                      │
                                      ▼
                                    T23 (Observability)
                                      │
                                      ▼
                                    T24 (Hardening)
```

---

## 🎯 DEFINITION OF DONE (DoD)

Toda task está "Done" quando:

- [ ] Código implementado seguindo `.cursor/rules/` e `CONSTITUTION.md`
- [ ] Testes unitários > 80% de cobertura em regras de negócio
- [ ] Testes de integração passando (TestContainers quando aplicável)
- [ ] Code review aprovado por pelo menos 1 dev senior
- [ ] SAST passando (Semgrep — 0 issues críticos no novo código)
- [ ] Documentação atualizada (README, API docs, ou inline comments)
- [ ] Nenhum secret hardcoded (GitLeaks passando)
- [ ] CI/CD passando (testes, lint, build)
- [ ] Feature flag desabilitada em prod (se aplicável) — habilitada apenas em staging

---

## 📝 NOTAS

- **T14 (AI Detector)** é a task mais arriscada — heurísticas de detecção de código AI são imprecisas. Recomenda-se começar com regras simples (git history) e iterar.
- **T20 (Web UI)** pode ser simplificado na Fase 1 — focar em API + CLI primeiro, UI como Fase 2.
- **T22 (CI/CD)** é crítico para adoção — sem integração em pipeline, devs não usarão a ferramenta.
- **T24 (Self-Audit)** é o "dog fooding" — se a ferramenta não consegue se auditar com score > 7.0, não está pronta.

---

> **Status:** `Ready for Implementation` — Todas as tasks estão estimadas, com dependências mapeadas, e critérios de aceite claros. Próximo passo: atribuir tasks à sprint e iniciar desenvolvimento.
