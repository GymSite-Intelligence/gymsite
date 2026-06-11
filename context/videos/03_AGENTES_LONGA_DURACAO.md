# Vídeo 03 — Agentes de longa duração com a Stack Agentic (ADK 2.0)

> Canal: Google Cloud Tech (The Agent Factory) · ~32:32
> Tema: agentes de longa duração, Agent Studio e ADK 2.0; estado persistente entre sessões.
> Feature GymSite: "UserProject" com contexto acumulativo (item não-implementado do as-built).

## Conceito aplicado
Evoluir de "conversa isolada" para "projeto vivo" com estados (EM_CONVERSA, PESQUISANDO, CONCLUÍDO) que persistem e retomam entre sessões.

## Testes de validação

### T03.1 — Persistência entre sessões
- Dado que o usuário iniciou um projeto e fechou o navegador
- Quando ele retorna depois
- Então o projeto reabre no mesmo estado e com o contexto anterior preservado.

### T03.2 — Transição de estado válida
- Dado um projeto EM_CONVERSA com slots obrigatórios completos e confirmados
- Então transita para PESQUISANDO; ao terminar o pipeline, vai para CONCLUÍDO.

### T03.3 — Retomada de pipeline longo
- Dado uma análise A0-A9 em andamento
- Quando o usuário volta antes de concluir
- Então vê o status atual sem reiniciar o processamento.

### T03.4 — Múltiplos projetos por usuário
- Então o usuário consegue manter e alternar entre vários projetos sem mistura de contexto.

### T03.5 — Não regressão de estado
- Dado um projeto CONCLUÍDO
- Então uma nova mensagem não apaga o relatório anterior; cria evolução/novo projeto.
