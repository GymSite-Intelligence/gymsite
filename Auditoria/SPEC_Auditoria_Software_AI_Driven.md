# SPEC.md — Auditoria de Software para Codebases AI-Driven

> **Metodologia:** Spec-Driven Development (SDD) + Frameworks de Auditoria de Software  
> **Baseado em:** OWASP ASVS 4.0, NIST SSDF 1.1, ISO 27001:2022, COBIT 2019, CIS Controls v8, SANS SWAT  
> **Versão:** 1.0  
> **Status:** Approved  
> **Escopo:** Processo genérico de auditoria aplicável a qualquer codebase AI-driven

---

## 📋 1. IDENTIFICAÇÃO

| Campo | Valor |
|-------|-------|
| **Feature ID** | `spec-audit-001` |
| **Nome** | Auditoria de Software para Codebases AI-Driven |
| **Status** | `Approved` |
| **Prioridade** | `P0` |
| **Responsável** | `@tech-lead` / `@security-officer` / `@auditor` |
| **Data de criação** | `2026-06-13` |
| **Data de aprovação** | `2026-06-13` |
| **Estimativa (SDD)** | `4 horas (execução) + 2 horas (report)` |
| **Sprint/Epic** | `Epic-000: Qualidade & Compliance` |
| **Frequência** | `A cada release major / A cada sprint / On-demand` |

---

## 🎯 2. OBJETIVO DE NEGÓCIO

### 2.1 Problema
Codebases desenvolvidos com assistência de IA apresentam riscos sistêmicos que os métodos tradicionais de auditoria não capturam: código gerado sem arquitetura definida, dependências inexistentes (hallucinação), vazamento de secrets, violação de licenças, e acúmulo exponencial de débito técnico. A falta de um processo de auditoria formalizado para este contexto expõe a organização a riscos de segurança, compliance, operacionais e financeiros.

### 2.2 Solução Proposta
Formalizar um processo de auditoria de software que combine **boas práticas estabelecidas de engenharia de software** (OWASP, NIST, ISO, COBIT, CIS) com **controles específicos para AI-Driven Development**, produzindo um scorecard de maturidade, relatório de gaps e plano de remediação acionável.

### 2.3 Critérios de Sucesso (KPIs)

| KPI | Baseline | Target | Métrica |
|-----|----------|--------|---------|
| Taxa de issues críticos pós-audit | `N/A` | `0` | Issues severidade 🔴 em produção |
| Tempo médio de remediação | `N/A` | `< 48h` | Horas entre identificação e fix |
| Cobertura de auditoria | `0%` | `100%` | % de features auditadas por sprint |
| Score de maturidade AI-Driven | `N/A` | `> 7.0` | Scorecard 0-10 |
| Falsos positivos de SAST | `N/A` | `< 10%` | % de findings descartados |

---

## 👤 3. PERSONAS & USUÁRIOS

### 3.1 Auditor Técnico
- **Perfil:** Tech Lead, Security Engineer, ou Arquiteto de Software
- **Necessidade:** Executar auditoria estruturada em < 4h com checklist claro e evidências automatizáveis
- **Frustração atual:** Falta de framework unificado que una segurança tradicional + riscos de IA

### 3.2 Desenvolvedor
- **Perfil:** Dev que usa IA (Cursor, Claude Code, Copilot) no dia a dia
- **Necessidade:** Saber exatamente o que precisa corrigir antes do merge
- **Frustração atual:** Recebe feedback de qualidade só em review, sem critérios objetivos

### 3.3 CISO / Compliance Officer
- **Perfil:** Responsável por segurança e compliance organizacional
- **Necessidade:** Evidência documentada de controles para auditorias externas (SOC2, ISO 27001)
- **Frustração atual:** Não consegue demonstrar controle sobre código gerado por IA

---

## 📝 4. REQUISITOS FUNCIONAIS

### RF-001: Execução de Auditoria Estruturada por Dimensão
**Descrição:** O sistema de auditoria deve permitir a execução de checks organizados em 9 dimensões críticas, cada uma mapeada a frameworks de boas práticas de software existentes.

**Fluxo Principal:**
1. Auditor seleciona o repositório/branch a ser auditado
2. Sistema executa checks automatizados (SAST, SCA, secrets, schema, etc.)
3. Auditor executa checks manuais (arquitetura, SDD, orquestração, context engineering)
4. Sistema consolida findings em relatório estruturado
5. Sistema calcula scorecard de maturidade ponderado

**Fluxos Alternativos:**
- **FA-001:** Repositório sem CI/CD configurado → auditoria manual completa com evidência documentada
- **FA-002:** Falha em tool de SAST/SCA → auditoria prossegue com checks manuais + flag de tooling gap
- **FA-003:** Código 100% AI-generated sem review humano → score de segurança = 0, bloqueio de deploy

