# SPEC_A5_ContactHunter.md

---

| Campo | Valor |
|---|---|
| **ID** | A5 |
| **Agente** | ContactHunter |
| **Modelo LLM** | **Determinístico** — sem LLM (`BaseAgent`) |
| **Versão** | 1.0 |
| **Data** | 2026-06-18 |

---

## 1. Responsabilidade Única (C6.1)

Identificar o decisor do candidato #1 e gerar script de abordagem comercial, executando a macro-tool `gerar_contato_decisor_completo` de forma determinística e gravando o resultado em `contato_decisor` no session state.

---

## 2. Contrato de Entrada

| Chave do State | Tipo | Descrição |
|---|---|---|
| `candidatos_geoscout` ou `candidatos_geoscout_pronto` | dict | Output do A1 com os candidatos ranqueados; a macro lê o top candidato internamente via `_StateShim.state` |
| `market_context` | dict/str | Contexto de mercado (A0); a macro acessa para cidade/bairro/tipo de negócio |
| `contato_decisor` | — | Não lido na entrada; sobrescrito na saída |

> A5 não acessa o state diretamente: usa `_StateShim(state)` (linhas 27-31 do código) para passar o state inteiro como `tool_context` à macro, que extrai o que precisar.

---

## 3. Contrato de Saída

**output_key**: não usa `output_key` ADK. Emite `EventActions(state_delta={"contato_decisor": result})` diretamente.

| Campo gravado | Tipo | Descrição |
|---|---|---|
| `contato_decisor` | dict | Resultado completo da macro `gerar_contato_decisor_completo`, incluindo: decisor (nome, cargo, canais), canal de abordagem, `script_abordagem`, próximos passos |
| `contato_decisor.erro` | str | Presente **em vez** dos campos normais quando a macro falha (ex: `{"erro": "ExceptionType: mensagem"}`) |

### Campos esperados quando sucesso

A macro `gerar_contato_decisor_completo` (em `tools/contact_tools.py`) monta o dict completo. Os campos mínimos esperados pelo A6 são:

| Campo | Uso no A6 |
|---|---|
| `decisor` | Exibido no relatório como contato prioritário |
| `script_abordagem` | Incluído na seção de contato do relatório |
| `resumo_executivo` | **Sobrescrito pelo A6** em `_extrair_relatorio_estruturado` via `_resumo_executivo_deterministico` (linhas 2584-2590) |

> **Atenção:** o campo `resumo_executivo` que chega do A5 é sobreposto pelo A6. O A5 não é responsável pelo resumo executivo final.

---

## 4. Regras de Negócio

**RN-A5-01 — Execução exclusivamente determinística.**
A5 é um `BaseAgent` (não `LlmAgent`). Roda `asyncio.to_thread(gerar_contato_decisor_completo, _StateShim(state))` e não faz nenhuma chamada LLM. Mudanças que reintroduzam LLM neste agente requerem SPEC atualizada e aprovação (ver histórico de refatoração no docstring: linha 3-13 do arquivo).

**RN-A5-02 — Falha não derruba o pipeline.**
Todo o bloco de execução é envolvido em `try/except Exception` (linhas 44-51). Em caso de erro, grava `{"erro": "TipoExcecao: mensagem"}` em `contato_decisor`. O A6 degrada graciosamente sem contato (linhas 2252-2253 do A6: `contato = contato_raw if isinstance(contato_raw, dict) else {}`).

**RN-A5-03 — Resultado deve ser dict.**
Se `gerar_contato_decisor_completo` retornar algo que não seja `dict`, o A5 substitui por `{}` (linha 47-48: `if not isinstance(result, dict): result = {}`). Nunca grava string ou None.

**RN-A5-04 — Execução em thread separada.**
A macro é síncrona (I/O potencial: Apollo, CNPJ lookup). `asyncio.to_thread` garante que não bloqueie o event loop do ADK.

**RN-A5-05 — Fora do pipeline de viabilidade.**
A5 é chamado **após** os agentes A1-A4 e **antes** do A6. Não lê outputs de viabilidade financeira; só precisa do candidato top para identificar o decisor.

---

## 5. Critérios de Aceite Mensuráveis

- [ ] `contato_decisor` está presente no session state após execução do A5
- [ ] `contato_decisor` é sempre um `dict` (nunca `None`, nunca `str`)
- [ ] Em caso de falha da macro, `contato_decisor` contém chave `"erro"` com mensagem não vazia
- [ ] Nenhum token LLM é consumido durante execução do A5 (verificável via `token_telemetry`)
- [ ] Pipeline completo não é interrompido quando A5 falha (smoke test: mock de falha em `gerar_contato_decisor_completo`)
- [ ] Teste unitário cobre: (a) sucesso normal, (b) macro retorna não-dict, (c) macro levanta exceção

---

## 6. Comportamento em Degradação (C4.4)

| Cenário | Comportamento |
|---|---|
| `gerar_contato_decisor_completo` levanta exceção | Grava `{"erro": "TipoExcecao: msg"}` em `contato_decisor`; pipeline segue |
| `gerar_contato_decisor_completo` retorna não-dict | Grava `{}` em `contato_decisor`; pipeline segue |
| State sem `candidatos_geoscout` | A macro recebe state vazio via `_StateShim`; comportamento depende da implementação interna da macro (esperado: retorno gracioso) |
| Thread timeout (I/O lento) | `asyncio.to_thread` herda o timeout do evento ADK pai; exceção capturada pelo `try/except` |

---

## 7. Contexto para IA

### Gotchas e invariantes

- **A5 usa `_StateShim`**: a macro `gerar_contato_decisor_completo` espera um objeto com atributo `.state` (interface `tool_context`). A5 não passa o `ctx` do ADK diretamente; cria um shim mínimo. Código que tente acessar `tool_context.session` ou `tool_context.invocation_id` dentro da macro quebrará.

- **Não é um agente de viabilidade**: A5 é o agente de *prospecção de contato*, separado do pipeline de viabilidade (A1-A4). Conforme a nota na memória do projeto (`project_gymsite_apollo_subutilizado_a5.md`), o A5 usa Apollo atualmente apenas como name-matcher do QSA; busca por `title/seniority` e email verificado são backlog.

- **`resumo_executivo` é sobrescrito pelo A6**: o campo `contato_decisor.resumo_executivo` que o A5 entrega é sempre substituído pelo resumo determinístico gerado em `_resumo_executivo_deterministico` (A6, linha 2585). Não adicionar lógica de resumo no A5 esperando que seja o final.

- **Histórico de refatoração**: antes de 2026-06-16, A5 era `LlmAgent` (gemini-3.6-flash) que consumia ~225k tokens de INPUT por relatório para re-emitir o output da macro sem decisão própria. O `after_agent_callback` de fallback já repopulava do determinístico quando o LLM vinha vazio — isso era o sinal de que o LLM era dispensável. A versão atual corta esse custo a zero.

- **Padrão igual ao A3a/A2**: A5 segue o mesmo padrão de agente determinístico adotado em A3a e A2 — `BaseAgent` + `EventActions(state_delta=...)` sem output_key ADK.
