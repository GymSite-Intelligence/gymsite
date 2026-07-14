# PRD — Resolução de Contexto Conversacional (Slot Tracking)

> **Curadoria GymSite · 2026-07-14**  
> **Modelo autor do PRD:** Claude Sonnet 4.5 (médio).  
> Alvos: **site agent** (`agents_site/`) e **consultor legado** (`services/consultor/`).

---

## Veredito da curadoria

**Útil e alinhado ao produto — mas metade já foi entregue no PR #94.**  
Não reimplementar “do zero” com `session.state["mercado.*"]` do ADK: o caminho canônico no GymSite é **`user_projects.localizacao` (JSONB)** + injeção determinística no turno. O que resta é fechar gaps práticos (referência por índice, frase “seguindo com…”, compartilhado com o consultor).

| Status | Significado |
|--------|-------------|
| ✅ Feito | Já no código de produção (`main`, pós-#94) |
| 🟡 Parcial | Comportamento existe, mas fora do desenho literal do PRD |
| ❌ Gap | Ainda vale construir |
| ⏸ Adiar | Bom em teoria; pouco retorno agora |

---

## Mapa RF → código atual

| # | Requisito (PRD) | Site agent | Consultor legado | Prioridade restante |
|---|-----------------|------------|------------------|---------------------|
| RF1 | Persistir bairro/cidade/uf/tipo após tool de concorrentes | 🟡 Persistência **antes** do LLM no `runner` (`user_projects.localizacao`), não via `tool_context.state` em `buscar_concorrentes` | 🟡 Já grava a partir dos **args da tool** em `_atualizar_projeto_de_resposta` | Baixa — redesenhar só se falhar em turno sem tool |
| RF2 | Detectar bairro novo; senão injetar último salvo | ✅ `resolver_localizacao` + `[localizacao_resolvida:…]` no `run_site_agent_adk` (equivalente ao callback, mas no runner) | 🟡 Lê `projeto.localizacao` / `dados_faltantes`; **não** injeta bloco canônico na mensagem | Média no consultor |
| RF3 | Resposta explícita (“Seguindo com Parangaba…”) quando reusa slot | ❌ Prompt só diz “não peça de novo”; não obriga a frase | ❌ Idem | **Alta** (barato, UX clara) |
| RF4 | Salvar últimos resultados p/ “o segundo”, “ali perto” | ❌ Não existe `ultimos_resultados` | ❌ Não existe lista indexável no state | **Alta** (maior dor restante do PRD) |
| RF5 | Bairro novo sobrescreve, não acumula | ✅ Merge `{**previa, **payload}` com chaves novas | ✅ `loc.update(...)` nos args | Baixa — só falta teste de regressão “trocou de bairro → limpa lista” |

**Não-objetivos do PRD — manter:** ambiguidade geográfica real continua pergunta fechada; sem personalização cross-usuário; não mexe no `gate_degustacao`.

---

## Adaptação prática (o que construir de verdade)

### A) Site agent — fechar o PRD sem trocar a arquitetura

1. **RF3 — sinalizar reuso**  
   Em `LocalizacaoResolvida` já existe `origem` (`hint_json` | `contexto` | `mensagem` | `previa`).  
   Se `origem == "previa"` e a mensagem do usuário **não** trouxe bairro novo, prefixar também algo como:
   `[slot_reaproveitado: bairro=Parangaba; cidade=Fortaleza]`  
   e instruir o Mercado a abrir com “Seguindo com Parangaba, Fortaleza…”.

2. **RF4 — lista indexável**  
   Após `buscar_concorrentes` / `analisar_reviews_e_dores`, gravar em `user_projects` (campo sugerido: `mercado.ultimos_resultados` ou chave dentro de `concorrencia` JSONB já prevista na arch do consultor):
   ```json
   {
     "atualizado_em": "…",
     "bairro": "Parangaba",
     "cidade": "Fortaleza",
     "itens": [
       {"i": 1, "nome": "…", "place_id": "…", "distancia_m": 320}
     ]
   }
   ```
   No próximo turno, se a mensagem casar com “o 2º”, “o segundo”, “a primeira”, “esse perto”, injetar `[referencia_lista: indice=2; nome=…]` **antes** do LLM — regex, zero chamada extra.

3. **RF5 + RF4 juntos**  
   Troca clara de bairro → zera `ultimos_resultados` (responde questão em aberto do PRD: **sim, expira ao trocar bairro**).

4. **Não fazer**  
   - Migrar persistência para `session.state` ADK como fonte da verdade (some no reinício / troca de app).  
   - Lista hardcode de todos os bairros de Fortaleza (o PR #94 já usa parse + prévia + hint; lista só como fallback opcional depois).

### B) Consultor legado — reaproveitar o mesmo módulo

O consultor **já** trata localização como estado de projeto (`user_projects.localizacao`) e bloqueia tools quando falta bairro/cidade. Gaps:

| Gap | Ação |
|-----|------|
| Repergunta / “esqueceu” entre turnos longos | Chamar o **mesmo** `agents_site.localizacao.resolver_localizacao` + injeção no `consultor_engine` antes do LLM (hoje só atualiza depois que a tool roda) |
| “O segundo concorrente” | Mesmo contrato `ultimos_resultados` no JSONB do projeto — um contrato, dois fronts |
| Frase “Seguindo com…” | Mesma regra de prompt do especialista Mercado / tool router |

**Fase 2 do PRD** (“slot nos outros 4 agentes”) no site: só depois de RF3+RF4 estáveis no Mercado. No consultor, localização já é transversal — priorizar **lista indexável** e injeção pré-LLM.

---

## Critérios de aceite (revisados)

- [ ] Com bairro já no projeto, perguntar “como está a concorrência?” **não** pede bairro de novo (site + consultor).  
- [ ] Resposta começa reconhecendo o lugar quando o slot veio da prévia (“Seguindo com…”).  
- [ ] “Analisa o segundo” aponta para o item `i=2` da última lista daquele bairro (teste scriptado).  
- [ ] Trocar “agora Cocó” sobrescreve Parangaba e limpa a lista anterior.  
- [ ] Zero regressão no `gate_degustacao` / antifatiamento.  
- [ ] Latência: só regex/heurística (sem LLM extra para slot).

---

## Riscos (resposta às questões em aberto do PRD)

| Questão original | Decisão curada |
|------------------|----------------|
| Heurística / lista de bairros Fortaleza | Não bloquear entrega. Priorizar prévia + parse; lista de bairros = opcional P2. |
| TTL do slot na sessão | Enquanto o **mesmo** `projeto_id` estiver ativo, o slot vale. Sem TTL artificial. |
| `ultimos_resultados` ao trocar bairro | **Expira** (limpa). |

---

## Escopo desta fase (congelado)

**Dentro:** RF3 + RF4 + limpeza RF5 no Mercado (site) e espelho no consultor (mesmo módulo).  
**Fora:** slot tracking rico para Equipamentos / Regulatório / Arquiteto / Obra; personalização entre usuários; ambiguidade geo real.

---

## Documento original (inalterado)

# PRD — Resolução de Contexto Conversacional (Slot Tracking) no GymSite

## 1. Contexto
O GymSite é um sistema multiagente (Google ADK) que dá uma degustação da análise de viabilidade para quem quer abrir uma academia no Brasil. Um agente roteador delega para 5 especialistas (Equipamentos, Regulatório, Mercado, Arquiteto, Engenheiro de Obra).

O agente Mercado hoje resolve referências entre turnos (ex.: usuário informa "Parangaba" após ser perguntado o bairro) apenas via inferência do LLM sobre o histórico da conversa. Funciona na maioria dos casos, mas é frágil: depende do LLM lembrar corretamente, não é auditável, e não sobrevive bem a conversas longas ou reinícios de sessão.

## 2. Problema
Sem estado explícito, o agente pode:
- Reperguntar um dado que o usuário já informou.
- Resolver errado uma referência ambígua ("avalie o segundo", "e ali perto?").
- Perder o contexto ao retomar sessão ou trocar de agente e voltar ao Mercado.

## 3. Objetivo
Tornar a resolução de contexto (bairro, cidade, UF, tipo de negócio, últimos resultados) determinística e auditável via `session.state` do ADK, em vez de depender só da inferência implícita do LLM.

## 4. Não-objetivos
- Ambiguidade geográfica real (dois bairros parecidos em cidades diferentes) continua sendo pergunta fechada ao usuário.
- Não inclui personalização entre sessões de usuários diferentes.
- Não substitui o `gate_degustacao` existente — é complementar.

## 5. Requisitos funcionais
| # | Requisito | Prioridade |
|---|---|---|
| RF1 | `buscar_concorrentes` deve persistir bairro/cidade/uf/tipo_negocio em `session.state["mercado.*"]` | Alta |
| RF2 | `before_model_callback` deve detectar bairro novo na mensagem; se ausente, injetar o último salvo como `[localizacao_resolvida: …]` | Alta |
| RF3 | Ao reaproveitar slot do state, a resposta deve deixar isso explícito ("Seguindo com Parangaba…") | Média |
| RF4 | Últimos resultados retornados devem ser salvos em `state["mercado.ultimos_resultados"]` para referências por índice | Média |
| RF5 | Mudança clara de bairro deve sobrescrever o state antigo, não acumular | Alta |

## 6. Requisitos não funcionais
- Zero aumento perceptível de latência (extração via regex/heurística, não LLM extra).
- Mudança aditiva via `tool_context`/`callback_context` — sem alterar contrato das tools.
- Manter 100% das regras de grounding existentes (zero número fabricado, degustação em amostra).

## 7. Design técnico (resumo)
1. **Persistência de slot na tool**: `buscar_concorrentes` recebe `tool_context: ToolContext` e grava os parâmetros resolvidos em `tool_context.state`.
2. **Callback de resolução**: `before_model_callback` no agente Mercado lê `callback_context.state`, tenta extrair bairro/cidade da mensagem atual (lista de bairros como heurística) e, se não achar, injeta o slot salvo anteriormente.
3. **Instrução do agente**: ajustar "LOCALIZAÇÃO (não reperguntar)" para diferenciar "novo slot detectado" vs. "slot reaproveitado", sinalizando isso na resposta.

## 8. Métricas de sucesso
- Redução para ~0% de reperguntas de bairro já informado (medir baseline primeiro).
- Redução de erros de correferência em teste manual com script de conversas.
- Sem regressão nas regras de degustação/antifatiamento.

## 9. Riscos / questões em aberto
- Heurística de bairro por regex pode não cobrir todos os bairros de Fortaleza — precisa de lista de referência.
- TTL do state: por quanto tempo um bairro salvo continua "válido" na mesma sessão.
- Definir se `mercado.ultimos_resultados` expira ao trocar de bairro.

## 10. Fora de escopo desta fase
- Slot tracking para os outros 4 agentes — possível fase 2 se o padrão validar bem no Mercado.