**Critérios de Aceite:**
- [ ] Todas as 9 dimensões são verificadas em toda auditoria
- [ ] Cada check tem severidade definida (🔴 Crítico / 🟡 Alto / 🟢 Médio)
- [ ] Framework de referência é citado para cada dimensão (OWASP, NIST, ISO, etc.)
- [ ] Relatório é gerado em < 5 minutos após execução
- [ ] Scorecard é calculado automaticamente com pesos configuráveis

**Regras de Negócio:**
- **RN-001:** Dimensão "Segurança" tem peso mínimo de 15% no scorecard
- **RN-002:** Qualquer check 🔴 Crítico não resolvido bloqueia aprovação de deploy
- **RN-003:** Auditoria deve ser repetível — mesmo auditor, mesmo repo, mesmo resultado
- **RN-004:** Evidências de cada check (screenshot, log, hash) são imutáveis e versionadas

---

### RF-002: Mapeamento a Frameworks de Boas Práticas Existentes
**Descrição:** Cada dimensão e check deve ser explicitamente mapeado a um requisito, controle ou diretriz de framework de software engineering reconhecido.

**Fluxo Principal:**
1. Auditor consulta matriz de mapeamento dimensão ↔ framework
2. Sistema exige evidência de compliance para cada controle mapeado
3. Relatório final inclui seção "Compliance Mapping" com referências cruzadas

**Critérios de Aceite:**
- [ ] Cada dimensão cita pelo menos 1 framework de referência
- [ ] Cada check 🔴 Crítico cita controle específico (ex: OWASP ASVS V2.1.1)
- [ ] Matriz de mapeamento é versionada e auditável
- [ ] Gaps são reportados com referência ao controle não atendido

**Regras de Negócio:**
- **RN-005:** Frameworks base: OWASP ASVS 4.0, NIST SSDF 1.1 (PW, PO, RV), ISO 27001:2022 (A.8, A.12, A.14), COBIT 2019 (APO12, BAI03, DSS05), CIS Controls v8 (Controls 6, 7, 8, 16), SANS SWAT
- **RN-006:** Frameworks AI-specific: OWASP Top 10 for LLM Applications 2026, AI-Induced Risk Audit (AIRA), NIST AI RMF 1.0

---

### RF-003: Detecção de Código AI-Generated e Rastreabilidade
**Descrição:** O sistema deve identificar arquivos/código gerados por IA, rastrear qual agente/modelo/prompt foi usado, e verificar se passou por review humano.

**Fluxo Principal:**
1. Sistema analisa git history para identificar commits AI-generated (via mensagem, autor, ou tag)
2. Sistema cruza com PRs para verificar presença de review humano aprovador
3. Sistema verifica se o código AI-generated tem testes associados
4. Sistema verifica se o código segue `.cursor/rules/` ou equivalente

**Fluxos Alternativos:**
- **FA-004:** Commit não identificável como AI ou humano → marcado como "origem desconhecida" → requer review manual
- **FA-005:** Código AI-generated sem testes → finding 🔴 Crítico automaticamente

**Critérios de Aceite:**
- [ ] % de código AI-generated é calculado por arquivo e por feature
- [ ] Cada arquivo AI-generated tem rastreabilidade: autor (human/AI), modelo (se AI), data, prompt ref
- [ ] 100% de código AI-generated em produção tem review humano aprovado
- [ ] Código AI-generated sem testes é bloqueado em CI

**Regras de Negócio:**
- **RN-007:** Commits AI-generated devem usar prefixo padronizado: `[AI]`, `ai-generated`, ou tag `co-authored-by: ai-agent`
- **RN-008:** Review humano obrigatório para qualquer arquivo com > 50% de código AI-generated
- **RN-009:** Código AI-generated que altera regras de segurança (auth, crypto, input validation) requer review de Security Officer

---

### RF-004: Validação de Spec-Driven Development (SDD)
**Descrição:** O sistema deve verificar se o projeto segue SDD: existência de SPEC.md, PLAN.md, tasks atômicas, e qualidade dos specs.

**Fluxo Principal:**
1. Sistema verifica existência de `specs/` ou diretório equivalente
2. Sistema verifica se cada feature recente tem SPEC.md + PLAN.md + TASKS.md
3. Sistema verifica qualidade dos specs (critérios de aceite, regras de negócio, copy)
4. Sistema verifica se specs são atualizados quando código muda (git diff vs spec)

**Critérios de Aceite:**
- [ ] % de features com SPEC.md completo > 90%
- [ ] % de features com PLAN.md > 80%
- [ ] % de features com TASKS.md > 80%
- [ ] Cada SPEC.md tem critérios de aceite mensuráveis
- [ ] Cada SPEC.md tem regras de negócio numeradas
- [ ] Cada SPEC.md tem copy exato da UI (não placeholder)

**Regras de Negócio:**
- **RN-010:** Feature sem SPEC.md não pode ser merged para main (gate em CI)
- **RN-011:** Alteração de código sem atualização de SPEC.md gera finding 🟡 Alto
- **RN-012:** SPEC.md deve ter seção "Contexto para IA" (AI-specific)

