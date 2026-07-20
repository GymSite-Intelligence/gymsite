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

Caso Maps (`buscar_imoveis_texto`) = **incidente** sob conformidade Fontes/Tools → já em `auditoria-tools` **Closed** (Retest ledger `699371c7` / `ed36ed08`).

## Caso — wall-clock 30 min / drift API↔worker (jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Closed** (A0 PASS · relatório `done` · A3a ainda NC latência · UX etapa paralelo documentada) |
| Tipo | Por incidente · domínio **Deploy** (+ Tools latência A3a) |
| Amostra baseline | `ed36ed08…` Cocó · `failed` 2151s · wall 1800 |
| Retest | `6bb90ff7-74e4-4f12-aff4-9950bbc7aa90` · **`done`** · wall **2331s** (teto worker 3600) |
| Critério | P-000 §7 worker env+imagem; SPEC_market_bundle_v2 |
| 5 Whys | [`tools/pipeline_wall_timeout_5whys.mmd`](../../tools/pipeline_wall_timeout_5whys.mmd) |
| SPEC | [`agents/specs/SPEC_market_bundle_v2.md`](../../agents/specs/SPEC_market_bundle_v2.md) · [`.mmd`](../../agents/specs/SPEC_market_bundle_v2.mmd) |

### Evidence (etapas `ed36ed08`)

| Agente | duracao_s | Nota |
|---|---:|---|
| ContextBuilder (A0) | 766 | worker sem `A0_CONTEXT_SOURCE=ckan_bundle` (API tem) |
| GeoScout (A1) | 5,5 | OK |
| CompetitorSearch (A3a) | 834 | enrich seq Playwright + Places |
| ReportConsolidator (A6) | 478 | LLM |
| PositioningStrategist (A9) | — | cortado pelo teto |

Mensagem erro: `Pipeline excedeu o tempo máximo (30 min)` → processo leu **1800**, não 3600.

| Serviço | `PIPELINE_MAX_WALL_SEC` | `A0_CONTEXT_SOURCE` | `A0_RESEARCH_PROVIDER` |
|---|---|---|---|
| `gymsite-api` | **3600** | `ckan_bundle` | `kimi` |
| `gymsite-worker` | **ausente → default 1800** | ausente → `auto` | ausente |

Maps Retest (mesmo run): `buscar_imoveis_texto` só `searchapi_google_maps` — **PASS** (fora deste caso).

### Findings

| Sev | Gap | Evidência |
|---|---|---|
| **Crítico** | Pipeline roda no **worker**; teto/config A0 só na **API** | gcloud describe + mensagem 30 min vs API 3600 |
| **Alto** | A3a enrich sequencial ≈14 min (Playwright + details) | código `analisar_concorrentes_a3a_completo` + 834s |
| **Médio** | Docs/`MARKET_ATLAS` falam “`.env` da API” — omitem worker | doc vs runtime Redis |
| **Baixo** | OTEL Token Context no abort | ruído pós-timeout |

### Corrective (shipped jul/2026)

1. **Ops:** worker `00076` — `PIPELINE_MAX_WALL_SEC=3600`, `A0_CONTEXT_SOURCE=ckan_bundle`, `A0_RESEARCH_PROVIDER=kimi`, `KIMI_RESEARCH_TIMEOUT_SEC=90`, `MARKET_BUNDLE_SUPABASE=1`, `COMPETITOR_PLAYWRIGHT_ENRICH=0` (+ mesma imagem API).
2. **Código:** A3a Playwright gated; `_fetch_reviews_bundle` → `search_raw` + `cache_reviews`; SPEC_market_bundle_v2.
3. **Bundle:** Cocó upsert Supabase (`renda_media=2095.2`).

### Retest final (`6bb90ff7…`) — `done`

| Agente | Antes (`ed36`) | Retest | Verdict |
|---|---:|---:|---|
| ContextBuilder (A0) | 766 | **29,6** | **PASS** (bundle + `ckan_bundle` worker) |
| GeoScout | 5,5 | 4,6 | OK |
| FinancialEstimator | 2,5 | 1,7 | OK |
| CompetitorSearch (A3a) | 834 | **1844** | **FAIL latência** (Playwright off ≠ suficiente; Places/reviews seq ainda long-pole) |
| ReportConsolidator | 478 | 369 | melhor |
| PositioningStrategist | cortado | 1,7 | OK |
| Wall | fail 1800 | **2331 done** | passa só com teto 3600 |

### Achado UX — `etapa_atual` mentiroso no paralelo

FinancialEstimator **acabou** em 03:02:26 (`etapas_concluidas`), mas `etapa_atual` ficou `FinancialEstimator` ~30 min. Causa: bloco paralelo A2‖A3a‖A4 — último `progress_before` vence; A4 curto sobrescreve label enquanto **CompetitorSearch** ainda roda. Stepper ≠ long-pole real. Filho: Act-on `pipeline_progress` (não sobrescrever se outra etapa paralela ainda em `_inicio_etapa`, ou priorizar A3a).

**Caso wall-clock A0/deploy = Closed.** NC A3a latência continua em [`auditoria-tools`](auditoria-tools.md) (filho aberto).

---

## Caso — Fontes / pipeline · amostra `3862ba63` (jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Corrective** (Approver: Marcelo · 2026-07-19) |
| Tipo | Interna periódica · domínio **Fontes / pipeline** |
| Amostra | `3862ba63-5ba5-49a4-8184-de0a5c698125` · Cocó/Fortaleza · `done` · wall ~526s · veredito REPROVADO |
| Critérios | [`conferencia-fontes-pipeline.md`](conferencia-fontes-pipeline.md) · [`pipeline-fontes-deterministicas.md`](pipeline-fontes-deterministicas.md) |
| Evidência | ledger `gymsite.relatorio_api_calls` · `relatorio_outputs` · `competidores` · logs A3a enrich (pico) |

