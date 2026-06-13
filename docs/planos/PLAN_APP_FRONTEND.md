# PLAN - App / Frontend

> Categoria: aplicacao web do GymSite Intelligence (geracao de relatorios de viabilidade).
> Atualizado em 2026-06-13.

## Objetivo

Entregar a aplicacao que gera relatorios de viabilidade para pontos comerciais (academias), cruzando bases publicas + modelagem proprietaria, com fluxo de coleta (formulario de producao) e execucao/visualizacao do relatorio.

## Stack (do projeto)

- Frontend: Vite + React.
- Backend/dados: Supabase (multi-tenant). (a confirmar) detalhes de schema.
- Pipeline de agentes A0-A7 (Google ADK / Gemini) para enriquecimento e execucao. (a confirmar) estado de integracao.
- Deploy alvo: Cloudflare Pages (a confirmar) vs HostGator — ver PLAN_INFRA_HOSTING.

## Estado atual (verificado parcialmente)

- App rodando em desenvolvimento em http://localhost:5174 (origem fora das permissoes desta sessao; conteudo nao lido).
- Rota observada: /execucao/<id>?etapa=<id> — indica fluxo de execucao por etapas de um relatorio.
- (a confirmar) telas de formulario, listagem, e render final do relatorio.

## Formulario de producao (campos canonicos)

O schema canonico de input do formulario esta documentado em docs/EVAL_GUIDE.md (alinhado ao form-snapshot.md). Inclui: localizacao (UF, municipio, bairro), parametros do imovel/negocio (tipo de negocio, porte/tamanho, publico-alvo por faixa etaria, genero, estacionamento) e contato.

## Pendencias / proximos passos

1. Confirmar e documentar as telas do app (formulario -> execucao -> relatorio).
2. Integrar o agente do site (isca) ao fluxo de captura/lead do app. Ver PLAN_AGENTE.
3. Definir o backend de cobertura (allowlist de municipios/UF, contagem canonica, rate-limit) — tambem citado no eval do agente.
4. Padronizar o deploy (ver PLAN_INFRA_HOSTING).
5. Garantir que o app nunca exponha as fontes de dados (sigilo) nem dados pessoais (LGPD).

## Constraints

- Sigilo de fontes na UI e nos textos do produto.
- LGPD na coleta e exibicao de dados.
- Fase 0: sem precos fixos no fluxo.

