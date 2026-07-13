# SPEC — Obra (árvore adaptação × bruta) + CUB estadual + licenças municipais

> Criada 2026-07-13. Gap analysis das propostas de produto frente ao código e ao
> [PRD Agentes de Descoberta](../docs/produto/PRD_AGENTES_DESCOBERTA_CURADORIA_LEIS.md).
> **Status:** parcialmente codado (SINAPI + legal_fees piloto); árvore de decisão, CUB e
> wiring A4↔município **não existem**.

## 0. Escopo vs PRD de descoberta

| Camada | O quê | Onde vive | Este SPEC |
|---|---|---|---|
| **Qualitativo (lei/norma)** | COE, NBR, CREF, checklist retrofit×zero | Vertex RAG (`gymsite-obra-app`, `gymsite-regulatorio-app`) + agentes agendados do PRD | Fora — PRD cobre ingest offline |
| **Quantitativo (CAPEX)** | R$/m² obra, projeto, alvarás, frete | A4 `financial_tools` → `cenarios.*.capex_detalhado` | **Este SPEC** |

Regra P-000: todo número exibido carrega carimbo `valor · base · fonte · janela`. Obra e
alvará no relatório são **motor A4**, não narrativa LLM. Agentes de descoberta podem
**alimentar** `data/legal_fees_pilot/` via PR humano, mas não substituem o contrato numérico.

---

## 1. Proposta A — Árvore de decisão obra + CUB estadual

### 1.1 O que o usuário deveria ver

- Input explícito ou inferido: **adaptação de imóvel existente** vs **obra bruta / shell novo**.
- CAPEX de obra com linha e rótulo corretos (`obra_adaptacao` vs `obra_bruta`), não sempre
  "adaptação".
- R$/m² ancorado no **CUB estadual** (sindicatos / índice oficial por UF), com fator de
  conversão academia documentado — não só SINAPI habitacional × 0,19.

### 1.2 O que já existe (codado + implantado)

| Peça | Arquivo | Estado |
|---|---|---|
| Proxy obra **só adaptação** | `tools/sinapi_indices.py` | ✅ batch semanal (`update_capex_indices.py`), cache `metrics/cache/capex_indices.json` |
| Fator 19% sobre SINAPI m² | `FATOR_OBRA_ADAPTACAO = 0.19` | ✅ calibrado vs benchmark R$ 350/m² mid |
| CAPEX breakdown | `tools/financial_tools._calcular_capex_detalhado` | ✅ linha única `obra_adaptacao = area × R$/m²` |
| Fallback benchmark | `parametros_metodologia` `capex_obra_m2_*` | ✅ Se SINAPI ausente |
| Chat retrofit×zero | `agents_site/agent.py`, `consultor_engine.py`, RAG obra | ✅ **qualitativo** — não altera A4 |
| CUB estadual | — | ❌ zero referência no repo |
| `obra_bruta` / árvore decisão | — | ❌ |
| `tipo_obra` no state A4 | — | ❌ |

**Fonte atual de régua:** IBGE SIDRA SINAPI tabela 2296 (custo m² **habitacional**), não CUB.

**Deploy:** SINAPI no bundle batch (`build_market_bundles.py` → `capex_indices`); gate
`e2e_gate.check_b3_sinapi_bundle`. A4 resolve índices via `_resolve_capex_indices(uf)` lendo
cache SINAPI direto — **não** recebe `market_bundle` na macro `analise_financeira_a4_completo`.

### 1.3 Contrato atual (origem → consumidores)

```
sinapi_indices.capex_indices_for_uf(uf)
  → market_bundle.capex_indices (batch)
  → financial_tools._resolve_capex_indices(uf)  # também lê cache direto
  → _calcular_capex_detalhado → capex_detalhado.obra_adaptacao
  → analise_financeira.cenarios.{low,mid,premium}
  → db/supabase_writer (capex_obra_adaptacao)
  → frontend useRelatorioDetail, CenarioFinanceiroTable, ParecerPdfExport
  → pdf/adapters.py (agrupa obra+projeto+alvará em capex_obra)
  → playbook_generator (step "Executar obra civil")
```

**Campos DB:** `capex_obra_adaptacao` — nome fixo em adaptação; sem coluna `obra_bruta`.

### 1.4 Lacunas (proposta A)

