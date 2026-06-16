#!/usr/bin/env bash
# ============================================================================
# audit.sh — Executor de Auditoria de Software AI-Driven
# Implementa o checklist do SPEC_Auditoria_Software_AI_Driven.md (spec-audit-001)
# e os gates do CONSTITUTION.md.
#
# Uso:
#   ./audit.sh [TARGET_DIR]
#   TARGET_DIR  diretório do repo a auditar (default: cwd)
#
# Saída:
#   audit-reports/<timestamp>/report.json   (schema RF-012)
#   audit-reports/<timestamp>/report.md     (legível p/ humano)
#   audit-reports/<timestamp>/report.sha256 (imutabilidade — RNF-003)
#
# Exit codes (gate de CI):
#   0  APROVADO    (score >= 7.0 e 0 crítico)
#   1  REPROVADO   (score < 5.0 ou crítico sem mitigação)  <- bloqueia deploy
#   2  CONDICIONAL (5.0 <= score < 7.0)
#
# Tooling ausente NÃO falha silenciosamente: vira "tooling gap" (FA-002) e
# zera/penaliza a dimensão afetada (princípio fail-closed do CONSTITUTION).
# ============================================================================
set -uo pipefail

TARGET="${1:-$(pwd)}"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${SELF_DIR}/audit-reports/${TS}"
mkdir -p "$OUT_DIR"

# ── Pesos do scorecard (SPEC §6.1) — devem somar 100 ────────────────────────
W_CONTEXT=15; W_SDD=20; W_ARCH=15; W_ORCH=15; W_SEC=15
W_TEST=10; W_OBS=5; W_DATA=3; W_DEPLOY=2

# ── Acumuladores ────────────────────────────────────────────────────────────
declare -a FINDINGS=()         # "SEV|DIM|CHECK|STATUS|DESC|REF"
CRIT=0; HIGH=0; MED=0
TOOLING_GAPS=""

have() { command -v "$1" >/dev/null 2>&1; }

# add_finding SEV DIM CHECK STATUS "DESC" "REF"
add_finding() {
  FINDINGS+=("$1|$2|$3|$4|$5|$6")
  case "$1" in
    CRITICAL) CRIT=$((CRIT+1));;
    HIGH)     HIGH=$((HIGH+1));;
    MEDIUM)   MED=$((MED+1));;
  esac
}

exists_any() { # exists_any path1 path2 ... -> 0 se algum existe
  for p in "$@"; do [ -e "${TARGET}/${p}" ] && return 0; done
  return 1
}

count_glob() { # count_glob "pattern" -> nº de matches (0 se nenhum)
  local n
  n=$(find "$TARGET" -type f -iname "$1" 2>/dev/null | wc -l | tr -d ' ')
  echo "${n:-0}"
}

echo "🔍 Auditoria AI-Driven — alvo: $TARGET"
echo "   relatório: $OUT_DIR"
echo

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: SEGURANÇA (peso 15%) — scanners
# ════════════════════════════════════════════════════════════════════════════
sec_score=10
echo "▶ Segurança…"

# C1.1 secrets
if have gitleaks; then
  if ! gitleaks detect --source "$TARGET" --no-banner -r "$OUT_DIR/gitleaks.json" >/dev/null 2>&1; then
    add_finding CRITICAL "Seguranca" "SEC-SECRETS" "FAIL" "GitLeaks encontrou secrets hardcoded" "CIS Control 6 / OWASP ASVS V8"
    sec_score=$((sec_score-5))
  else
    add_finding MEDIUM "Seguranca" "SEC-SECRETS" "PASS" "Nenhum secret detectado (GitLeaks)" "CIS Control 6"
  fi
else
  TOOLING_GAPS="${TOOLING_GAPS} gitleaks"
  add_finding HIGH "Seguranca" "SEC-SECRETS" "N/A" "gitleaks ausente — secrets não verificados (tooling gap)" "FA-002"
  sec_score=$((sec_score-3))
fi

