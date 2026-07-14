# Curadoria de PRDs — site agent + consultor legado

Lista viva dos PRDs avaliados para melhorias práticas de conversação (degustação / consultor).  
Só entra o que tem caminho claro no código atual e retorno de uso.

| # | PRD | Veredito | Próximo passo prático | Doc |
|---|-----|----------|----------------------|-----|
| 1 | Slot tracking / contexto conversacional | Útil; RF1–RF2/RF5 em grande parte já no `main` (#94). Gaps: RF3 + RF4 | Implementar RF3+RF4; espelhar no consultor | [PRD_SLOT_TRACKING…](./PRD_SLOT_TRACKING_CONTEXTO_CONVERSACIONAL.md) |
| 2 | Resiliência de contexto / elipse multi-turn | Bom produto; **F3 no `gate_degustacao` recusado**. Gaps: sticky US03 + desambiguação US02 | Pinagem determinística + MC; NFR hist. 8 | [PRD_RESILIENCIA…](./PRD_RESILIENCIA_CONTEXTO_ELIPSE.md) |

---

## Ranking unificado (fila de implementação)

| Rank | Entrega | PRD | Valor | Esforço | Status |
|------|---------|-----|-------|---------|--------|
| 1 | Lista indexável (“o segundo / ali perto”) | #1 RF4 | Alto | Médio | ❌ |
| 2 | Sticky: fragmento curto → último especialista | #2 US03/F1 | Alto | Baixo–médio | 🟡 |
| 3 | “Seguindo com Parangaba…” | #1 RF3 | Médio-alto | Baixo | ❌ |
| 4 | Desambiguação múltipla escolha (“centro”) | #2 US02 | Alto | Médio | 🟡 |
| 5 | Histórico 8 turnos + prompt sticky | #2 NFR/F1 | Médio | Baixo | 🟡 |
| 6 | Exemplos de elipse nas docstrings das tools | #2 F2 | Médio | Baixo | 🟡 |
| 7 | Espelho consultor (`localizacao` + sticky se couber) | #1+#2 | Alto | Médio | 🟡 |
| 8 | Só-bairro sem cidade na 1ª mensagem | #2 US01 buraco | Médio | Médio | 🟡 |
| — | Inject kwargs dentro de `gate_degustacao` | #2 F3 | — | — | **Recusar** |
| — | Lista hardcode todos os bairros | #1 risco | Baixo | Alto | Adiar |
| ✅ | Não reperguntar bairro/cidade (prévia + inject) | #1 RF2 / #2 US01 | Alto | — | Feito #94 |
| ✅ | Troca de bairro sobrescreve | #1 RF5 | Alto | — | Feito #94 |

**Como enviar o próximo:** cole o PRD no chat; a curadoria cruza com `agents_site/` + `services/consultor/` e atualiza esta tabela.
