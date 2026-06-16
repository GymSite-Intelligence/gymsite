# PLAN.md — Arquitetura da Ferramenta de Auditoria AI-Driven

> **Baseado em:** SPEC.md `spec-audit-001`  
> **Metodologia:** Spec-Driven Development (SDD) — Formação DEV AI Driven Development  
> **Versão:** 1.0  
> **Status:** Draft → Review → Approved  
> **Responsável:** `@arquiteto` / `@tech-lead`

---

## 📋 1. IDENTIFICAÇÃO

| Campo | Valor |
|-------|-------|
| **Plan ID** | `plan-audit-001` |
| **Feature ID** | `spec-audit-001` |
| **Nome** | Arquitetura da Ferramenta de Auditoria AI-Driven |
| **Status** | `Draft` |
| **Data de criação** | `2026-06-13` |
| **Estimativa Total** | `3 sprints (6 semanas)` |
| **Equipe** | `1 Arquiteto + 2 Devs Senior + 1 Security Engineer + 1 DevOps` |

---

## 🎯 2. VISÃO ARQUITETURAL

### 2.1 Objetivo do Plano
Definir a arquitetura técnica de uma ferramenta de auditoria de software que:
- Execute checks automatizados e manuais em 9 dimensões
- Integre com ferramentas de segurança existentes (SAST, SCA, secrets scanning)
- Produza scorecard de maturidade com pesos configuráveis
- Gere relatórios em JSON + Markdown + PDF
- Seja aplicável a qualquer codebase AI-driven (genérica)
- Satisfaça requisitos de compliance (SOC2, ISO 27001, OWASP ASVS)

### 2.2 Princípios Arquiteturais

| # | Princípio | Justificativa |
|---|-----------|---------------|
| 1 | **Domain-First** | Regras de auditoria isoladas de ferramentas de scanning — o domínio é "qualidade e compliance", não "Semgrep" ou "Snyk" |
| 2 | **Plugin-Based** | Cada ferramenta de scanning (SAST, SCA, secrets) é um plugin com interface comum — troca de tool não quebra o core |
| 3 | **Immutability** | Evidências de auditoria são append-only, hashadas, não deletáveis |
| 4 | **Configurability** | Pesos do scorecard, thresholds, e frameworks de referência são configuráveis por organização |
| 5 | **Repeatability** | Mesmo auditor, mesmo repo, mesmo resultado — determinístico |
| 6 | **Observability** | Toda execução de auditoria é traced, logged, e medida |
| 7 | **Fail-Closed** | Se um scanner falha, o check é marcado como "N/A" com justificativa, nunca como "PASS" silencioso |

---

## 🏗️ 3. ARQUITETURA DE ALTO NÍVEL

### 3.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   CLI Tool   │  │   Web UI     │  │   CI/CD      │  │   API        │  │
│  │  (Node.js)   │  │  (Next.js)   │  │  (GitHub     │  │  (REST/      │  │
│  │              │  │              │  │   Actions)   │  │   GraphQL)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │                 │
          └─────────────────┴─────────────────┴─────────────────┘
                                    │
