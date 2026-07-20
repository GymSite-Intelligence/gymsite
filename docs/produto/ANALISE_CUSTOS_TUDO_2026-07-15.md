# Análise — `custos_tudo_2026-07-15` (export real `/custos`)

**Arquivo:** `custos_tudo_2026-07-15_e909.csv`  
**Data da análise:** 2026-07-15  
**Amostra:** 90 linhas · 78 `done` · 12 `failed` · **84 com custo** · Σ **R$ 499,94**

---

## 1. O que este arquivo tem (e o que não tem)

| Tem | Não tem |
|-----|---------|
| Data, Cidade, Bairro, Status, Tempo(s), Tokens, Custo(BRL) | Linhas por **chamada** (`tool_name`, `api_sku`, `num_calls`) |
| 1 linha = **1 relatório** | **Score** (`score_bairro`, `score_top1`) |

Consequência:  
- Colunas de **responsável + tool** neste entrega são o **pacote esperado** do pipeline (A3a enrich + LLM), não o log real por call.  
- Divergência **score × custo** **não é mensurável aqui** — o export não traz score. O que dá para provar com força é **tokens × custo** no mesmo bairro.

Arquivos gerados:
- `docs/produto/assets/custo-granular/custos_tudo_2026-07-15_enriquecido.csv`
- `docs/produto/assets/custo-granular/divergencia_mesma_localidade.csv`
- Catálogo agente→tool: `catalogo_chamadas_agente_tool.csv` (já na branch)

---

## 2. Números gerais

| Métrica | Valor |
|---------|-------|
| Custo mediana | **R$ 4,41** |
| Custo média | R$ 5,95 |
| Min / Max | R$ 0,96 / **R$ 17,49** |
| P75 / P90 | R$ 8,58 / R$ 12,06 |
| Correlação **tokens × custo** | **0,82** (forte) |
| Correlação tempo × custo | 0,62 |

**Leitura:** o custo do relatório está **dominado por tokens LLM**, não pelo pacote SearchAPI (~R$ 0,3–0,5). SearchAPI explica pouco do range R$ 1–17; tokens (46k → 2,6M) explicam a ordem de grandeza.

---

## 3. Mesma localidade — divergência de custo (prova)

### 3.1 Fortaleza / Cocó (n=36) — caso principal

| | Jun/2026 (n=22) | Jul/2026 (n=14) |
|--|-----------------|-----------------|
| Custo mediana | **R$ 5,90** | **R$ 2,71** (−54%) |
| Tokens mediana | **~1,04 M** | **~73 k** (−93%) |
| Faixa custo | R$ 2,22–17,49 | R$ 1,60–6,17 |
| Razão max/min (todos Cocó) | | **×10,9** (R$ 1,60 → R$ 17,49) |

CV do custo no Cocó: **71%** — mesma praça, runs muito diferentes.

**Por quê (hipóteses alinhadas aos dados):**

1. **Tokens LLM caíram uma ordem de magnitude** de junho→julho (modelo/prompt/cache/pipeline mais enxuto). Isso sozinho explica a queda de mediana.  
2. **Runs caros de junho** (>R$ 10, >1,5M tokens) = pipeline “gordo” (retries, Pro, contextos enormes) — não “o Cocó ficou pior”.  
3. **Outlier 15/jul R$ 6,17** com só **53k tokens** mas **3427 s** — custo alto relativo aos tokens: APIs long-pole / timeout / mix SearchAPI+Places, ou telemetria incompleta. Flag: `tokens_baixos_custo_alto`.  
4. SearchAPI `MAX_ENRIQUECIMENTO=6` adiciona ruído de **centavos a poucos reais**, insuficiente para explicar R$ 17.

### 3.2 Outras praças com n≥2

| Localidade | n | Min–Max (R$) | Razão | Hipótese |
|------------|---|--------------|-------|----------|
| Fortaleza/Aldeota | 5 | 1,29–17,16 | **×13,3** | Tokens 205k→2,2M |
| Fortaleza/Meireles | 5 | 3,43–7,53 | ×2,2 | Tokens sobem com custo |
| Fortaleza/Parangaba | 2 | 8,28–14,03 | ×1,7 | Tokens altos (2,3M–2,9M) |
| Niterói/Itaipu | 4 | 2,53–4,79 | ×1,9 | Tokens 482k→1,0M |
| JP/Bessa, Cabo Branco, Hortolândia | 2–3 | estável (±20%) | ×1,0–1,2 | Runs parecidos |
| SP/Vila Formosa | 3 | 3,50–4,04 | ×1,2 | Tokens já baixos (~70k) |