---

### RF-005: Verificação de Context Engineering
**Descrição:** O sistema deve verificar se o projeto tem rules, skills, MCPs e memória de contexto bem gerenciada.

**Fluxo Principal:**
1. Sistema verifica existência de `.cursor/rules/`, `CLAUDE.md`, `copilot-instructions.md`
2. Sistema verifica se rules seguem progressive disclosure (geral → específico)
3. Sistema verifica se MCPs estão configurados e versionados
4. Sistema verifica se existe `CONSTITUTION.md` com não-negociáveis

**Critérios de Aceite:**
- [ ] `.cursor/rules/` ou equivalente existe e tem > 1 arquivo
- [ ] `CONSTITUTION.md` existe com não-negociáveis (testes, segurança, estilo)
- [ ] MCPs estão documentados em `mcp/` ou equivalente
- [ ] Rules são versionadas junto com código (não em .gitignore)
- [ ] Context window de tasks é monitorado (evidência de threshold)

**Regras de Negócio:**
- **RN-013:** Projeto sem `CONSTITUTION.md` recebe score máximo de 5.0 em Context Engineering
- **RN-014:** Rules em `.cursor/rules/` devem ser numeradas (01-, 02-) para ordem de aplicação

---

### RF-006: Auditoria de Segurança AI-Specific
**Descrição:** O sistema deve executar checks de segurança específicos para código AI-generated, além dos checks tradicionais.

**Fluxo Principal:**
1. SAST tradicional (Semgrep, SonarQube, CodeQL) — OWASP Top 10
2. SCA (Snyk, Dependabot) — CVEs, licenças, typosquatting
3. Secrets scanning (GitLeaks, TruffleHog) — hardcoded credenciais
4. AI-specific: verificação de imports hallucinados, licenças de código gerado, PII leakage, prompt injection vectors
5. Verificação de fail-closed (comportamento seguro quando IA falha)

**Critérios de Aceite:**
- [ ] SAST passa com 0 issues críticos (OWASP ASVS V1-V14)
- [ ] SCA passa com 0 CVEs críticos (NIST SSDF RV.1)
- [ ] 0 secrets hardcoded (CIS Control 6)
- [ ] 0 imports inexistentes / typosquatting (AIRA Framework)
- [ ] PII redaction verificado antes de envio a LLM (OWASP LLM Top 10 — Sensitive Data Exposure)
- [ ] Fail-closed testado: sistema nega acesso quando IA indisponível (ISO 27001 A.12.1)

**Regras de Negócio:**
- **RN-015:** Código AI-generated que altera auth/crypto requer SAST + review manual (OWASP ASVS V2, V3, V6)
- **RN-016:** Licenças de código AI-generated devem ser compatíveis com licença do projeto (GPL/AGPL = bloqueio)
- **RN-017:** Prompt injection vectors são testados em todos os endpoints que recebem input do usuário (OWASP LLM Top 10 — LLM01)

---

### RF-007: Avaliação de Arquitetura de Software
**Descrição:** O sistema deve verificar se a arquitetura segue princípios de engenharia de software: separação de camadas, API-first, domain isolation, resiliência.

**Fluxo Principal:**
1. Verificar separação domain / application / infrastructure (Clean Architecture / Hexagonal)
2. Verificar API contracts definidos (OpenAPI / GraphQL / protobuf)
3. Verificar anti-corruption layers para integrações externas
4. Verificar circuit breakers, retry, idempotência
5. Verificar state management externo (não in-memory only)

**Critérios de Aceite:**
- [ ] Domínio isolado de frameworks e LLMs (NIST SSDF PO.3.2)
- [ ] API-first: OpenAPI/Schema é source of truth (COBIT BAI03.01)
- [ ] Circuit breaker para LLM e serviços externos (ISO 27001 A.12.1)
- [ ] Idempotência em workflows e endpoints (OWASP ASVS V11.1)
- [ ] State de orquestração persistido externamente (CIS Control 8)

**Regras de Negócio:**
- **RN-018:** Código que viola fronteiras de arquitetura (domain importa infra) é finding 🔴 Crítico
- **RN-019:** Integração com LLM sem anti-corruption layer é finding 🔴 Crítico

---

### RF-008: Verificação de Multi-Agent Orchestration
**Descrição:** O sistema deve verificar se a orquestração de agentes segue padrões de resiliência, comunicação segura e human-in-the-loop.

**Fluxo Principal:**
1. Verificar se papéis de agentes são definidos e documentados
2. Verificar se comunicação inter-agent usa schemas estritos
3. Verificar se HITL checkpoints existem para decisões de alto risco
4. Verificar timeout, retry, checkpoint/recovery
5. Verificar output validation entre agentes

