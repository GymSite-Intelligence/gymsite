# Auditoria de Conformidade Global — Processo Canônico

> Adotado jul/2026. Guarda-chuva de **adesão a políticas internas GymSite** (e obrigações externas quando aplicável).
> Inspirado no ciclo clássico de [auditoria de conformidade](https://www.sailpoint.com/pt-br/identity-library/compliance-audit) (snapshot + gaps + corretiva ≠ monitoramento contínuo).
> Diagrama: [`auditoria-conformidade.mmd`](auditoria-conformidade.mmd).
>
> **Não confundir:**
> - [`auditoria-tools.md`](auditoria-tools.md) = processo de **NC em tool** (sintoma → 5 Whys → Act-on)
> - Este arquivo = **ciclo de conformidade** (política → evidência → gap → corretiva → re-teste)
> - SailPoint IAM (identidade/acesso IdP) = domínio separado; aqui só se o gap for RLS/auth/segredo

## 1. O que é (no GymSite)

**Auditoria de conformidade** = avaliação pontual: código, tools, schema e operação **aderem** às normas que nós mesmos adotamos (P-000, fontes, carimbo, deploy) e, quando existir, a lei/contrato (LGPD, termos API).

| É | Não é |
|---|---|
| Snapshot com critério escrito | Monitoramento 24/7 (logs/alertas) |
| Gap + ação corretiva rastreável | Refactor “porque feio” |
| Independência relativa (Reviewer ≠ Author do trecho) | Substitui code review de PR |
| Relatório curto de achados | Checklist de 200 itens sem evidência |

## 2. Políticas = critérios de auditoria

| Domínio | Critério (fonte) | Evidência típica |
|---|---|---|
| **Fontes / pipeline** | `conferencia-fontes-pipeline.md` · `pipeline-fontes-deterministicas.md` | ledger `api_sku`, state keys, SPEC |
| **Número / carimbo** | P-000 §5–§6 · `data_lineage.md` | PDF/UI + campo JSON |
| **Tools / custo API** | SearchAPI-primário · fallback explícito | `relatorio_api_calls` agregado |
| **Schema / banco** | P-000 §7 gotcha `gymsite` vs `public` | migration + `relkind` |
| **Deploy** | P-000 §7–§8 · API+worker mesma imagem | `/api/version` |
| **Segurança / dados** | RLS, service role, sem secret em git | advisors Supabase · `.gitignore` |
| **Produto / UX mudança** | `processo-mudanca.md` | PR + artefato visual se UI |

Gap num domínio **Tools** → abre ou reusa ciclo [`auditoria-tools.md`](auditoria-tools.md) (Draft→Approved).

## 3. Tipos (adaptados)

| Tipo | Escopo | Quem |
|---|---|---|
| **Interna periódica** | Amostra (1 relatório golden + 1 domínio) | Author interno + Reviewer |
| **Por incidente** | Sintoma prod (custo, Places, split-brain) | quem achou = Author |
| **Pré-release / pré-deploy** | Diff `tools/` `agents/` + checklist fontes | Author do PR |
| **Externa / formal** | Só se contrato/lei exigir (futuro) | terceiro — fora do dia a dia |

## 4. Ciclo (estados)

Ver `auditoria-conformidade.mmd`.

| Estado | SLA | Saída |
|---|---|---|
| **Scoped** | 1d | domínio + critério + amostra definidos |
| **Evidence** | 2d | evidência coletada (ledger, diff, UUID) |
| **Findings** | 2d | gaps classificados (Crítico / Alto / Médio / Baixo) |
| **Corrective** | conforme gap | Act-on / ticket; se tool → `auditoria-tools` |
| **Retest** | 1d pós-fix | evidência de fechamento |
| **Closed** | imediato | relatório 1 página + link artefatos |

**Reject / defer:** Approver pode fechar sem fix (“aceito risco”) — motivo escrito.

## 5. Severidade

| Nível | Exemplo | Ação |
|---|---|---|
| **Crítico** | Aluguel via listing/LLM; secret em repo; Places no caminho crítico sem flag | Act-on imediato + Cloud Run |
| **Alto** | Dual SKU SearchAPI+Places; freeze `param()` import | Act-on ≤ 1 sprint |
| **Médio** | Doc/SPEC desatualizado; ledger sem `motivo_fallback` | PR docs ou debt |
| **Baixo** | Naming / comentário | backlog |

## 6. Papéis

| Papel | Responsabilidade |
|---|---|
| **Author** | Scoped + Evidence + rascunho Findings |
| **Reviewer** | Confere critério vs evidência; pede mais prova |
| **Approver** | Aceita Findings; autoriza Corrective ou defer |
| **Owner domínio** | Executa Corrective no código/processo |

Default Approver: Marcelo (produto). Reviewer: quem **não** escreveu o trecho sob auditoria quando der.

## 7. Relatório mínimo (Closed)

1. Escopo + data + amostra (UUID / branch / arquivos)
2. Critérios usados (links `.agent/rules/…`)
3. Achados (tabela severidade)
4. Corretivas (PR / commit / defer)
5. Retest (pass/fail + prova)

## 8. Ponte com processos existentes

```
Conformidade GLOBAL (este doc)
    ├─ gap Fontes     → checklist + Act-on P-000
    ├─ gap Tool       → auditoria-tools (5 Whys + Draft→Approved)
    ├─ gap Número UI  → P-010 / processo-mudanca
    ├─ gap Deploy     → P-000 §7 + Cloud Run worker
    └─ gap Segurança  → advisors + skill supabase (não misturar com Maps)
```

Caso Maps (`buscar_imoveis_texto`) = **incidente** sob conformidade Fontes/Tools → já em `auditoria-tools` Approved (código local); Conformidade marca Corrective até Cloud Run = Retest Closed.