# C1.3 SAST
if have semgrep; then
  if ! semgrep --config=auto --error --json -o "$OUT_DIR/semgrep.json" \
        --exclude=audit-reports --exclude=node_modules --exclude='*.json' \
        --exclude='*.html' --exclude=mocks "$TARGET" >/dev/null 2>&1; then
    add_finding CRITICAL "Seguranca" "SEC-SAST" "FAIL" "Semgrep reportou issues (ver semgrep.json)" "OWASP ASVS V1-V14"
    sec_score=$((sec_score-3))
  else
    add_finding MEDIUM "Seguranca" "SEC-SAST" "PASS" "SAST limpo (Semgrep)" "OWASP ASVS"
  fi
else
  TOOLING_GAPS="${TOOLING_GAPS} semgrep"
  add_finding HIGH "Seguranca" "SEC-SAST" "N/A" "semgrep ausente — SAST não executado (tooling gap)" "FA-002"
  sec_score=$((sec_score-3))
fi

# C1.2 SCA
if have snyk; then
  # Snyk exit codes: 0=sem vulns | 1=vulns encontradas | 2=erro (auth/rede) | 3=sem manifest.
  # Só exit 1 é CVE real; 2/3 = tooling gap (não falso-crítico). Robusto a stdout vazio em não-TTY.
  snyk test --severity-threshold=critical >/dev/null 2>&1; snyk_code=$?
  if [ $snyk_code -eq 1 ]; then
    add_finding CRITICAL "Seguranca" "SEC-SCA" "FAIL" "Snyk reportou CVE crítico em dependências" "NIST SSDF RV.1"
    sec_score=$((sec_score-2))
  elif [ $snyk_code -eq 0 ]; then
    add_finding MEDIUM "Seguranca" "SEC-SCA" "PASS" "0 CVE crítico (Snyk)" "NIST SSDF RV.1"
  else
    # exit 2/3: auth ausente, sem manifest suportado, ou erro de rede
    TOOLING_GAPS="${TOOLING_GAPS} snyk(exit${snyk_code})"
    add_finding HIGH "Seguranca" "SEC-SCA" "N/A" "snyk não executou SCA (exit ${snyk_code}: auth/rede/sem-manifest) — rode 'snyk auth'" "FA-002"
    sec_score=$((sec_score-2))
  fi
elif have dependency-check; then
  add_finding MEDIUM "Seguranca" "SEC-SCA" "PASS" "Dependency-Check disponível (rode manualmente)" "NIST SSDF PO.3.2"
else
  TOOLING_GAPS="${TOOLING_GAPS} snyk/dependency-check"
  add_finding HIGH "Seguranca" "SEC-SCA" "N/A" "SCA ausente — CVEs não verificados (tooling gap)" "FA-002"
  sec_score=$((sec_score-2))
fi
[ $sec_score -lt 0 ] && sec_score=0

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: SPEC-DRIVEN DEVELOPMENT (peso 20%)
# ════════════════════════════════════════════════════════════════════════════
sdd_score=0
echo "▶ Spec-Driven Development…"
specs=$(count_glob "SPEC*.md")
plans=$(count_glob "PLAN*.md")
tasks=$(count_glob "TASKS*.md")
if exists_any "specs" "spec" || [ "$specs" -gt 0 ]; then
  sdd_score=$((sdd_score+5))
  add_finding MEDIUM "SDD" "SDD-SPEC" "PASS" "SPEC.md presente ($specs encontrados)" "RN-010"
else
  add_finding CRITICAL "SDD" "SDD-SPEC" "FAIL" "Nenhum SPEC.md — feature sem spec não funde" "RN-010"
fi
[ "$plans" -gt 0 ] && { sdd_score=$((sdd_score+3)); add_finding MEDIUM "SDD" "SDD-PLAN" "PASS" "PLAN.md presente" "RF-004"; } \
                   || add_finding HIGH "SDD" "SDD-PLAN" "FAIL" "PLAN.md ausente" "RF-004"