**Critérios de Aceite:**
- [ ] Cada agente tem escopo único documentado
- [ ] Comunicação inter-agent usa Pydantic/JSON Schema/protobuf
- [ ] HITL existe para deploy, financeiro, dados sensíveis, alterações de auth
- [ ] Timeout e retry configurados para cada agente
- [ ] Checkpoint/recovery permite resumir workflow após falha
- [ ] Output de cada agente é validado antes de passar ao próximo

**Regras de Negócio:**
- **RN-020:** Orquestração sem HITL para alterações de auth/crypto = finding 🔴 Crítico
- **RN-021:** Agentes paralelos sem mecanismo de sincronização = finding 🟡 Alto

---

### RF-009: Observabilidade e Audit Trail
**Descrição:** O sistema deve verificar se existe observabilidade completa: tracing, LLM call logging, cost monitoring, audit trail imutável.

**Fluxo Principal:**
1. Verificar tracing distribuído (trace ID, span hierarchy)
2. Verificar LLM call observability (prompt, response, tokens, latency, modelo)
3. Verificar cost monitoring por feature/agente/usuário
4. Verificar audit trail imutável de decisões de IA
5. Verificar health checks e métricas de negócio

**Critérios de Aceite:**
- [ ] Cada execução de agente tem trace ID (OpenTelemetry / W3C)
- [ ] Cada chamada LLM é logada com prompt hash, response hash, tokens, modelo (ISO 27001 A.12.4)
- [ ] Dashboard de custo existe e é acessível (COBIT APO12.01)
- [ ] Audit trail é imutável (append-only, hash chain ou equivalente)
- [ ] Health checks expostos para load balancers
- [ ] Métricas de negócio (eficiência, acurácia, ROI) são trackadas

**Regras de Negócio:**
- **RN-022:** Audit trail mutável ou deletável = finding 🔴 Crítico (ISO 27001 A.12.4)
- **RN-023:** LLM call sem logging de tokens = finding 🟡 Alto

---

### RF-010: Testes e Quality Assurance
**Descrição:** O sistema deve verificar cobertura de testes, incluindo testes específicos para falhas de IA.

**Fluxo Principal:**
1. Verificar cobertura de testes unitários (> 80% domínio)
2. Verificar testes de integração
3. Verificar testes E2E
4. Verificar evals/scorers para qualidade de resposta LLM
5. Verificar fail-soft testing (LLM indisponível, timeout, erro)
6. Verificar AI drift detection

**Critérios de Aceite:**
- [ ] Cobertura unitária > 80% em regras de negócio (NIST SSDF RV.1.1)
- [ ] Testes de integração passando
- [ ] Testes E2E passando
- [ ] Evals existem e passam para features com IA (score > threshold)
- [ ] Fail-soft testado: comportamento quando LLM retorna erro/timeout/malformado
- [ ] AI drift detection: testes detectam mudança de comportamento entre versões de modelo

**Regras de Negócio:**
- **RN-024:** Código AI-generated sem testes associados = finding 🔴 Crítico
- **RN-025:** Feature com IA sem evals = finding 🟡 Alto
- **RN-026:** 62.6% dos erros em PRs AI-generated são runtime — mutation testing é recomendado (SANS SWAT)

---

### RF-011: Dados, RAG e Privacidade
**Descrição:** O sistema deve verificar estratégia de RAG, isolamento de dados, PII handling e grounding.

**Fluxo Principal:**
1. Verificar chunking strategy documentada
2. Verificar embedding model versionado
3. Verificar vector store isolation (multi-tenant)
4. Verificar pipeline de re-indexação
5. Verificar PII handling (redaction, anonymization)
6. Verificar grounding verification (respostas verificadas contra fonte)

**Critérios de Aceite:**
- [ ] Chunking strategy documentada e justificada
- [ ] Embedding model versionado e compatível
- [ ] Dados multi-tenant isolados no vector store (ISO 27001 A.8.1)
- [ ] Pipeline de re-indexação automática quando base muda
- [ ] PII anonimizado antes de vector store ou LLM (GDPR / LGPD)
- [ ] Grounding: respostas da IA são verificadas contra fonte (evita alucinação)

**Regras de Negócio:**
- **RN-027:** PII em vector store sem anonimização = finding 🔴 Crítico (GDPR Art. 32, LGPD Art. 46)
- **RN-028:** RAG sem threshold de relevance = finding 🟡 Alto

---

### RF-012: Deploy e Infraestrutura
**Descrição:** O sistema deve verificar pipeline CI/CD, feature flags, rate limiting, cost controls e rollback.

**Fluxo Principal:**
1. Verificar CI/CD com gates de qualidade (testes, SAST, SCA, evals)
2. Verificar feature flags para funcionalidades IA
3. Verificar rate limiting (API própria + LLM gateway)
4. Verificar cost controls (budget alerts, hard limits)
5. Verificar rollback automático
6. Verificar IaC (environment parity)