1. **Árvore de decisão** — módulo determinístico (ex. `tools/obra_capex.py`):
   - Entradas: `tipo_obra` (`adaptacao` | `bruta`), `area_m2`, `modelo`, `uf`, opcional
     `imovel_existente_m2`, `necessita_reforco_estrutural` (bool, só orienta alerta).
   - Saída: `capex_obra` com `linha` (`obra_adaptacao` | `obra_bruta`), `valor`, `r_m2`,
     `carimbo` (valor · base · fonte · janela).
   - Default conservador: sem input → `adaptacao` (comportamento atual).
2. **CUB estadual** — nova fonte primária ou co-fonte com SINAPI:
   - Ingest por UF (CSV/JSON curado ou API sindicato), snapshot versionado
     (`metrics/cache/cub_estadual.json` ou `data/cub_pilot/`).
   - Dois fatores de conversão calibrados: `fator_adaptacao`, `fator_obra_bruta` (param
     banco P-008).
   - Política de fallback: CUB UF → SINAPI × fator → `parametros_metodologia`.
3. **Contrato A4** — estender `analise_financeira_a4_completo` / `calcular_viabilidade_3_cenarios`
   com `tipo_obra` e `capex_indices` opcional do bundle (hoje ignorado).
4. **Schema v3 capex_detalhado** — renomear ou duplicar linha:
   - Opção mínima: manter `obra_adaptacao` como chave legada com `tipo_obra` no metadata.
   - Opção limpa: `obra_civil` + `tipo_obra` no JSON; migration aditiva DB + PDF.

### 1.5 Critérios de aceite (proposta A)

- [ ] Com `tipo_obra=bruta`, R$/m² > adaptação no mesmo UF (fator documentado).
- [ ] Carimbo cita CUB ou SINAPI + período + UF.
- [ ] Teste: Fortaleza/CE mid 1250 m² — adaptação e bruta divergem; snapshot estável.
- [ ] `compute_bundle_stale` marca degradado se CUB+SINAPI ausentes (análogo `sinapi_fallback`).
- [ ] PIPELINE_AGENTES.md atualizado se A4 ganhar parâmetro `tipo_obra`.

---

## 2. Proposta B — Licenças/alvarás por município + projeto escalando

### 2.1 O que o usuário deveria ver

- Alvará e taxas (funcionamento, bombeiros, sanitária) **por cidade/UF**, editáveis, com faixa
  min/max e fonte municipal.
- **Projeto arquitetônico** que escala com área e/ou tipo de obra (não fixo R$ 15.000).

### 2.2 O que já existe (codado + implantado)

| Peça | Arquivo | Estado |
|---|---|---|
| JSON piloto editável | `data/legal_fees_pilot/{cidade}_{uf}.json` | ✅ Fortaleza, Curitiba (disco local; versionar com `git add -f`) |
| Loader | `tools/legal_fees_loader.py` | ✅ `load_legal_fees`, `bloco_para_bundle` |
| Bundle batch | `scripts/batch/build_market_bundles.py` | ✅ `legal_fees` no payload |
| Briefing A0 | `tools/market_bundle.bundle_to_briefing_md` | ✅ mostra faixa alvará se `disponivel` |
| Testes | `tools/test_fase_c.py`, gate `c2_curadoria` | ✅ |
| CAPEX alvará/projeto | `financial_tools._calcular_capex_detalhado` | ⚠️ **fixos** `capex_alvara_taxas` (8k) e `capex_projeto_arquitetonico` (15k) via `parametros_metodologia` |
| JSON piloto tem `projeto_arquitetonico_cau_brl` | `fortaleza_ce.json` | ❌ **não consumido** pelo A4 |

**Gap crítico:** `legal_fees` entra no bundle para contexto A0, mas **nunca** chega ao motor
financeiro. Relatório pago usa sempre benchmark Sebrae para alvará/projeto.

### 2.3 Contrato atual legal_fees

```json
{
  "cidade": "Fortaleza",
  "uf": "CE",
  "fonte": "curadoria_gymsite_fase_c",
  "data_coleta": "2026-06-03",
  "taxas": {
    "alvara_funcionamento_brl": {"min": 800, "max": 3500},
    "taxa_bombeiros_brl": {"min": 400, "max": 2000},
    "projeto_arquitetonico_cau_brl": {"min": 15000, "max": 45000},
    "vistoria_sanitaria_brl": {"min": 200, "max": 800}
  },
  "prazo_meses_tipico": {"alvara": 3, "bombeiros": 2}
}
```