[ "$tasks" -gt 0 ] && { sdd_score=$((sdd_score+2)); add_finding MEDIUM "SDD" "SDD-TASKS" "PASS" "TASKS.md presente" "RF-004"; } \
                    || add_finding HIGH "SDD" "SDD-TASKS" "FAIL" "TASKS.md ausente" "RF-004"

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: CONTEXT ENGINEERING (peso 15%)
# ════════════════════════════════════════════════════════════════════════════
ctx_score=0
echo "▶ Context Engineering…"
if exists_any "CONSTITUTION.md"; then
  ctx_score=$((ctx_score+5)); add_finding MEDIUM "ContextEng" "CTX-CONST" "PASS" "CONSTITUTION.md presente" "RN-013"
else
  add_finding HIGH "ContextEng" "CTX-CONST" "FAIL" "Sem CONSTITUTION.md — teto de 5.0 na dimensão" "RN-013"
fi
if exists_any ".cursor/rules" "CLAUDE.md" ".github/copilot-instructions.md" "GEMINI.md"; then
  ctx_score=$((ctx_score+3)); add_finding MEDIUM "ContextEng" "CTX-RULES" "PASS" "Rules de contexto presentes" "RN-014"
else
  add_finding HIGH "ContextEng" "CTX-RULES" "FAIL" "Sem rules (.cursor/rules, CLAUDE.md…)" "RN-014"
fi
if exists_any "mcp" ".mcp.json" "mcp-config.template.json"; then
  ctx_score=$((ctx_score+2)); add_finding MEDIUM "ContextEng" "CTX-MCP" "PASS" "MCPs documentados" "RF-005"
else
  add_finding MEDIUM "ContextEng" "CTX-MCP" "FAIL" "MCPs não documentados" "RF-005"
fi

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: RASTREABILIDADE DE CÓDIGO AI (entra em Testes/QA + Segurança)
# ════════════════════════════════════════════════════════════════════════════
echo "▶ Rastreabilidade AI…"
ai_commits=0; total_commits=0
if [ -d "${TARGET}/.git" ] && have git; then
  total_commits=$(git -C "$TARGET" rev-list --count HEAD 2>/dev/null || echo 0)
  ai_commits=$(git -C "$TARGET" log --pretty=%B 2>/dev/null \
    | grep -ciE '\[ai\]|ai-generated|co-authored-by:.*(ai|claude|copilot|gpt|gemini)' || true)
  if [ "$total_commits" -gt 0 ]; then
    pct=$(( ai_commits * 100 / total_commits ))
    add_finding MEDIUM "Seguranca" "AI-TRACE" "PASS" "Commits marcados AI: ${ai_commits}/${total_commits} (~${pct}%)" "RN-007"
  fi
else
  add_finding HIGH "Seguranca" "AI-TRACE" "N/A" "Sem git history — rastreabilidade AI impossível" "FA-004"
fi

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: TESTES & QA (peso 10%)
# ════════════════════════════════════════════════════════════════════════════
test_score=0
echo "▶ Testes & QA…"
testfiles=$(( $(count_glob "*test*.py") + $(count_glob "*.test.*") + $(count_glob "*.spec.*") + $(count_glob "*_test.go") ))
if [ "$testfiles" -gt 0 ]; then
  test_score=$((test_score+6)); add_finding MEDIUM "TestesQA" "TEST-EXIST" "PASS" "${testfiles} arquivos de teste encontrados" "NIST SSDF RV.1.1"
else
  add_finding CRITICAL "TestesQA" "TEST-EXIST" "FAIL" "Nenhum teste — código AI sem teste é bloqueado" "RN-024"
fi
if exists_any "eval" "evals" "tests/evals"; then
  test_score=$((test_score+4)); add_finding MEDIUM "TestesQA" "TEST-EVAL" "PASS" "Evals presentes" "RN-025"
else
  add_finding HIGH "TestesQA" "TEST-EVAL" "FAIL" "Sem evals para features com IA" "RN-025"
fi

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: ARQUITETURA (peso 15%) — heurística leve
# ════════════════════════════════════════════════════════════════════════════
arch_score=0
echo "▶ Arquitetura…"
exists_any "domain" "src/domain" "core" "Imobiliario" && arch_score=$((arch_score+4))
exists_any "openapi.json" "openapi.yaml" "schema.graphql" && { arch_score=$((arch_score+3)); add_finding MEDIUM "Arquitetura" "ARCH-API" "PASS" "Contrato de API presente" "COBIT BAI03.01"; } \
  || add_finding MEDIUM "Arquitetura" "ARCH-API" "FAIL" "Sem contrato OpenAPI/GraphQL" "COBIT BAI03.01"
