# Melhorias de System Prompt — Agente Conversacional (12/06/2026)

> Síntese de 3 fontes: análise dos eBooks Cortex (`Agent_Resumo e Pesquisa
> dos eBooks.zip` → Reputação/LLMO + Vendas B2B 2026), fichas de vídeo
> `context/videos/01..05` (Google Cloud Tech/ADK, com testes de validação),
> e leitura do código real (`services/conversational_engine.py`: 4 prompts
> — classificação, extração, slot-filler, confirmação — + proposta via
> template).
>
> Regra de processo: nada disso entra em produção antes da consolidação de
> junho fechar. Diffs prontos pra aplicar quando a fila liberar; os testes
> T0x.x dos vídeos são os gates de aceitação.

---

## P0 — Guardrails no classificador (vídeo 01 + eBook Reputação)

**Problema:** `_PROMPT_CLASSIFICACAO` tem 5 intenções e nenhuma rota de
recusa. "Qual cripto compro pra financiar a academia?" hoje cai em
`pergunta_simples` e o agente responde — risco reputacional direto (eBook:
hallucination/conselho fora de escopo destrói confiança; cada resposta é a
marca falando).

**Mudança no prompt (classificação):**
- Nova intenção `fora_de_escopo`: conselho de investimento financeiro,
  jurídico, tributário, médico, cripto, ou qualquer tema não relacionado a
  viabilidade/expansão/operação de academia.