**Consumidores hoje:** só `market_bundle` (briefing). **Não consumidores:** A4, PDF numérico,
playbook valores.

### 2.4 Lacunas (proposta B)

1. **Wire A4 ← legal_fees** — em `_calcular_capex_detalhado` ou helper dedicado:
   - `alvara_e_taxas` = soma taxas municipais (política: **mid** da faixa ou `max` conservador;
     documentar no carimbo).
   - Se cidade sem piloto → manter `param("capex_alvara_taxas")` + alerta em `alertas[]`.
2. **Projeto escalando** — fórmula determinística, ex.:
   - `projeto = clamp(area_m2 × r_m2_projeto(modelo), min_cau, max_cau)` com `min/max` do
     piloto municipal quando existir.
   - Parâmetros `capex_projeto_r_m2_*` em `parametros_metodologia`; piloto sobrescreve faixa.
   - Escalar com `tipo_obra`: bruta exige pacote completo (arquitetônico + complementares);
     adaptação pode usar fator < 1.
3. **Edição operacional** — manter JSON em `data/legal_fees_pilot/` (curadoria humana);
   agentes de descoberta do PRD podem **propor** atualização via PR, não escrever direto.
4. **Admin UI (futuro)** — fora do MVP; JSON + PR basta até N cidades.

### 2.5 Critérios de aceite (proposta B)

- [ ] Fortaleza: `alvara_e_taxas` ≠ default 8000; carimbo cita `legal_fees_pilot` + data_coleta.
- [ ] Cidade sem JSON: fallback 8000 + alerta "taxas municipais não curadas".
- [ ] Projeto 1250 m² mid > projeto 500 m² (mesma cidade).
- [ ] `bundle_to_briefing_md` e `capex_detalhado` usam **mesmos** números (sem divergência A0 vs A4).
- [ ] Teste integração: `build_market_bundles` + `calcular_viabilidade_3_cenarios` com `legal_fees` injetado.

---

## 3. PRD Agentes de Descoberta — relação

| Item PRD | Status repo | Ligação com este SPEC |
|---|---|---|
| Agente Descoberta Obras/Arquitetura/Regulatório | ❌ não implantado (`deployments.create` ausente) | Alimenta RAG + futuros JSON `legal_fees` |
| Diário de buracos (reativo) | ❌ só mencionado no PRD | Pré-requisito para priorizar cidades no piloto |
| `consultar_engenharia_obra` / `consultar_base_regulatoria` | ✅ deploy PR #79 | Chat qualitativo; não calcula CAPEX |
| Purge/replace docs Vertex | ✅ parcial (`SPEC_RAG_AGENTES_SITE`) | Ortogonal |

**Ordem sugerida:** (1) wire B piloto→A4 — valor imediato Fortaleza/Curitiba; (2) árvore A +
CUB; (3) PRD descoberta para escalar cidades no piloto.

---

## 4. Mapa de arquivos a tocar (implementação futura)

| Arquivo | Mudança |
|---|---|
| `tools/obra_capex.py` (novo) | Árvore + CUB/SINAPI + carimbo |
| `tools/financial_tools.py` | `_calcular_capex_detalhado` usa obra_capex + legal_fees |
| `tools/legal_fees_loader.py` | `resolver_taxas_capex(cidade, uf, area_m2, tipo_obra)` |
| `tools/sinapi_indices.py` | Coexistir com CUB; não remover até CUB cobrir 27 UFs |
| `scripts/batch/build_market_bundles.py` | Opcional: `cub_indices` block |
| `agents/a4_*.py` / `apply_patches.py` | Passar `tipo_obra`, `legal_fees` do contexto |
| `db/migrations/` | Aditivo: `capex_tipo_obra`, `capex_obra_carimbo` jsonb se necessário |
| `frontend/.../CenarioFinanceiroTable.tsx` | Label dinâmico adaptação vs bruta |
| `docs/arquitetura/PIPELINE_AGENTES.md` | § fonte obra/alvará |

---

## 5. Riscos

- **CUB ≠ SINAPI** — misturar sem rótulo quebra auditoria; sempre carimbar qual índice.
- **legal_fees ilustrativo** — JSON atual tem `notas: validar na prefeitura`; não promover a
  verdade absoluta sem revisão humana (alinha PRD).
- **Dupla fonte chat vs relatório** — EngenheiroObra fala em checklist; A4 deve bater com
  piloto quando cidade curada.
