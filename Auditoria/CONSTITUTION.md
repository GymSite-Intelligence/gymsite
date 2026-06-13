# CONSTITUTION.md — Não-Negociáveis do Projeto de Auditoria AI-Driven

> **Status:** Active · **Versão:** 1.0 · **Data:** 2026-06-13
> **Vincula:** todo código, agente, PR e deploy deste projeto.
> **Origem:** derivado das Regras de Negócio (RN-001…RN-030) e dos NFRs do
> [`SPEC_Auditoria_Software_AI_Driven.md`](./SPEC_Auditoria_Software_AI_Driven.md).
>
> Estas regras são **invioláveis**. Um PR que as quebre é rejeitado em CI — sem
> exceção, sem override silencioso. Mudar este documento exige PR próprio,
> aprovado por Tech Lead **e** Security Officer.

---

## ⛔ Princípio Zero — Fail-Closed

Quando qualquer controle desta constituição **não puder ser verificado**, o
default é **bloquear**, não liberar. Ausência de evidência ≠ evidência de
conformidade. Tooling indisponível vira `tooling gap` explícito (FA-002), nunca
um `PASS` silencioso.

---

## 1. Segurança (non-negotiable)

- **C1.1** — Zero secrets hardcoded. GitLeaks + TruffleHog rodam em CI; qualquer
  finding bloqueia o merge. *(RN — CIS Control 6, OWASP ASVS V8)*
- **C1.2** — Zero CVE crítico em dependências. SCA (Snyk / OWASP Dependency-Check)
  com 0 críticos para merge. *(NIST SSDF RV.1)*
- **C1.3** — Zero issue 🔴 Crítico de SAST. Semgrep/SonarQube limpos de críticos.
  *(OWASP ASVS V1-V14)*
- **C1.4** — Código AI-generated que toca **auth, crypto ou input validation**
  exige review manual de Security Officer. *(RN-015, RN-009)*
- **C1.5** — Dependências **hallucinadas / typosquatting são proibidas**. Todo
  import resolve para pacote real e fixado (lockfile). *(RN — AIRA)*
- **C1.6** — Licenças GPL/AGPL em código gerado = **bloqueio**. *(RN-016)*
- **C1.7** — Endpoints que recebem input de usuário testam vetores de prompt
  injection. *(RN-017, OWASP LLM01)*
- **C1.8** — Secrets vivem em vault/secret manager (refs), **nunca** em `.env`
  commitado ou no código.

## 2. Spec-Driven Development (non-negotiable)

- **C2.1** — Feature sem `SPEC.md` **não entra na main**. Gate de CI. *(RN-010)*
- **C2.2** — Alterar código sem atualizar o `SPEC.md` correspondente = finding
  🟡 Alto que precisa ser sanado antes do merge. *(RN-011)*
- **C2.3** — Todo `SPEC.md` tem: critérios de aceite mensuráveis, regras de
  negócio numeradas, e seção "Contexto para IA". *(RN-012)*
- **C2.4** — Ordem do ciclo é sagrada: **SPEC → PLAN → TASKS → código**. Código
  antes de spec aprovado é débito, não entrega.

## 3. Rastreabilidade de Código AI (non-negotiable)

- **C3.1** — Commits AI-generated usam marcação padronizada (`[AI]`,
  `ai-generated`, ou `Co-Authored-By: <agente>`). *(RN-007)*
- **C3.2** — Arquivo com > 50% de código AI-generated exige review humano
  aprovador antes da main. *(RN-008)*
- **C3.3** — 100% do código AI-generated em produção passou por review humano
  aprovado. Origem desconhecida → review manual obrigatório. *(FA-004)*
- **C3.4** — Código AI-generated **sem testes associados é bloqueado em CI**.
  *(RN-024, FA-005)*

## 4. Testes & QA (non-negotiable)

- **C4.1** — Cobertura unitária **> 80%** nas regras de negócio. *(RN — NIST SSDF RV.1.1)*
- **C4.2** — Suites de integração e E2E verdes antes do merge.
- **C4.3** — Feature com IA tem **evals** que passam (score > threshold).
  Sem evals = finding 🟡 Alto. *(RN-025)*
- **C4.4** — Fail-soft testado: comportamento definido quando LLM retorna
  erro/timeout/malformado. *(RF-010)*

## 5. Arquitetura (non-negotiable)

- **C5.1** — Domínio **isolado** de frameworks e LLMs. Domain importar infra =
  finding 🔴 Crítico. *(RN-018, NIST SSDF PO.3.2)*
