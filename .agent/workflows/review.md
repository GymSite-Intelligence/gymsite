---
description: Code review on current changes/PR — types, security, fontes, carimbo, schema-split.
---

# Workflow: /review

> **Regras:** [P-000](../rules/P-000_REGRA_MESTRA_MUDANCA.md) · [conferencia-fontes-pipeline.md](../rules/conferencia-fontes-pipeline.md) · [processo-mudanca.md](../rules/processo-mudanca.md) · [REGRAS_USO_GLOBAL](../rules/REGRAS_USO_GLOBAL.md).
> **Gate teste:** `/test`. **Não confundir:** `/audit` (amostra + ciclo Closed).

## Steps

1. **Gate automático** // turbo
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -x --tb=line -q
   cd frontend; npx tsc --noEmit; cd ..
   ```
   Opcional: `pyrefly check .` se disponível. **Não** exigir `npm run lint` / Vitest fantasmas.

2. **Security**
   - Secrets hardcoded (`api_key`, `password`, `service_role` em client)
   - Sem `eval`/`exec` com input
   - SQL: sem f-string de user input; writers via `tbl()` / params

3. **Fontes / pipeline** (se toca `agents/` `tools/` contrato relatório)
   - [ ] Primário SearchAPI ou determinístico?
   - [ ] Aluguel tocado? → só MRLR / A4 Tier 0?
   - [ ] Places = fallback explícito (não caminho crítico default)?
   - [ ] Número LLM? Justificado + PIPELINE_AGENTES §6?
   - [ ] Carimbo P-010 se UI/PDF exibe número?
   - [ ] `PIPELINE_AGENTES.md` / conferencia-fontes se fonte mudou?

4. **Schema / SQL** (se migration)
   - [ ] `relkind`: DDL em `gymsite.*` (tabela), não `public.*` view
   - [ ] View `public` atualizada se PostgREST depende
   - [ ] Uma migration nomeada — ver `/migrate`

5. **Deploy impact**
   - Mudou Python runtime (`agents`/`tools`/`api.py`)? → Cloud Run + **worker sync** no merge
   - Só front? → Wrangler/Pages `gymsite`
   - Só SQL/seed? → `/migrate`; Cloud Run só se código também mudou

6. **Style / diff hygiene**
   - Mudança mínima (P-000 §1); sem refactor adjacente
   - Nomes EN no código; Conventional Commits
   - Sem `print()` de debug; logging ok

7. **Report**
   - CRITICAL / WARNING / NIT
   - Fix sugerido com path; pedir `/test` verde antes de approve

## Anti-padrões

- ❌ Aprovar PR pipeline sem checklist fontes
- ❌ `ALTER public.*` em prod SEP sem checar view
- ❌ “LGTM” sem gate `/test` quando Python/TS mudou
