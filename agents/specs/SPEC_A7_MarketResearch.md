# SPEC_A7_MarketResearch.md

---

| Campo | Valor |
|---|---|
| **ID** | A7 |
| **Agente** | MarketResearch |
| **Modelo LLM** | `gemini-2.5-flash` via `build_llm_agent` + `google_search` grounding |
| **Versão** | 1.1 |
| **Data** | 2026-07-13 |

---

## 1. Responsabilidade Única (C6.1)

Executar pesquisa em tempo real via Google Search Grounding para gaps qualitativos que **não** são cobertos pelo pipeline determinístico: crowdsource §14, pico narrativo residual, contexto web pontual com carimbo.

**Fora do escopo A7 (jul/2026):** aluguel de viabilidade → **A4 MRLR** (`aluguel_mrlr.py`); concorrência → **A3a** SearchAPI; demografia → **A2** IBGE. A7 **não** substitui essas fontes mesmo no chat.

---

## 2. Contrato de Entrada

A7 é acionado diretamente pelo `root_agent` via mensagem do usuário ou roteamento condicional. Não lê chaves estruturadas do session state de outros agentes.

| Fonte | Conteúdo |
|---|---|
| Mensagem do usuário/root_agent | Tema da pesquisa + termos (cidade, bairro, nome de academia, tipo de dado) |
| `google_search` tool (ADK built-in) | Grounding automático Gemini — não configurável além de declarar a tool |

> **Limitação de design**: por restrição da API ADK/Gemini, A7 **não pode ter nenhuma outra tool além de `google_search`** (docstring, linha 6-8 do arquivo). Adicionar qualquer outra tool quebra o agente.

---

## 3. Contrato de Saída

**output_key**: `market_research_result` (configurado via `build_llm_agent`, linha 19).

| Campo gravado | Tipo | Descrição |
|---|---|---|
| `market_research_result` | str (markdown) | Resultado estruturado da pesquisa conforme template da instrução |

### Estrutura esperada do markdown de saída

```
# Pesquisa de Mercado — <Tema>

## Resumo
<3-5 linhas com a resposta principal>

## Detalhes
<bullets ou parágrafos com dados extraídos>

## Fontes
- [<Título da fonte 1>](<URL>)
- [<Título da fonte 2>](<URL>)

## Confiabilidade
<ALTA/MEDIA/BAIXA + justificativa>
```

A seção `## Fontes` com URLs reais do grounding é **obrigatória** (ver RN-A7-03).

---

## 4. Regras de Negócio

**RN-A7-01 — Execução autônoma, sem confirmação.**
A7 nunca solicita confirmação ao usuário. Recebeu o tema → executa a pesquisa imediatamente com os termos disponíveis (instrução: "NUNCA peça confirmação. Execute a pesquisa SEMPRE com os termos do usuário").

**RN-A7-02 — Anti-alucinação: declare ausência em vez de inventar.**
Se o Google Search Grounding não retornar dados para uma consulta, A7 declara explicitamente "Sem dados públicos disponíveis" para o item em questão. Proibido inventar números ou URLs (instrução: "NUNCA invente dados").

**RN-A7-03 — Seção `## Fontes` é obrigatória.**
Todo relatório de A7 deve incluir a seção `## Fontes` com pelo menos uma URL real extraída do grounding. Ausência de fontes = hallucination risk alto. Esta seção é o mecanismo de grounding verificável exigido pela cláusula C8.3 da CONSTITUTION.

**RN-A7-04 — Dados numéricos em range, não ponto único (exceto aluguel viabilidade).**
Para custos operacionais genéricos: preferir range com carimbo "Estimativa baseada em...". **Aluguel de viabilidade/OPEX:** redirecionar ao A4/`estimar_investimento` (MRLR) — A7 não produz R$/m² para decisão financeira. Para horários de pico: preferir forma direta (ex: "lotado 18h-21h") ou declarar ausência; fonte primária de pico no pipeline = A3a SearchAPI.

**RN-A7-05 — Isolamento de tool: apenas `google_search`.**
A7 só pode ter `google_search` como tool. Qualquer outra tool (function tool, built-in ADK) causa incompatibilidade com a API de Search Grounding do Gemini. A instanciação em `tools=[google_search]` (linha 82) não deve ser alterada sem testes.

