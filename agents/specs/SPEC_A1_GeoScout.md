# SPEC_A1_GeoScout.md

---
id: spec-a1-001
agente: GeoScout
modelo_llm: gemini-2.5-flash (thinking_budget=0)
versao: 1.0
data: 2026-06-18
constitution: C2.1, C2.3, C6.1
---

## 1. Responsabilidade Única

O A1 GeoScout tem escopo exclusivo de **identificação de endereços-âncora comerciais** para field research de academias: a partir do bairro/cidade informados, chama uma única macro-tool (`analisar_pontos_comerciais_completo`) que executa todo o pipeline geoespacial internamente e retorna candidatos com scores, listings reais e investigações de imóveis. O A1 **não interpreta** os dados — copia o JSON da macro-tool para o `output_key` e o persiste no state via `after_tool_callback`.

---

## 2. Contrato de Entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `input_params.bairro` | `str` | usuário via `api.py` |
| `input_params.cidade` | `str` | usuário via `api.py` |
| `input_params.uf` | `str` | usuário via `api.py` |

O agente extrai `bairro`, `cidade`, `uf` do `input_params` no state para passar à macro-tool. Não lê `market_context` (A0) nem `analise_demografica` (A2).

---

## 3. Contrato de Saída

**`output_key`**: `candidatos_geoscout`

**Chave paralela no state** (gravada via `after_tool_callback`): `candidatos_geoscout_pronto`

> A chave `candidatos_geoscout_pronto` é o mecanismo de mitigação de truncamento do LLM (incidente b5b0e627, 2026-06-12). Agentes downstream (A6) leem esta chave primeiro e usam `candidatos_geoscout` apenas como fallback.

| Campo | Tipo | Descrição |
|---|---|---|
| `total_candidatos` | `int` | Número total de candidatos retornados pela macro |
| `ancoras_heuristicas` | `int` | Zonas-âncora identificadas por heurística Places |
| `listings_reais` | `int` | Listings OLX/ImovelWeb encontrados |
| `estrategia` | `str` | Descrição da estratégia usada (copiado da macro) |
| `qualidade_sinal` | `str` | `"direto-listing"` ou `"indireto-heuristico"` (copiado da macro) |
| `checklist_diligencia` | `list[str]` | 6 itens fixos de diligência |
| `investigacoes_imoveis` | `dict` | `{disparados, executados, limite}` |
| `candidatos` | `list[dict]` | Lista de candidatos com scores e metadados |
| `aviso` | `str` (opcional) | Presente apenas quando a macro retorna `{"erro": ...}` |

**Campos relevantes por candidato** (quando `fonte: "listing"`):

| Campo | Tipo | Descrição |
|---|---|---|
| `score_geoscout` | `float` (0-10) | Score determinístico da macro |
| `score_ancoragem` | `float` (0-10) | Proximidade de polos geradores |
| `polos_geradores` | `list[dict]` | Terminais/atacadistas no raio 2km |
| `visibilidade` | `str` | `"alta"` \| `"media"` \| `"baixa"` |
| `avenida_principal` | `bool` | Heurística de via principal |
| `street_view_url` | `str` | URL Street View |
| `listing_url` | `str` | URL do anúncio OLX/ImovelWeb |
| `listing_id` | `str` | ID do anúncio |
| `price_raw` | `str` | Preço bruto do anúncio |
| `source` | `str` | `"olx"` \| `"imovelweb"` |
| `investigacao` | `bool` (opcional) | Se investigação web foi disparada |
| `investigacao_resultado` | `str` (opcional) | O que opera no endereço hoje |

---

## 4. Regras de Negócio

**RN-A1-01 — Uma única chamada à macro-tool**
O agente chama `analisar_pontos_comerciais_completo(bairro, cidade, uf)` **exatamente uma vez**. É proibido chamar ferramentas separadas de geocoding, busca, scoring ou visibilidade — todas foram consolidadas na macro.

**RN-A1-02 — Proibição de inventar scores**
Nenhum campo de score (`score_geoscout`, `score_ancoragem`), polo gerador, visibilidade ou URL é inventado pelo LLM. Todos vêm exclusivamente da macro-tool.

**RN-A1-03 — Tratamento de erro da macro**
Se `analisar_pontos_comerciais_completo` retornar `{"erro": ...}`, o agente emite JSON com `total_candidatos: 0`, `candidatos: []` e o erro no campo `aviso`. Não tenta refazer com parâmetros diferentes.

**RN-A1-04 — Lista pequena é aceitável**
Se `total_candidatos < 5`, a lista é emitida mesmo assim. Lista vazia é falha, lista pequena é resultado válido.

**RN-A1-05 — Preservação de campos de listing**
Campos `listing_url`, `listing_id`, `price_raw` e `source` dos candidatos com `fonte: "listing"` devem ser preservados integralmente no JSON de saída. O A5 ContactHunter depende desses campos.

