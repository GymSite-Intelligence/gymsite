# SPEC_A2_DemoAnalyst.md

---
id: spec-a2-002
agente: DemoAnalyst
modelo_llm: determinístico sem LLM (BaseAgent Python puro)
versao: 2.0 (atualizada PONTO 8 — migração score CKAN 2010 → IPECE/IBGE 2022)
data: 2026-08-10
constitution: C2.1, C2.3, C6.1
---

## 1. Responsabilidade Única

O A2 DemoAnalyst tem escopo exclusivo de **análise demográfica determinística**: lê cidade/UF/bairro do state, chama a macro `analise_demografica_completa` (IBGE Censo 2022), gera 3 insights em Python puro e opcionalmente enriquece com perfil sexo×idade (Censo 2022/BQ) e densidade de setor censitário. Não usa LLM — é um `BaseAgent` que grava `analise_demografica` no state via `EventActions(state_delta=...)`. Em nenhuma circunstância derruba o pipeline: qualquer exceção resulta em `{"erro": ..., "score_demografico": None}`.

---

## 2. Contrato de Entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `input_params` | `dict` | `api.py` (usuário) |
| `input_params.cidade` | `str` | usuário |
| `input_params.uf` | `str` | usuário |
| `input_params.bairro` | `str` | usuário (opcional) |
| `cidade` | `str` | raiz do state (fallback) |
| `uf` | `str` | raiz do state (fallback) |
| `bairro` | `str` | raiz do state (fallback) |
| `market_context` | `dict` \| `str` | A0 (fallback adicional via `_parse_market_context`) |

A função `_loc_do_state` (linha 34) resolve a localização com prioridade: raiz do state > `input_params` > `market_context` (A0). `bairro` pode ser `None` — a macro de IBGE aceita só cidade+UF.

---

## 3. Contrato de Saída

**State delta**: `{"analise_demografica": <dict>}`

Gravado via `EventActions(state_delta=...)` — não usa `output_key`.

| Campo | Tipo | Descrição |
|---|---|---|
| `codigo_ibge` | `str` \| `None` | Código IBGE do município |
| `score_demografico` | `float` (0-10) \| `None` | Score demográfico; `None` em caso de erro total |
| `publico_potencial_fitness` | `int` \| `dict` \| `None` | Público estimado na faixa fitness |
| `renda_bairro` \| `renda_media_domiciliar` | `float` \| `dict` | Renda do bairro/município (pode vir como dict com chave `valor`) |
| `classificacao` | `str` | Classificação textual do score demográfico |
| `insights` | `list[str]` | 3 insights determinísticos gerados por `_insights_deterministicos` |
| `perfil_sexo_publico` | `dict` \| ausente | Perfil sexo×idade do público fitness (Censo 2022/BQ); opcional |
| `densidade_setor` | `dict` \| ausente | Densidade populacional do setor censitário (espelho censo_setor); opcional |
| `latitude` \| `lat` | `float` \| ausente | Latitude geocodificada (usada pelo enrichment de setor) |
| `longitude` \| `lng` | `float` \| ausente | Longitude geocodificada |
| `erro` | `str` \| ausente | Presente somente em caso de falha total da macro |

**Contrato mínimo validado por schema** (`models/pipeline_schemas.py`, classe `AnaliseDemografica`):

```python
class AnaliseDemografica(_Lenient):
    codigo_ibge: Optional[Any] = None
    score_demografico: Optional[float] = None
    publico_potencial_fitness: Optional[Any] = None
    insights: Optional[list] = None
    perfil_sexo_publico: Optional[dict] = None
    densidade_setor: Optional[dict] = None
```

---

## 4. Regras de Negócio

**RN-A2-01 — Determinismo total**
O A2 não usa LLM. Toda lógica é Python puro: `analise_demografica_completa`, `_insights_deterministicos`, `perfil_sexo_publico_fitness`, `demografia_setor_censo`. Resultado é auditável e reproduzível.