**Critérios de Aceite:**
- [ ] CI/CD tem gates: testes, SAST, SCA, evals, secrets scan (NIST SSDF PO.3.1)
- [ ] Feature flags para funcionalidades IA (LaunchDarkly / Unleash)
- [ ] Rate limiting por usuário e global (OWASP ASVS V4.2)
- [ ] Budget alerts e hard limits de gasto LLM (COBIT APO12.01)
- [ ] Rollback automático se error rate > threshold
- [ ] Dev/staging/prod idênticos via IaC (Terraform / Pulumi)

**Regras de Negócio:**
- **RN-029:** Deploy de código AI-generated sem gates = finding 🔴 Crítico
- **RN-030:** API de LLM sem rate limiting = finding 🔴 Crítico (prevenção de custo runaway)

---

## 🚫 5. REQUISITOS NÃO-FUNCIONAIS

| ID | Categoria | Requisito | Severidade | Framework Ref |
|----|-----------|-----------|------------|---------------|
| RNF-001 | Performance | Auditoria completa executa em < 30 min para repo médio (< 100k LOC) | 🔴 Crítico | NIST SSDF RV.1.3 |
| RNF-002 | Performance | Relatório gera em < 5 min após execução | 🟡 Alto | COBIT APO12.02 |
| RNF-003 | Segurança | Evidências de auditoria são imutáveis e versionadas (hash SHA-256) | 🔴 Crítico | ISO 27001 A.12.4 |
| RNF-004 | Segurança | Dados sensíveis (secrets, PII) nunca aparecem em evidências de auditoria | 🔴 Crítico | OWASP ASVS V8.1 |
| RNF-005 | Disponibilidade | Sistema de auditoria disponível 24/7 para CI/CD pipelines | 🟡 Alto | CIS Control 8 |
| RNF-006 | Compliance | Relatório de auditoria é aceito por auditores externos SOC2 / ISO 27001 | 🔴 Crítico | ISO 27001 A.18.2 |
| RNF-007 | Escalabilidade | Auditoria suporta repos de até 1M LOC sem degradação | 🟢 Médio | NIST SSDF PO.3.3 |
| RNF-008 | Usabilidade | Relatório é legível por devs não-técnicos (PO, CISO) | 🟡 Alto | COBIT BAI03.02 |

---

## 🖼️ 6. INTERFACE & RELATÓRIO DE AUDITORIA

### 6.1 Estrutura do Relatório de Auditoria

```
RELATÓRIO DE AUDITORIA — [Nome do Projeto] — [Data]
├── 1. Resumo Executivo
│   ├── Score de Maturidade: [X.X / 10]
│   ├── Status Geral: [APROVADO / CONDICIONAL / REPROVADO]
│   ├── Issues por Severidade: 🔴 [N] | 🟡 [N] | 🟢 [N]
│   └── Recomendação: [Deploy liberado / Deploy condicional / Deploy bloqueado]
│
├── 2. Scorecard por Dimensão
│   ├── Context Engineering: [X/10] (Peso 15%)
│   ├── Spec-Driven Development: [X/10] (Peso 20%)
│   ├── Arquitetura de Software: [X/10] (Peso 15%)
│   ├── Multi-Agent Orchestration: [X/10] (Peso 15%)
│   ├── Segurança: [X/10] (Peso 15%)
│   ├── Testes & QA: [X/10] (Peso 10%)
│   ├── Observabilidade: [X/10] (Peso 5%)
│   ├── Dados & RAG: [X/10] (Peso 3%)
│   └── Deploy & Infra: [X/10] (Peso 2%)
│
├── 3. Findings Detalhados (por dimensão)
│   ├── [Dimensão]
│   │   ├── [Check ID] | [Severidade] | [Status: PASS/FAIL]
│   │   ├── Descrição: [O que foi verificado]
│   │   ├── Evidência: [Link / Screenshot / Hash / Log]
│   │   ├── Framework Ref: [OWASP ASVS VX.X / NIST SSDF X.X / etc.]
│   │   └── Recomendação: [O que fazer para corrigir]
│
├── 4. Compliance Mapping
│   ├── OWASP ASVS 4.0: [X%] de controles atendidos
│   ├── NIST SSDF 1.1: [X%] de práticas atendidas
│   ├── ISO 27001:2022: [X%] de controles A.8, A.12, A.14 atendidos
│   ├── COBIT 2019: [X%] de componentes atendidos
│   ├── CIS Controls v8: [X%] de controls atendidos
│   └── OWASP LLM Top 10 2026: [X%] de riscos mitigados
│
├── 5. Plano de Remediação
│   ├── Prioridade 🔴: [Ações imediatas — < 24h]
│   ├── Prioridade 🟡: [Ações curtas — < 1 semana]
│   └── Prioridade 🟢: [Ações médias — < 1 sprint]
│
└── 6. Apêndice
    ├── Metodologia de Auditoria
    ├── Ferramentas Utilizadas
    ├── Limitações e Escopo
    └── Glossário
```

### 6.2 Estados do Relatório