- Instrução de recusa: educada, em linguagem de domínio, redireciona pro
  que o agente SABE fazer ("Análise de cripto está fora do meu campo — meu
  trabalho é viabilidade de academia. Quer que eu analise um bairro?").

**Mudança no código (junto):**
- Fallback determinístico: parse do classificador falhou/inesperado →
  trata como `fora_de_escopo`, NUNCA dispara pipeline (T01.4).
- Disclaimer legal único por sessão, na primeira resposta (T01.3): uma
  linha "análise informativa, não é recomendação de investimento" — flag
  `_disclaimer_mostrado` nos slots internos.

**Gates:** T01.1 (cripto → recusa, pipeline não roda), T01.2 (pergunta de
bairro passa), T01.3 (disclaimer 1×), T01.4 (erro de parse nega ação).

---

## P0 — Capability transparency na abertura (eBooks Vetor 4, NN/g)

**Problema:** usuário decide em ~5 segundos se o chat vale o engajamento.
Hoje a primeira mensagem não diz o que o agente faz nem o que não faz —
expectativa quebrada vira frustração (e o upload de anexos que o backend
ignora é o exemplo vivo: ADR-005).

**Mudança (mensagem de abertura, template — não LLM):**
```
Sou o especialista em expansão de academias da GymSite. O que eu faço:
• Analiso a viabilidade de abrir academia em qualquer bairro do Brasil
  (concorrência, preços, demografia, imóveis disponíveis)
• Comparo bairros e recomendo alternativas
• Gero plano de abertura com cronograma e fornecedores

O que NÃO faço: recomendação de investimento financeiro.

Exemplos: "academia média no Bessa, João Pessoa" · "compare Cocó e
Aldeota em Fortaleza"
```

**Junto:** esconder upload de anexos até a extração existir (recomendação
5.1 do doc dos eBooks; vídeo 05 mapeia a implementação futura com Gemini
Vision — T05.1-T05.5 são os gates de quando ela vier).

---

## P1 — Slot-filler de formulário → consultor com dado (eBooks Vetor 1)

**Problema:** `_PROMPT_SLOT_FILLER` pergunta bem, mas seco. eBook
Reputação: copy deve carregar DADO estruturado (entidade + número + fonte)
— é o que diferencia consultor de formulário, pra humano E pra LLM que um
dia cite a marca (LLMO).

**Mudança no prompt (acréscimo):**
```
- Quando souber a cidade, demonstre conhecimento: 1 fato relevante curto
  ("João Pessoa tem um dos m² mais valorizados do Nordeste — o bairro
  importa muito").
- Toda afirmação factual com número: inclua a fonte entre parênteses ou
  declare estimativa. NUNCA invente número (se não sabe, não cita).
- Cada pergunta termina orientando a próxima ação do usuário (1 pergunta,
  zero listas).
```

**Fase 2 (pós-bundle):** injetar no contexto do prompt o snapshot do
`market_bundle` da cidade (pop., renda, nº academias) — aí o "1 fato" vem
de dado nosso auditável, não da memória do modelo (T02.2/T02.3: dado real
da ferramenta, não inventado).

---

## P1 — Proposta de confirmação enriquecida (eBooks Vetor 1)

**Problema:** proposta atual lista "Cidade: João Pessoa · Bairro: Bessa"
— formulário. eBook manda: "João Pessoa (PB) — 815 mil hab, renda média
R$ 2.800" — consultor que já demonstra a inteligência ANTES do relatório
(aumenta taxa de confirmação, métrica-alvo > 50%).

**Mudança:** template da proposta ganha linha de contexto por entidade
quando o dado existir (bundle/cache); sem dado → formato atual (nunca
inventar — P-004 vale pra texto também).

---

## P1 — Regra transversal de citação + incerteza (eBooks Vetor 5, vídeo 02)

Adicionar a TODOS os prompts geradores de texto (slot-filler, A6, A9):

```
REGRAS DE CONFIANÇA:
1. Número factual → fonte nomeada ("IBGE 2022", "Places", "anúncio
   ImovelWeb") ou rótulo "estimativa".
2. Não tem o dado → diga que não tem e o que faria pra obter. Proibido
   fabricar.
3. Entidades sempre completas na primeira menção: "Smart Fit Papicu
   (Fortaleza/CE)", nunca "ela"/"a unidade" sem antecedente claro.
```

A regra 3 é LLMO puro (eBooks Vetor 1): relatório com entidade nomeada e
bloco atômico é citável por LLM externo E recuperável pelo NOSSO RAG
(sinergia direta com o crédito GCP de R$ 5.7k → Vertex AI Search indexando
relatórios — quanto mais citável o texto, melhor o chat premium).

---

## P2 — Métrica → próxima ação nos relatórios (eBook Vendas)

Regra de prompt pro A6/A9: **todo indicador apresentado vem com a ação que
ele dispara** ("Saturação 7/10 → evite musculação pura; o gap é X"). eBook:
"indicadores orientam a próxima ação, não explicam o passado". Já é a
filosofia do plano de abertura — falta virar regra explícita de prompt pra
nunca regredir.

---

## Mapa vídeos → roadmap (não é prompt, é fila)

| Vídeo | Feature | Onde está na fila |
|---|---|---|
| 01 Guardrails | callbacks + juiz + cache | P0 acima (prompt) + LangCache já existe |
| 02 Multiagente | orquestrador + sub-agentes | A0-A9 JÁ é multiagente; falta isolamento de falha (T02.4) e rastreabilidade por resposta (T02.5) |
| 03 Longa duração | projeto vivo entre sessões | ponte `sessions` → `user_projects` (F2/F3, já na fila) — T03.1-T03.5 são os gates |
| 04 MCP dados | fontes atrás de servidor MCP | pós-Motor v2; casa com Trilha 6 (BigQuery) e mata fragilidade de scraper (BUG-003) |
| 05 Visão anexos | extração de foto/planta | curto prazo: ESCONDER upload (P0 acima); médio: Gemini Vision com T05.1-T05.5 |

## Ordem de aplicação (quando a fila liberar)

1. P0 guardrails + P0 abertura/esconder-upload — 1 sessão, risco baixo,
   valor reputacional imediato.
2. P1 citação+incerteza transversal — 1 sessão (3 prompts).
3. P1 slot-filler consultor + proposta enriquecida — depende do bundle pra
   versão com dado; versão sem dado pode ir junto do item 2.
4. P2 métrica→ação — junto da próxima mexida no A6/A9.