┌───────────────────────────────────┼───────────────────────────────────────┐
│                         API GATEWAY / BFF                                 │
│  • Rate Limiting • Auth (JWT/API Key) • Request Validation • Routing      │
└───────────────────────────────────┼───────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼───────────────────────────────────────┐
│                      ORCHESTRATION LAYER (CORE)                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │              AUDIT ENGINE (Domain Service)                        │   │
│  │  • Workflow: Initialize → Scan → Analyze → Score → Report       │   │
│  │  • State Machine: PENDING → RUNNING → COMPLETED / FAILED        │   │
│  │  • Checkpointing: Persiste estado a cada transição              │   │
│  │  • Human-in-the-Loop: Review manual para checks não-automatizáveis│  │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │   Agente     │ │   Agente     │ │   Agente     │ │   Agente     │      │
│  │  Scanner     │ │   Analyzer   │ │   Scorer     │ │   Reporter   │      │
│  │ (Coleta)     │ │ (Análise)    │ │ (Scorecard)  │ │ (Relatório)  │      │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘      │
│         │                │                │                │              │
│         └────────────────┴────────────────┴────────────────┘              │
│                                    │                                      │
│  ┌─────────────────────────────────┼────────────────────────────────────┐  │
│  │           SHARED MEMORY / CONTEXT STORE                              │  │
│  │  • Short-term: Redis — Cache de resultados de scan, sessões        │  │
│  │  • Mid-term: PostgreSQL — Auditorias, findings, configurações      │  │
│  │  • Long-term: S3/MinIO — Evidências (logs, screenshots, hashes)  │  │
│  └─────────────────────────────────┼────────────────────────────────────┘  │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼──────────────────────────────────────┐
│                      SCANNER PLUGIN LAYER                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │   SAST       │ │   SCA        │ │   Secrets    │ │   Custom     │    │
│  │   Plugins    │ │   Plugins    │ │   Plugins    │ │   Plugins    │    │
│  │              │ │              │ │              │ │              │    │
│  │ • Semgrep    │ │ • Snyk       │ │ • GitLeaks   │ │ • AI-Gen     │    │
│  │ • SonarQube  │ │ • Dependabot │ │ • TruffleHog │ │   Detector   │    │
│  │ • CodeQL     │ │ • OWASP DC   │ │ • Custom     │ │ • Arch Check │    │
│  │ • Bandit     │ │ • Snyk Code  │ │   Regex      │ │ • SDD Check  │    │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘    │
│                                                                           │
│  Interface: ScannerPlugin {                                               │
│    name: string;                                                          │
│    version: string;                                                       │
│    execute(repoPath: string, config: Config): Promise<ScanResult>;      │
│    parseOutput(rawOutput: string): Finding[];                             │
│  }                                                                        │
└───────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼──────────────────────────────────────┐
│                         DATA LAYER                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ PostgreSQL   │ │   Redis      │ │   S3/MinIO   │ │   Vector     │      │
│  │ (Relacional) │ │  (Cache/     │ │  (Evidências)│ │   Store      │      │
│  │              │ │   Session)   │ │              │ │  (RAG docs)  │      │
│  │ • Audits     │ │ • Cache de   │ │ • Logs de    │ │ • OWASP      │      │
│  │ • Findings   │ │   scan       │ │   scanner    │ │   ASVS docs  │      │
│  │ • Configs    │ │ • Rate limit │ │ • Screenshots│ │ • NIST SSDF  │      │
│  │ • Compliance │ │ • Locks      │ │ • Hashes     │ │   docs       │      │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Camadas Detalhadas

#### **Layer 1: Client Layer**
- **CLI Tool:** `audit-cli` em Node.js/TypeScript — executa auditoria localmente, gera relatório local
- **Web UI:** Next.js 15+ — dashboard de auditorias, scorecards, findings, tendências
- **CI/CD Integration:** GitHub Actions / GitLab CI / Jenkins — executa auditoria em pipeline
- **API:** REST + GraphQL — para integrações com Jira, Slack, SIEM

#### **Layer 2: API Gateway / BFF**
- **Rate Limiting:** Por API key, por IP (Redis-based)
- **Authentication:** JWT para usuários, API Key para CI/CD
- **Authorization:** RBAC — Auditor, Admin, Viewer
- **Request Validation:** Zod schemas para todos os endpoints
- **Response Filtering:** DTOs que não expõem evidências brutas (apenas hashes)

#### **Layer 3: Orchestration Layer (Audit Engine)**

**Audit Engine (Domain Service):**
- **Workflow Engine:** Orquestra o fluxo de auditoria em 5 fases:
  1. `Initialize` — Carrega configuração, valida repositório, prepara ambiente
  2. `Scan` — Executa plugins de scanning em paralelo (SAST, SCA, secrets, custom)
  3. `Analyze` — Consolida findings, remove duplicatas, classifica severidade
  4. `Score` — Calcula scorecard por dimensão com pesos configuráveis
  5. `Report` — Gera relatório em JSON + Markdown + PDF

- **State Machine:**
  ```
  PENDING → RUNNING → COMPLETED
                     → FAILED (rollback, retry, ou abort)
  ```
  Cada transição é checkpointada em PostgreSQL.

- **Human-in-the-Loop:** Checks manuais (arquitetura, SDD, orquestração) são atribuídos a auditor humano via Web UI. O workflow pausa até aprovação.

- **Circuit Breaker:** Se um scanner falha repetidamente, o plugin é desabilitado e o check é marcado como "N/A" com justificativa.

**Agentes Especializados (Audit Engine):**

