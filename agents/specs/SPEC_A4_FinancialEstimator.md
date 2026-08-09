---
id: spec-a4-001
agente: A4 FinancialEstimator
modelo_llm: gemini-2.5-flash
versão: 1.1
data: 2026-07-13
---

# SPEC — A4 FinancialEstimator

## 1. Responsabilidade única

O A4 é responsável exclusivamente por **calcular e estruturar a viabilidade financeira do negócio em 3 cenários (low/mid/premium)**, incluindo aluguel via **MRLR determinístico (Tier 0)** com fallbacks legados em tiers inferiores, CAPEX, margem, payback, análise de sensibilidade e score de viabilidade. Todos os números são determinísticos, produzidos pela macro-tool `analise_financeira_a4_completo` (`BaseAgent` sem LLM desde jun/2026).

---

## 2. Contrato de entrada

| Chave / parâmetro | Tipo | Origem |
|---|---|---|
| `bairro` | `str` | Extraído do `market_context.bairro` pelo LLM na chamada da macro |
| `cidade` | `str` | Extraído do `market_context.cidade` |
| `uf` | `str` (opcional, default `""`) | Extraído do `market_context.uf` |
| `area_m2` | `float` (default 1250.0) | Derivado de `area_min`/`area_max` do prompt ou inferido de `tamanho_preset` |
| `destino_lat` / `destino_lng` | `float \| None` | Extraído de `candidatos_geoscout.candidatos[0].latlng` (injetado por `apply_patches.py`) |
| `tipo_negocio` | `str` (default `"academia"`) | `market_context.tipo_negocio` |
| `tamanho_preset` | `str` (default `"m"`) | `market_context.tamanho_preset` |
| `genero_alvo` | `str` (default `"misto"`) | `market_context.genero_alvo` — lido pelo LLM para calibrar a justificativa |
| `market_context` | `dict` / `str` | A0 (`output_key="market_context"`) — lido pelo LLM para extrair os campos acima |
| `candidatos_geoscout` | `dict` | A1 GeoScout (`output_key="candidatos_geoscout"`) — fonte de lat/lng do top-1 |

---

## 3. Contrato de saída

**output_key:** `analise_financeira`

| Campo | Tipo | Produtor |
|---|---|---|
| `analise_financeira.bairro` / `.cidade` / `.area_m2` | `str` / `float` | macro-tool |
| `analise_financeira.aluguel_mensal` | `float` | macro-tool |
| `analise_financeira.fonte_aluguel` | `str` | macro-tool (tier label) |
| `analise_financeira.aluguel_pesquisa_detalhes` | `dict` | macro-tool (tier, mediana_r_m2, queries_com_dados, etc.) |
| `analise_financeira.aluguel_municipio_referencia` | `dict` | macro-tool |
| `analise_financeira.referencia_macro_bcb` | `dict \| null` | macro-tool (somente quando tier1_vazio) |
| `analise_financeira.schema_cenarios` | `"v2"` | macro-tool |
| `analise_financeira.cenarios.low \| mid \| premium` | `dict` (shape completo) | macro-tool |
| `analise_financeira.recomendacao_modelo` | `str` | macro-tool via `_resumo_decisao_a4` |
| `analise_financeira.score_viabilidade` | `float` (0-10) | macro-tool via `_resumo_decisao_a4` |
| `analise_financeira.alertas` | `list[str]` | macro-tool (determinísticos) + LLM (pode adicionar alerta textual de nicho) |
| `analise_financeira.justificativa` | `str` | LLM (único campo redigido) |
| `analise_financeira.aviso_metodologia_aluguel` | `str` | macro-tool |

**State delta adicional (after_tool_callback):**

| Chave | Tipo | Produtor |
|---|---|---|
| `analise_financeira_pronto` | `dict` | `_persistir_a4_no_state` — snapshot do `tool_response` da macro antes do LLM |

---

## 4. Regras de negócio

**RN-A4-01 — Macro-tool única, sem separação de calls**
O LLM chama `analise_financeira_a4_completo(bairro, cidade, uf, area_m2, destino_lat, destino_lng)` em uma única chamada. As funções `pesquisar_aluguel_mediana` e `analise_financeira_completa` não devem ser chamadas separadamente — foram consolidadas na macro após `MALFORMED_FUNCTION_CALL` no Run 20 (2 tools com 7 parâmetros confundiam o Pro na primeira function_call).

