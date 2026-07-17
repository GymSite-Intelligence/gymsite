# Auditoria de Tools — Processo Canônico

> Adotado jul/2026. Governança de **não conformidade em `tools/`** (custo API, fonte errada, fallback abusivo, tool mal composta).
> **Pai:** [`auditoria-conformidade.md`](auditoria-conformidade.md) (ciclo global). Este arquivo = trilho **Tools**.
> Complementa: [`pipeline-fontes-deterministicas.md`](pipeline-fontes-deterministicas.md) · [`conferencia-fontes-pipeline.md`](conferencia-fontes-pipeline.md) · P-000.
> Diagrama: [`auditoria-tools.mmd`](auditoria-tools.mmd).

## Quando abre uma auditoria

- Ledger (`relatorio_api_calls`) com SKU dual / custo anomalamente alto
- Tool viola SearchAPI-primário ou misturam jobs (POI ≠ listing ≠ aluguel)
- Mesmo sintoma em ≥2 relatórios
- Fix superficial falhou (ex.: “SearchAPI falhou” sem 5 Whys)
- Feedback produto: relatório lento / número sem carimbo / Places no caminho crítico

## Papéis

| Papel | Quem | Faz |
|---|---|---|
| **Author** | quem achou o sintoma (agente ou humano) | Draft: evidência + 5 Whys + `.mmd` |
| **Reviewer** | dono metodologia / pipeline | confere causa raiz vs regras de fonte; `request changes` ou avança |
| **Approver** | dono produto ou tech lead | approve → Act-on, ou reject |
| **Reviewer Lead** | default Marcelo se Reviewer não assigned | SLA Submitted |

## Estados e SLA

| Estado | SLA | Notificar se pending |
|---|---|---|
| **Draft** | 2 dias | Author se >1 dia |
| **Submitted** | 1 dia | Reviewer Lead se >1 dia |
| **Reviewed** | 3 dias | Approver se >2 dias |
| **Approved** | imediato | Author — pode Act-on / merge / Cloud Run |
| **Rejected** | imediato | Author — fecha com motivo |

Transições: ver `auditoria-tools.mmd`.

## Artefatos obrigatórios por estado

### Draft (Author)

1. Sintoma mensurável (ex.: relatório UUID + agregação `tool_name`/`api_sku`)
2. **5 Porquês** até causa raiz (não parar em “API falhou”)
3. Diagrama `.mmd` ao lado da tool ou em `docs/metodologia/`
4. Hipótese: tool mal composta? engine errado? fallback trata `[]` = erro?

### Submitted

- Pacote acima completo; Author marca pronto pra Reviewer
- Checklist pré-leitura: `pipeline-fontes-deterministicas` + `conferencia-fontes-pipeline`

### Reviewed (Reviewer)

- Concorda / discorda da causa raiz
- Mapeia ações: Act-on mínimo vs redesign
- Ou **request changes** → volta Draft

### Approved (Approver)

- Act-on: código + testes + (se `tools/`) Cloud Run API+worker
- Atualizar PIPELINE_AGENTES / data_lineage se fonte mudar
- Critério de Done: ledger ou teste prova que o sintoma sumiu

### Rejected

- Motivo escrito; opcional ticket “não agora”
- Não merge de “fix cosmético” que não ataca a raiz

## Encaixe com regras já existentes

```
sintoma (custo/fonte/latência)
    → Auditoria Tools (este processo)
        → 5 Whys + .mmd
        → Review vs conferencia-fontes / SearchAPI-primário
        → Approved = P-000 Act-on (código mínimo + teste + deploy)
```

Auditoria **não** substitui checklist pré-merge do pipeline — **precede** quando o merge já passou e produção / ledger prova regressão, ou quando o Author quer mudar a tool antes do PR.

