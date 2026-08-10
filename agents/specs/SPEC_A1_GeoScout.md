---
id: spec-a1-002
agente: GeoScout
modelo_llm: BaseAgent (sem LLM)
versao: 2.0
data: 2026-08-10
constitution: C2.1, C2.3, C4.4, C6.1
---

## 1. Responsabilidade Única

O A1 GeoScout é um **agente determinístico (BaseAgent, sem LLM)** responsável exclusivamente por **identificar listings comerciais ativos no bairro-alvo** via SearchAPI, filtrar por geografia e área (500–5000 m² default), e anexar aluguel MRLR determinístico. O output é uma lista de candidatos com scores, URLs de anúncios e preços brutos. O A1 **não interpreta** os dados — apenas executa a macro-tool `buscar_candidatos_listing_mrlr` e grava o resultado no state.

**Mudança crítica vs v1.0:** A spec v1.0 descrevia um LlmAgent chamando `analisar_pontos_comerciais_completo` (macro de âncoras heurísticas). Evidência em campo (Pirapora-MG Centro, 2026-08-05): ≥90% dos resultados eram `indireto-heuristico`, com área repetida (600 m²) e contaminação entre cidades (Diadema-SP). O código foi refatorado para BaseAgent determinístico que busca **anúncios individuais reais** (OLX/ImovelWeb via SearchAPI), não âncoras genéricas.

---

## 2. Contrato de Entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `input_params.bairro` | `str` | usuário via `api.py` |
| `input_params.cidade` | `str` | usuário via `api.py` |
| `input_params.uf` | `str` | usuário via `api.py` |
| `input_params.area_m2_min` | `int` (default 500) | usuário via `api.py` |
| `input_params.area_m2_max` | `int` (default 5000) | usuário via `api.py` |
| `market_context` | `dict` | A0 ContextBuilder (fallback para cidade/bairro/uf) |

O agente extrai localização de `input_params` com fallback para `market_context` (via `_parse_market_context`). Não lê `analise_demografica` (A2) nem `candidatos_geoscout` (auto-referência).

---

## 3. Contrato de Saída

**`output_key`**: `candidatos_geoscout`

**Chave paralela no state** (gravada inline no `_run_async_impl`): `candidatos_geoscout_pronto`

> Ambas as chaves recebem o **mesmo JSON bruto** da macro-tool. Não há pós-processamento por LLM.

| Campo | Tipo | Descrição |
|---|---|---|
| `status` | `str` | `"ok_vazio"` (sucesso, pode ter 0 candidatos) ou `"erro"` |
| `total_candidatos` | `int` | Número total de candidatos retornados |
| `candidatos` | `list[dict]` | Lista de candidatos (pode ser vazia) |
| `aviso` | `str` (opcional) | Presente apenas em erro ou degradação |
| `fonte` | `str` | `"listing_cascata_searchapi+mrlr"` |
| `cidade` | `str` | Cidade da busca |
| `uf` | `str` | UF da busca |
| `bairro` | `str` | Bairro da busca |

**Campos por candidato** (quando presente na lista):

| Campo | Tipo | Descrição |
|---|---|---|
| `score_geoscout` | `float` (0-10) | Score determinístico da macro |
| `endereco` | `str` | Endereço completo do imóvel |
| `area_m2` | `float` | Área em m² |
| `aluguel_m2_mrlr` | `float` | Aluguel/m² MRLR (Tier 0) |
| `aluguel_total_estimado` | `float` | `area_m2 × aluguel_m2_mrlr` |
| `listing_url` | `str` | URL do anúncio OLX/ImovelWeb |
| `listing_id` | `str` | ID do anúncio |
| `price_raw` | `str` | Preço bruto do anúncio (se disponível) |
| `source` | `str` | `"olx"` \| `"imovelweb"` \| `"searchapi"` |
| `latlng` | `dict` | `{"lat": float, "lng": float}` |
| `visibilidade` | `str` | `"alta"` \| `"media"` \| `"baixa"` |
| `avenida_principal` | `bool` | Se está em via principal |

---

## 4. Regras de Negócio

**RN-A1-01 — Macro-tool única, sem LLM**
O agente chama `buscar_candidatos_listing_mrlr(cidade, uf, bairro, area_m2_min, area_m2_max)` **exatamente uma vez** via `asyncio.to_thread`. Não há function_call, não há LLM, não há re-interpretação do resultado.

**RN-A1-02 — Lista vazia é resultado válido**
Se `total_candidatos == 0`, o output é `{"status": "ok_vazio", "total_candidatos": 0, "candidatos": []}`. Lista vazia **não é erro** — é sinal de que não há listings comerciais no bairro com os filtros aplicados. O pipeline continua (A6 lida com ausência de candidatos).

**RN-A1-03 — Preservação de campos A5**
Campos `listing_url`, `listing_id`, `price_raw` e `source` devem ser preservados integralmente. O A5 ContactHunter depende desses campos para identificar o dono do imóvel. Perder esses campos é bug silencioso.

