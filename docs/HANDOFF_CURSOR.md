# Handoff — GymSite Intelligence (Cursor Agent)

**Atualizado:** 02/06/2026  
**Autor:** Marcelo Rosas / GymSite Intelligence Dev Team  
**Repositório:** https://github.com/Marcelo-Rosas/gymsite.git  
**Branch:** `main`  
**HEAD remoto:** `79bd74c` (`feat(eval): golden 10 casos, EVAL_GUIDE e positioning nightly`)

> **Regra de ouro:** Se este documento divergir do código local, **confie no código local**, rode `git status` e `python eval/run_eval.py` antes de sugerir alterações.

---

## Restrições críticas (não ignorar)

1. **Eval determinísticos:** `structural_eval.py` + `financial_consistency_eval.py` rodam no default de `run_eval.py` (gate PR). Positioning LLM continua só com `--with-positioning`.
2. **CLI eval:** `python eval/run_eval.py` ou `--case <case_id>`. **Não existe** `--all`.
3. **Golden:** regras CNO em `expected_output.json` → `cno_validation`. **Não existe** `cno_validation.json`.
4. **Encoding CNO:** nunca remova `encoding="latin-1", errors="replace"` nos CSVs (quebra no Windows).
5. **LLM-as-Judge:** `PositioningQualityEval` só nightly/manual (`continue-on-error: true`). **Nunca** gate bloqueante de PR.

---

## Validação executada (02/06/2026)

```powershell
git status
# limpo exceto ?? scripts/_debug_cno_niteroi.py (não commitar)

python -c "import tools.cno_fitness_tools; import agents.a6_report_consolidator; print('OK')"
# OK

python eval/run_eval.py
# 10 casos | CNO FAIL: 0 | STR FAIL: 0 | FIN FAIL: 0  (WARN em curadoria conhecida)

python eval/run_eval.py --with-positioning
# POS: SKIP em todos (sem posicionamento_estrategico nos snapshots ainda)

python eval/run_eval.py --cno-only
# só CNO (legado)
```

---

## Pilares do pipeline

| Pilar | Status | Evidência |
|-------|--------|-----------|
| **#1 Silent Failures** | ✅ Produção | Logging A6/A8/A9; fail-safe Supabase writer |
| **#2 LangCache** | ✅ Produção | TTL 7d, hash concorrentes, métricas hit/miss |
| **#3 Avaliação (CNO)** | ✅ CI | Job `eval-golden-dataset`; **10** golden cases |
| **#3 Avaliação (structural/financial)** | ✅ CI | `structural_eval.py`, `financial_consistency_eval.py` |
| **#3 Avaliação (LLM)** | ✅ Nightly | `positioning_quality_eval.py` + `eval-positioning.yml` |

---

## Arquitetura e arquivos-chave

```text
gymsite_intelligence/
├── agents/
│   ├── a6_report_consolidator.py    # A8 pós-gravação; coleta_geografica no JSON
│   ├── a8_validator.py
│   └── a9_positioning_strategist.py # LangCache; posicionamento_estrategico
├── tools/
│   ├── cno_fitness_tools.py         # _eh_obra_fitness()
│   ├── cnpj_fitness_tools.py
│   ├── a8_runner.py                 # timeout, persist async, resolve rpt_* → UUID
│   └── langcache_client.py
├── eval/
│   ├── run_eval.py                  # CNO+STR+FIN; --with-positioning LLM; --cno-only
│   ├── evaluators/
│   │   ├── cno_consistency_eval.py
│   │   ├── structural_eval.py
│   │   ├── financial_consistency_eval.py
│   │   └── positioning_quality_eval.py
│   └── golden_dataset/              # 10 casos
├── frontend/                        # Custos: propostas via Supabase RLS (não API)
├── scripts/
│   ├── query_cnpj_cno.py
│   ├── extract_golden_case.py
│   └── list_golden_candidates.py
├── .github/workflows/
│   ├── ci-cd.yml                    # eval-golden-dataset (gate PR)
│   └── eval-positioning.yml         # nightly 04:30 UTC + manual
└── docs/
    ├── CNO_INTEGRACAO.md
    ├── EVAL_GUIDE.md
    └── HANDOFF_CURSOR.md
```

---

## Eval (estado real)

| Evaluator | Arquivo | Gate PR | Nightly |
|-----------|---------|---------|---------|
| CNO | `cno_consistency_eval.py` | ✅ | — |
| Positioning (LLM) | `positioning_quality_eval.py` | ❌ | ✅ |

```powershell
python eval/run_eval.py
python eval/run_eval.py --case fortaleza_parangaba_20260528
python eval/run_eval.py --with-positioning   # requer GOOGLE_API_KEY
```

Ver `docs/EVAL_GUIDE.md`. Eval **não lê** `cno.csv` no CI.