**RN-A1-06 — Preservação de campos de investigação**
Campos `investigacao` e `investigacao_resultado` devem ser preservados nos candidatos que os possuírem. Esses campos descrevem o que opera no endereço hoje (aberto/vago/fechado).

**RN-A1-07 — Persistência bypass-LLM via after_tool_callback**
A função `_persistir_macro_no_state` (linha 32) é registrada como `after_tool_callback`. Ela grava o output bruto da macro em `state["candidatos_geoscout_pronto"]` **antes** do LLM processar o resultado — mitigando o risco de truncamento do array de candidatos pelo LLM ao copiar para o `output_key`.

**RN-A1-08 — thinking_budget=0**
O A1 usa `thinking_budget=0` porque seu papel é apenas copiar o JSON da macro — sem raciocínio. Não alterar esse valor sem análise de custo/benefício.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] Exatamente 1 chamada a `analisar_pontos_comerciais_completo` por execução do agente (verificável no trace de tool calls).
- [ ] `candidatos_geoscout_pronto` está presente no `state` após a execução (gravado pelo `after_tool_callback`).
- [ ] `checklist_diligencia` contém exatamente 6 itens.
- [ ] `total_candidatos` é `int >= 0`.
- [ ] `candidatos` é `list` (pode ser vazia apenas em cenário de erro com `aviso` preenchido).
- [ ] Nenhum candidato tem `score_geoscout` fora do intervalo `[0, 10]`.
- [ ] Candidatos com `fonte: "listing"` possuem `listing_url` não-vazio.
- [ ] Em cenário de erro da macro, `aviso` está presente e `candidatos == []`.
- [ ] `candidatos_geoscout` (output_key) e `candidatos_geoscout_pronto` (state) contêm o mesmo conjunto de candidatos.

---

## 6. Comportamento em Degradação (Fail-Soft, C4.4)

| Cenário | Comportamento |
|---|---|
| Macro retorna `{"erro": ...}` | `total_candidatos=0`, `candidatos=[]`, `aviso` com o erro; pipeline segue |
| Geocoding interno falha (bairro não encontrado) | Macro trata e retorna erro; A1 emite com `aviso` |
| OLX/ImovelWeb inacessíveis (Playwright) | Macro retorna apenas heurísticas (`listings_reais=0`); `qualidade_sinal="indireto-heuristico"` |
| LLM trunca o JSON ao copiar para output_key | A6 usa `candidatos_geoscout_pronto` (gravado pelo callback) como fallback; incidente b5b0e627 |
| Polo gerador não encontrado no raio | `polos_geradores=[]`; `score_ancoragem` calculado sem polos (score menor, não erro) |

---

## 7. Contexto para IA

**Gotchas críticos:**

- **`_persistir_macro_no_state` é o mecanismo de resiliência principal**: esse callback (linha 32) grava `candidatos_geoscout_pronto` no state **antes** do LLM processar. Remover ou alterar esse callback sem entender o incidente b5b0e627 resulta em candidatos zerados no A6. O incidente aconteceu porque o LLM truncou um array de 14 candidatos ao copiar para o output_key.

- **thinking_budget=0 é intencional**: o A1 tem o menor orçamento de thinking do pipeline porque sua função é puramente de cópia/pass-through da macro. Aumentar o thinking não melhora resultado — só aumenta custo.

- **A macro é determinística, o LLM é só embalagem**: todo o raciocínio de scoring, geocoding, visibilidade e ancoragem ocorre dentro de `analisar_pontos_comerciais_completo` (tools/anchoring_tools.py). O LLM não deve e não consegue modificar esses valores.

- **MALFORMED_FUNCTION_CALL foi o bug motivador**: antes do refator (2026-05-09, VEC-379 fase 1B), havia 10 tools separadas. O LLM tentava passar a lista de 30+ polos geradores como argumento, corrompendo o JSON do function_call em 5 de 9 runs. A macro única eliminou esse problema — não reverter para tools separadas.

- **`qualidade_sinal` distingue dois tipos de candidatos**: `"direto-listing"` = listing real de OLX/ImovelWeb com URL e preço; `"indireto-heuristico"` = endereço âncora derivado de estabelecimentos vizinhos. A6 trata diferente na tabela de candidatos.

- **Campos A5 devem ser preservados**: `listing_url`, `listing_id`, `price_raw`, `source` são consumidos pelo A5 ContactHunter para identificar o dono do imóvel. Perder esses campos no LLM-copy é bug silencioso — o A5 simplesmente não encontra contato.

- **`build_llm_agent`**: o agente é construído via `agent_factory.build_llm_agent` com retry automático (4 tentativas, exp backoff 2-60s para 429/503/500) e telemetria de tokens injetados. Não instanciar `Agent(...)` diretamente.