**RN-A4-02 — Cascata de tiers para aluguel (determinística)**
A macro em `analise_financeira_a4_completo` aplica tiers e **Tier 0 MRLR sobrescreve** quando `aluguel_deterministico` retorna `status=ok`:
- **Tier 0 (primário)** — MRLR IBAPE-GO (`tools/aluguel_mrlr.py` + `mrlr_modelo.py`) sobre espelhos `renda_bairro` + `municipio_pib`. Mesma praça = mesmo R$/m². `fonte_aluguel`: `"MRLR IBAPE-GO (determinístico)"`. `tier_usado == 0`.
- **Tier 1** — Portais municipais (ZAP/Viva/OLX via `pesquisar_aluguel_municipio`). Só se Tier 0 indisponível e `tier1_suficiente=True`.
- **Tier 2** — Search Grounding (`pesquisar_aluguel_mediana`). Só se Tier 0 indisponível e Tier 1 insuficiente.
- **Tier 3** — Benchmark ACAD/FipeZap. Último fallback.
**Proibido:** usar preço de listing SearchAPI ou snippet `rent_sqm` como Tier 0. Ver `.agent/rules/conferencia-fontes-pipeline.md` §2.

**RN-A4-03 — Snapshot determinístico `analise_financeira_pronto` (after_tool_callback)**
`_persistir_a4_no_state` (registrado como `after_tool_callback`) grava o `tool_response` bruto de `analise_financeira_a4_completo` em `state["analise_financeira_pronto"]` antes de o LLM processar a resposta. Razão: o A4-Flash às vezes dropa/renomeia campos ao ecoar o JSON (`aviso_metodologia`, `aluguel_pesquisa_detalhes`, `capex.frete_equipamentos`, `custos_detalhados.aluguel`). O A6 lê `analise_financeira_pronto` para os números auditáveis e usa `analise_financeira` (output_key) apenas para a `justificativa`.

**RN-A4-04 — LLM como redator, não como calculador**
`score_viabilidade`, `recomendacao_modelo` e `alertas[]` são calculados deterministicamente por `_resumo_decisao_a4(fin)` dentro da macro e devem ser copiados literais. O LLM não recalcula, não inventa e não remove alertas de risco. Pode adicionar **um** alerta textual de nicho (gênero/tamanho), mas apenas adicionando — nunca removendo os existentes.

**RN-A4-05 — Alertas de risco determinísticos (6 regras em `_resumo_decisao_a4`)**
A macro aplica estas regras em código e devolve em `alertas[]`:
1. Payback > 60 meses → `"inviável"`.
2. Margem < 10% → `"apertada"`.
3. Aluguel > 15% do faturamento → `"compromete viabilidade"`.
4. Pico simultâneo > capacidade física → `"capacidade insuficiente"`.
5. Sensibilidade matrículas -30% = INVIAVEL → `"só fecha no benchmark Smart Fit"`.
6. Tier 2/3 de aluguel → alerta de fonte com recomendação de cotação local.

**RN-A4-06 — Calibração por gênero e tamanho (LLM)**
O LLM aplica ajustes de classificação/justificativa conforme `genero_alvo` e `tamanho_preset`:
- `exclusivamente_feminino`: Mix recomendado Premium > Mid (NUNCA Low). Adiciona alerta de mercado ~30% menor.
- `exclusivamente_masculino`: adiciona alerta de mercado restrito.
- `gg`: adiciona alerta de plano multi-unidade/franquia.
- `pp`: adiciona alerta de densidade urbana necessária se `score_viabilidade < 6`.

**RN-A4-07 — Zero benchmark hardcoded no prompt**
Os parâmetros numéricos do prompt (ticket, matr/m², capacidade simultânea, inadimplência, payback thresholds) são renderizados em tempo de boot por `_bloco_benchmarks()` via `param()` (lendo de `parametros_metodologia` no Supabase). Recalibrar o banco propaga automaticamente ao prompt. Nenhum número de benchmark deve ser hardcoded no agente.

**RN-A4-08 — Modelo gemini-2.5-flash (não Pro)**
O A4 usa Flash por ser aritmética estruturada (tools fazem a conta). O Pro foi revertido para Flash em 12/06 após estabilização do pipeline. Flash APENAS para o A4; A6 (síntese final) permanece Pro. Re-testar Flash com prompt anti-code-execution antes de qualquer rollback para Pro.

**RN-A4-09 — Campos obrigatórios para A6 (`_renderizar_secao_referencia_aluguel`)**
O A6 `_renderizar_secao_referencia_aluguel` lê `fonte_aluguel`, `aluguel_mensal`, `aluguel_mediana_m2`, `aluguel_mrlr_inputs` e `aviso_metodologia_aluguel` do snapshot `analise_financeira_pronto`. Só valores com fonte MRLR são narrados como aluguel de decisão. Se MRLR estiver indisponível, o relatório pede cotação local e não promove portal, anúncio ou Grounding a fonte decisória.

---

## 5. Critérios de aceite mensuráveis