- **C5.2** — Integração com LLM **sempre** atrás de anti-corruption layer.
  Violação = 🔴 Crítico. *(RN-019)*
- **C5.3** — API-first: o schema (OpenAPI/protobuf) é a fonte da verdade. *(COBIT BAI03.01)*
- **C5.4** — Circuit breaker + retry + idempotência em todo chamado externo/LLM.
  *(RF-007, OWASP ASVS V11.1)*

## 6. Orquestração Multi-Agente (non-negotiable)

- **C6.1** — Cada agente tem escopo único documentado.
- **C6.2** — Comunicação inter-agente usa schema estrito (Pydantic/JSON Schema/protobuf).
- **C6.3** — **HITL obrigatório** para deploy, financeiro, dados sensíveis e
  alterações de auth/crypto. Ausência = 🔴 Crítico. *(RN-020)*
- **C6.4** — Estado de orquestração é persistido externamente (recuperável),
  nunca só em memória. *(CIS Control 8)*

## 7. Observabilidade & Audit Trail (non-negotiable)

- **C7.1** — Audit trail é **imutável** (append-only / hash chain). Trail
  mutável ou deletável = 🔴 Crítico. *(RN-022, ISO 27001 A.12.4)*
- **C7.2** — Toda chamada LLM loga prompt hash, response hash, tokens, modelo.
  Sem logging de tokens = 🟡 Alto. *(RN-023)*
- **C7.3** — Evidências de auditoria são imutáveis e versionadas (SHA-256).
  *(RNF-003)*
- **C7.4** — Evidências **nunca** contêm secrets ou PII em claro. *(RNF-004, OWASP ASVS V8.1)*

## 8. Dados, RAG & Privacidade (non-negotiable)

- **C8.1** — PII anonimizado **antes** de vector store ou LLM. PII cru no vector
  store = 🔴 Crítico. *(RN-027, GDPR Art. 32 / LGPD Art. 46)*
- **C8.2** — Dados multi-tenant isolados no vector store. *(ISO 27001 A.8.1)*
- **C8.3** — Respostas da IA têm grounding verificável contra fonte (anti-alucinação).

## 9. Deploy & Custo (non-negotiable)

- **C9.1** — Deploy de código AI-generated **sem gates** (testes+SAST+SCA+secrets+evals)
  = 🔴 Crítico. *(RN-029, NIST SSDF PO.3.1)*
- **C9.2** — API de LLM **sem rate limiting** = 🔴 Crítico (runaway de custo).
  *(RN-030, OWASP ASVS V4.2)*
- **C9.3** — Budget alerts + hard limits de gasto LLM configurados. *(COBIT APO12.01)*
- **C9.4** — Rollback automático quando error rate > threshold.

## 10. Context Engineering (non-negotiable)

- **C10.1** — Este `CONSTITUTION.md` existe e é versionado junto ao código.
  Projeto sem ele teto de 5.0 em Context Engineering. *(RN-013)*
- **C10.2** — Rules (`.cursor/rules/`, `CLAUDE.md` ou equivalente) versionadas,
  numeradas e fora do `.gitignore`. *(RN-014)*
- **C10.3** — MCPs documentados e versionados.

---

## 🚦 Gate de Merge — Resumo Executável

Um PR só funde se **todos** verdadeiros:

1. SAST 🔴 = 0 · SCA CVE crítico = 0 · secrets = 0
2. Cobertura de regras de negócio ≥ 80%
3. Código AI-generated com testes + review humano
4. `SPEC.md` presente/atualizado para a feature
5. Nenhum finding 🔴 Crítico aberto sem mitigação aprovada
6. `audit.sh` retorna **status ≠ REPROVADO** (score ≥ 5.0)

> Score ≥ 7.0 e 0 🔴 → **APROVADO** · 5.0–7.0 ou 🔴 mitigado → **CONDICIONAL** ·
> < 5.0 ou 🔴 sem mitigação → **REPROVADO (deploy bloqueado)**.

---

## ✍️ Emenda

Alterar esta constituição:
1. PR dedicado tocando **apenas** este arquivo.
2. Justificativa por cláusula alterada.
3. Aprovação de **Tech Lead + Security Officer** (dois reviewers distintos).
4. Bump de versão + entrada no changelog abaixo.

### Changelog
| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 1.0 | 2026-06-13 | Constituição inicial derivada do SPEC spec-audit-001 | `@tech-lead` |