| Agente | Modelo | Função | Input | Output |
|--------|--------|--------|-------|--------|
| **Scanner Agent** | GPT-5.4 Codex | Executa plugins de scanning | Repo path + config | Raw scan results |
| **Analyzer Agent** | Claude Sonnet 4.6 | Consolida findings, deduplica, classifica | Raw results + rules | Normalized findings |
| **Scorer Agent** | Claude Opus 4.7 | Calcula scorecard por dimensão | Findings + weights + thresholds | Scorecard JSON |
| **Reporter Agent** | GPT-5.4 Codex | Gera relatório em múltiplos formatos | Scorecard + findings + evidence | JSON + Markdown + PDF |

**Shared Memory / Context Store:**
- **Short-term (Redis):** Cache de resultados de scan (TTL: 1h), sessões de auditoria, rate limiting
- **Mid-term (PostgreSQL):** Auditorias, findings, configurações, compliance mappings, audit trail
- **Long-term (S3/MinIO):** Evidências imutáveis (logs brutos, screenshots, hashes SHA-256)

#### **Layer 4: Scanner Plugin Layer**

**Interface Comum (Plugin Contract):**
```typescript
interface ScannerPlugin {
  readonly name: string;
  readonly version: string;
  readonly category: 'SAST' | 'SCA' | 'SECRETS' | 'CUSTOM';
  readonly frameworks: string[]; // ['OWASP ASVS', 'NIST SSDF']

  execute(context: ScanContext): Promise<ScanResult>;
  parseOutput(rawOutput: string): Finding[];
  validateConfig(config: unknown): ValidationResult;
}

interface ScanResult {
  pluginName: string;
  duration: number;
  findings: Finding[];
  rawOutput: string; // Para evidência
  exitCode: number;
}

interface Finding {
  id: string;
  checkId: string;
  dimension: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  filePath?: string;
  lineNumber?: number;
  codeSnippet?: string;
  frameworkRef: string; // 'OWASP ASVS V2.1.1'
  recommendation: string;
  evidenceHash: string; // SHA-256 da evidência
}
```

**Plugins Implementados (Fase 1):**

| Plugin | Categoria | Frameworks | O que verifica |
|--------|-----------|------------|----------------|
| `semgrep-plugin` | SAST | OWASP ASVS | Vulnerabilidades de código |
| `sonarqube-plugin` | SAST | OWASP ASVS, NIST SSDF | Quality gates, code smells |
| `snyk-plugin` | SCA | NIST SSDF, CIS | CVEs, licenças, typosquatting |
| `gitleaks-plugin` | SECRETS | OWASP ASVS V8 | Secrets hardcoded |
| `trufflehog-plugin` | SECRETS | CIS Control 6 | Secrets em histórico git |
| `ai-gen-detector` | CUSTOM | AIRA | % de código AI-generated |
| `sdd-validator` | CUSTOM | SDD | Existência de SPEC.md, PLAN.md |
| `context-engineering-check` | CUSTOM | AI-specific | Rules, MCPs, CONSTITUTION.md |
| `architecture-check` | CUSTOM | NIST SSDF, COBIT | Clean Architecture, API-first |
| `orchestration-check` | CUSTOM | AI-specific | Agentes, HITL, schemas |

**Plugins Futuros (Fase 2+):**
- `codeql-plugin` (SAST avançado)
- `owasp-dependency-check` (SCA Java)
- `bandit-plugin` (SAST Python)
- `docker-security-check` (Container security)
- `infra-as-code-check` (Terraform/CloudFormation security)

#### **Layer 5: Data Layer**
- **PostgreSQL:** Dados relacionais (audits, findings, configs, compliance mappings, users)
- **Redis:** Cache, sessões, rate limiting, pub/sub para notificações
- **S3/MinIO:** Evidências imutáveis (append-only, versionadas, com lifecycle policy)
- **Vector Store (Opcional):** RAG com documentação de frameworks (OWASP ASVS, NIST SSDF) para consulta durante auditoria manual

---

## 🔧 4. DECISÕES DE DESIGN

### 4.1 Plugin Architecture vs. Monolith

**Decisão:** Plugin Architecture

**Justificativa:**
- Ferramentas de scanning evoluem rapidamente (Semgrep, Snyk, CodeQL)
- Organizações usam stacks diferentes — uma usa SonarQube, outra usa Semgrep
- Troca de tool não deve exigir deploy do core
- Cada plugin pode ser versionado independentemente

**Trade-off:**
- Overhead de manter interface comum
- Latência de inicialização de plugins (mitigado com caching)

### 4.2 Síncrono vs. Assíncrono

**Decisão:** Híbrido