- [ ] `state["analise_financeira"]` existe após execução e contém `cenarios.low`, `cenarios.mid`, `cenarios.premium` como dicts.
- [ ] `state["analise_financeira_pronto"]` existe (gravado pelo `_persistir_a4_no_state`) e é identico em campos numéricos a `state["analise_financeira"]`.
- [ ] `score_viabilidade` é float entre 0 e 10.
- [ ] `recomendacao_modelo` é um de: `"Low Cost"`, `"Mid Market"`, `"Premium"`, `"Nenhum"`.
- [ ] `alertas` é lista com ao menos 1 item quando `payback > 60` ou `margem < 10%`.
- [ ] `fonte_aluguel` contém `"Portais municipais"` quando Tier 1 suficiente, ou `"Search Grounding"` quando Tier 2, ou `"Benchmark ACAD"` quando Tier 3.
- [ ] `aluguel_pesquisa_detalhes.tier` reflete o tier efetivamente usado (1, 2 ou 3).
- [ ] `aviso_metodologia_aluguel` presente e não-vazio.
- [ ] Para `genero_alvo="exclusivamente_feminino"`, `recomendacao_modelo != "Low Cost"`.
- [ ] Smoke E2E: relatório completo com bairro Tier 1 disponível gera `fonte_aluguel` com `"Portais municipais"` e `aluguel_pesquisa_detalhes.tier == 1`.
- [ ] Sem `MALFORMED_FUNCTION_CALL` no log da macro (verificável via `finish_reason` na telemetria do A4).

---

## 6. Comportamento em degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| Tier 1 sem amostras (N=0) | Cascata para Tier 2 (Search Grounding); `motivo_tier1` documenta o motivo; `referencia_macro_bcb` é populado via BCB |
| Tier 1 e Tier 2 falham | Tier 3 (Benchmark ACAD/FipeZap); `aluguel_pesquisa_detalhes.tier == 3`; alerta de fonte adicionado a `alertas[]` |
| `analise_financeira_a4_completo` lança exceção | ADK captura; A4 emite `OUT=0`; A6 lê `analise_financeira_pronto` (se callback rodou antes da exceção) ou falha gracefully no gate do A6 |
| LLM tenta chamar `pesquisar_aluguel_mediana` separadamente | ADK não encontra a tool (não está registrada diretamente no A4); function_call falha; LLM deve usar apenas `analise_financeira_a4_completo` |
| LLM alucina tool inexistente (ex: `run_code`) | Pipeline morre naquele run — padrão histórico do Flash (run 7, 2026-06-12). Prevenido pelo prompt `regra_execucao: autonoma` e instrução `NÃO tente chamar ... separadamente` |
| Narrativa recebe aluguel sem fonte MRLR | A6 lê `analise_financeira_pronto`, omite o valor alternativo como decisão e exige validação por cotação local |

---

## 7. Contexto para IA

**Gotcha 1 — `analise_financeira_pronto` é a fonte auditável:** O A6 foi arquitetado para ler números de `analise_financeira_pronto` (tool_response cru), não de `analise_financeira` (echo do LLM). Se `_persistir_a4_no_state` não rodar (ex: exceção antes do callback), o A6 pode usar dados inconsistentes. O snapshot é idempotente: só grava se `tool.name == "analise_financeira_a4_completo"` e o response é `dict`.

**Gotcha 2 — Flash alucinando `run_code`:** O Flash tentou executar código Python para aritmética (em vez de chamar a macro) no run 7 de 12/06. O Pro foi mantido por instabilidade. Re-testar Flash com `instruction` que proíba explicitamente execução de código antes de qualquer mudança de modelo.

**Gotcha 3 — `_bloco_benchmarks()` roda em boot:** Os benchmarks são renderizados uma vez na inicialização do módulo quando `financial_estimator_agent` é construído. Mudanças em `parametros_metodologia` no Supabase exigem reinício do servidor para propagar ao prompt.

**Gotcha 4 — `destino_lat`/`destino_lng` injetados por `apply_patches.py`:** O top-1 de `candidatos_geoscout` é extraído no próprio prompt do LLM (código comentado no `instruction`). Se `candidatos_geoscout` estiver ausente ou vazio, `destino_lat/lng` ficam `None` e a macro usa fallback de distância nulo — não é erro crítico, apenas `frete_equipamentos=0` no CAPEX.

**Gotcha 5 — `schema_cenarios: "v2"`:** O shape dos cenários mudou entre versões. O A6 e o markdown renderer esperam `v2` (com `matriculas` como dict `{conservador, realista, agressivo}` onde cada item é `{valor, matr_por_m2, premissa}`). Schema v1 (onde `matriculas` era int simples) causou crash no A4 em produção (bug documentado em memória do projeto).

**Gotcha 6 — BCB só popula quando `tier1_vazio=True`:** `referencia_macro_bcb` é calculado apenas quando nenhum portal retornou amostra. É dado macro-econômico de contexto (não R$/m² local) e não substitui aluguel real.
