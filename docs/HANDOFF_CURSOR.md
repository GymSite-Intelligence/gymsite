# Handoff — GymSite Intelligence (Cursor Agent)

**Atualizado:** 02/06/2026  
**Autor:** Marcelo Rosas / sessão Cursor  
**Repositório:** https://github.com/Marcelo-Rosas/gymsite.git  
**Branch:** `main`  
**HEAD remoto:** `1bd75cd` (`docs: add HANDOFF_CURSOR.md for agent context`)

> Se este documento divergir do código local, **confie no código local** e atualize este arquivo.

---

## Resposta validada (02/06/2026)

```powershell
python eval/run_eval.py
# 3 PASS, 2 SKIP, 0 FAIL

python eval/run_eval.py --case fortaleza_parangaba_20260528
# 1 PASS, 0 FAIL

python -c "import tools.cno_fitness_tools; print('OK')"
# OK
```

---

## Pilares do pipeline

| Pilar | Status | Evidência |
|-------|--------|-----------|
| **#1 Silent Failures** | ✅ Produção | Logging em A6/A8/A9; fail-safe em Supabase writer |
| **#2 LangCache** | ✅ Produção | TTL 7d, hash concorrentes, métricas hit/miss |
| **#3 Avaliação** | ✅ CI integrado | Golden dataset (5 casos) + job `eval-golden-dataset` |
| PositioningQualityEval (LLM) | ⏳ Pendente | Nightly/manual — não gate de PR |
| structural_eval / financial_consistency | ⏳ Pendente | **Não existem** no repo |

---

## Estado real do eval (crítico)

O CI roda `python eval/run_eval.py`, que hoje executa **somente** `cno_consistency_eval.py`.

| Arquivo | Existe? | No CI? |
|---------|---------|--------|
| `eval/evaluators/cno_consistency_eval.py` | ✅ | ✅ |
| `eval/evaluators/structural_eval.py` | ❌ | ❌ |
| `eval/evaluators/financial_consistency.py` | ❌ | ❌ |
| `PositioningQualityEval` (LLM) | ❌ | ❌ |

**CLI correta:**

```powershell
python eval/run_eval.py
python eval/run_eval.py --case fortaleza_parangaba_20260528
```

- **Não existe** `--all`
- **Não existe** `cno_validation.json` — regras em `expected_output.json` → `cno_validation`
- Eval **não lê** `cno.csv` no CI — usa `full_report.json` + snapshots JSON

**Resultado esperado:** 3 PASS, 2 SKIP, 0 FAIL (~18–22s).

---

## Golden dataset (5 casos)

| Case ID | CNO eval | Notas |
|---------|----------|-------|
| `fortaleza_parangaba_20260528` | PASS (required) | 4 obras município, Selfit encerrada |
| `fortaleza_aldeota_20260601` | PASS (required) | Max Forma 4583 m², `warn_keyword_only` |
| `niteroi_camboinhas_20260513` | PASS (supplement) | 0 fitness keyword; `cno_cruzamento_cnpj.json` |
| `anapolis_anapolis_city_20260529` | SKIP | sem `cno_validation` |
| `curitiba_batel_20260512` | SKIP | sem `cno_validation` |

Arquivos por caso: `input.json`, `expected_output.json`, `full_report.json`, `notes.md`.  
Opcional: `cno_cruzamento_cnpj.json`, `cno_live.json`.

---

## CNO × CNPJ (regras de negócio)

- Docs: `docs/CNO_INTEGRACAO.md`
- Código: `tools/cno_fitness_tools.py`, `tools/cnpj_fitness_tools.py`
- Obra CNO = CNAE **construção** (4120400); academia = **9313100** no CNPJ responsável
- `_eh_obra_fitness()` → `metodo_classificacao`: `keyword` | `cnpj_cnae` | `cnpj_cnae_area_atipica`
- Fluxo obrigatório: **CNPJ entrantes 90d → CNO município inteiro → recorte bairro depois**
- CSVs: `encoding="latin-1", errors="replace"` (não remover)
- Windows stdout: `query_cnpj_cno.py` — UTF-8 + `->` (não `→`)

Scripts:

| Script | Função |
|--------|--------|
| `scripts/query_cnpj_cno.py` | CLI canônico CNPJ→CNO |
| `scripts/query_cno_golden_case.py` | CNO ao vivo por UUID (lento) |
| `scripts/extract_golden_case.py` | Extrai caso do Supabase |

---

## CI/CD

`.github/workflows/ci-cd.yml`:

```
PR/push →  Build & Test (ci)
        →  Golden Dataset Eval (eval-golden-dataset)
        →  CD deploy (push main, needs ambos)
```

Job `eval-golden-dataset`: Python 3.11, sem pip, sem secrets, sem `cno.csv`.

---

## Commits recentes (main)

```
1bd75cd docs: add HANDOFF_CURSOR.md for agent context
8236928 ci: add eval-golden-dataset job to CI pipeline
dcb0ec1 feat(eval): CNO metodo_classificacao + supplement CNPJ×CNO
9f9d8aa fix(api): callbacks ADK, SRE agents e LangCache para deploy
```

---

## Ambiente local

### Variáveis (.env — NÃO commitar)

```env
CNO_DATA_DIR=C:\Users\marce\Downloads\cno_extract   # junction → D:\Limpeza Disco\cno_extract
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
GOOGLE_API_KEY=...
LANGCACHE_DEFAULT_TTL_MS=604800000
```

### Disco (limpeza 02/06/2026)

| Item | Destino D: | Junction? |
|------|------------|-----------|
| `metrics/rfb_cnpj_cache` (~6,3 GB) | `D:\Limpeza Disco\gymsite_intelligence\metrics_rfb_cnpj_cache` | ✅ |
| `Downloads/cno_extract` (~1,25 GB) | `D:\Limpeza Disco\cno_extract` | ✅ |

Manifesto: `D:\Limpeza Disco\gymsite_intelligence\MANIFEST.md`  
C: ~9 GB livres (era ~80 MB).

---

## Working tree local (não commitado em 1bd75cd)

```
M  agents/a6_report_consolidator.py, a9_positioning_strategist.py
M  api.py, Dockerfile, docker-compose*.yml
M  frontend/ (RelatorioViewer, ContextoMercado, Custos)
M  tools/a8_runner.py, maps_tools.py, rfb_cnpj_fitness_loader.py
?? frontend/src/lib/dados-indisponiveis.ts
?? tools/health_components.py
?? scripts/_debug_cno_niteroi.py, mapeamento_canonico_rpt.py
```

Sempre `git status` antes de assumir remoto = local.

---

## Não fazer

| Ação | Motivo |
|------|--------|
| Assumir `structural_eval` / `financial_consistency` existem | Não implementados |
| `run_eval.py --all` ou `cno_validation.json` | Não existem |
| Remover `errors="replace"` nos CSVs CNO | Quebra no Windows |
| Commitar `.env` ou chaves | Segurança |
| LLM-as-Judge como gate de PR | Flake + custo |
| Alterar score sem atualizar golden | Falsos positivos no eval |

---

## Próximos passos sugeridos

1. **GitHub Action** — ✅ feito (`8236928`)
2. **PositioningQualityEval** — workflow nightly, `continue-on-error: true`
3. **structural_eval + financial_consistency** — implementar e registrar em `run_eval.py`
4. **Golden dataset** — expandir 5 → 20 casos
5. **Commitar** mudanças locais pendentes (A6/A9/frontend) em PRs separados
6. **AppData** (~160 GB) — mapear subpastas se precisar mais espaço em C:

---

## Estrutura relevante

```
gymsite_intelligence/
├── agents/          a6 (consolidador), a8 (validator), a9 (posicionamento ERRC)
├── tools/           cno_fitness_tools, cnpj_fitness_tools, langcache_client
├── eval/
│   ├── run_eval.py
│   ├── evaluators/cno_consistency_eval.py
│   └── golden_dataset/          # 5 casos
├── scripts/         query_cnpj_cno.py, extract_golden_case.py
├── docs/            CNO_INTEGRACAO.md, HANDOFF_CURSOR.md
└── .github/workflows/ci-cd.yml
```

---

**Nota para o próximo agente:** Conecte-se ao repo local, rode `git status` e `python eval/run_eval.py` antes de qualquer sugestão de código. Este documento reflete validação em 02/06/2026.
