# Guia de Avaliação — Golden Dataset

**Atualizado:** 02/06/2026  
**Entrypoint:** `eval/run_eval.py`

---

## Comandos válidos

```powershell
# Todos os casos (eval CNO — gate de PR)
python eval/run_eval.py

# Um caso específico (nome da pasta ou case_id)
python eval/run_eval.py --case fortaleza_parangaba_20260528

# Dataset alternativo
python eval/run_eval.py --dataset eval/golden_dataset

# Incluir PositioningQualityEval (LLM — requer GOOGLE_API_KEY)
python eval/run_eval.py --with-positioning
```

### O que **não** existe

| Comando / artefato | Status |
|------------------|--------|
| `python eval/run_eval.py --all` | ❌ Não implementado |
| `cno_validation.json` (arquivo separado) | ❌ Regras ficam em `expected_output.json` → `cno_validation` |
| `structural_eval.py` | ✅ Gate PR (default) |
| `financial_consistency_eval.py` | ✅ Gate PR (default) |
| Leitura de `cno.csv` no CI | ❌ Usa snapshots JSON + `full_report.json` |

---

## Output esperado (CNO + structural + financial)

```text
[OK] fortaleza_parangaba_20260528 — CNO PASS — STR OK PASS — FIN OK PASS
[--] anapolis_anapolis_city_20260529 — CNO SKIP — STR OK PASS — FIN OK PASS

10 casos | CNO FAIL: 0 | STR FAIL: 0 | FIN FAIL: 0
```

| Ícone | Significado |
|-------|-------------|
| `[OK]` | PASS |
| `[!!]` | WARN |
| `[XX]` | FAIL (exit code 1) |
| `[--]` | SKIP (sem `cno_validation` no golden ou eval desabilitado) |

**Exit code:** `0` se nenhum FAIL em CNO, structural ou financial; `1` se qualquer um falhar.

```powershell
# Apenas CNO (comportamento legado)
python eval/run_eval.py --cno-only
```

---

## Estrutura de um caso

```
eval/golden_dataset/<case_id>/
├── input.json              # input_canonico
├── expected_output.json    # ground truth + cno_validation (opcional)
├── full_report.json        # snapshot do pipeline
├── notes.md                # curadoria manual
├── cno_cruzamento_cnpj.json   # opcional — supplement CNPJ×CNO
└── cno_live.json              # opcional — query CNO ao vivo
```

### Extrair novo caso do Supabase

```powershell
python scripts/list_golden_candidates.py
python scripts/extract_golden_case.py <uuid>
# Revisar notes.md, marcar approved: true, ajustar cno_validation se necessário
```

---

## Evaluators registrados

| Evaluator | Arquivo | Gate PR | Nightly |
|-----------|---------|---------|---------|
| CNO consistency | `eval/evaluators/cno_consistency_eval.py` | ✅ | — |
| Structural | `eval/evaluators/structural_eval.py` | ✅ | — |
| Financial consistency | `eval/evaluators/financial_consistency_eval.py` | ✅ | — |
| Positioning quality (LLM) | `eval/evaluators/positioning_quality_eval.py` | ❌ | ✅ (`eval-positioning.yml`) |

### Regras structural / financial (resumo)

- **Structural:** `critical_fields` + `tolerance_fields` vs `output_consolidado`; input `cidade`/`bairro`/`uf`; contagens `candidatos_count` / `competidores_count` com tolerância ±2 (WARN).
- **Financial:** coerência `veredito` × `score_top1` (APROVADO ≥ 8, RESSALVAS ≥ 6); `modelo_recomendado`; ticket por cenário A4 só quando `viabilidade_3_cenarios` existir no JSON.
- **SKIP:** `structural_validation.required: false` ou `financial_validation.required: false` no golden.

---

## CI

- **PR / push `main`:** job `eval-golden-dataset` roda `python eval/run_eval.py` (sem secrets, ~20s).
- **Nightly / manual:** workflow `eval-positioning.yml` roda `--with-positioning` com `continue-on-error: true` e secret `GOOGLE_API_KEY`.

---

## Regras CNO (resumo)

Ver `docs/CNO_INTEGRACAO.md` e `eval/golden_dataset/README.md`.

- Obra fitness CNO = CNAE construção (4120400) no responsável; academia = 9313100 no CNPJ.
- Fluxo: CNPJ entrantes 90d → CNO município → recorte bairro.
- Tolerância de score no golden: ±0,5 absoluto (`tolerance_fields.score_top1_candidato`).

### Local CLI: ImportError `create_client` from `supabase`

A pasta `supabase/` na raiz (Supabase CLI) sombreia o pacote Python `supabase` quando `sys.path` inclui o repo. Instale o SDK no venv: `pip install -r requirements.txt`. Scripts de rerun/cleanup usam PostgREST via `httpx` (`tools/postgrest_sb.py`); `api.py` usa `tools/supabase_client.load_create_client()`.



---

## Schema canonico de input (alinhado ao formulario de producao)

Fonte da verdade: form-snapshot.md (formulario "Novo Relatorio"). Os input.json
do golden dataset devem usar exatamente estes valores canonicos.

| Campo | Valores canonicos | Label no formulario |
| --- | --- | --- |
| uf | sigla 2 letras (CE, SP, RJ...) | Estado (27 UFs) |
| cidade | string | Municipio (depende do estado) |
| bairro | string | Bairro (depende do municipio) |
| tipo_negocio | academia / crossfit / pilates / funcional / outro | Academia tradicional / CrossFit-Box / Estudio Pilates / Studio Funcional / Outro |
| tamanho_preset | pp / p / m / g / gg | PP 250-400 / P 400-800 / M 800-1500 (mais comum) / G 1500-2500 / GG 2500-5000 m2 |
| area_m2_min / area_m2_max | inteiros (m2) | Override manual do preset |
| publico_alvo | 18-29 / 25-40 / 30-50 / 40+ | Publico-alvo (idade) |
| genero_alvo | misto / predom_fem / predom_masc / excl_fem / excl_masc | Misto / Predom. fem / Predom. masc / Excl. fem / Excl. masc |
| estacionamento_obrigatorio | true / false | Estacionamento obrigatorio (checkbox) |
| bairros_indicados | lista (pode ser vazia) | — |

Mapeamento preset -> area: pp=250-400, p=400-800, m=800-1500, g=1500-2500, gg=2500-5000.

Cobertura de eval por segmento: hoje os 10 casos cobrem apenas tipo_negocio=academia,
publico_alvo=25-40, genero_alvo=misto, preset=m. Faltam casos para crossfit / pilates /
funcional / outro e demais faixas/generos (extrair do Supabase quando houver ground truth).

## Agent Eval (agente isca) — separado do golden dataset

Eval comportamental do agente de pre-venda do site, independente do pipeline de relatorios.

- Local: eval/agent_eval/ (README.md, agent_behavior_eval.py, run_agent_eval.py, cases/, responses/)
- Entrypoint: python eval/agent_eval/run_agent_eval.py --transcript
- Filtros: --case <case_id> | --gate PR|nightly
- Modo --live: stub desativado (requer endpoint/credencial; nao cria chaves nem faz deploy)

| Evaluator | Arquivo | Gate |
| --- | --- | --- |
| Agent behavior (deterministico) | eval/agent_eval/agent_behavior_eval.py | PR (casos com gate=PR) |

Cobre: matriz de intencao, self-sufficient-only, degustacao=1-condicao, gate de formulario
completo, sigilo de fontes, LGPD (sem telefones), anti-fatiamento, cobertura/fallback,
bairro inexistente, prompt injection, jailbreak de preco, off-topic.
