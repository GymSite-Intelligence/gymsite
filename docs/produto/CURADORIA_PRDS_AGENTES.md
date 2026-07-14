# Curadoria de PRDs — site agent + consultor legado

Lista viva dos PRDs avaliados para melhorias práticas de conversação (degustação / consultor).  
Só entra o que tem caminho claro no código atual e retorno de uso.

## Proveniência (modelo autor)

| # | Modelo autor | PRD | Nota da curadoria sobre o autor |
|---|--------------|-----|----------------------------------|
| 1 | **Claude Sonnet 4.5 médio** | Slot tracking / DST | Melhor formato de PRD (RF claros, não-objetivos, riscos). Proposta próxima do que o repo já faz — pouco “inventa arquitetura”. |
| 2 | **Gemini 3.1 Pro** | Elipse / resiliência multi-turn | Bom em user stories e KPIs; errou o alvo técnico no F3 (`gate_degustacao` ≠ fill de kwargs). |
| 3 | **Kimi K2.6** | ICL + proactive + state | Melhor **diagnóstico de produto** (conversa real). Pior **entrega de eng.**: §4 “código pronto” incompatível com o runner (sessão ADK efêmera) + FSM inchada. |

| # | PRD | Veredito | Próximo passo prático | Doc |
|---|-----|----------|----------------------|-----|
| 1 | Slot tracking *(Sonnet)* | Útil; RF1–2/5 feitos (#94). Gaps RF3+RF4 | Lista indexável + “seguindo com” | [PRD_SLOT…](./PRD_SLOT_TRACKING_CONTEXTO_CONVERSACIONAL.md) |
| 2 | Elipse / resiliência *(Gemini)* | Bom; F3 no gate **recusado**. Gaps sticky + MC | Pinagem + desambiguação | [PRD_RESILIENCIA…](./PRD_RESILIENCIA_CONTEXTO_ELIPSE.md) |
| 3 | ICL + proactive *(K2.6)* | Melhor diagnóstico; §4 código **não colar**. Pegar só proactive + sticky | Prompt CTA + pin Mercado; estado mínimo em JSONB | [PRD_ICL…](./PRD_MELHORIA_CONVERSACIONAL_ICL_PROACTIVE.md) |

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
| ✅ | Não reperguntar bairro/cidade | #1/#2/#3 ICL | Alto | — | Feito #94 |
| ✅ | Troca de bairro sobrescreve | #1 RF5 | Alto | — | Feito #94 |

**Por que sticky ficou no topo:** o exemplo do K2.6 (“mensalidade da Smart Fit?”) é o bug de produto mais claro (roteador errado). Proactive (também K2.6) é o 2º. O Sonnet deu o melhor encaixe com o código já existente (#94). O Gemini trouxe US/KPIs úteis, mas F3 no gate foi o maior falso-amigo técnico.

### Ranking dos autores (qualidade do PRD para o nosso repo)

| Rank | Modelo | Por quê |
|------|--------|---------|
| 1 | Sonnet 4.5 médio | RF cirúrgicos, não-objetivos, sem “código pronto” que quebra o runner |
| 2 | Gemini 3.1 Pro | Stories e métricas boas; 1 erro de arquitetura sério (F3) |
| 3 | Kimi K2.6 | Insight de conversa real excelente; implementação §4 descartável |

**Como enviar o próximo:** cole o PRD no chat (e diga o modelo, se souber); a curadoria cruza com `agents_site/` + `services/consultor/` e atualiza esta tabela.