| Estado | Descrição | Ação |
|--------|-----------|------|
| **APROVADO** | Score > 7.0, 0 issues 🔴 | Deploy liberado |
| **CONDICIONAL** | Score 5.0-7.0, ou issues 🔴 com mitigação temporária | Deploy liberado com feature flags + plano de remediação < 48h |
| **REPROVADO** | Score < 5.0, ou issues 🔴 críticos sem mitigação | Deploy bloqueado até remediação |

### 6.3 Mensagens & Copy do Relatório

| Contexto | Mensagem |
|----------|----------|
| APROVADO | `"✅ Auditoria aprovada. Score: [X.X]/10. Deploy liberado."` |
| CONDICIONAL | `"⚠️ Auditoria condicional. Score: [X.X]/10. [N] issues 🔴 requerem atenção. Deploy liberado com mitigações."` |
| REPROVADO | `"❌ Auditoria reprovada. Score: [X.X]/10. [N] issues 🔴 bloqueiam deploy. Plano de remediação obrigatório."` |
| Issue 🔴 | `"🔴 [CHECK-ID]: [Descrição curta]. Framework: [Ref]. Ação: [Recomendação]. Owner: [Nome]."` |
| Issue 🟡 | `"🟡 [CHECK-ID]: [Descrição curta]. Framework: [Ref]. Ação: [Recomendação]. Prazo: [Data]."` |
| Issue 🟢 | `"🟢 [CHECK-ID]: [Descrição curta]. Recomendação: [Ação de melhoria]."` |

---

## 🔌 7. INTEGRAÇÕES & DEPENDÊNCIAS

### 7.1 Integrações com Ferramentas de Auditoria

| Sistema | Tipo | Contrato | Framework Ref |
|---------|------|----------|---------------|
| Semgrep | SAST CLI | JSON output | OWASP ASVS |
| SonarQube | SAST API | REST API | NIST SSDF RV.1 |
| Snyk | SCA CLI | JSON output | CIS Control 7 |
| GitLeaks | Secrets CLI | JSON output | OWASP ASVS V8 |
| TruffleHog | Secrets CLI | JSON output | CIS Control 6 |
| OWASP Dependency-Check | SCA CLI | XML/JSON | NIST SSDF PO.3.2 |
| OpenTelemetry | Tracing API | OTLP / gRPC | ISO 27001 A.12.4 |
| Langfuse | LLM Observability | REST API | AI-specific |
| GitHub/GitLab | VCS API | GraphQL/REST | COBIT BAI03.01 |
| Jira/Linear | Issue Tracker | REST API | COBIT APO12.02 |

### 7.2 Dependências Internas

| Dependência | Status | Impacto |
|-------------|--------|---------|
| CI/CD pipeline configurada | Required | Alto — sem CI, auditoria é 100% manual |
| Repositório com git history | Required | Alto — rastreabilidade de código AI |
| `.cursor/rules/` ou equivalente | Recommended | Médio — impacta score de Context Engineering |
| `specs/` com SPEC.md | Recommended | Médio — impacta score de SDD |
| Observabilidade configurada | Recommended | Médio — impacta score de Observabilidade |

### 7.3 Schema de Dados do Relatório

```sql
-- Tabela de auditorias
CREATE TABLE software_audits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_name VARCHAR(255) NOT NULL,
  repository_url VARCHAR(500),
  branch VARCHAR(100) NOT NULL,
  commit_hash VARCHAR(64) NOT NULL,
  auditor_name VARCHAR(255),
  audit_date TIMESTAMP DEFAULT NOW(),
  overall_score DECIMAL(3,1), -- 0.0 a 10.0
  overall_status VARCHAR(20), -- 'APPROVED', 'CONDITIONAL', 'REJECTED'
  critical_issues INTEGER DEFAULT 0,
  high_issues INTEGER DEFAULT 0,
  medium_issues INTEGER DEFAULT 0,
  total_lines_of_code INTEGER,
  ai_generated_percentage DECIMAL(5,2),
  report_hash VARCHAR(64), -- SHA-256 do relatório para imutabilidade
  created_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de findings
CREATE TABLE audit_findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id UUID REFERENCES software_audits(id),
  dimension VARCHAR(50) NOT NULL, -- 'Context Engineering', 'Security', etc.
  check_id VARCHAR(50) NOT NULL,
  severity VARCHAR(20) NOT NULL, -- 'CRITICAL', 'HIGH', 'MEDIUM'
  status VARCHAR(20) NOT NULL, -- 'PASS', 'FAIL', 'N/A'
  description TEXT NOT NULL,
  evidence_url TEXT,
  evidence_hash VARCHAR(64),
  framework_ref VARCHAR(100), -- 'OWASP ASVS V2.1.1'
  recommendation TEXT NOT NULL,
  owner VARCHAR(255),
  due_date TIMESTAMP,
  resolved_at TIMESTAMP,
  resolution_evidence TEXT
);

-- Índices
CREATE INDEX idx_audits_project ON software_audits(project_name, audit_date DESC);
CREATE INDEX idx_audits_status ON software_audits(overall_status);
CREATE INDEX idx_findings_audit ON audit_findings(audit_id);
CREATE INDEX idx_findings_severity ON audit_findings(severity, status);
```

