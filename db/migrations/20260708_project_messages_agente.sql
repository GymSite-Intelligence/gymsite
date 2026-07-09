-- 20260708_project_messages_agente.sql — registra QUAL agente produziu cada resposta.
--
-- Schema vivo: gymsite (flags GYMSITE_SCHEMA_SEP=1 + SHARED_SCHEMA_SEP=1 ON em prod).
-- Idempotente. Aditiva e nullable: nenhuma linha existente muda, nenhum insert antigo
-- quebra.
--
-- POR QUÊ: na degustação o usuário escolhe um especialista, mas quando ele não escolhe
-- (`agente=degustacao`) quem responde é decidido pelo roteador ADK em tempo de execução.
-- O pedido não diz quem respondeu. Sem esta coluna não dá pra (a) mostrar na UI qual
-- especialista falou nem (b) alimentar a roda de aprendizado / SFT por especialidade.
--
-- Guarda o `name` do Agent ADK ("Regulatorio", "Mercado", ...), não o id público da API
-- ("regulatorio", "mercado") — é o autor real do evento (Event.author). O mapa id→name
-- vive em agents_site/catalog.py.
--
-- NULL = mensagem de user/system, ou resposta gravada antes desta migration.
--
-- ORDEM DE APLICAÇÃO: esta migration ANTES do deploy do código. O runner passa
-- `agente=` no insert; sem a coluna, o insert falha.
-- Consumida por: services/consultor/project_messages.py (salvar_mensagem),
--                agents_site/runner.py (run_site_agent_adk).

alter table if exists gymsite.project_messages
  add column if not exists agente text;

comment on column gymsite.project_messages.agente is
  'Nome do Agent ADK que produziu a resposta (Event.author). NULL para user/system.';

-- Consulta típica da roda de aprendizado: "quais perguntas cada especialista recebeu".
create index if not exists project_messages_agente_idx
  on gymsite.project_messages (agente)
  where agente is not null;