**RN-A2-02 — Fail-soft: nunca derruba o pipeline**
O bloco `try/except` externo (linha 144) captura qualquer exceção da macro IBGE e emite `{"erro": f"{type(e).__name__}: {e}", "score_demografico": None}`. O A6 downstream degrada com `score_demografico=None` em vez de falhar.

**RN-A2-03 — `_num_campo` trata renda como dict**
O campo `renda_bairro` (e aliases) pode chegar como `dict` com chave `valor`, `renda_media`, `value` ou `media` — esse é o comportamento real do IBGE tools em alguns municípios. A função `_num_campo` (linha 50) extrai o número sem levantar `TypeError`. Não simplificar para `float(r.get("renda_bairro"))` direto.

**RN-A2-04 — Insights determinísticos (3 templates)**
`_insights_deterministicos` (linha 66) gera até 3 insights:
1. Potencial de captação: `~{pub:,} alunos potenciais na faixa fitness.`
2. Renda: `Renda de R$ {renda:,.0f} suporta|não suporta mensalidade premium.` — threshold via `param("score_demo_renda_baixa")`.
3. Score: `Score {score:.1f}/10 indica mercado {classificacao.lower()}.`

Cada insight só é adicionado se o valor correspondente for não-nulo/não-zero.

**RN-A2-05 — Enriquecimento gancho sexo×idade (opcional)**
Se `perfil_sexo_publico_fitness(codigo_ibge)` retornar dados, eles são adicionados em `r["perfil_sexo_publico"]` e um 4º insight é adicionado via `insight_gancho_mkt(perfil)`. Falha nesse bloco é capturada e logada como `[A2 gancho sexo×idade] falha (degrada)` — não derruba o agente.

**RN-A2-06 — Flag `A2_FONTE` controla density enrichment**
O enriquecimento de densidade de setor censitário é habilitado por padrão (`A2_FONTE=espelho`). Se `os.getenv("A2_FONTE") == "rest"`, o bloco de `demografia_setor_censo` é pulado. Isso existe porque o BQ-runtime falha em prod (nota no código linha 119). O espelho Supabase é a fonte prod-viável.

**RN-A2-07 — Geocoding lazy para density enrichment**
O setor só precisa de coordenadas. Se `r.get("latitude")` ou `r.get("longitude")` forem None, o A2 chama `nominatim_geocode(f"{bairro}, {cidade}, {uf}, Brasil")` para obtê-las. Falha no geocode é capturada e logada — não derruba.

**RN-A2-08 — Validação leniente de schema (C6.2)**
Após construir `r`, o A2 chama `validar_lenient(AnaliseDemografica, r, agente="A2")` (linha 152). Divergências são logadas em `gymsite.schemas` mas o dado original é retornado sem coerção. A validação nunca levanta exceção para o caller.

**RN-A2-09 — Fonte de renda migrada para IPECE/IBGE 2022 (v2.0, PONTO 8)**
O campo `renda_bairro` agora usa dados do **IPECE/IBGE 2022** (Censo 2022), substituindo a fonte legada CKAN 2010. Esta migração impacta diretamente o `score_demografico`, que pode aumentar em municípios com crescimento de renda pós-2010. A função `enrich_demografia_bairro` deve ser atualizada para consumir a nova fonte. Implementação requer validação de impacto nos scores históricos.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `analise_demografica` está presente no `state` após execução (mesmo em erro total).
- [ ] `score_demografico` é `float` entre 0 e 10 (inclusivo) **ou** `None` — nunca outro tipo.
- [ ] `insights` é `list[str]` com 1 a 4 itens (0 só em erro total onde o campo pode estar ausente).
- [ ] Em erro total da macro IBGE, o state recebe `{"erro": "...", "score_demografico": None}` e a pipeline continua.
- [ ] `_num_campo` não levanta exceção quando `renda_bairro` é `dict` com chave `valor`.
- [ ] Quando `A2_FONTE=rest`, `densidade_setor` nunca aparece no output.
- [ ] `validar_lenient` é chamado e divergências aparecem nos logs (`gymsite.schemas`) — sem exceção propagada.
- [ ] Zero chamadas LLM durante a execução do A2 (verificável por custo_brl=0 no trace de tokens).
- [ ] Falha em `perfil_sexo_publico_fitness` ou `demografia_setor_censo` não altera `score_demografico`.
- [ ] **v2.0**: `renda_bairro` usa IPECE/IBGE 2022 (não CKAN 2010); validar impacto no score vs baseline histórica.