**Justificativa:**
- Scanners rápidos (Semgrep, GitLeaks): síncrono, retornam em < 2 min
- Scanners lentos (SonarQube full scan, Snyk monitor): assíncrono, via fila
- Workflow orquestra ambos: inicia síncronos, enfileira assíncronos, consolida quando todos terminam

**Implementação:**
- Fila: BullMQ (Redis) ou RabbitMQ
- Workers: Docker containers isolados por plugin
- Timeout: 10 min para síncronos, 30 min para assíncronos

### 4.3 Imutabilidade de Evidências

**Decisão:** S3/MinIO com versioning + hash SHA-256 + WORM (Write Once Read Many)

**Justificativa:**
- Compliance externo (SOC2, ISO 27001) exige evidências não-modificáveis
- Audit trail legal em caso de incidente de segurança
- Confiança no relatório: hash verificável independentemente

**Implementação:**
- Cada evidência é um objeto S3 com versioning habilitado
- Hash SHA-256 calculado no upload e armazenado em PostgreSQL
- Lifecycle policy: nunca deletar, apenas arquivar para Glacier após 1 ano
- Acesso: apenas via API Audit, nunca direto

### 4.4 Scorecard Configurável vs. Fixo

**Decisão:** Configurável por organização, com defaults baseados no SPEC

**Justificativa:**
- Fintech pode priorizar segurança (peso 25%)
- Startup pode priorizar velocidade (SDD com peso 25%)
- Compliance requirements variam por indústria

**Implementação:**
```yaml
# config/scorecard-defaults.yml
dimensions:
  context_engineering: { weight: 0.15, min_score: 5.0 }
  spec_driven_development: { weight: 0.20, min_score: 6.0 }
  software_architecture: { weight: 0.15, min_score: 6.0 }
  multi_agent_orchestration: { weight: 0.15, min_score: 5.0 }
  security: { weight: 0.15, min_score: 7.0 }
  testing_qa: { weight: 0.10, min_score: 6.0 }
  observability: { weight: 0.05, min_score: 5.0 }
  data_rag: { weight: 0.03, min_score: 5.0 }
  deploy_infra: { weight: 0.02, min_score: 5.0 }

thresholds:
  approved: { min_score: 7.0, max_critical: 0 }
  conditional: { min_score: 5.0, max_critical: 2 }
  rejected: { min_score: 0.0, max_critical: 999 }
```

### 4.5 Banco de Dados: SQL vs. NoSQL

**Decisão:** PostgreSQL (SQL) para dados estruturados, S3 para evidências, Redis para cache

**Justificativa:**
- Dados de auditoria são altamente estruturados (audits, findings, configs)
- Relacionamentos complexos (audit → findings → evidence → compliance mapping)
- ACID necessário para imutabilidade e consistência do scorecard
- Evidências (logs, screenshots) são blobs — melhor em S3

---

## 🗄️ 5. MODELO DE DADOS

### 5.1 Entidades Principais

```typescript
// Audit (Auditoria)
interface Audit {
  id: UUID;
  projectName: string;
  repositoryUrl: string;
  branch: string;
  commitHash: string;
  commitMessage: string;
  auditorId: string; // human or AI agent
  auditType: 'FULL' | 'INCREMENTAL' | 'DIMENSION' | 'CUSTOM';
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'ABORTED';
  startedAt: Date;
  completedAt?: Date;
  overallScore: number; // 0.0 - 10.0
  overallStatus: 'APPROVED' | 'CONDITIONAL' | 'REJECTED';
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  totalLinesOfCode: number;
  aiGeneratedPercentage: number;
  reportHash: string; // SHA-256 do relatório final
  configSnapshot: ScorecardConfig; // Config usada nesta auditoria
  createdAt: Date;
  updatedAt: Date;
}

// Finding (Hallazgo)
interface Finding {
  id: UUID;
  auditId: UUID;
  dimension: Dimension;
  checkId: string;
  pluginName: string;
  severity: Severity;
  status: 'PASS' | 'FAIL' | 'N/A' | 'PENDING_REVIEW';
  title: string;
  description: string;
  filePath?: string;
  lineNumber?: number;
  columnNumber?: number;
  codeSnippet?: string;
  frameworkRef: string; // 'OWASP ASVS V2.1.1'
  recommendation: string;
  evidenceUrl: string; // S3 URL
  evidenceHash: string; // SHA-256
  owner?: string; // Responsável pela remediação
  dueDate?: Date;
  resolvedAt?: Date;
  resolutionEvidence?: string;
  createdAt: Date;
}

// ScorecardConfig (Configuração do Scorecard)
interface ScorecardConfig {
  id: UUID;
  organizationId: string;
  name: string;
  dimensions: DimensionConfig[];
  thresholds: StatusThresholds;
  isDefault: boolean;
  createdAt: Date;
  updatedAt: Date;
}

interface DimensionConfig {
  dimension: Dimension;
  weight: number; // 0.0 - 1.0
  minScore: number; // Mínimo para não ser reprovado nesta dimensão
  checks: CheckConfig[];
}

interface CheckConfig {
  checkId: string;
  severity: Severity;
  automationLevel: 'AUTOMATED' | 'SEMI_AUTOMATED' | 'MANUAL';
  pluginName?: string;
  frameworkRefs: string[];
}

// ComplianceMapping (Mapeamento de Compliance)
interface ComplianceMapping {
  id: UUID;
  auditId: UUID;
  framework: string; // 'OWASP ASVS 4.0'
  version: string;
  totalControls: number;
  passedControls: number;
  failedControls: number;
  naControls: number;
  coveragePercentage: number;
  details: ControlDetail[];
}

interface ControlDetail {
  controlId: string;
  controlName: string;
  status: 'PASS' | 'FAIL' | 'N/A';
  relatedFindings: UUID[];
  evidenceHash: string;
}
```

