---
description: Auditoria de conformidade — ciclo Scoped→Closed. Domínio + amostra + gaps + corretiva + reteste.
---

# Workflow: /audit

> **Canônico:** [auditoria-conformidade.md](../rules/auditoria-conformidade.md) · diagrama [auditoria-conformidade.mmd](../rules/auditoria-conformidade.mmd).
> **Não confundir:** [auditoria-tools.md](../rules/auditoria-tools.md) = NC de **tool** (5 Whys). Este workflow = **conformidade global** (política → evidência → gap).
> **Approver default:** Marcelo. Relatório mínimo = §7 do doc de conformidade.

## Tipos

| Tipo | Quando |
|---|---|
| Interna periódica | 1 relatório golden + 1 domínio |
| Por incidente | Sintoma prod (custo, Places, split-brain, wall-clock) |
| Pré-release | Diff `tools/` `agents/` + checklist fontes antes de `/deploy` |

## Ciclo (estados)

```
Scoped → Evidence → Findings → Corrective → Retest → Closed
```

| Estado | Fazer | Saída |
|---|---|---|
| **Scoped** | Domínio + critérios (links `.agent/rules/…`) + amostra (UUID / branch / arquivos) | Escopo escrito |
| **Evidence** | Coletar prova (ledger `api_sku`, outputs, logs, `relkind`, `/api/version`) | Artefatos citáveis |
| **Findings** | Gaps com severidade Crítico / Alto / Médio / Baixo | Tabela achados |
| **Corrective** | Approver autoriza; Act-on / PR; gap Tool → `auditoria-tools` | Fix ou defer escrito |
| **Retest** | Nova evidência pós-fix (mesmo critério) | pass/fail |
| **Closed** | Relatório 1 página no caso em `auditoria-conformidade.md` (ou link) | Closed |

Reject/defer: Approver fecha sem fix — **motivo escrito**.

## Domínios → critérios

| Domínio | Ler |
|---|---|
| Fontes / pipeline | `conferencia-fontes-pipeline.md` · `pipeline-fontes-deterministicas.md` |
| Número / carimbo | P-000 §5–§6 · `data_lineage.md` |
| Tools / custo API | SearchAPI-primário; ledger `relatorio_api_calls` |
| Schema / banco | P-000 §7 (`gymsite` vs `public`) |
| Deploy | P-000 §7–§8; API+worker mesma imagem |
| Segurança | RLS, advisors, sem secret em git |
| Produto / UX | `processo-mudanca.md` |

## Steps (execução)

1. **Scoped** — escolher tipo + domínio + amostra. Ex.: Fontes · relatório `3862ba63-…`.
2. **Evidence** — queries/logs/diff. Não afirmar sem abrir fonte.
3. **Findings** — tabela severidade; PASS explícito também.
4. **Pedir Approver** antes de Corrective amplo.
5. **Corrective** — implementar mínimo; se tool NC → Draft `auditoria-tools`.
6. **Retest** — mesma checklist; anexar prova.
7. **Closed** — atualizar caso em `auditoria-conformidade.md` (§7: escopo, critérios, achados, corretivas, retest).

## Ponte

```
gap Fontes  → P-000 + checklist fontes
gap Tool    → /auditoria-tools (5 Whys)
gap Deploy  → /deploy + sync worker
gap Schema  → /migrate (1 SQL)
```

## Anti-padrões

- ❌ Checklist de 200 itens sem evidência
- ❌ Refactor “porque feio” sem gap de política
- ❌ Confundir com `/review` (PR) ou monitoramento 24/7