---

## Golden dataset (10 casos)

| Case ID | Veredito | CNO |
|---------|----------|-----|
| `fortaleza_parangaba_20260528` | APROVADO COM RESSALVAS | PASS |
| `fortaleza_aldeota_20260601` | APROVADO | PASS |
| `niteroi_camboinhas_20260513` | INVESTIGAR MAIS | PASS |
| `fortaleza_meireles_20260528` | APROVADO | PASS |
| `fortaleza_eusebio_20260529` | APROVADO COM RESSALVAS | PASS |
| `altamira_altamira_20260529` | APROVADO COM RESSALVAS | PASS |
| `anapolis_anapolis_city_20260529` | APROVADO COM RESSALVAS | SKIP |
| `curitiba_batel_20260512` | APROVADO COM RESSALVAS | SKIP |
| `brasilia_ade_aguas_claras_setor_habitacional_arniqueira_20260512` | APROVADO | SKIP |
| `fortaleza_cidade_inteira_20260527` | INVESTIGAR MAIS | SKIP |

**Lacuna:** não há `REPROVADO` no Supabase (jun/2026); `INVESTIGAR MAIS` / `fortaleza_cidade_inteira` serve como proxy.

Extrair caso: `python scripts/extract_golden_case.py <uuid>`

---

## CNO × CNPJ (crítico)

CNO registra CNAE da **construtora** (4120400), não da academia (9313100).

**`_eh_obra_fitness()` — obra fitness se:**
1. Keyword no nome + área 80–8000 m² + sem exclusões (`universidade`, `prefeitura`, `creche`, …), **ou**
2. CNPJ responsável com CNAE `9313100` (`metodo_classificacao`: `keyword` | `cnpj_cnae` | `cnpj_cnae_area_atipica`).

**Fluxo `cruzar_entrantes_obras_cno`:**
1. CNPJ fitness entrantes 90d no município  
2. CNO municipal inteiro (sem filtrar keyword antes)  
3. Match: `cnpj_responsavel` → `endereco_cep_numero` → `nome_obra_cep8`  
4. Recorte por bairro depois  

Docs: `docs/CNO_INTEGRACAO.md`

---

## Contexto de mercado (tickets estruturais, jun/2026)

| Tier | Faixa | Exemplos |
|------|-------|----------|
| Low Cost | R$ 89,90 – 119,90 | Selfit Light, MaxForma Vitalidade |
| Mid Market | R$ 139,90 – 149,90 | Smart Fit Smart, Skyfit SKY |
| Premium | R$ 159,90+ | Smart Fit Black, Bodytech |

Regressão A4: ticket Mid Market &lt; ~R$ 80 ou Premium irreal em bairro de baixa renda.

---

## CI/CD

```
PR/push → Build & Test → eval-golden-dataset → CD (main)
Nightly → eval-positioning.yml (--with-positioning, continue-on-error)
```

---

## Commits recentes (main)

```
79bd74c feat(eval): golden 10 casos, EVAL_GUIDE e positioning nightly
7769415 refactor(a8): extrair _supabase_client helper
0b60130 fix(frontend): ranking bairros com chave normalizada
a7a111e fix(a8): persist validacao com UUID e timeout
4eeb93c fix(frontend): propostas de custo via Supabase RLS
```

---

## Ambiente local

```env
CNO_DATA_DIR=...          # junction D:\Limpeza Disco\cno_extract
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
GOOGLE_API_KEY=...
LANGCACHE_DEFAULT_TTL_MS=604800000
```

Working tree: só `scripts/_debug_cno_niteroi.py` untracked (debug).

---

## Não fazer

| Ação | Motivo |
|------|--------|
| Ignorar WARN structural (contagens DB vs markdown) | Ver `notes.md` por caso |
| `run_eval.py --all` ou `cno_validation.json` | Não existem |
| Remover `errors="replace"` nos CSVs CNO | Windows |
| Commitar `.env` | Segurança |
| LLM-as-Judge como gate de PR | Flake + custo |
| Alterar score sem atualizar golden | Falsos positivos |

---

## Próximos passos (backlog)

1. **Golden com A9:** re-extrair 1–2 casos após pipeline com `posicionamento_estrategico` (destrava POS eval).
2. **Caso `REPROVADO`:** quando existir no Supabase, extrair via `list_golden_candidates.py`.
3. **Golden 10 → 20** — curadoria + `cno_validation` nos SKIP.
4. **Secret `GOOGLE_API_KEY`** no GitHub para workflow positioning.
5. **Cenários A4 no JSON:** quando `viabilidade_3_cenarios` entrar nos snapshots, financial valida ticket×modelo.

---

**Próximo agente:** rode o bloco de validação no topo antes de codar.