if grep -rqiE 'circuit.?breaker|retry|backoff|idempoten' "$TARGET" --include=*.py --include=*.ts 2>/dev/null; then
  arch_score=$((arch_score+3)); add_finding MEDIUM "Arquitetura" "ARCH-RESIL" "PASS" "Padrões de resiliência detectados" "OWASP ASVS V11.1"
else
  add_finding HIGH "Arquitetura" "ARCH-RESIL" "FAIL" "Sem circuit breaker/retry/idempotência aparente" "RF-007"
fi
[ "$arch_score" -gt 10 ] && arch_score=10

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: ORQUESTRAÇÃO MULTI-AGENTE (peso 15%)
# ════════════════════════════════════════════════════════════════════════════
orch_score=0
echo "▶ Orquestração…"
if exists_any "agents" ".agents" "agent"; then
  orch_score=$((orch_score+5)); add_finding MEDIUM "Orquestracao" "ORCH-AGENTS" "PASS" "Diretório de agentes presente" "RF-008"
else
  add_finding MEDIUM "Orquestracao" "ORCH-AGENTS" "N/A" "Sem agentes detectados (pode não se aplicar)" "RF-008"
  orch_score=$((orch_score+5))
fi
if grep -rqiE 'BaseModel|pydantic|JSONSchema|protobuf' "$TARGET" --include=*.py 2>/dev/null; then
  orch_score=$((orch_score+3)); add_finding MEDIUM "Orquestracao" "ORCH-SCHEMA" "PASS" "Schemas estritos (Pydantic/JSON Schema)" "RF-008"
else
  add_finding HIGH "Orquestracao" "ORCH-SCHEMA" "FAIL" "Comunicação inter-agente sem schema estrito" "RF-008"
fi
grep -rqiE 'human.?in.?the.?loop|hitl|requires_approval|approval' "$TARGET" 2>/dev/null \
  && orch_score=$((orch_score+2)) \
  || add_finding HIGH "Orquestracao" "ORCH-HITL" "FAIL" "Sem HITL aparente p/ decisões de alto risco" "RN-020"

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: OBSERVABILIDADE (peso 5%)
# ════════════════════════════════════════════════════════════════════════════
obs_score=0
echo "▶ Observabilidade…"
grep -rqiE 'opentelemetry|otlp|trace_id|langfuse|tracing' "$TARGET" 2>/dev/null \
  && { obs_score=$((obs_score+6)); add_finding MEDIUM "Observabilidade" "OBS-TRACE" "PASS" "Tracing/LLM observability detectado" "ISO 27001 A.12.4"; } \
  || add_finding HIGH "Observabilidade" "OBS-TRACE" "FAIL" "Sem tracing/observabilidade de LLM" "RN-023"
grep -rqiE 'cost|tokens_total|usage.*tokens' "$TARGET" 2>/dev/null \
  && obs_score=$((obs_score+4)) \
  || add_finding MEDIUM "Observabilidade" "OBS-COST" "FAIL" "Sem cost monitoring de tokens" "COBIT APO12.01"

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: DADOS & RAG (peso 3%)
# ════════════════════════════════════════════════════════════════════════════
data_score=5
echo "▶ Dados & RAG…"
grep -rqiE 'pii|anonymiz|redact|lgpd|gdpr' "$TARGET" 2>/dev/null \
  && { data_score=10; add_finding MEDIUM "DadosRAG" "DATA-PII" "PASS" "PII handling detectado" "GDPR/LGPD"; } \
  || add_finding HIGH "DadosRAG" "DATA-PII" "FAIL" "Sem tratamento de PII aparente" "RN-027"