**RN-A7-06 — Acionamento condicional pelo root_agent.**
A7 é acionado em dois cenários: (a) usuário solicita explicitamente "pesquisa de mercado", "preços atuais" etc.; (b) pipeline solicitou fallback narrativo de horários de pico quando o scraper Playwright falhou (Knowledge Panel indisponível). Fora desses contextos, A7 não deve ser acionado desnecessariamente (custo de grounding).

**RN-A7-07 — Consumidores leem `state["market_research_result"]` por contrato.**
Antes de 2026-06-16, A7 não tinha `output_key` e o resultado se perdia no state (comentário no código, linhas 15-19). Agora o `output_key="market_research_result"` garante propagação. Código que acesse o resultado de A7 deve usar esta chave.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `market_research_result` está presente no session state após execução do A7
- [ ] `market_research_result` é string markdown não vazia
- [ ] A string contém a seção `## Fontes` com pelo menos uma URL (grounding verificável)
- [ ] Para pesquisa de **aluguel viabilidade**: A7 **não** é acionado — usar A4 MRLR ou `estimar_investimento` no site
- [ ] Para pesquisa de horários de pico (chat): resultado inclui horário específico ou declara ausência; pipeline usa A3a como primário
- [ ] Seção `## Confiabilidade` está presente com classificação ALTA/MEDIA/BAIXA
- [ ] A7 não chama nenhuma tool além de `google_search` (verificável via log ADK de tool calls)
- [ ] Execução não solicita confirmação ao usuário (verificável em smoke test com inputs parciais)

---

## 6. Comportamento em Degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| Google Search não retorna resultados para a query | A7 declara "Sem dados públicos disponíveis" na seção correspondente; entrega markdown com `## Fontes` vazio mas seção presente |
| Google Search Grounding API indisponível (timeout/erro) | ADK propaga erro ao root_agent; root_agent deve tratar com circuit breaker (C5.4); A7 em si não tem retry interno |
| Usuário fornece termos ambíguos (sem cidade/bairro) | A7 tenta a pesquisa com os termos disponíveis e declara a incerteza na seção `## Confiabilidade` |
| Resultado do grounding está em idioma estrangeiro | A7 deve traduzir e adaptar pro contexto brasileiro; não entregar texto em inglês como resposta final |

---

## 7. Contexto para IA

### Gotchas e invariantes

- **Única tool = `google_search`**: esta restrição não é opcional. A API do Gemini Search Grounding (modo nativo) entra em conflito com function calling quando outras tools estão presentes. O workaround atual é isolar o A7 como agente dedicado sem nenhuma tool extra.

- **`output_key="market_research_result"` foi bug histórico**: antes de existir, o resultado do A7 ia para um output key default interno do ADK e se perdia para outros agentes. O comentário nas linhas 15-19 do código documenta isso como fix de C6.2/C6.4. Ao criar novos agentes com `build_llm_agent`, sempre declarar `output_key` explícito se o resultado precisa ser acessado por outros agentes.

- **A7 é acionado pelo root_agent / chat, não pelo pipeline de viabilidade**: o pipeline corre A0 → A1 → ParallelAnalysis(A2, A3a→A3b, A4) → A6 → A9. A7 cobre gaps qualitativos on-demand (crowdsource §14, web pontual). **Aluguel = A4 MRLR Tier 0**, nunca A7 SearchAPI.

- **Queries de horários de pico:** fonte primária = A3a SearchAPI (`popular_times`). A7 só como fallback **narrativo** no chat quando Maps não tem Knowledge Panel — não entra na fórmula de viabilidade.

- **Canônico de fontes:** antes de mudar A7, ler `.agent/rules/conferencia-fontes-pipeline.md` §5.

- **Confiabilidade deve refletir a real**: "ALTA" só quando o grounding retornou dados de fontes primárias identificáveis (sites oficiais, portais imobiliários como VivaReal/ZAP, relatórios setoriais ACAD/Sebrae). "MEDIA" para estimativas de secundárias. "BAIXA" quando os dados são indiretos ou escassos. Classificação otimista sem base = hallucination.