---

## 6. Comportamento em Degradação (Fail-Soft, C4.4)

| Cenário | Comportamento |
|---|---|
| `analise_demografica_completa` lança exceção | `r = {"erro": "...", "score_demografico": None}`; pipeline segue |
| `perfil_sexo_publico_fitness` falha | Log `[A2 gancho sexo×idade] falha (degrada)`; `perfil_sexo_publico` ausente; sem impacto no score |
| `demografia_setor_censo` falha | Log `[A2 densidade setor] falha (degrada)`; `densidade_setor` ausente |
| `nominatim_geocode` falha | Setor enrichment pulado (sem coordenadas); log de falha |
| `validar_lenient` lança exceção interna | `try/except` (linha 150) captura; dado original retornado sem validar |
| `A2_FONTE=rest` | Bloco setor censitário completamente pulado |
| IBGE API indisponível | `analise_demografica_completa` usa fallbacks hardcoded (dict de municípios em `ibge_tools.py`) |

---

## 7. Contexto para IA

**Gotchas críticos:**

- **É um `BaseAgent`, não `LlmAgent`**: o A2 herda `google.adk.agents.BaseAgent` e implementa `_run_async_impl`. Não há LLM, não há `output_key`, não há `instruction`. A saída vai via `EventActions(state_delta={"analise_demografica": r})`. Se converter para `LlmAgent` por acidente (ex.: para "melhorar insights"), custo aumenta ~135k tokens/run sem benefício downstream (A6 só lê `score_demografico`).

- **`_num_campo` é proteção contra tipo variável**: o campo `renda_bairro` às vezes é `{"valor": 1500}` e às vezes é `1500.0` dependendo do município e do cache. A função `_num_campo` abstrai isso. Remover e usar `float()` diretamente quebra em produção com `TypeError` — esse era o bug do A4 antes do fix.

- **`_loc_do_state` tem 3 camadas de fallback**: (1) raiz do state, (2) `input_params`, (3) `market_context` do A0. Se o A0 falhar silenciosamente e `market_context` vier vazio, o A2 ainda funciona com os parâmetros da raiz do state.

- **Migração renda 2010 → 2022 implementada (v2.0)**: O campo `renda_bairro` agora consome IPECE/IBGE 2022. Scores demográficos podem aumentar em municípios com crescimento pós-2010. Validar impacto comparando baseline histórica antes de deploy em produção.

- **`A2_FONTE` flag existe por limitação de prod**: BQ-runtime (`demografia_setor_censo` via BigQuery direto) falha em Cloud Run por timeout/credenciais. O modo `espelho` usa Supabase como intermediário (prod-viável). O modo `rest` pula totalmente o setor — útil para testes rápidos ou ambientes sem Supabase.

- **`validar_lenient` nunca deve elevar para `raise`**: o schema `AnaliseDemografica` é `extra="allow"` e todos os campos são `Optional`. O objetivo é observabilidade (log de divergências), não rejeição. Endurecer para `raise` é uma decisão futura atrás de flag, não deve ser feito no A2 diretamente.

- **A6 lê `score_demografico` com `None` como caso válido**: downstream o A6 degrada graciosamente quando `score_demografico is None` — não trata como ausência de `analise_demografica`. Manter esse contrato.
