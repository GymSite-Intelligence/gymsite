# Curadoria de PRDs — site agent + consultor legado

Lista viva dos PRDs avaliados para melhorias práticas de conversação (degustação / consultor).  
Só entra o que tem caminho claro no código atual e retorno de uso.

> **Documento canônico da decisão (MD + PDF + layouts Mermaid):**  
> [DECISAO_CURADORIA_PRDS_CONVERSACIONAIS.md](./DECISAO_CURADORIA_PRDS_CONVERSACIONAIS.md) ·  
> [PDF](./DECISAO_CURADORIA_PRDS_CONVERSACIONAIS.pdf)

## Entrada comum (comparação justa)

Os três modelos receberam **o mesmo pacote** (textos de contexto + código do `agents_site`).  
Não houve “um viu a conversa do usuário e os outros não”. A diferença é só **ângulo e proposta** de cada modelo.

## Definição — o que é o 1, o 2 e o 3

| # | Modelo | Nome curto | Em uma linha: o que esse PRD **é** |
|---|--------|------------|-------------------------------------|
| **1** | Claude Sonnet 4.5 médio | Slot tracking | Guardar e reusar bairro/cidade/últimos resultados no estado, de forma auditável (não só no “jeito” do LLM). |
| **2** | Gemini 3.1 Pro | Elipse / resiliência | Mensagens curtas ou vagas (“Parangaba”, “centro”) + root que não se perde no follow-up. |
| **3** | Kimi K2.6 | ICL + proactive | Depois dos dados, empurrar o próximo passo e manter o especialista certo (não virar Técnico na mensalidade). |

| # | Ângulo que escolheu | Acertou | Errou / excesso |
|---|---------------------|---------|-----------------|
| **1** Sonnet | Estado explícito + não reperguntar | Formato RF/não-objetivo; encaixa no que o repo já fez (#94); RF4 lista indexável ainda vale | Quase não fala de sticky do root nem de CTA proativo |
| **2** Gemini | User stories + tipagem de tools + KPIs | Sticky (US03) e desambiguação fechada (US02); métricas claras | Fill de kwargs no `gate_degustacao` (F3) — papel errado |
| **3** K2.6 | Fluxo fim-a-fim + “código pronto” | Sticky no Mercado + CTA pós-concorrentes (mesmo input, fatiou de outro jeito) | `ConversationState` em sessão ADK some a cada turno no nosso runner; FSM/patterns pesados demais p/ degustação |

| # | Veredito curto | Próximo passo prático | Doc |
|---|----------------|----------------------|-----|
| 1 | Útil; RF1–2/5 feitos (#94). Gaps RF3+RF4 | Lista indexável + “seguindo com” | [PRD_SLOT…](./PRD_SLOT_TRACKING_CONTEXTO_CONVERSACIONAL.md) |
| 2 | Bom; F3 no gate **recusado**. Gaps sticky + MC | Pinagem + desambiguação | [PRD_RESILIENCIA…](./PRD_RESILIENCIA_CONTEXTO_ELIPSE.md) |
| 3 | Ângulo de fluxo bom; §4 **não colar**. Pegar sticky + CTA | Prompt CTA + pin Mercado; estado mínimo em JSONB | [PRD_ICL…](./PRD_MELHORIA_CONVERSACIONAL_ICL_PROACTIVE.md) |

---

## Ranking unificado (fila de implementação)

| Rank | Entrega | PRD | Valor | Esforço | Status |
|------|---------|-----|-------|---------|--------|
| 1 | Sticky: follow-up / msg curta → último especialista (esp. Mercado) | #2 US03 + #3 continuidade | Alto | Baixo–médio | 🟡 |
| 2 | Proactive: 1 CTA após concorrentes (reviews ou plataforma) | #3 | Alto | Baixo | ❌ |
| 3 | Lista indexável (“o segundo / eles / essas academias”) | #1 RF4 + #3 coref | Alto | Médio | ❌ |
| 4 | “Seguindo com Parangaba…” | #1 RF3 | Médio-alto | Baixo | ❌ |
| 5 | Desambiguação MC (“centro”) | #2 US02 | Alto | Médio | 🟡 |
| 6 | Bloco `[conversa: pending_offer=…]` no runner (JSONB projeto) | #3 mínimo | Médio | Médio | ❌ |
| 7 | Histórico 8 turnos + prompt sticky root | #2 NFR/F1 | Médio | Baixo | 🟡 |
| 8 | Tom direto se msgs curtas (só prompt) | #3 | Baixo–médio | Baixo | ❌ |
| 9 | Exemplos elipse nas docstrings | #2 F2 | Médio | Baixo | 🟡 |
| 10 | Espelho consultor | #1–#3 | Alto | Médio | 🟡 |
| — | FSM + `conversation_state` em ADK session | #3 §4 | Baixo | Alto | **Recusar** |
| — | Fill kwargs dentro de `gate_degustacao` | #2 F3 / #3 | — | — | **Recusar** |
| — | Pattern recognition “sempre pede vizinho” | #3 | Baixo | Alto | Adiar |
| ✅ | Não reperguntar bairro/cidade | #1/#2/#3 | Alto | — | Feito #94 |
| ✅ | Troca de bairro sobrescreve | #1 RF5 | Alto | — | Feito #94 |

### Ranking dos autores (mesmo input → qualidade do PRD p/ o repo)

| Rank | Modelo | Critério |
|------|--------|----------|
| 1 | Sonnet 4.5 médio | Proposta mais cirúrgica e implementável sem reinventar o runner |
| 2 | Gemini 3.1 Pro | Stories/KPIs úteis; um erro de arquitetura serio (F3) |
| 3 | Kimi K2.6 | Boa fatia de fluxo (sticky + CTA); pior como pacote de eng. (§4) |

**Como enviar o próximo:** cole o PRD (e o modelo, se souber); a curadoria cruza com `agents_site/` + `services/consultor/` e atualiza esta tabela.
