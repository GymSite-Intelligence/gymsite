# SPEC_A6_ReportConsolidator.md

---

| Campo | Valor |
|---|---|
| **ID** | A6 |
| **Agente** | ReportConsolidator |
| **Modelo LLM** | `gemini-2.5-flash` com `thinking_budget=8192` |
| **Versão** | 2.0 (atualizada PONTO 17-19) |
| **Data** | 2026-08-10 |

---

## 1. Responsabilidade Única (C6.1)

Consolidar os outputs dos agentes A0-A5 em um relatório executivo markdown estruturado, ao mesmo tempo em que executa consolidação determinística (scores, veredito, zoneamento, bairros alternativos, entrantes CNPJ) e persiste o JSON canônico em filesystem e Supabase.

---

## 2. Contrato de Entrada

| Chave do State | Tipo | Produzido por | Descrição |
|---|---|---|---|
| `market_context` | dict/str | A0 | Contexto de mercado (cidade, bairro, UF, ticket, renda, redes concorrentes, insights) |
| `candidatos_geoscout` | dict/str | A1 | Candidatos de imóveis ranqueados pelo GeoScout |
| `candidatos_geoscout_pronto` | dict | A1 callback | Snapshot determinístico preferido (evita truncamento pelo LLM) |
| `analise_demografica` | dict/str | A2 | Score demográfico + perfil sexo/público |
| `concorrentes_brutos` | dict/str | A3a | Envelope de busca bruta (raio 3km) + metadados de redes |
| `inteligencia_competitiva` | dict/str | A3b | Análise profunda de concorrentes: scores, dores, posicionamento |
| `oferta_concorrentes` | dict/str/JSON | A3b (oferta fundida do ex-A3c) | Mapeamento de planos/mensalidades por academia |
| `analise_financeira` | dict/str | A4 | Cenários financeiros, modelo recomendado, alertas |
| `analise_financeira_pronto` | dict | A4 callback | Snapshot determinístico do A4 (preferido sobre echo do LLM) |
| `contato_decisor` | dict | A5 | Decisor do candidato #1 + script de abordagem |
| `bairros_alternativos_pronto` | dict | A6 precompute callback | Bairros alternativos com busca real (raio 2km por bairro) |
| `entrantes_cnpj_pronto` | dict | A6 precompute callback | Novos entrantes CNPJ fitness (90 dias) |
| `obras_cno_pronto` | dict | A6 precompute callback | Obras fitness CNO em andamento |
| `demanda_futura` | dict | api.py | Obras residenciais → moradores → captura fitness T+24 |
| `input_params` | dict | api.py | Parâmetros originais do formulário (area_m2, publico_alvo, etc.) |
| `relatorio_id` | str | api.py | UUID externo (Supabase) para upsert |

---

## 3. Contrato de Saída

### 3.1 output_key ADK: `relatorio_md`

O LLM emite o relatório markdown completo em `relatorio_md` (configurado via `build_llm_agent`).

### 3.2 state_delta via callbacks

| Chave gravada | Onde | Tipo | Descrição |
|---|---|---|---|
| `bairros_alternativos_pronto` | `_a6_precompute_callback` | dict | Resultado da busca real por bairro alternativo |
| `entrantes_cnpj_pronto` | `_a6_precompute_callback` | dict | Novos entrantes CNPJ (90d) |
| `obras_cno_pronto` | `_a6_precompute_callback` | dict | Obras fitness em curso |
| `relatorio_local_id` | `_a6_after_agent_callback` | str | ID do arquivo JSON gravado (ex: `rpt_1750000000`) |
| `relatorio_md` (alinhado) | `_a6_after_agent_callback` | str | Markdown com veredito/scores corrigidos por `_alinhar_markdown_ao_estruturado` |

### 3.3 output_consolidado — campos canônicos

O JSON canônico `metrics/relatorios/<id>.json` contém `output_consolidado` com os seguintes campos principais:

| Campo | Tipo | Origem |
|---|---|---|
| `veredito` | str | Determinístico: `APROVADO` / `APROVADO COM RESSALVAS` / `INVESTIGAR MAIS` / `REPROVADO` |
| `score_bairro` | float/None | Média de 3 dimensões regionais (demográfico, competitivo, viabilidade) |
| `score_top1_candidato` | float/None | Média de 4 dimensões (+ geoscout do candidato #1) — BASE DO VEREDITO |
| `score_concorrencia` | float | Score competitivo do A3b |
| `scores_regionais` | dict | `{demografico, competitivo, viabilidade}` — None preservado (não fabricar 0.0) |
| `nivel_saturacao` | str | Saturação do bairro (nunca do raio 3km) |
| `total_concorrentes_analisados` | int | Contagem gated (bairro+tipo); autoritativa |
| `top_3_candidatos` | list | Top 3 candidatos enriquecidos com `investigacao_site` |
| `zoneamento` | dict/None | Análise LUOS do top candidato ou centroide do bairro |
| `bairros_alternativos` | list | Bairros alternativos com prioridade ALTA/MEDIA/BAIXA |
| `viabilidade_3_cenarios` | dict | 3 cenários financeiros normalizados (aluguel garantido) |
| `modelo_recomendado` | str | Modelo de negócio recomendado pelo A4 |
| `alertas_financeiros` | list | Alertas filtrados (sem ruído EBITDA/SMFT3/CVM) |
| `contato_decisor` | dict | Output do A5 + `resumo_executivo` determinístico |
| `market_context` | dict | `slim_market_context` (sem `briefing_completo_md`) |
| `entrantes_cnpj_90d` | dict | Novos entrantes para prospecção |
| `obras_cno_em_curso` | dict | Obras fitness CNO |
| `demanda_futura` | dict | Captura potencial T+24 |
| `aneis_competitivos` | dict | Score ponderado por anel (NO_BAIRRO/FRONTEIRA/REGIONAL) |
| `demografia_bairro` | dict | Dados Censo 2022 do bairro (renda CKAN, pop, perfil sexo) — **Bridge para A9**: A6 grava no state via `after_agent_callback` para consumo pelo A9 PositioningStrategist (ver PONTO 19) |
| `cobertura_redes_a0` | dict | Redes DR validadas vs redes fantasma |

---

## 4. Regras de Negócio

**RN-A6-01 — Score Bairro vs Score Top 1 são distintos.**
`score_bairro = média(score_demografico, score_concorrencia, score_viabilidade)`. `score_top1_candidato = média(score_geoscout_top1, score_demografico, score_concorrencia, score_viabilidade)`. O veredito usa **score_top1_candidato**; se indisponível, cai em `score_bairro`. Não misturar as fórmulas (linhas 2406-2432).

**RN-A6-02 — Veredito heurístico por limiares parametrizados.**
Limiares lidos de `param("veredito_limiar_aprovado")`, `param("veredito_limiar_ressalvas")`, `param("veredito_limiar_investigar")` — da tabela `parametros_metodologia` no Supabase. Zero hardcode inline (linhas 2433-2439).

**RN-A6-03 — Guard P1: 0 concorrentes forçam INVESTIGAR MAIS.**
Se `concorrentes_detalhados` vazio E `total_concorrentes == 0`, o veredito APROVADO ou APROVADO COM RESSALVAS é rebaixado para INVESTIGAR MAIS, e alerta específico é adicionado (linhas 2513-2523).

**RN-A6-04 — Guard P3: zoneamento RESTRITO rebaixa o veredito.**
Se `zoneamento_block.compatibilidade == "RESTRITO"`, veredito positivo é rebaixado para INVESTIGAR MAIS e `score_top1_candidato` é penalizado em `param("zoneamento_penal_restrito")`. CONDICIONADO penaliza com `param("zoneamento_penal_condicionado")` sem rebaixar veredito (linhas 2528-2544).

**RN-A6-05 — Guard financeiro: ticket Premium fora da banda.**
Se modelo recomendado é Premium e `ticket_recomendado >= 750` OU `ticket >= renda_local * 0.5`, alerta é adicionado e APROVADO é rebaixado para APROVADO COM RESSALVAS (linhas 2564-2579).

**RN-A6-06 — `resumo_executivo` é determinístico, sobrescreve o do LLM.**
`_resumo_executivo_deterministico(...)` (linhas 1926-2026) monta o resumo a partir dos campos estruturados (veredito, saturação do bairro, zoneamento, candidato gated). O resultado é gravado em `contato["resumo_executivo"]` e depois em `_alinhar_markdown_ao_estruturado` o bloco `## Resumo Executivo` do markdown é substituído via regex (linhas 1868-1877). O LLM nunca narra o resumo final. **PONTO 18**: Narração Claude opcional via `NARRADOR_CLAUDE_ENABLED` foi removida — resumo é 100% determinístico por design.

**RN-A6-07 — Candidato só nomeado no resumo se está no bairro alvo.**
`_no_bairro(c)` normaliza e verifica se o endereço/bairro/título do candidato contém o bairro alvo. Candidato de bairro adjacente (ex: Eng. Luciano Cavalcante em relatório de Cocó) não é nomeado — a narrativa registra "Nenhum imóvel anunciado no bairro" (linhas 2004-2025).

**RN-A6-08 — Zoneamento cai no centroide do bairro quando sem candidato geocodado.**
Se nenhum candidato top-3 tem `lat/lng`, A6 geocoda via Nominatim o centroide `"<bairro>, <cidade>"` e roda o zoneamento LUOS point-in-polygon assim mesmo. O campo `zoneamento_block["ancora"]` indica `"imovel"` ou `"centroide_bairro"` (linhas 2207-2227).

**RN-A6-09 — Saturação sempre do bairro, nunca do raio 3km.**
`total_concorrentes` autoritativo vem do cross-check gated (`cross_check_concorrentes_bairro`). Quando `gated_n > total_anterior`, o nível de saturação é recalculado via `classificar_saturacao_bairro(gated_n)` (linhas 2493-2505). A narrativa do LLM é corrigida por `_alinhar_markdown_ao_estruturado` que aplica regex pra substituir "extrema saturação" / "altamente saturado" pelo nível real quando `nivel_saturacao` é BAIXO ou MEDIO (linhas 1847-1866).

**RN-A6-10 — Seções pré-computadas são injetadas no system prompt via `_a6_before_model_callback`.**
Bairros alternativos, ofertas mapeadas, novos entrantes e referência de aluguel são renderizados como markdown literais com cabeçalho "SEÇÃO PRÉ-COMPUTADA" e injetados via `llm_request.append_instructions()` (linhas 1291-1397). O LLM deve copiar as tabelas literalmente; o único campo livre é a justificativa textual dos bairros alternativos.

**RN-A6-11 — `analise_financeira_pronto` é preferido sobre o echo do LLM.**
`_resolver_analise_financeira(state)` lê o snapshot bruto da tool (gravado pelo `after_tool_callback` do A4) e só enxerta `justificativa` do echo LLM quando ausente no snapshot (linhas 1452-1478). Evita que o flash do A4 drope campos como `aviso_metodologia` ou `aluguel_pesquisa_detalhes`.

**RN-A6-12 — `candidatos_geoscout_pronto` é preferido sobre o echo do A1.**
O snapshot `candidatos_geoscout_pronto` (after_tool_callback do A1) é carregado antes do echo para evitar truncamento do array `candidatos` pelo LLM (linhas 2168-2173).

**RN-A6-13 — Aluguel normalizado nos cenários.**
`_normalizar_cenarios_aluguel(cenarios, aluguel_fallback)` garante que `custos_detalhados.aluguel` exista em todos os 3 cenários antes de gravar, preenchendo do `aluguel_mensal` quando o A4-flash dropou o breakdown (linhas 1416-1448).

**RN-A6-14 — Filtro de alertas: sem ruído EBITDA/SMFT3/CVM.**
`_filtrar_alertas_ruido(alertas)` remove alertas que contenham tokens de ruído interno (ex: "fora da banda", "smft3", "ebitda smart fit", "cvm itr") antes de gravar no JSON canônico e no Supabase (linhas 679-695).

**RN-A6-15 — Renda autoritativa: IPECE 2022 sobrepõe CKAN 2010.**
Quando `renda_bairro_ipece` retorna dado, `slim_market_context["renda_media_bairro"]` é sobreposto e insights do A0 que citem renda divergente >15% ou citem "Censo 2010" são dropados via `_sanear_insights_renda` (linhas 2317-2346).

**RN-A6-16 — Seção "Demanda Futura" é determinística e appendada ao markdown.**
Se `output_consolidado["demanda_futura"]` tiver `status=ok` E `provavel_residencial_n > 0`, a seção é renderizada por `_renderizar_md_demanda_futura` e appendada ao markdown via `_alinhar_markdown_ao_estruturado` — o LLM não narra esta seção (linhas 1879-1885).

**RN-A6-17 — Persistência em filesystem é source-of-truth; Supabase é cache.**
`metrics/relatorios/<id>.json` é escrito em `_a6_after_agent_callback` (linha 3001-3004). Falha no Supabase gera warning mas não bloqueia o pipeline (linhas 3051-3056).

**RN-A6-18 — A8 validation foi movido para after-A9 (ver PONTO 29).**
O A8 agora roda após o posicionamento do A9 estar disponível, permitindo validação cruzada completa incluindo coerência do ERRC e veredito de posicionamento. A chamada é feita pelo `after_agent_callback` do A9 via `tools/a8_runner.run_a8_validation()`.

**RN-A6-19 — Bridge `demografia_bairro` → A9 está documentada (§3.2, PONTO 19).**
O campo `demografia_bairro` é gravado no state pelo `after_agent_callback` do A6 para consumo direto pelo A9 PositioningStrategist. Esta bridge permite que o A9 acesse dados demográficos do Censo 2022 (renda, população, perfil de sexo) sem precisar re-buscar. O A9 usa estes dados para fundamentar o framework ERRC e o veredito de posicionamento.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `output_consolidado.veredito` é um dos 4 valores válidos: `APROVADO`, `APROVADO COM RESSALVAS`, `INVESTIGAR MAIS`, `REPROVADO`
- [ ] `output_consolidado.score_bairro` e `output_consolidado.score_top1_candidato` são floats ou None (não podem ser 0.0 fabricado quando score é indisponível)
- [ ] `output_consolidado.nivel_saturacao` reflete o bairro gated (não o raio 3km)
- [ ] `output_consolidado.contato_decisor.resumo_executivo` é o gerado por `_resumo_executivo_deterministico` (não o do LLM)
- [ ] `relatorio_md` contém as seções "SEÇÃO PRÉ-COMPUTADA" sem invenção de status competitivo
- [ ] `metrics/relatorios/<id>.json` é criado após cada run com schema version `"1.5"`
- [ ] Guard P1 dispara: com mock de `concorrentes_detalhados=[]` e `total_concorrentes=0`, veredito vira `INVESTIGAR MAIS`
- [ ] Guard P3 dispara: com `zoneamento.compatibilidade=RESTRITO`, veredito positivo é rebaixado
- [ ] Alerta de ticket Premium é adicionado quando `ticket >= 750`
- [ ] Seção "🏗️ Demanda Futura" aparece no markdown apenas quando `demanda_futura.status=ok` E `provavel_residencial_n > 0`
- [ ] Teste de smoke end-to-end com golden case produz `veredito`, `score_bairro`, e `score_top1_candidato` dentro dos intervalos esperados para o caso

---

## 6. Comportamento em Degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| A3b retorna vazio (`concorrentes_detalhados=[]`) | Fallback para `concorrentes_brutos` do A3a via `_resolver_competitividade_extracao`; `fonte_fallback="concorrentes_brutos_a3a"` logado |
| A4 LLM dropa `custos_detalhados.aluguel` | `_normalizar_cenarios_aluguel` preenche do `aluguel_mensal`; sem este campo, recorre a qualquer cenário que tenha aluguel >0 |
| A1 LLM trunca array `candidatos` | `candidatos_geoscout_pronto` (snapshot do callback) é preferido; sem snapshot, lê o echo como antes |
| `bairros_alternativos_inteligentes` falha | Seção omitida ou montada a partir de `BAIRROS_ALTERNATIVOS` estáticos; `_a6_precompute_callback` loga `ERROR` mas não propaga exceção |
| `analisar_zoneamento_candidato` falha | `zoneamento_block = None`; relatório segue sem seção de zoneamento; warning logado |
| Supabase indisponível | `write_relatorio_failsafe` falha com warning; filesystem permanece source-of-truth |
| LLM emite markdown sem seção `## Resumo Executivo` | `_alinhar_markdown_ao_estruturado` regex não acha a seção; resumo determinístico não é injetado; fallback: o markdown fica sem substituição (não quebra) |
| `_a6_before_model_callback` falha | LLM recebe prompt sem seções pré-computadas; risco de alucinação de status competitivo; logado como ERROR (linha 1394) |

---

## 7. Contexto para IA

### Gotchas e invariantes

- **`_alinhar_markdown_ao_estruturado` força md = estruturado**: alinhador pós-LLM corrige veredito, **tabela Scores Regionais** (inclui células `—`), Score Bairro/Top1, transparência concorrentes/raio, **substitui seção Top 3** por render de `top_3_candidatos`, saturação exagerada e `## Resumo Executivo`. Célula `—` antes só atualizava dígitos → split-brain (ex.: c908a99d).

- **Injeção via `append_instructions` não é idempotente sem o guard de string**: o `_a6_before_model_callback` verifica se a seção já está no `system_instruction` antes de injetar (ex: `if "SEÇÃO PRÉ-COMPUTADA — BAIRROS ALTERNATIVOS" not in existing_si`). Sem esse guard, em retries a seção seria duplicada.

- **`score_concorrencia` e `score_oportunidade_mercado` são campos distintos**: o A3b pode emitir ambos. O A6 usa `score_concorrencia` na tabela de Scores Regionais (range 0-10, 10=favorável). `score_oportunidade_mercado` (range 0-10, 10=muitas dores) é diferente e não entra na fórmula de scores.

- **`None` ≠ `0.0` nos scores**: os campos de `scores_regionais` preservam `None` explicitamente. `_safe_float(None) = 0.0`, então score ausente não vira zero (bug anterior mostrou "Competitivo: 0.0" fake quando score era indisponível).

- **cidade_efetiva vs cidade**: quando o usuário informa `bairro="Eusébio"` com `cidade="Fortaleza"`, `resolver_cidade_efetiva` detecta que Eusébio é município separado da RM e troca a `cidade_efetiva` para "eusébio". Os `BAIRROS_ALTERNATIVOS` derivados são de Eusébio, não de Fortaleza. O campo `aviso_geografico` é propagado para o output_consolidado.

- **`_concorrente_campos_pesados` reduz custo de token**: os campos `enrichment_search_grounding_text`, `reviews_traduzidas`, `atividade_marketing`, `enrichment` são dropados por `_slim_concorrente` antes de compor o contexto do LLM. Reviews são limitadas a 5 por concorrente com `quote_curta[:180]`. Esta otimização foi motivada por acúmulo de R$107 em custo de token.

- **`thinking_budget=8192`**: o A6 usa thinking config alto porque sintetiza outputs de 5 agentes com regras condicionais complexas (tabelas, tie-breaker, bairros alternativos, 3 cenários). Reduzir o budget degrada consistência da síntese — revertível.

- **Modelo: Pro → Flash (2026)**: A6 era ~46% do custo LLM (R$4,82/relatório). A migração para Flash corta ~R$3,6/relatório. A instrução é muito detalhada e os dados já chegam estruturados/pre-computados; Flash dá conta. Reverter para Pro se a qualidade narrativa degradar em golden cases.