## Caso — `buscar_imoveis_texto` (jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Closed** (Corrective + Retest operacional ledger) |
| Sintoma | Cocó `c908…` · dual SKU SearchAPI+Places · ~R$2,53 em `buscar_imoveis_texto` |
| 5 Whys | [`tools/maps_tools_5whys_imoveis.mmd`](../../tools/maps_tools_5whys_imoveis.mmd) |
| Causa raiz | Tool misturou polo/POI + listing; Maps Local vazio ≠ outage; fallback Places em `[]` |
| Act-on feito | (1) Places só se SearchAPI `None` (2) A1 removeu queries listing — cascata já em `_fetch_listings_como_candidatos` (3) teste `empty_nao_fallback_places` |
| Done prod | commit `8095337` · API `00477` · worker `00074` · `GIT_SHA=8095337` · `stale:false` |
| Retest | `699371c7…` + `ed36ed08…` · `buscar_imoveis_texto` = só `searchapi_google_maps` (11·R$0,24) · **sem** `places_search_new` · `buscar_pontos_comerciais` idem · (relatórios failed por wall/restart — não Maps) |

## Caso — A3a enrich latência (filho · jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Act-on parcial (jul/16)** — pico→SB + MAX=3 + skip attributes; dual-SKU Maps ainda aberto |
| Sintoma | Cocó `6bb90ff7` · A3a **1844s** (pior que 834) · wall 2331s done só c/ teto 3600 |
| 5 Whys | [`tools/a3a_competitor_search_5whys.mmd`](../../tools/a3a_competitor_search_5whys.mmd) |
| SPEC | [`agents/specs/SPEC_a3a_store_v2.md`](../../agents/specs/SPEC_a3a_store_v2.md) · [`.mmd`](../../agents/specs/SPEC_a3a_store_v2.mmd) |
| Causa raiz | Loop seq ×6: Places details + pico (FS ephemeral CR) + reviews/planos frios; PW não era único vilão |
| Ledger | `obter_atributos_place`×6 · `places_search_new`×7 · reviews/pico/planos×6 |
| Act-on | (1)~~pico → Supabase TTL~~ **done** (2)~~skip details se contato~~ **done** (3)~~`MAX_ENRIQUECIMENTO=3`~~ **done** (4) dedupe reviews baixa_nota (5) Maps empty≠Places em descobrir |
| Pai | conformidade A0/wall **Closed** |

## Caso — A2 DemoAnalyst (filho · jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Closed** (não long-pole) |
| Sintoma | n/a · `6bb90ff7` DemoAnalyst **7,8s** |
| SPEC | [`SPEC_a2_store_v2.md`](../../agents/specs/SPEC_a2_store_v2.md) |
| Forma | BaseAgent · macro IBGE · zero LLM |
| Act-on | nenhum wall · dívida renda CKAN 2010 vs IBGE 2022 (doc only) |

## Caso — A4 FinancialEstimator + A4bak (filho · jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Closed** (não long-pole) |
| Sintoma | n/a · `6bb90ff7` FinancialEstimator **1,7s** |
| SPEC | [`SPEC_a4_store_v2.md`](../../agents/specs/SPEC_a4_store_v2.md) |
| Forma prod | BaseAgent · MRLR Tier0 · justificativa template |
| A4bak | LLM Pro eco-macro · **fora do grafo** · não reintroduzir |
| Act-on | monitorar miss MRLR → Tier1/2 |

## Caso — A6 ReportConsolidator latência (filho · jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Submitted** (aguarda Approver · após A3a) |
| Sintoma | Cocó `6bb90ff7` · A6 **369s** (#2 wall) |
| 5 Whys | [`tools/a6_report_consolidator_5whys.mmd`](../../tools/a6_report_consolidator_5whys.mmd) |
| SPEC | [`SPEC_a6_store_v2.md`](../../agents/specs/SPEC_a6_store_v2.md) |
| Causa raiz | Flash+thinking + precompute `bairros_alternativos` Places live ×N sem cache bairro_alt |
| Act-on proposto | (1) cache Places `(bairro_alt,cidade)` (2) fallback CNPJ/parque antes Maps (3) thinking ↓ medir golden |
| Prioridade | **depois** Act-on A3a |