### 5.2 Diagrama ER (Simplificado)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Audit     │──1:N──│   Finding   │──N:1──│  Evidence   │
│             │       │             │       │   (S3)      │
└─────────────┘       └─────────────┘       └─────────────┘
       │
       │ 1:N
       ▼
┌─────────────┐       ┌─────────────┐
│ Compliance  │──1:N──│ Control     │
│   Mapping   │       │   Detail    │
└─────────────┘       └─────────────┘
       │
       │ N:1
       ▼
┌─────────────┐
│ Scorecard   │
│   Config    │
└─────────────┘
```

---

## 🔒 6. SEGURANÇA

### 6.1 Threat Model

| Threat | Mitigação |
|--------|-----------|
| **Tampering de evidências** | S3 versioning + WORM + hash SHA-256 |
| **Acesso não autorizado a findings** | RBAC + object-level auth + field-level filtering |
| **Injection em relatório** | Output encoding (Markdown/HTML) + sanitização de code snippets |
| **DoS via scan de repo gigante** | Rate limiting + timeout + max LOC (1M) + circuit breaker |
| **Leaking de secrets em evidências** | Redaction automática de PII/secrets antes de upload S3 |
| **Manipulação de scorecard** | Config snapshot por audit + hash do relatório + audit trail |
| **Plugin malicioso** | Sandbox de plugins (Docker) + assinatura digital + allowlist |

### 6.2 Auth & Authorization

```yaml
authentication:
  methods: [JWT, API_Key]
  mfa: required_for_admins

authorization:
  roles:
    - name: Admin
      permissions: [manage_configs, manage_users, delete_audits, view_all]
    - name: Auditor
      permissions: [run_audit, view_findings, view_reports, resolve_findings]
    - name: Developer
      permissions: [view_own_findings, view_own_reports, resolve_own_findings]
    - name: Viewer
      permissions: [view_reports, view_scorecards]
    - name: CI_CD
      permissions: [run_audit, view_report]