---

## 🤖 8. CONTEXTO PARA IA

### 8.1 Regras de Contexto
```
Rules aplicáveis:
- .cursor/rules/01-architecture.md → Seções 3.1 (Clean Architecture), 3.4 (API-first)
- .cursor/rules/03-testing.md → Cobertura > 80% em regras de negócio
- .cursor/rules/04-security.md → OWASP ASVS, NIST SSDF, ISO 27001
- .cursor/rules/05-audit.md → Processo de auditoria e scorecard
```

### 8.2 MCPs Necessários

| MCP | Propósito | Configuração |
|-----|-----------|-------------|
| Context7 | Buscar docs OWASP ASVS, NIST SSDF, ISO 27001 | `mcp/context7-security.yaml` |
| GitHub | Acessar repo, PRs, commits, reviews | `mcp/github.yaml` |
| SonarQube | Coletar métricas de SAST | `mcp/sonarqube.yaml` |
| Snyk | Coletar métricas de SCA | `mcp/snyk.yaml` |
| Langfuse | Coletar métricas de LLM observability | `mcp/langfuse.yaml` |

### 8.3 Modelo Recomendado

| Tarefa | Modelo | Justificativa |
|--------|--------|---------------|
| Análise de arquitetura | Claude Opus 4.7 | Excelente em análise de padrões arquiteturais |
| Análise de segurança | Claude Sonnet 4.6 | Boa em identificação de vulnerabilidades |
| Geração de relatório | GPT-5.4 Codex | Melhor em formatação e estruturação de dados |
| Review de compliance | Claude Sonnet 4.6 | Boa em mapeamento de frameworks |

### 8.4 Prompts de Referência

```
Master Prompt para Agente Auditor:
"Você é um auditor de software sênior certificado em OWASP ASVS, NIST SSDF e ISO 27001.
Sua tarefa é executar a auditoria seguindo estritamente:
1. O SPEC.md de auditoria (spec-audit-001)
2. Os frameworks de referência citados em cada dimensão
3. NUNCA ignorar um check 🔴 Crítico — se não puder verificar, marque como 'N/A' com justificativa
4. Documentar evidência para CADA check (screenshot, log, hash, ou referência a tool)
5. Output: relatório JSON seguindo o schema definido em RF-012 + scorecard"
```

### 8.5 Contexto de Domínio

```
Este spec de auditoria é GENÉRICO e aplica-se a qualquer codebase AI-driven.
Não é atrelado a um domínio de negócio específico (fintech, health, etc.).

Frameworks base obrigatórios:
- OWASP ASVS 4.0 (Application Security Verification Standard)
- NIST SSDF 1.1 (Secure Software Development Framework) — Práticas PW, PO, RV
- ISO 27001:2022 — Controles A.8 (Asset Management), A.12 (Operations), A.14 (Development)
- COBIT 2019 — Componentes APO12 (Risk Management), BAI03 (Managed Solutions), DSS05 (Managed Security)
- CIS Controls v8 — Controls 6 (Access Control), 7 (Continuous Vulnerability Management), 8 (Audit Log Management), 16 (Application Software Security)
- SANS SWAT (Software Assurance Technology) — Checklist de qualidade de software

Frameworks AI-specific:
- OWASP Top 10 for LLM Applications 2026
- AI-Induced Risk Audit (AIRA) Framework
- NIST AI Risk Management Framework (AI RMF) 1.0

Regras de execução:
- Auditoria é REPETÍVEL: mesmo auditor, mesmo repo, mesmo resultado
- Evidências são IMUTÁVEIS: hash SHA-256, append-only, não deletáveis
- Scorecard é CONFIGURÁVEL: pesos por dimensão podem ser ajustados por organização
- Relatório é LEGÍVEL: deve ser compreensível por CISO, PO, e dev júnior
```

---

## 🧪 9. CRITÉRIOS DE ACEITE GERAIS

### 9.1 Funcional
- [ ] RF-001 a RF-012 implementados e testados
- [ ] Scorecard calcula corretamente com pesos configuráveis
- [ ] Relatório gerado em formato JSON + Markdown + PDF
- [ ] Mapeamento de compliance inclui todos os frameworks base
- [ ] Plano de remediação é gerado automaticamente a partir de findings

### 9.2 Técnico
- [ ] Código segue `.cursor/rules/` e `CONSTITUTION.md`
- [ ] Testes unitários > 85% cobertura
- [ ] Testes de integração com Semgrep, Snyk, GitLeaks passando
- [ ] Schema de banco validado e migrations testadas
- [ ] API de auditoria documentada em OpenAPI v3

