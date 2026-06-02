# Golden Dataset — GymSite Intelligence

Casos extraídos do Supabase (`relatorios` + `relatorio_inputs` + `relatorio_outputs`).

```powershell
python scripts/extract_golden_case.py <uuid>
python scripts/list_golden_candidates.py
python scripts/query_cnpj_cno.py --cidade Niterói --uf RJ --bairros Itaipu,Piratininga,Camboinhas
```

Cada pasta contém `input.json`, `expected_output.json`, `full_report.json` e `notes.md` (curadoria manual).

## Status (5 casos iniciais)

| # | Case ID | Veredito | Score | Benchmark | Aprovado |
|---|---------|----------|-------|-----------|----------|
| 1 | `anapolis_anapolis_city_20260529` | APROVADO COM RESSALVAS | 6.65 | ✅ 5/5 | ✅ |
| 2 | `fortaleza_parangaba_20260528` | APROVADO COM RESSALVAS | 6.99 | ✅ 5/5 | ✅ |
| 3 | `fortaleza_aldeota_20260601` | APROVADO | 9.0 | ⏳ 3/5 | ⏳ parcial |
| 4 | `niteroi_camboinhas_20260513` | INVESTIGAR MAIS | 4.99 | ⏳ 1/5 | ⏳ curado |
| 5 | `curitiba_batel_20260512` | APROVADO COM RESSALVAS | 6.0 | ⏳ 2/5 | ⏳ curado |

## Regras de eval (derivadas da curadoria)

| Regra | Definição |
|-------|-----------|
| **Score tolerance** | ±0,5 pontos absolutos (`tolerance_fields.score_top1_candidato`) — nunca % |
| **Ticket estrutural** | Menor recorrente com musculação+cardio na unidade; ignorar promo 1º mês |
| **CNPJ ≠ concorrentes** | `novos_cnpj_fitness_90d` (município) ≠ `total_concorrentes_analisados` (raio Maps) |
| **Mid Market** | Faixa ~R$ 129,90–149,90 (rede + modalidades) — ref. Parangaba |
| **Low Cost** | Faixa ~R$ 99,90–119,90 — ref. Anápolis |
| **Premium** | Acima de ~R$ 159,90 + club/full-service — ref. Aldeota |
| **Saturação vs score** | `MEDIO` + `score_concorrencia` baixo é tensão conhecida; não reprovar só por isso |
| **Referência municipal** | Unidade fora do raio = contexto de preço, não concorrente georreferenciado |
| **Campo vazio** | `nivel_saturacao` ou concorrentes=0 exige exceção ou fix antes de eval estrito |

## Próximo passo

```powershell
python eval/run_eval.py                    # CNO + futuros evaluators
python eval/run_eval.py --case fortaleza_parangaba_20260528
```

### Validação CNO (`cno_validation` em `expected_output.json`)

| Caso | CNO | Foco |
|------|-----|------|
| Parangaba | ✅ required | 4 obras município, 0 no bairro, Selfit encerrada 1.829 m² |
| Aldeota | ✅ required | Max Forma 4.583 m² em curso no bairro |
| Camboinhas | ⏸ optional | 0 fitness Niterói (audit manual) |
| Batel / Anápolis | pendente | extrair após re-run com CNO |

Evaluator: `eval/evaluators/cno_consistency_eval.py`