```

---

## 🧪 7. TESTES

### 7.1 Estratégia de Testes

| Tipo | O que testa | Ferramenta | Cobertura |
|------|-------------|------------|-----------|
| **Unit** | Domain logic, scoring, parsing | Jest/Vitest | > 85% |
| **Integration** | Plugins, DB, filas | TestContainers | 100% de plugins |
| **E2E** | Fluxo completo de auditoria | Playwright | 5 fluxos principais |
| **Contract** | API schemas | Zod + Pact | 100% de endpoints |
| **Security** | SAST, SCA, secrets | Semgrep + Snyk | 0 issues críticos |
| **Performance** | Tempo de scan, geração de relatório | k6 / Artillery | P95 < 30 min |
| **AI Evals** | Qualidade de scoring, análise de findings | Custom scorers | > 8.0/10 |

### 7.2 Testes de Fail-Soft

```typescript
// Exemplo: Teste de falha de plugin
describe('Audit Engine - Fail-Soft', () => {
  it('should mark check as N/A when SAST scanner fails', async () => {
    // Arrange: Simula falha de Semgrep
    mockSemgrepPlugin.execute.mockRejectedValue(new Error('Timeout'));

    // Act: Executa auditoria
    const audit = await auditEngine.run({ repoPath: '/tmp/repo' });

    // Assert: Check é N/A, não PASS
    const sastFindings = audit.findings.filter(f => f.dimension === 'SECURITY' && f.pluginName === 'semgrep');
    expect(sastFindings.every(f => f.status === 'N/A')).toBe(true);
    expect(audit.overallStatus).not.toBe('APPROVED'); // Não aprova silenciosamente
  });

  it('should complete audit when one plugin fails', async () => {
    // Um plugin falha, outros continuam
    mockSnykPlugin.execute.mockRejectedValue(new Error('Network error'));

    const audit = await auditEngine.run({ repoPath: '/tmp/repo' });

    expect(audit.status).toBe('COMPLETED');
    expect(audit.findings.length).toBeGreaterThan(0); // Outros plugins retornaram
  });
});
```

---

## 🚀 8. DEPLOY & INFRA

### 8.1 Infraestrutura

```yaml
# docker-compose.yml (desenvolvimento)
services:
  api:
    build: ./docker/Dockerfile.api
    ports: ["3000:3000"]
    env_file: .env
    depends_on: [postgres, redis, s3]

  worker:
    build: ./docker/Dockerfile.worker
    env_file: .env
    depends_on: [postgres, redis, s3]
    # Escalável horizontalmente
    deploy:
      replicas: 3

  web:
    build: ./docker/Dockerfile.web
    ports: ["3001:3001"]
    depends_on: [api]

  postgres:
    image: postgres:16-alpine
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine

  s3:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: ["s3_data:/data"]

  # Scanners como sidecars ou containers efêmeros
  scanner-semgrep:
    build: ./docker/Dockerfile.scanner-semgrep
    # Executa sob demanda, não persistente
```

### 8.2 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
stages:
  1. lint
  2. unit-tests (cobertura > 85%)
  3. integration-tests (TestContainers)
  4. e2e-tests (Playwright)
  5. contract-tests (Pact)
  6. sast (Semgrep, SonarQube)
  7. sca (Snyk)
  8. secrets-scan (GitLeaks)
  9. performance-tests (k6)
  10. security-audit (self-audit com a própria tool)
  11. deploy-staging
  12. smoke-tests
  13. deploy-prod (canary: 10% → 50% → 100%)
```

---

## 📊 9. MÉTRICAS & SLAs

| Métrica | Target | Como medir |
|---------|--------|------------|
| Tempo de auditoria completa (100k LOC) | < 30 min | Prometheus histogram |
| Tempo de geração de relatório | < 5 min | Prometheus histogram |
| Precisão de detecção AI-generated | > 90% | Dataset anotado manualmente |
| Recall de detecção AI-generated | > 85% | Dataset anotado manualmente |
| Falsos positivos de SAST | < 10% | Feedback de devs |
| Disponibilidade do serviço | 99.9% | Uptime monitoring |
| Latência API (P95) | < 500ms | Prometheus |

---

## 📝 10. RISCOS TÉCNICOS

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Scanner lento bloqueia fila | Média | Alto | Timeout + circuit breaker + fila separada por prioridade |
| Falso positivo excessivo | Alta | Médio | Baseline por projeto + tuning de regras + feedback loop |
| Escalabilidade de plugins | Média | Alto | Docker + K8s + auto-scaling de workers |
| Dependência de ferramentas externas | Alta | Médio | Múltiplas tools por categoria + fallback |
| Complexidade de configuração | Média | Médio | Defaults sensatos + wizard de configuração + templates |

---

## ✅ 11. CRITÉRIOS DE ACEITE DO PLANO

- [ ] Arquitetura aprovada por Arquiteto e Tech Lead
- [ ] Modelo de dados validado contra requisitos do SPEC.md
- [ ] Plugin interface definida e documentada
- [ ] Decisões de design (plugin, sync/async, immutability, scorecard) documentadas em ADR
- [ ] Threat model revisado por Security Officer
- [ ] Estimativa de infraestrutura (custo) aprovada pelo CISO
- [ ] SLA de performance validado com stakeholders

---

> **Próximo passo:** Após aprovação deste PLAN.md, o agente **Gerente de Projeto** gera o `TASKS.md` com tarefas atômicas para implementação.
