# Design — Top3 candidatos por viabilidade (geo + payback MRLR)

**Data:** 2026-08-04  
**Âmbito:** Pipeline A0–A9 — bloco Top 3 do relatório (A1 geo + A4 mid + A6 rank)  
**Humano:** Marcelo  

---

## Problema

A1 entrega candidatos com score de localização (GeoScout / ancoragem). A4 entrega **uma** viabilidade financeira (payback/ROI). No relatório, Top 3 e § financeiro ficam **desconectados**: o leitor vê pontos “bons no mapa” sem payback amarrado, e ROI “solto” sem vínculo ao endereço.

Output raso atual (`top_3_candidatos` / MD só com score geo) **não** comunica decisão de ponto.

## Decisões (brainstorm)

| # | Escolha |
|---|---------|
| Ranking | **C** — um bloco só: Top 3 reordenado por viabilidade (geo + payback) |
| Custo | **A** — 1× A4 completo; por ponto só MRLR + payback derivado |
| Peso | **B** — `score_composto = 0.35 × score_geo_norm + 0.65 × score_payback_norm` |
| Aluguel | **Só MRLR** (`aluguel_deterministico`) — **nunca** `price_raw` / listing scrapado |
| Output raso | **Deprecar** Top3 sem payback/composto no estruturado + MD |

## Fora de escopo

- Rodar A4 × 3 (macro completa por candidato).
- Mudar fórmula MRLR / Tier 0.
- Reordenar A1 `candidatos_geoscout_pronto` (lista bruta interna permanece).
- Front redesign além de consumir campos novos se já espelha `top_3_candidatos`.

## Architecture

```
A1 → candidatos_geoscout_pronto (listing SearchAPI filtrado + score distância + MRLR)
A4 → analise_financeira_pronto (1× mid: CAPEX, receita, custos, payback oficial modelo)
A6 precompute:
  para cada candidato candidato a TopN:
    aluguel = MRLR(area do ponto, cidade, bairro)
    payback_est = f(A4 mid com aluguel substituído)
    score_composto = 0.35×geo_norm + 0.65×payback_norm
  ordena por score_composto → top_3_candidatos (enriched only)
  MD ## Top 3 = único bloco (geo + aluguel MRLR + payback_est + composto)
§ financeiro A4 = modelo oficial 3 cenários (abaixo), com nota de vínculo
```

**Onde:** Approach 1 — lógica no A6 (ao montar `top_3_candidatos` / `_renderizar_md_top3_candidatos`). A1/A4 wiring intactos.

## Fórmulas (determinísticas)

### Inputs por candidato `c`

- `area_m2` = `c.area_m2` / `area_estimada_m2` se > 0; senão área usada na A4 (mesmo preset).
- `score_geoscout` ∈ [0, 10] (ou 0 se ausente).
- A4 mid snapshot: `investimento_total`, receita/custos mid **exceto** linha aluguel (e condomínio %-aluguel se A4 amarra assim).

### Aluguel

```text
mrlr = aluguel_deterministico(area_m2=area, cidade=..., bairro=...)
aluguel_mensal = mrlr["aluguel_total"]  # só se status=ok
PROIBIDO: price_raw, listing SearchAPI, mediana portal no ranking
```

### Payback estimado

Recalcular lucro mensal mid com `aluguel_mensal` MRLR do ponto (mesma regra de OPEX da A4 para condomínio/IPTU relativos ao aluguel, se existirem no snapshot).

```text
payback_est_meses = investimento_total / lucro_mensal   se lucro > 0
                  = 999                                  senão
```

Rotular sempre `payback_est` — **não** substitui payback oficial da tabela A4 3 cenários.

### Normalização e composto

```text
score_geo_norm = clamp(score_geoscout / 10, 0, 1)

score_payback_norm:
  payback_est <= 12  → 1.0
  payback_est >= 48  → 0.0
  12 < x < 48        → linear (48 - x) / (48 - 12)
  999 / inválido     → 0.0

score_composto = 0.35 * score_geo_norm + 0.65 * score_payback_norm
```

Desempate: maior `score_geoscout`; depois ordem estável por endereço.

### Fallback

- A4 mid ausente / MRLR falha no ponto: candidato entra com `payback_est=null`, `score_payback_norm=0`, ou **fora do rank composto** — preferir: rank só geo + `aviso: viabilidade indisponível` no bloco (não inventar ROI).
- Se **nenhum** ponto tem MRLR ok: Top3 geo + banner único “ranking só localização”.

## Deprecação output raso

| Artefato | Ação |
|----------|------|
| A1 `candidatos_geoscout(_pronto)` | Listing SearchAPI filtrado + MRLR; macro POI continua morta |
| `top_3_candidatos` no output A6 | **Só** enriched: exige campos abaixo quando A4+MRLR ok |
| MD `## Top 3 Candidatos` | **Só** bloco viabilidade; proibido tabela só-score |
| Schema / front | Tratar Top3 sem `score_composto` como legado |

### Campos obrigatórios (enriched)

Por item em `top_3_candidatos`:

- existentes: nome, endereço, score_geoscout, score_ancoragem, area, …
- novos: `aluguel_mrlr_mensal`, `aluguel_fonte`=`MRLR`, `payback_est_meses`, `score_geo_norm`, `score_payback_norm`, `score_composto`, `carimbo_aluguel` (valor · base · fonte · janela/área)

## MD (um bloco)

Por `#i`:

- Score composto + breakdown (35% geo / 65% payback)
- Endereço, área, score GeoScout / ancoragem
- Aluguel MRLR + carimbo
- Payback estimado (meses) + nota “derivado A4 mid + MRLR ponto”
- Polos / próximo passo (como hoje)

Rodapé do bloco: § financeiro abaixo = cenários oficiais A4.

## Files

| Path | Mudança |
|------|---------|
| `tools/candidato_viabilidade_rank.py` (novo) | pure fns: payback_est, norms, rank, enrich list |
| `agents/a6_report_consolidator.py` | usar rank no lugar de `_rank_candidatos_for_top3` raso; MD enriched |
| `docs/arquitetura/PIPELINE_AGENTES.md` | A1/A6: Top3 = ranking composto; MRLR |
| `tests/tools/test_candidato_viabilidade_rank.py` | TDD fórmulas + “nunca price_raw” |

## Testing

1. Unit: `score_payback_norm` nos limiares 12/48/999.  
2. Unit: composto 0.35/0.65 com fixtures.  
3. Unit: enrich lista — candidato com `price_raw` alto **não** altera aluguel (só MRLR mock).  
4. Unit: ordenação — payback melhor sobe mesmo com geo um pouco menor.  
5. A6: MD Top3 contém `payback_est` / `MRLR` quando A4 mock presente.

## Aceite

- [ ] Relatório: um único Top3 com geo + aluguel MRLR + payback_est + score_composto  
- [ ] Nenhum Top3 “só score” quando A4 mid ok  
- [ ] `price_raw` não entra na conta  
- [ ] A4 3 cenários intactos; nota de vínculo presente  
- [ ] Testes unitários verdes  

## Relação com regras canônicas

- Aluguel viabilidade = MRLR Tier 0 (`.agent/rules/conferencia-fontes-pipeline.md`)  
- Número = tool; LLM A6 não inventa payback do Top3 — precompute determinístico  
- Carimbo valor · base · fonte · janela em aluguel exibido  