**RN-A1-04 — Fail-soft absoluto**
Qualquer exceção na macro-tool resulta em `{"status": "ok_vazio", "total_candidatos": 0, "candidatos": [], "aviso": "<tipo_excecao>: <mensagem>"}`. Nunca derrubar o pipeline.

**RN-A1-05 — Cascata de busca interna à macro**
A macro `buscar_candidatos_listing_mrlr` aplica internamente:
1. SearchAPI direta por termos `"galpão comercial"`, `"loja comercial"`, `"salão comercial"` + bairro
2. Filtro geográfico (dentro do bairro ou raio 500m)
3. Filtro de área (area_m2_min a area_m2_max)
4. Anexação de aluguel MRLR via `tools/aluguel_mrlr.py`

**RN-A1-06 — Sem re-cálculo de aluguel**
O aluguel/m² vem exclusivamente de `tools/aluguel_mrlr.py` (MRLR IBAPE-GO determinístico). O A1 não calcula, não ajusta e não interpola valores de aluguel.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `state["candidatos_geoscout"]` existe após execução e é um dict com `status`, `total_candidatos`, `candidatos`.
- [ ] `state["candidatos_geoscout_pronto"]` existe e é idêntico a `candidatos_geoscout`.
- [ ] `total_candidatos` é `int >= 0`.
- [ ] `candidatos` é `list` (pode ser vazia).
- [ ] Nenhum candidato tem `score_geoscout` fora do intervalo `[0, 10]`.
- [ ] Candidatos com `source: "olx"` ou `"imovelweb"` possuem `listing_url` não-vazio.
- [ ] Em cenário de erro, `aviso` está presente e `candidatos == []`.
- [ ] Smoke E2E: A1 não emite `OUT=0` (ausência de output_key) mesmo com 0 candidatos.
- [ ] Validação `GeoScoutOutput` (Pydantic, se existir) sem erros críticos.

---

## 6. Comportamento em Degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| SearchAPI indisponível (rate limit / down) | `status="ok_vazio"`, `candidatos=[]`, `aviso="SearchAPI indisponível: <detalhe>"` |
| Bairro não encontrado no geocoding | `status="ok_vazio"`, `candidatos=[]`, `aviso="Bairro não encontrado: <nome>"` |
| OLX/ImovelWeb inacessíveis (Playwright) | Retorna apenas candidatos sem `price_raw`; `source="searchapi"` |
| MRLR indisponível (espelho vazio) | Candidatos retornam sem `aluguel_m2_mrlr`; `aluguel_total_estimado=null` |
| Exception genérica na macro | `status="ok_vazio"`, `candidatos=[]`, `aviso="<ExceptionType>: <msg>"` |

---

## 7. Contexto para IA

**Gotcha #1 — BaseAgent, não LlmAgent:**
O A1 foi migrado de LlmAgent para BaseAgent em 2026-08. O código em `agents/a1_geoscout.py` é um `BaseAgent` puro que chama a macro diretamente via `asyncio.to_thread`. Não há `tools=[]`, não há `before_model_callback`, não há function_call. Qualquer spec que mencione LLM para A1 está obsoleta.

**Gotcha #2 — `candidatos_geoscout_pronto` é redundante por design:**
Ambas as chaves (`candidatos_geoscout` e `candidatos_geoscout_pronto`) recebem o mesmo JSON. A redundância era um mecanismo de mitigação de truncamento do LLM na v1.0 (incidente b5b0e627, 2026-06-12). Na v2.0 (BaseAgent), é mantida por compatibilidade com downstream (A6 lê `candidatos_geoscout_pronto` primeiro).

**Gotcha #3 — `thinking_budget=0` não se aplica:**
Na v1.0, a spec mencionava `thinking_budget=0` porque o LLM só copiava JSON. Na v2.0, não há LLM — o conceito é irrelevante. Remover qualquer menção a budget de thinking.

**Gotcha #4 — Cascata de localização:**
O agente tenta obter localização nesta ordem:
1. `state["input_params"]["bairro/cidade/uf"]`
2. `state["bairro/cidade/uf"]` (root)
3. `market_context["market_context"]["bairro/cidade/uf"]` (parse via `_parse_market_context`)
Se nenhuma fonte retornar, a macro recebe strings vazias e tende a retornar erro.

**Gotcha #5 — Área default:**
Se `area_m2_min` e `area_m2_max` não forem fornecidos, a macro usa defaults internos (geralmente 500–5000 m² para academia). Não assumir área fixa sem explicitar nos parâmetros.

**Gap C6.4 conhecido:**
`InMemorySessionService` — estado A1 vive em memória durante a sessão ADK. Crash entre A1 completar e A2 iniciar pode perder `candidatos_geoscout_pronto`. O `output_key` `candidatos_geoscout` é a fonte de verdade primária; `candidatos_geoscout_pronto` é cache de resiliência.

---

## 8. Fora de Escopo

**Fora de escopo do A1:**
- Buscar concorrentes (A3a)
- Calcular viabilidade financeira (A4)
- Traduzir reviews (fora de escopo, ver PONTO 13)
- Investigar web de endereços específicos (Playwright — fora de escopo desde 2026-08)
- Validar zoneamento (A9)
- Gerar relatório final (A6)