---

## 4. “Muitas chamadas da mesma tool”

Neste CSV **não aparecem** as tools — só o total. O padrão N× no código continua válido:

- 1× Maps descobrir + até 6× reviews + 6× pico + 6× IG (`MAX_ENRIQUECIMENTO`)
- Isso **não** é o vilão do R$ 17 no Cocó; o vilão é **tokens LLM**

Para ver “muitas calls” de fato: exportar `relatorio_api_calls` (tool_name, num_calls, custo_brl) por `relatorio_id`.

---

## 5. Score × custo — status

| Pergunta | Resposta com este arquivo |
|----------|---------------------------|
| Por que score e custo divergem no mesmo bairro? | **Não mensurável** — score não está no export |
| Proxy forte disponível | Tokens ≈ custo (r=0,82); qualidade de mercado (score) é ortogonal |
| O que fazer | Estender `exportarCSV` em `CustosPage.tsx` com `score_bairro`, `score_top1` + drill-down de API calls |

Até lá: **não usar custo como proxy de “bairro bom/ruim”**.

---

## 6. Colunas de responsável / tool (no CSV enriquecido)

Em `custos_tudo_2026-07-15_enriquecido.csv`:

| Coluna | Conteúdo |
|--------|----------|
| `responsavel_pacote` | pipeline A0–A9 (custo dominante = LLM) |
| `tools_chamadas_esperadas` | A3a maps/reviews/pico/ig + A1 geocode/listings + LLM |
| `custo_vs_mediana_local` | razão vs mediana da mesma cidade/bairro |
| `faixa_tokens` | baixo / médio / alto / extremo |
| `flag_outlier` | ≥2× mediana, tokens baixos+custo alto, tempo muito alto |
| `score_*` | vazio (ausente na fonte) |

Detalhe SKU: `catalogo_chamadas_agente_tool.csv`.

---

## 7. Plano de ação (atualizado com evidência)

### P0 — Visibilidade (desbloqueia o resto)

1. Alterar `exportarCSV` / API de custos para incluir:  
   `score_bairro`, `score_top1`, e child export `relatorio_id,tool_name,api_sku,num_calls,custo_brl,cache_hit`  
2. Normalizar bairro no export (`Cocó` vs `Coco`) para agregação correta

### P0 — Custo LLM (maior retorno — já parcialmente visto em jul)

3. Confirmar em prod: A4 Flash, LangCache A9, thinking budget (ver `AUDITORIA_CUSTO_LLM_PIPELINE.md`)  
4. Alertar runs com tokens > 1,5M ou custo > 2× mediana da localidade  
5. Investigar outlier **2026-07-15 Cocó R$ 6,17 / 53k tok / 3427s** (tempo absurdo vs tokens baixos)

### P1 — SearchAPI N× (economia marginal vs LLM)

6. `MAX_ENRIQUECIMENTO` = 4 em re-run / degustação  
7. Logar `cache_hit` por place_id (reviews/pico/IG)

### P1 — Produto / score

8. Scatter score × custo por localidade (só após P0.1)  
9. Copy na UI: “custo do relatório ≠ nota do bairro”

### Aceite

- [ ] Export com score + linhas por tool  
- [ ] Mediana Cocó permanece ≤ R$ 3 em re-runs (regredir se voltar a 1M+ tokens)  
- [ ] Alerta automático custo ≥ 2× mediana local  
- [ ] Caso 15/jul Cocó diagnosticado (causa do tempo/custo)

---

## 8. Resumo executivo

No Cocó, o mesmo bairro custou de **R$ 1,60 a R$ 17,49**. Em julho o custo mediano caiu **54%** porque os **tokens caíram ~93%** — não porque o mercado mudou. Sem coluna de score neste CSV, a “divergência score×custo” fica como **hipótese de produto** (métricas ortogonais); a divergência **custo×custo** no mesmo lugar está **provada** e é quase toda **LLM**.