### Evidence — ledger `api_sku`

| api_sku | calls | tool_name (agregado) | Nota vs política |
|---:|---:|---|---|
| `searchapi_google_maps` | 20 | `buscar_imoveis_texto` 11 · `descobrir_concorrentes_bairro` 8 · `buscar_pontos_comerciais` 1 | Listing **PASS** (só SearchAPI) |
| `places_search_new` | 7 | **só** `descobrir_concorrentes_bairro` | Fallback Places quando SearchAPI vazio — **dual SKU** no mesmo agente |
| `searchapi_google_maps_place` | 6 | `searchapi_maps_place` | Place/reviews/pico path SearchAPI |
| `searchapi_google_light` | 3 | `planos_precos` | Planos via light (site-first não persistiu) |
| `geocoding` | 1 | `geocode_google` | OK |

- Coluna `motivo_fallback` **ausente** no schema ledger (dívida doc/telemetria).
- Sem SKU Playwright/scrape no ledger deste run.
- Sem SKU `rent_sqm` / grounding de aluguel.

### Evidence — aluguel / demografia / CNPJ

| Dado | Valor · base · fonte (amostra) | Verdict |
|---|---|---|
| Aluguel OPEX | `aluguel_mensal=25440` · `fonte_aluguel=MRLR IBAPE-GO (R²=0,8633) — espelhos municipio_pib + renda_bairro` · `queries_aluguel_com_dados=0` | **PASS** Tier 0 MRLR |
| Demografia pop | `60165` · `censo_n_setores=105` · `populacao_fonte=IBGE Censo 2022…` | **PASS** (janela implícita 2022 via renda) |
| Renda | `4952.75` · `renda_fonte=IBGE… Responsável` · `renda_data_referencia=2022` | **PASS** (proxy responsável — rótulo ok) |
| CNPJ entrantes | `fonte=RFB CNPJ Aberto` · `status=ok` · Places validate **off** | **PASS** |
| CNO | `status=nao_configurado` · `CNO_DATA_DIR ausente` | **Médio** (falha honesta) |
| Listing→aluguel | candidatos=0; listing ledger só SearchAPI; aluguel ≠ portal | **PASS** (não alimentou OPEX) |

### Evidence — A3a persistido vs runtime

| Sinal | Runtime (log enrich) | Persistido `competidores` (2 rows) |
|---|---|---|
| Pico | `pico` 1.5–3.7s · `playwright: 0` | `horarios_pico` / `pico_semanal` = **null** |
| Planos | `planos` 10–20s · `planos=False` | `planos_precos` = **null** |
| Reviews | SearchAPI path | presentes · `categoria_dor` card (substring) |

### Findings

| Sev | Gap | Evidência | Critério |
|---|---|---|---|
| **Alto** | Dual SKU concorrentes: SearchAPI **8** + Places **7** no mesmo tool | ledger `descobrir_concorrentes_bairro` | SearchAPI primário; Places só fallback — taxa de fallback ~47% das calls Places vs SearchAPI no agente |
| **Alto** | Pico coletado no enrich **não chega** ao `competidores` | log `[A3a enrich timing]` vs colunas null | Número/fonte no relatório = tool; dado some na persistência |
| **Médio** | Planos: `google_light` rodou (3) mas `planos_precos` null · site-first `planos=False` | ledger + competidores | Oferta site/IG no caminho crítico |
| **Médio** | Ledger sem `motivo_fallback` | schema `relatorio_api_calls` | Telemetria de fallback Places opaca |
| **Médio** | CNO `nao_configurado` no golden Cocó | `obras_cno_em_curso` | CNPJ/CNO determinístico incompleto em prod |
| **Baixo** | `perfil_sexo_publico` granularidade **município** (647k) ao lado de pop bairro 60k | `demografia_bairro` | Risco de leitura cruzada sem carimbo de escala no PDF/UI |
| **Baixo** | `censo_n_setores=105` vs `perfil_idade_sexo_bairro.n_setores=183` | mesmo JSON | Duas bases de setor sem rótulo unificado |

### PASS (domínio Fontes)

1. Aluguel viabilidade = **MRLR** (não listing, não SearchAPI rent, não A7).
2. Listing (`buscar_imoveis_texto`) = **só** `searchapi_google_maps` (Retest alinhado ao caso Maps Closed).
3. Demografia / CNPJ com fonte RFB/IBGE explícita.
4. Pico path runtime sem Playwright (NC latência A3a parcial fechada neste ângulo).

### Corrective (proposto — não executado)

1. Instrumentar `motivo_fallback` (ou log estruturado) em `_places_textsearch` quando SearchAPI→Places; investigar por que 7 queries Cocó caíram no Places.
2. Act-on persistência A3a: `horarios_pico` / `planos_precos` do enrich → `competidores` (e PDF).
3. Site-first planos: por que `website` presente e `planos=False` (Smart Fit ausente neste persist; Parque/VS sem preço público).
4. Ops: garantir `CNO_DATA_DIR` no worker ou selo ORANGE explícito no PDF.

### Retest

Pendente pós-Corrective — mesma amostra Cocó ou novo UUID; checklist: Places calls≈0 com SearchAPI saudável · pico/planos non-null em `competidores` · `fonte_aluguel` continua MRLR.
