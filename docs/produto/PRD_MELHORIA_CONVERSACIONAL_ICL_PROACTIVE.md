# PRD — Melhoria Conversacional (ICL, Proactive Dialogue, State)

> **Curadoria GymSite · 2026-07-14** (#3 da série)  
> Alvos: site agent + consultor legado.  
> Relacionados: [#1 slot](./PRD_SLOT_TRACKING_CONTEXTO_CONVERSACIONAL.md) · [#2 elipse](./PRD_RESILIENCIA_CONTEXTO_ELIPSE.md)

---

## Veredito

**Diagnóstico de produto é o melhor dos três PRDs. Implementação proposta (§4) está inchada e incompatível com o runner atual.**

O que o usuário sentiu na conversa real está certo:
1. “Parangaba” após a pergunta → o modelo já resolve via ICL (histórico) — não precisa de máquina de estados só pra isso.
2. Falta **oferta do próximo passo** depois dos concorrentes (proactive).
3. Falta **não perder o Mercado** em follow-ups (“mensalidade da Smart Fit?”).
4. Adaptar tom pelo padrão do usuário é nice-to-have, não núcleo.

O código “pronto” do PRD **não deve ser colado**:
- Cada turno do site cria `InMemorySessionService()` + `create_session` do zero (`runner._rodar_turno`) → `session_state` / `gym_site_state` **morre entre turnos**.
- `update_entities` com regex + hardcode `parangab` compete e piora o módulo já curado `localizacao.py` (#94).
- Misturar fill de args com `gate_degustacao` (#2 F3) — **recusado** de novo.
- Mutar `callback_context.agent.instruction` em runtime é frágil no ADK e difícil de testar.
- `user_patterns` / few-shot dinâmico em 2–3 turnos de degustação: pouco sinal, risco de “aprender” errado.

---

## Ranking deste PRD (fatias)

| Rank | Fatia | Valor | Esforço | Status | Decisão |
|------|-------|-------|---------|--------|---------|
| 1 | Continuidade Mercado em follow-up (mensalidade, reviews, “lá”) | Alto | Baixo–médio | ❌/🟡 | **Fazer** = sticky #2 + prompt root |
| 2 | Proactive: após concorrentes oferecer reviews (1 CTA) | Alto | Baixo | ❌ | **Fazer** — regra no prompt Mercado (+ checklist sem repetir oferta) |
| 3 | Coref “eles / essas academias” → última lista | Alto | Médio | ❌ | **Fazer** = #1 RF4 + hint no prompt |
| 4 | Bloco curto `[conversa: fase=…; pending=…]` no runner | Médio | Médio | ❌ | Fazer **só** o mínimo em `user_projects` JSONB |
| 5 | Tom “direto” se msgs curtas | Baixo–médio | Baixo | ❌ | **Polir** no prompt; sem detector pesado |
| 6 | FSM completa (fases Enum, topic_stack, turn_history no ADK state) | Baixo | Alto | ❌ | **Recusar / adiar** |
| 7 | `conversation_state.py` + callbacks como no §4 | — | Alto | ❌ | **Não colar** |
| 8 | Pattern Recognition (“sempre pede bairro vizinho”) | Baixo na degustação | Alto | ❌ | Adiar (sessões curtas, K=2 amostras) |

---

## Adaptação canônica (substitui o §4)

| PRD §4 | GymSite |
|--------|---------|
| `ConversationState` em ADK `session_state` | Persistir em `user_projects` (ex.: `mercado` / `concorrencia` JSONB): `active_agent`, `pending_offer`, `ultimos_resultados`, entities já em `localizacao` |
| `before_model_callback` mutando instruction | Prefixo na mensagem no **runner** (já faz `[localizacao_resolvida:]`) — acrescentar `[conversa:…]` / `[slot_reaproveitado:…]` |
| `after_model_callback` | Atualizar JSONB a partir de `tool_calls` já salvos em `project_messages` (determinístico) |
| `before_tool_callback_with_state` | Gate intacto; fill opcional em callback **separado** ou args já preenchidos pelo LLM graças ao bloco inject |
| Máquina `PendingIntent` rica | Enum mínimo: `none \| offer_reviews \| offer_plataforma` — o bastante p/ degustação |
| Detectores de padrão | Uma linha no prompt: “se o usuário for curto, seja curto” |

### Proactive Dialogue (escopo fechado)

Após `buscar_concorrentes` com sucesso, a resposta **deve** terminar com **uma** oferta, nesta ordem de preferência:
1. “Quer que eu veja o que os alunos reclamam nessas academias?” → `analisar_reviews_e_dores`
2. Se reviews já foram amostra / gate → convite plataforma (CTA)

Não oferecer mensalidade/investimento se a tool não existir ou estiver bloqueada no gate (evita prometer Tier 2 na degustação).

### Root continuity

Não confiar só em prompt: se último `project_messages.agente == Mercado` e a mensagem casa com follow-up mercado (preço, mensalidade, review, “lá”, “eles”, “e o”), **pinar Mercado** (`_PINADOS`) — igual US03 do #2.

---

## Sobreposição com #1 e #2

| Ideia deste PRD | Já coberta por |
|-----------------|----------------|
| Não reperguntar bairro | #1 / #94 |
| Fragmento “Parangaba” | ICL + #1 + sticky #2 |
| “Mensalidade Smart Fit” no Mercado | sticky #2 US03 |
| “O segundo / eles” | #1 RF4 |
| Proactive próximo passo | **Novo** neste #3 (prompt + flag `pending_offer`) |
| FSM + patterns + few-shot dinâmico | Novo e **fora** da fila curta |

---

## Aceite (fase enxuta)

- [ ] Após listar concorrentes, sempre há 1 CTA de próximo passo (reviews ou plataforma).
- [ ] “E os reviews?” / “mensalidade da Smart Fit?” permanece no Mercado (pinagem).
- [ ] Nenhuma máquina `ConversationState` em memória ADK efêmera.
- [ ] Gate de degustação inalterado em responsabilidade.
- [ ] Sem hardcode de bairro no extrator.

---

## Documento original — problema e visão (preservado)

### O problema (conversa real)
Turno 1: agente pede bairro em Fortaleza.  
Turno 2: “Parangaba”.  
Turno 3: agente entende e busca — **ICL nativo funcionou**.  

Faltou: antecipar próximo passo (preços/reviews); adaptar tom; root não saber que está no meio da análise de viabilidade (risco de mandar “mensalidade Smart Fit” para Técnico).

### Termos
ICL, Conversational State Tracking, Coreference, Proactive Dialogue, Pattern Recognition — ver tabela no PRD fonte.

### Arquitetura proposta (fonte)
Camada de estado (topic_stack, entities, turn_count, user_patterns, pending_intent) → callbacks ADK → prompt ICL/proactive.

### Checklist fonte (não executar como escrito)
Criar `conversation_state.py` / `callbacks.py` / trocar gate / atualizar root — **substituído pela adaptação canônica acima**.