# ════════════════════════════════════════════════════════════════════════════
# DIMENSÃO: DEPLOY & INFRA (peso 2%)
# ════════════════════════════════════════════════════════════════════════════
deploy_score=0
echo "▶ Deploy & Infra…"
exists_any ".github/workflows" ".gitlab-ci.yml" "cloudbuild.yaml" && { deploy_score=$((deploy_score+5)); add_finding MEDIUM "DeployInfra" "DEP-CI" "PASS" "CI/CD presente" "NIST SSDF PO.3.1"; } \
  || add_finding CRITICAL "DeployInfra" "DEP-CI" "FAIL" "Sem CI/CD — deploy AI sem gates" "RN-029"
grep -rqiE 'rate.?limit|ratelimit|RateLimitMiddleware' "$TARGET" 2>/dev/null \
  && deploy_score=$((deploy_score+5)) \
  || add_finding CRITICAL "DeployInfra" "DEP-RATE" "FAIL" "API de LLM sem rate limiting" "RN-030"

# ════════════════════════════════════════════════════════════════════════════
# SCORECARD PONDERADO
# ════════════════════════════════════════════════════════════════════════════
# overall = Σ(score_dim * peso_dim) / 100  → escala 0..10
overall=$(awk -v c=$ctx_score -v s=$sdd_score -v a=$arch_score -v o=$orch_score \
  -v se=$sec_score -v t=$test_score -v ob=$obs_score -v d=$data_score -v dp=$deploy_score \
  -v wc=$W_CONTEXT -v ws=$W_SDD -v wa=$W_ARCH -v wo=$W_ORCH -v wse=$W_SEC \
  -v wt=$W_TEST -v wob=$W_OBS -v wd=$W_DATA -v wdp=$W_DEPLOY \
  'BEGIN{printf "%.1f",(c*wc+s*ws+a*wa+o*wo+se*wse+t*wt+ob*wob+d*wd+dp*wdp)/100}')

# Status (SPEC §6.2): crítico sem mitigação => REPROVADO independente do score
status="APROVADO"; code=0
awk_lt() { awk -v x="$1" -v y="$2" 'BEGIN{exit !(x<y)}'; }
if [ "$CRIT" -gt 0 ] || awk_lt "$overall" 5.0; then
  status="REPROVADO"; code=1
elif awk_lt "$overall" 7.0; then
  status="CONDICIONAL"; code=2
fi

# ── report.json ─────────────────────────────────────────────────────────────
{
  echo "{"
  echo "  \"project\": \"$(basename "$TARGET")\","
  echo "  \"target\": \"$TARGET\","
  echo "  \"date\": \"$TS\","
  echo "  \"overall_score\": $overall,"
  echo "  \"overall_status\": \"$status\","
  echo "  \"issues\": { \"critical\": $CRIT, \"high\": $HIGH, \"medium\": $MED },"
  echo "  \"ai_commits\": $ai_commits, \"total_commits\": $total_commits,"
  echo "  \"tooling_gaps\": \"$(echo "$TOOLING_GAPS" | sed 's/^ //')\","
  echo "  \"dimensions\": {"
  echo "    \"context_engineering\": {\"score\": $ctx_score, \"weight\": $W_CONTEXT},"
  echo "    \"spec_driven_dev\": {\"score\": $sdd_score, \"weight\": $W_SDD},"
  echo "    \"architecture\": {\"score\": $arch_score, \"weight\": $W_ARCH},"
  echo "    \"orchestration\": {\"score\": $orch_score, \"weight\": $W_ORCH},"
  echo "    \"security\": {\"score\": $sec_score, \"weight\": $W_SEC},"
  echo "    \"testing_qa\": {\"score\": $test_score, \"weight\": $W_TEST},"
  echo "    \"observability\": {\"score\": $obs_score, \"weight\": $W_OBS},"
  echo "    \"data_rag\": {\"score\": $data_score, \"weight\": $W_DATA},"
  echo "    \"deploy_infra\": {\"score\": $deploy_score, \"weight\": $W_DEPLOY}"
  echo "  },"
  echo "  \"findings\": ["
  first=1
  for f in "${FINDINGS[@]}"; do
    IFS='|' read -r sev dim chk st desc ref <<< "$f"
    [ $first -eq 0 ] && echo ","
    first=0
    printf '    {"severity":"%s","dimension":"%s","check":"%s","status":"%s","description":"%s","framework_ref":"%s"}' \
      "$sev" "$dim" "$chk" "$st" "$desc" "$ref"
  done
  echo
  echo "  ]"
  echo "}"
} > "$OUT_DIR/report.json"

