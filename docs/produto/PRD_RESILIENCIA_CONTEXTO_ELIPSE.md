# PRD — Resiliência de Contexto e Resolução de Elipse (Multi-turn)

> **Curadoria GymSite · 2026-07-14** (#2 da série)  
> Alvos: **site agent** (degustação) e, por espelho, **consultor legado**.  
> Relacionado: [PRD slot tracking](./PRD_SLOT_TRACKING_CONTEXTO_CONVERSACIONAL.md) (#1).

---

## Veredito

**Bom produto, desenho técnico parcialmente errado no F3.**  
O problema real (resposta curta tipo “Parangaba” / “Aldeota” / “centro”) é verdadeiro. Parte de **US01** e da localização já está no `main` (#94). O que ainda falta de alto valor é **grudar no último especialista** (US03) e **desambiguação fechada** (US02).

**Não expandir `gate_degustacao` para preencher cidade.** Esse callback é barreira de antifatiamento / Tier 2 — misturar DST nele cria risco de “liberar sample e ainda mutar args” opaco. Preencher parâmetro faltante deve ficar no **mesmo lugar do #94** (`resolver_localizacao` + runner / `before_tool` dedicado).

---

## Ranking tabulado — requisitos deste PRD

| Rank | ID | Item | Valor | Esforço | Status no código | Decisão |
|------|----|------|-------|---------|------------------|---------|
| 1 | US03 / sticky | Mensagem curta → último especialista ativo (não rerotear) | Alto | Baixo–médio | 🟡 Há pinagem por `agente` + retry pós-transfer; **root não tem regra de sticky** | **Fazer** — regra no runner (preferível) ou instrução do root |
| 2 | US02 | “centro” / vago → 1 pergunta múltipla escolha | Alto | Médio | 🟡 Prompt Mercado já pede pergunta fechada; **sem opções concretas** | **Fazer** — lista curta de candidatos quando ambíguo |
| 3 | F1 | Prompt do roteador olhar turnos anteriores em msgs &lt; 5 palavras | Médio–alto | Baixo | ❌ Instrução atual só mapeia domínio→agente | **Fazer** — complementar ao sticky (não basta prompt sozinho) |
| 4 | US01 | Só bairro → saturação sem reperguntar cidade/intenção | Alto | — | ✅ Quase: `[localizacao_resolvida]` + prévia do projeto | **Manter** — só fechar buraco “1ª mensagem só bairro sem cidade” |
| 5 | F2 | Docstrings/tipagem com exemplos de elipse nas tools | Médio | Baixo | 🟡 Tipagem + docs já existem; faltam exemplos de elipse | **Polir** — barato, não resolve sozinho |
| 6 | NFR hist. | Truncar histórico a 6–8 turnos | Médio (custo) | Baixo | 🟡 Hoje `limite=20` | **Ajustar** para 8 (ou 6+último especialista) |
| 7 | F3 | Preencher kwargs no `gate_degustacao` | — | — | ❌ Conceito errado p/ esse arquivo | **Recusar neste desenho** — ver adaptação abaixo |
| 8 | KPI conversão | Taxa CTA pós-saturação | Produto | — | Fora do agent loop | Medir depois; não bloqueia eng. |

---

## Ranking cruzado — PRD #1 + #2 (fila única de implementação)

| Rank | Origem | Entrega | Por quê sobe/desce |
|------|--------|---------|-------------------|
| 1 | #1 RF4 | Lista indexável (“o segundo”) | Elipse **entre resultados**, maior buraco restante |
| 2 | #2 US03 | Sticky no último agente | Elipse **de roteamento**; quebra “Parangaba” sem domínio na mensagem |
| 3 | #1 RF3 | “Seguindo com Parangaba…” | UX barata; reforça confiança |
| 4 | #2 US02 | Desambiguação MC | Evita inventar bairro/cidade (anti-alucinação do próprio PRD) |
| 5 | #2 F1+NFR | Prompt sticky + hist. 8 turnos | Complementar; custo/latência |
| 6 | #2 F2 | Exemplos elipse nas docstrings | Polimento ADK |
| 7 | #1+#2 | Espelho no consultor | Mesmo módulo `localizacao` + sticky se houver multiagente |
| — | #2 F3 literal | Inject no `gate_degustacao` | Fora — usar fill dedicado / runner |

---

## Adaptação técnica (canônica)

| PRD diz | GymSite deve |
|---------|----------------|
| F3 no `gate_degustacao` | Manter gate só para Tier/amostras. Fill de `cidade`/`bairro` faltantes: (a) runner já injeta texto; (b) opcional `before_tool_callback` **separado** que completa `args` a partir de `user_projects.localizacao` e retorna `None` |
| `session.state` como verdade | `user_projects.localizacao` (+ opcional `mercado.ultimos_resultados`) |
| Inferir no root só via prompt | Preferir **pinagem determinística**: se `len(msg.split()) ≤ N` e último `project_messages.agente` for especialista, rodar pinado (já existe `_PINADOS`) |
| Histórico 6–8 | Baixar `carregar_historico(..., limite=8)` (hoje 20) |
| Grounding / zero inventar cidade | Já alinhado; US02 reforça — nunca default “Fortaleza” sem evidência |

---

## Casos de uso × status

| US | Status | Nota |
|----|--------|------|
| US01 | ✅/~ | Ok se cidade já está no projeto ou na mesma mensagem; falha se 1ª fala for só o bairro sem cidade conhecida |
| US02 | 🟡 | Falta múltipla escolha estruturada (não só “confirma X?”) |
| US03 | 🟡 | Falta sticky automático no root/runner para fragmento curto |

---

## Aceite (fase desta curadoria)

- [ ] “E a saturação?” após análise em Parangaba → Mercado pinado, sem “qual especialista?”
- [ ] “Parangaba” com cidade já no projeto → tool roda com cidade preenchida (sem inventar)
- [ ] “centro” → opções fechadas (ex.: Centro / Aldeota / Meireles), nunca chute
- [ ] `gate_degustacao` continua só bloqueando Tier 2 / K amostras
- [ ] Histórico efetivo ≤ 8 turnos no site

---

## Documento original (resumo preservado)

**Produto:** GymSite Agents (degustação landing)  
**Feature:** Resiliência de contexto e resolução de elipse  
**Stack:** Google ADK + Gemini-2.5-Flash

### Problema / objetivo
Respostas fragmentadas (“Parangaba”) sem DST blindado → falha de roteamento ou validação de tools. Objetivo: cruzar fragmento com histórico/sessão sem obrigar o usuário a repetir o contexto.

### User stories
- **US01** — Só o nome do bairro → saturação imediata sem reperguntar cidade/intenção.
- **US02** — Resposta vaga (“centro”) → uma pergunta de múltipla escolha.
- **US03** — Root retém último sub-agente ativo para resposta curta.

### Requisitos funcionais
- **F1** — Instrução do `root_agent`: inspecionar turnos anteriores em mensagens curtas (&lt; 5 palavras) antes de delegar.
- **F2** — Tipagem/docstrings rígidas em `buscar_concorrentes` e `analisar_reviews_e_dores` com exemplos de elipse.
- **F3** — Expandir `gate_degustacao` para injetar kwargs faltantes a partir do estado (ver **recusa de desenho** na curadoria).

### Não funcionais
- +≤500 ms na resolução de parâmetros.
- Grounding: nunca preencher bairro/cidade não confirmados.
- Truncar contexto a 6–8 interações.

### KPIs
- Sucesso de tool após resposta de 1–2 palavras.
- Queda de “não entendi” no root.
- Conversão degustação → CTA plataforma.
