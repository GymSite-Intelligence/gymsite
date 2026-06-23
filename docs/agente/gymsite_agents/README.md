# Handoff Badge (Swarm UI) — handoff de frontend p/ gym-insight-hub

Componentes React/TSX que mostram os agentes **passando o bastão** ao vivo no chat
(animação entra → ativo → sai). Extraído de `gymsite_agents.zip` (agora redundante).
**Destino:** repo do frontend `gym-insight-hub` — aqui é só handoff versionado/diffável.

## Duas versões de chat

| Versão | Config | Agentes | Forma |
|---|---|---|---|
| **Pipeline (logado)** | `config_handoff.ts` | 5 setores × **18 agentes** A0–A9 | Pipeline sequencial (relatório completo) |
| **Site (degustação)** | `config_handoff_site.ts` | **5 especialistas** | Roteamento 1-hop (`transfer_to_agent`) |

- **Pipeline** = a geração do relatório logado (Context Builder → GeoScout → Demo/Competitor/Financeiro → CNPJ/Diligência/Validador → RAG D2 Cast → Positioning/Report/Contact Hunter). Eventos chegam via WebSocket/SSE (`pipelineEvent`).
- **Site** = a landing pública: roteador → Mercado / Técnico / Arquiteto / Engenheiro / Regulatório. IDs batem com `agents_site/agent.py`. Cada agente tem ícone, cor e textos (saudação/placeholder/exemplo) p/ o **seletor de agente** + badge do agente ativo.

## Arquivos
- `types_handoff.ts` — tipos (SetorId, AgenteStatus, HandoffState/Event, IconComponent)
- `config_handoff.ts` — **versão pipeline**: 5 SETORES + 18 AGENTES_PIPELINE + helpers
- `config_handoff_site.ts` — **versão site**: 5 AGENTES_SITE + ORDEM_SITE + textos por agente
- `useHandoff.ts` — máquina de estado da transição (anti-flash `tempoMinimoVisivel`)
- `HandoffTimeline.tsx` — timeline visual dos agentes
- `ChatLayout.tsx` — shell do chat integrando `HandoffBadge` (recebe `pipelineEvent`)
- `gymsite-icons.tsx` — SVGs (robô + objeto temático): 5 do pipeline (Dados/Financeiro/Contabilidade/Marketing/Conhecimento) **+ 5 do site** (Técnico/Arquiteto/Engenheiro/Regulatório/Mercado)

## Integração (no gym-insight-hub)
1. Copiar p/ os caminhos esperados pelos imports: `types/handoff.ts`, `config/handoff.ts`, `config/handoff_site.ts`, `hooks/useHandoff.ts`, `components/handoff/*`, `components/icons/gymsite-icons.tsx`.
2. Chat logado → `ChatLayout` com `config/handoff` (pipeline) + `pipelineEvent` do WebSocket.
3. Chat da landing → seletor com `AGENTES_SITE`/`ORDEM_SITE`; ao escolher, manda `agente` no POST `/conversar`; badge mostra o agente ativo via `getAgenteSite(agente)`.
4. Dependências: `framer-motion`, `lucide-react`, `@/lib/utils (cn)`, ui `Button`.

> Depois de integrado no frontend, `docs/agente/gymsite_agents.zip` vira lixo → deletar.