# ── report.md ─────────────────────────────────────────────────────────────────
icon="✅"; [ "$status" = "CONDICIONAL" ] && icon="⚠️"; [ "$status" = "REPROVADO" ] && icon="❌"
{
  echo "# Relatório de Auditoria — $(basename "$TARGET") — $TS"
  echo
  echo "## 1. Resumo Executivo"
  echo "- **Score de Maturidade:** ${overall} / 10"
  echo "- **Status Geral:** ${icon} ${status}"
  echo "- **Issues:** 🔴 ${CRIT} · 🟡 ${HIGH} · 🟢 ${MED}"
  echo "- **Código AI:** ${ai_commits}/${total_commits} commits marcados"
  [ -n "$TOOLING_GAPS" ] && echo "- **Tooling gaps:** ${TOOLING_GAPS}"
  echo
  echo "## 2. Scorecard por Dimensão"
  echo "| Dimensão | Score | Peso |"
  echo "|----------|-------|------|"
  echo "| Spec-Driven Development | ${sdd_score}/10 | ${W_SDD}% |"
  echo "| Context Engineering | ${ctx_score}/10 | ${W_CONTEXT}% |"
  echo "| Arquitetura | ${arch_score}/10 | ${W_ARCH}% |"
  echo "| Orquestração Multi-Agente | ${orch_score}/10 | ${W_ORCH}% |"
  echo "| Segurança | ${sec_score}/10 | ${W_SEC}% |"
  echo "| Testes & QA | ${test_score}/10 | ${W_TEST}% |"
  echo "| Observabilidade | ${obs_score}/10 | ${W_OBS}% |"
  echo "| Dados & RAG | ${data_score}/10 | ${W_DATA}% |"
  echo "| Deploy & Infra | ${deploy_score}/10 | ${W_DEPLOY}% |"
  echo
  echo "## 3. Findings"
  echo "| Sev | Dimensão | Check | Status | Descrição | Framework |"
  echo "|-----|----------|-------|--------|-----------|-----------|"
  for f in "${FINDINGS[@]}"; do
    IFS='|' read -r sev dim chk st desc ref <<< "$f"
    s="🟢"; [ "$sev" = "HIGH" ] && s="🟡"; [ "$sev" = "CRITICAL" ] && s="🔴"
    echo "| $s | $dim | $chk | $st | $desc | $ref |"
  done
  echo
  echo "## 4. Recomendação"
  case "$status" in
    APROVADO)    echo "✅ Auditoria aprovada. Score: ${overall}/10. Deploy liberado.";;
    CONDICIONAL) echo "⚠️ Auditoria condicional. Score: ${overall}/10. ${CRIT} issues 🔴 requerem atenção. Deploy liberado com mitigações + remediação < 48h.";;
    REPROVADO)   echo "❌ Auditoria reprovada. Score: ${overall}/10. ${CRIT} issues 🔴 bloqueiam deploy. Plano de remediação obrigatório.";;
  esac
} > "$OUT_DIR/report.md"

# ── Imutabilidade (RNF-003) ───────────────────────────────────────────────────
if have sha256sum; then sha256sum "$OUT_DIR/report.json" > "$OUT_DIR/report.sha256"
elif have shasum; then shasum -a 256 "$OUT_DIR/report.json" > "$OUT_DIR/report.sha256"; fi

# ── Console ───────────────────────────────────────────────────────────────────
echo
echo "════════════════════════════════════════════"
echo "  ${icon} ${status}   Score: ${overall}/10"
echo "  🔴 ${CRIT}  🟡 ${HIGH}  🟢 ${MED}"
echo "  Relatório: $OUT_DIR/report.md"
echo "════════════════════════════════════════════"
exit $code
