# Curadoria de PRDs — site agent + consultor legado

Lista viva dos PRDs avaliados para melhorias práticas de conversação (degustação / consultor).  
Só entra o que tem caminho claro no código atual e retorno de uso.

| # | PRD | Veredito | Próximo passo prático | Doc |
|---|-----|----------|----------------------|-----|
| 1 | Slot tracking | Útil; RF1–2/5 feitos (#94). Gaps RF3+RF4 | Lista indexável + “seguindo com” | [PRD_SLOT…](./PRD_SLOT_TRACKING_CONTEXTO_CONVERSACIONAL.md) |
| 2 | Elipse / resiliência multi-turn | Bom; F3 no gate **recusado**. Gaps sticky + MC | Pinagem + desambiguação | [PRD_RESILIENCIA…](./PRD_RESILIENCIA_CONTEXTO_ELIPSE.md) |
| 3 | ICL + proactive + state | Melhor diagnóstico; §4 código **não colar** (ADK state some a cada turno). Pegar só proactive + sticky | Prompt CTA + pin Mercado; estado mínimo em JSONB | [PRD_ICL…](./PRD_MELHORIA_CONVERSACIONAL_ICL_PROACTIVE.md) |

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

**Por que #1 sticky subiu para o topo com #3:** o exemplo “mensalidade da Smart Fit?” é o bug de produto mais claro do trilhão (roteador errado). Proactive é o 2º porque muda a conversa no mesmo turno, com uma linha de prompt + oferta única.

**Como enviar o próximo:** cole o PRD no chat; a curadoria cruza com `agents_site/` + `services/consultor/` e atualiza esta tabela.
