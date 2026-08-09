# SPEC_A0_ContextBuilder.md

---
id: spec-a0-001
agente: ContextBuilder
modelo_llm: gemini-2.5-flash (thinking_budget=1024)
versao: 1.1
data: 2026-07-16
constitution: C2.1, C2.3, C6.1
---

## 1. Responsabilidade Única

O A0 ContextBuilder é o **primeiro agente do pipeline** e tem escopo exclusivo de **coleta e consolidação de fatos de mercado**: dados qualitativos via **market_bundle** (Deep Research / Kimi **removidos** — Act-on 2026-07-16), dados quantitativos CNPJ/CNO e competição OSM local. Ele não faz análise preditiva, não pontua candidatos e não emite recomendações além dos dados devolvidos pelas tools — qualquer dado não retornado por tool é marcado como `"dados_nao_disponiveis"`.

---

## 2. Contrato de Entrada

| Chave no `state` | Tipo | Origem |
|---|---|---|
| `input_params` | `dict` | `api.py` (usuário) |
| `input_params.cidade` | `str` | usuário |
| `input_params.bairro` | `str` | usuário |
| `input_params.uf` | `str` (2 letras) | usuário |
| `input_params.genero_alvo` | `str` | usuário (opcional) |
| `input_params.tipo_negocio` | `str` | usuário (opcional) |
| `input_params.tamanho_preset` | `str` (`s`/`m`/`l`) | usuário (opcional) |

O agente também lê `cidade`, `uf`, `bairro` diretamente na raiz do `state` como fallback, embora a fonte canônica seja `input_params`.

---

## 3. Contrato de Saída

**`output_key`**: `market_context`

O valor é um JSON com chave de envelope `"market_context"` contendo os seguintes campos principais:

| Campo | Tipo | Descrição |
|---|---|---|
| `cidade` | `str` | Cidade analisada |
| `bairro` | `str` | Bairro analisado |
| `uf` | `str` | UF (2 letras) |
| `ticket_medio_mercado` | `str` | Ticket médio de academia na cidade/bairro |
| `aluguel_medio_m2` | `str` | Referência batch (`bundle.aluguel_portais`) se existir — **não** substitui A4 MRLR |
| `renda_media_bairro` | `str` \| `"dados_nao_disponiveis"` | Renda do bairro (frequentemente indisponível) |
| `faixa_etaria_predominante` | `str` | Faixa demográfica predominante |
| `genero_alvo` | `str` | Default `"misto"` |
| `tipo_negocio` | `str` | Default `"academia"` |
| `tamanho_preset` | `str` | `s`/`m`/`l` |
| `principais_redes_concorrentes` | `list[str]` | Somente `redes_detectadas_osm` da tool local |
| `tendencia_mercado` | `str` | `"crescimento"` \| `"estavel"` \| `"retracao"` |
| `regulamentacao_resumo` | `str` | Resumo regulatório |
| `insights_estrategicos` | `list[str]` | Ao menos 3 insights com fonte rotulada |
| `parque_ativo_total` | `int` | Total de CNPJs fitness ativos |
| `parque_comercial_total` | `int` | Total CNPJs comerciais |
| `novos_cnpj_fitness_90d` | `int` | Aberturas fitness nos últimos 90 dias (`as_of`) |
| `baixas_cnpj_fitness_90d` | `int` | Baixas (`situacao=08`) na janela 90d |
| `baixas_cnpj_fitness_q` | `int` | Baixas no último trimestre civil fechado |
| `entrantes_cnpj_fitness_q` | `int` | Aberturas no último Q fechado |
| `saldo_oferta_q` | `int` | entrantes_q − baixas_q |
| `pressao_oferta_q` | `str` | `retracao` \| `expansao` \| `neutro` (sinal por saldo_q) |
| `janela_q_label` | `str` | Ex. `2026-Q1` |
| `cnpj_as_of` | `str` | Âncora temporal (`min(hoje, fim ref_month)`) |
| `arvore_oferta` | `dict` | Estoque/entrantes/baixas × mun/bairro × 90d/Q + carimbo |
| `redes` | `dict` | Multunidade vs solo por `cnpj_basico` (≥2 ativos BR) |
| `excluidos_saude_clinica` | `int` | CNPJs excluídos (saúde/clínica) |
| `pendentes_validacao` | `int` | CNPJs pendentes de validação |
| `composicao_parque` | `dict` | Distribuição por segmento |
| `novas_unidades_90d_por_segmento` | `dict` | Aberturas 90d por segmento |
| `academias_ativas_cidade_cnpj` | `int` | Academias ativas per CNPJ |
| `serie_aberturas_anual` | `dict` | Série histórica de aberturas por ano |
| `fatos_parque_cnpj` | `dict` | Sub-objeto com métricas, indicadores derivados, cruzamento CNO, lacunas |
| `fonte_entrantes` | `str` | Fonte dos dados de entrantes |
| `fonte` | `str` | `"market_bundle + CNPJ/CNO (tools)"` |
| `data_coleta` | `str` | Data no formato `YYYY-MM-DD` |
| `cached` | `bool` | Se veio de bundle cacheado |
| `briefing_completo_md` | `str` | Markdown completo do market bundle (quando disponível) |

---

## 4. Regras de Negócio

**RN-A0-01 — Proibição de inventar dados**
Se a tool não retornou o dado, o campo recebe `"dados_nao_disponiveis"` ou é omitido. É proibido emitir achismos, frases como "parece que" ou oportunidades/riscos sem fonte explícita.

**RN-A0-02 — Proibição da palavra "estoque"**
O term "estoque" é proibido em toda saída. Usar "parque ativo" para unidades no CNPJ e "aberturas recentes" / "fluxo de aberturas" para novas unidades em 90 dias.

