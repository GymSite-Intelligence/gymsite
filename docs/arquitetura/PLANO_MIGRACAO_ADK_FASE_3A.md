# Migração ADK — Fase 3a: motor da degustação da landing ([2] → [3])

> Plano de execução da Fase 3a da migração `consultor_engine` → `agents_site` (ADK).
> Contexto e fases 0–4: ver a auditoria em [PIPELINE_AGENTES.md](PIPELINE_AGENTES.md) e o
> handoff de agentes do site. Estado no momento (auditado 2026-07-04): Fase 0+1 em main
> (PR #40), Fases 2–4 não iniciadas. Este doc detalha só a **3a**.

## Onde estamos (auditoria 2026-07-04)

| Fase | Estado | Evidência |
|---|---|---|
| 0 — tools de dado | ✅ feita | 5 FunctionTools em `agents_site/tools.py` |
| 1 — gate/antifatiamento | ✅ feita | `agents_site/guardrails.py::gate_degustacao`, usado no agente Mercado |
| 2 — ponte de estado | ❌ não iniciada | zero SessionService/ProjectState/callbacks em `agents_site/` |
| 3 — endpoint/deploy | ❌ não iniciada | nenhum endpoint importa `agents_site.agent.root_agent` (órfão) |
| 4 — cutover | ❌ não iniciada | landing roda `conversar(modo_site=True)` (site_agent.py, redis_queue.py) |

**Insight que motiva a 3a:** a Fase 2 (ponte `session.state` ↔ `user_projects`) só é
necessária para o **modo logado**. A landing é **degustação anônima/efêmera** e o gate de
degustação (Fase 1) já está pronto. Logo, dá pra migrar a landing pro ADK **antes** da Fase 2 —
caminho mais curto pro valor (Arquiteto/Engenheiro/Mercado ganham voz no site).

## Objetivo e escopo

- **Fazer:** a landing roda `agents_site.root_agent` (ADK, 5 especialistas) em vez de
  `conversar(modo_site=True)`.
- **Ganho:** Arquiteto / Engenheiro de Obra / Mercado alcançáveis pelo visitante; persona com
  fonte única (mata o drift [2]×[3]).
- **Fora de escopo:** modo logado do consultor; ponte `user_projects` (Fase 2); aposentar o
  `modo_site` (Fase 4).

## Contrato preservado (o front NÃO muda)

`POST /api/site-agent/conversar` e `GET /api/site-agent/conversar/{id}/mensagens` (polling)
continuam idênticos. Turnstile, criação de projeto anon e persistência em `project_messages`
inalterados. O front não sabe qual motor rodou → a troca é transparente e reversível.

## Ponto de troca (único)

`tools/redis_queue.py`, job `site_conversar` (hoje chama `conversar(modo_site=True)`). Trocar
por `run_site_agent_adk(projeto_id, mensagem, agente)` **atrás de feature flag**:

```
SITE_AGENT_ENGINE = "legacy" (default) | "adk"
```

Rollback = trocar 1 env var no worker, sem deploy.

## Núcleo: `run_site_agent_adk` (novo — ex. `agents_site/runner.py`)

Espelha o Runner do pipeline [1] (`api.py:807`), com uma diferença de sessão (ver abaixo):

1. Carrega histórico de `project_messages(projeto_id)` → `Content[]` do ADK.
2. Cria sessão com state inicial `{"tier": "degustacao", "agente": agente, "amostras_dadas": N}`.
3. `Runner(agent=root_agent, app_name="gymsite", session_service=...)` →
   `run_async(new_message=<mensagem do user>)`.
4. Coleta a resposta final do agente.
5. Persiste user+assistant em `project_messages` — **mesmo formato do `conversar`** → o polling
   do front funciona sem alteração.

## O nó de design: sessão entre turnos

`InMemorySessionService` (usado pelo [1]) **não serve**: o pipeline roda uma vez, mas a
degustação é multi-turno e **cada turno é um job separado no worker** (stateless entre jobs). O
state (tier + contador K do gate) se perderia. Opções:

| Opção | Como | Trade-off |
|---|---|---|
| **1. Reconstruir do histórico** ✅ recomendada p/ 3a | Re-hidrata o state a cada turno de `project_messages`: `tier="degustacao"` fixo; `amostras_dadas` derivado do histórico (ou campo leve em `user_projects.state`) | Zero infra nova; desacopla da Fase 2; degustação é curta (K=2), reconstruir é barato |
| **2. `DatabaseSessionService` ADK → Supabase** | SessionService SQL do ADK apontando pro Postgres; state durável de graça | Cria schema ADK no banco **compartilhado com a Vectra**; validar pooler/permissões — mais peso |
| **3. SessionService custom** | Implementa a interface no Supabase | É trabalho da Fase 2; overkill pra 3a |

**Decisão: Opção 1.** A Opção 2 fica para a Fase 2 (modo logado com state durável real).

## Manter o `gate_degustacao` (Fase 1) funcionando

O gate lê `session.state["tier"]` e corta amostras após K=2. Na Opção 1, popular o state na
reconstrução: `tier="degustacao"` sempre, `amostras_dadas` derivado. **Teste-chave da 3a:**
provar que o gate ainda bloqueia Tier 2 e corta no K após a troca de motor.

## Roteamento por `agente`

O request já manda `agente` (degustacao / responsavel_tecnico / regulatorio). Duas escolhas de UX:
- (a) Ignorar e deixar o `root_agent` rotear pela mensagem (força do ADK). **Padrão recomendado.**
- (b) Se a landing tem botões que fixam o especialista, passar `agente` como hint no state.

## Rollout (canário)

1. Deploy com `SITE_AGENT_ENGINE=legacy` — código dorme, risco zero.
2. Liga `adk` em staging / % do tráfego (hash do `projeto_id`).
3. Compara **latência, custo/tokens e qualidade** contra o legacy.
4. 100% adk → depois remove o `modo_site` (Fase 4).

## Riscos a medir antes do 100%

- **Latência/custo:** roteador + especialista = 2 hops LLM no ADK; pode gastar mais que o loop
  atual. Medir no canário.
- **Paridade:** o [3] deve cobrir tudo que o [2] modo_site fazia + os agentes novos.
- **Deploy do worker:** compartilha a imagem da api e NÃO auto-deploya — redeploy manual
  (`gcloud run services update gymsite-worker --image <api_image>`).

## Testes

Golden de uma conversa de degustação pelo runner ADK, validando: roteamento ao especialista
certo; gate bloqueia Tier 2; K=2 corta amostras; resposta persiste em `project_messages` no
formato que o polling espera.

## Esforço

Frente focada, sem tocar o modo logado. Grosso: `runner.py` + reconstrução de sessão/gate
(médio). Feature flag + canário (baixo). Teste golden fecha a validação.

## Próximo passo

Implementar `run_site_agent_adk` (Opção 1) + o teste do gate, atrás da flag em `legacy` (risco
zero até ligar o canário).
