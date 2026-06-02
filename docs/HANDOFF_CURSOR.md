# Handoff — GymSite Intelligence (Cursor Agent)

**Atualizado:** 02/06/2026  
**Repositório:** https://github.com/Marcelo-Rosas/gymsite.git  
**Branch:** `main`  
**HEAD remoto:** `8236928` (`ci: add eval-golden-dataset job to CI pipeline`)

> Se este documento divergir do código local, **confie no código local** e atualize este arquivo.

---

## Estado real do eval (importante)

O CI roda `python eval/run_eval.py`, que hoje executa **somente** `cno_consistency_eval.py`.

| Arquivo | Existe? | No CI? |
|---------|---------|--------|
| `eval/evaluators/cno_consistency_eval.py` | ✅ | ✅ |
| `eval/evaluators/structural_eval.py` | ❌ | ❌ |
| `eval/evaluators/financial_consistency.py` | ❌ | ❌ |
| `PositioningQualityEval` (LLM) | ❌ | ❌ |

**CLI correta:**

```powershell
python eval/run_eval.py                                          # todos os casos
python eval/run_eval.py --case fortaleza_parangaba_20260528      # um caso
```

Não existe flag `--all`. Não existe `cno_validation.json` — regras ficam em `expected_output.json` → chave `cno_validation`.

**Resultado esperado:** 3 PASS, 2 SKIP, 0 FAIL (~18–22s).

---

## Golden dataset (5 casos)

```
eval/golden_dataset/
├── fortaleza_parangaba_20260528/   # cno_validation required
├── fortaleza_aldeota_20260601/     # cno_validation required + warn_keyword_only
├── niteroi_camboinhas_20260513/    # validar_supplemento + cno_cruzamento_cnpj.json
├── anapolis_anapolis_city_20260529/  # sem cno_validation → SKIP
└── curitiba_batel_20260512/        # sem cno_validation → SKIP
```

Por caso: `input.json`, `expected_output.json`, `full_report.json`, `notes.md`.  
Opcional: `cno_cruzamento_cnpj.json`, `cno_live.json` (snapshots CNPJ→CNO, **sem** `cno.csv` no CI).

---

## CNO × CNPJ (regras de negócio)

Documentação: `docs/CNO_INTEGRACAO.md`  
Implementação: `tools/cno_fitness_tools.py`

- Obra CNO usa CNAE **construção** (4120400), não academia (9313100).
- Inclusão: keywords em `nome_obra` + área 80–8000 m² + exclusões.
- Alta confiança: CNPJ responsável com CNAE 9313100.
- `_eh_obra_fitness()` → `metodo_classificacao`: `keyword` | `cnpj_cnae` | `cnpj_cnae_area_atipica`.
- Fluxo: **CNPJ entrantes 90d → CNO município inteiro → recorte bairro depois**.
- CSVs: `encoding="latin-1", errors="replace"` (não remover).
- Console Windows: `query_cnpj_cno.py` usa UTF-8 stdout + `->` (não `→`).

Scripts: `query_cnpj_cno.py`, `query_cno_golden_case.py`, `extract_golden_case.py`.

---

## CI/CD

`.github/workflows/ci-cd.yml`:

```
PR/push →  Build & Test (ci)
        →  Golden Dataset Eval (eval-golden-dataset)
        →  CD deploy (só push main, needs ambos)
```

Job `eval-golden-dataset`: Python 3.11, sem pip install, sem secrets, sem `cno.csv`.

---

## Commits recentes (main)

```
8236928 ci: add eval-golden-dataset job to CI pipeline
dcb0ec1 feat(eval): CNO metodo_classificacao + supplement CNPJ×CNO
9f9d8aa fix(api): callbacks ADK, SRE agents e LangCache para deploy
```

---

## Working tree local (pode divergir do remoto)

Após `8236928`, mudanças não commitadas em: A6, A9, api, Docker, frontend, maps_tools, rfb loader, etc.  
Sempre `git status` antes de assumir remoto = local.

---

## Ambiente local

```powershell
.venv\Scripts\Activate.ps1
python eval/run_eval.py
python -c "import tools.cno_fitness_tools; print('OK')"
```

Variáveis (`.env`, não commitar): `CNO_DATA_DIR`, `SUPABASE_*`, `GOOGLE_API_KEY`, `LANGCACHE_*`.

`CNO_DATA_DIR` aponta para extract local (queries ao vivo; CI não usa).

---

## Não fazer

| Ação | Motivo |
|------|--------|
| Assumir `structural_eval` / `financial_consistency` existem | Ainda não implementados |
| `run_eval.py --all` ou `cno_validation.json` | Não existem |
| Remover `errors="replace"` nos CSVs CNO | Quebra no Windows |
| Commitar `.env` | Segurança |
| LLM-as-Judge como gate de PR sem `continue-on-error` | Flake + custo |

---

## Próximos passos

1. PositioningQualityEval — nightly/manual  
2. structural_eval + financial_consistency — integrar em `run_eval.py`  
3. Expandir golden dataset (5 → 20)  
4. Commitar mudanças locais pendentes em PRs separados

---

## Estrutura relevante

```
gymsite_intelligence/
├── agents/          a6, a8, a9
├── tools/           cno_fitness_tools, cnpj_fitness_tools
├── eval/            run_eval.py + golden_dataset/
├── scripts/         query_cnpj_cno.py, extract_golden_case.py
├── docs/            CNO_INTEGRACAO.md, HANDOFF_CURSOR.md
└── .github/workflows/ci-cd.yml
```