### 9.3 Segurança
- [ ] SAST passando (Semgrep — 0 issues críticos)
- [ ] SCA passando (Snyk — 0 CVEs críticos)
- [ ] Secrets scan passando (GitLeaks — 0 findings)
- [ ] Relatório não expõe dados sensíveis (secrets, PII)
- [ ] Hash de imutabilidade do relatório verificável

### 9.4 Performance
- [ ] Auditoria completa em repo 100k LOC: < 30 min
- [ ] Geração de relatório: < 5 min
- [ ] Consulta de histórico de auditorias: < 2s
- [ ] Suporte a repos de até 1M LOC sem OOM

### 9.5 AI-Specific
- [ ] Evals passando: scorer de qualidade de auditoria = 8.5/10
- [ ] Detecção de código AI-generated: precision > 90%, recall > 85%
- [ ] Rastreabilidade de código AI: 100% de arquivos identificáveis
- [ ] Audit trail de decisões do agente auditor: todas logadas

---

## 🚧 10. RISCOS & MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação | Owner |
|-------|--------------|---------|-----------|-------|
| Falso negativo de SAST (vuln não detectada) | Média | Crítico | Múltiplas tools (Semgrep + SonarQube + CodeQL) + review manual | `@security-officer` |
| Falso positivo excessivo (devs ignoram findings) | Alta | Médio | Tuning de regras, baseline por projeto, severity ajustável | `@tech-lead` |
| Auditoria muito lenta (bloqueia CI) | Média | Alto | Paralelização, caching de resultados, audit incremental | `@devops-lead` |
| Código AI-generated não identificável | Alta | Médio | Convenção de commits + git hooks + heurísticas de diff | `@tech-lead` |
| Frameworks desatualizados | Baixa | Alto | Processo de revisão anual de frameworks + versionamento do spec | `@security-officer` |
| Resistência da equipe a auditoria | Média | Médio | Gamificação (scorecard público), integração em CI (não opcional), educação | `@tech-lead` |

---

## 📝 11. NOTAS & DECISÕES

| Data | Decisão | Quem | Motivação |
|------|---------|------|-----------|
| 2026-06-13 | 9 dimensões baseadas no AI-Driven Development (Formação DEV) | `@tech-lead` | Alinhamento com metodologia de desenvolvimento da org |
| 2026-06-13 | Pesos do scorecard: SDD 20%, Segurança 15% | `@security-officer` | SDD é o diferencial de qualidade; segurança é non-negotiable |
| 2026-06-13 | Frameworks base: OWASP + NIST + ISO + COBIT + CIS + SANS | `@security-officer` | Cobertura completa de compliance internacional |
| 2026-06-13 | Frameworks AI: OWASP LLM Top 10 + AIRA + NIST AI RMF | `@tech-lead` | Cobertura específica de riscos de IA |
| 2026-06-13 | Score < 5.0 = deploy bloqueado | `@ciso` | Zero tolerância para codebases imaturos em produção |
| 2026-06-13 | Evidências imutáveis com SHA-256 | `@security-officer` | Audit trail para auditorias externas (SOC2, ISO) |

---

## 12. APROVAÇÕES

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Tech Lead | `@tech-lead` | 2026-06-13 | `commit: audit-spec-001` |
| Security Officer | `@security-officer` | 2026-06-13 | `commit: audit-spec-001` |
| CISO | `@ciso` | 2026-06-13 | `commit: audit-spec-001` |
| Arquiteto | `@arquiteto` | 2026-06-13 | `commit: audit-spec-001` |

---

## 13. REFERÊNCIAS

| Tipo | Link | Descrição |
|------|------|-----------|
| Epic | `https://jira.company.com/Epic-000` | Qualidade & Compliance |
| Framework | `https://owasp.org/www-project-asvs/` | OWASP ASVS 4.0 |
| Framework | `https://csrc.nist.gov/projects/ssdf` | NIST SSDF 1.1 |
| Framework | `https://www.iso.org/standard/27001` | ISO 27001:2022 |
| Framework | `https://www.isaca.org/cobit` | COBIT 2019 |
| Framework | `https://www.cisecurity.org/controls` | CIS Controls v8 |
| Framework | `https://owasp.org/www-project-top-10-for-large-language-model-applications/` | OWASP LLM Top 10 |
| Framework | `https://www.nist.gov/itl/ai-risk-management-framework` | NIST AI RMF 1.0 |
| Metodologia | `https://formacao.dev/ai-driven-development` | Formação DEV AI Driven Development |
| PLAN.md | `https://github.com/company/project/blob/main/specs/spec-audit-001/PLAN.md` | Plano técnico |
| TASKS.md | `https://github.com/company/project/blob/main/specs/spec-audit-001/TASKS.md` | Tarefas atômicas |

---

> **Próximo passo:** Após aprovação desta SPEC.md, o agente **Líder Técnico** gera o `PLAN.md` com arquitetura da ferramenta de auditoria, e o agente **Gerente de Projeto** gera o `TASKS.md` com tarefas atômicas.