**RN-A0-03 — Prioridade do market bundle**
`carregar_market_bundle(cidade, bairro, uf)` é chamado **primeiro**. Se retornar briefing com marcador `<!-- market_bundle` (sem `status=missing`), o bundle é usado como `briefing_completo_md`.

**RN-A0-04 — Deep Research / Kimi OFF (Act-on 2026-07-16)**
`rodar_deep_research` e `rodar_kimi_research` **não estão** nas tools do A0. Bundle missing ou lacuna qualitativa → `"dados_nao_disponiveis"`. Renda = A2/`renda_bairro`; concorrência detalhada = A3a; aluguel viabilidade = A4 MRLR.

**RN-A0-05 — Fonte de concorrentes**
`principais_redes_concorrentes` é preenchido **somente** com `redes_detectadas_osm` retornado pela tool `fatos_competicao_local`. Se a tool falhar ou retornar lista vazia, o campo recebe `[]`. Proibido inventar redes.

**RN-A0-06 — Insights com fonte rotulada**
Cada item de `insights_estrategicos` deve ser 1 frase com a fonte entre parênteses: `(market_bundle)`, `(CNPJ)`, `(CNO)` ou `(OSM)`. Ao menos 1 insight deve citar número CNPJ.

**RN-A0-07 — Regras CNPJ (campos escalares)**
Os campos escalares (`parque_ativo_total`, `novos_cnpj_fitness_90d`, etc.) devem ser copiados de `metricas_objetivas` retornado pela tool `dados_parque_cnpj_para_a0`. `fatos_parque_cnpj.indicadores_derivados` recebe apenas o que a tool calculou (ex: `taxa_renovacao_parque_90d_pct`, `segmento_dominante_parque`).

**RN-A0-08 — Divergência parque vs aberturas**
Se a tool CNPJ retornar `divergencia_parque_vs_aberturas=true`, o fato deve ser registrado em `fatos_parque_cnpj` como fato descritivo ("parque dominado por X; aberturas 90d por Y") — sem recomendar ação.

**RN-A0-09 — CNO: area_m2 só com match real**
`cruzamento_cno` recebe `resumo_match` e até 5 entrantes com `area_m2_obra` preenchida. Se `sem_obra > 0`, listar em `lacunas` — não estimar m² por chute.

**RN-A0-10 — Ordem canônica das tools**
1. `carregar_market_bundle` → 2. `dados_parque_cnpj_para_a0` → 3. `fatos_competicao_local`.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `market_context` é sempre um dict (nunca `None` ou string).
- [ ] `insights_estrategicos` contém ao menos 1 item com `(CNPJ)` na string.
- [ ] Nenhum item de `insights_estrategicos` contém a palavra "estoque".
- [ ] `principais_redes_concorrentes` é `list` (pode ser vazia, nunca `None`).
- [ ] Trace A0 **não** contém `rodar_deep_research` nem `rodar_kimi_research`.
- [ ] Bundle ausente → campos qualitativos `"dados_nao_disponiveis"`; pipeline segue.
- [ ] `parque_ativo_total` é `int >= 0` (não string, não None).
- [ ] `fonte` contém a string `"CNPJ/CNO (tools)"`.
- [ ] `data_coleta` está no formato `YYYY-MM-DD`.

---

## 6. Comportamento em Degradação (Fail-Soft, C4.4)

| Cenário | Comportamento |
|---|---|
| Bundle missing / lacuna qualitativa | Campos → `"dados_nao_disponiveis"`; **sem** DR/Kimi |
| `dados_parque_cnpj_para_a0` erro | `fatos_parque_cnpj.lacunas` descreve a falha; campos CNPJ recebem `0` ou `{}` |
| `fatos_competicao_local` falha ou lista vazia | `principais_redes_concorrentes = []` |
| Todos os tools falham | JSON com zeros/`dados_nao_disponiveis`; **nunca** derruba o pipeline |

---

## 7. Contexto para IA

**Gotchas críticos:**

- **"estoque" é campo minado**: qualquer ferramenta de lint/review deve rejeitar essa palavra na saída do A0. O substituto correto é "parque ativo" (CNPJ) e "fluxo de aberturas" (90d).

- **Deep Research não entrega renda por bairro**: esse comportamento foi verificado empiricamente no caso Parangaba (CE). Não adianta chamar DR esperando `renda_media_bairro` por bairro — o modelo não tem essa granularidade. Deixar como `"dados_nao_disponiveis"` é o comportamento correto, não um bug.

- **`principais_redes_concorrentes` tem fonte única**: vem **apenas** de `fatos_competicao_local` → `redes_detectadas_osm`. O LLM tem forte tendência a copiar redes mencionadas no texto do Deep Research para esse campo — isso é proibido por RN-A0-05.

- **`carregar_market_bundle` é síncrono e deve ser a primeira chamada**: chamá-lo depois do DR resulta em DR cobrado desnecessariamente.

- **Invariante de envelope**: a saída tem **duplo envelope** — `output_key="market_context"` e dentro há `{"market_context": {...}}`. Agentes downstream como A2 usam `_parse_market_context(state.get("market_context"))` que desembala esse envelope. Não "achatar" a estrutura.

- **Tool `fatos_competicao_local` pode fazer geocode externo**: pode ser lenta ou falhar em ambientes sem acesso à internet. O agente deve prosseguir sem ela (RN-A0-05: lista vazia).

- **thinking_budget=1024**: o A0 usa thinking, o que eleva o custo. Não aumentar sem análise de custo.

- **`build_llm_agent`**: o agente é construído via `agent_factory.build_llm_agent` que injeta retry (4 tentativas, exp backoff para 429/503/500) e telemetria de tokens. Não instanciar `Agent(...)` diretamente.
