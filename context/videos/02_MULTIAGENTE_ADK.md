# Vídeo 02 — Intro to multi-agent systems with ADK

> Canal: Google Cloud Tech · ~11:53 · Palestrante: Greg Baugues
> Tema: criar o primeiro agente no ADK, equipá-lo com ferramentas customizadas (data em tempo real, Google Search), interface web de debug, e montar um sistema multiagente que reduz alucinações e garante exatidão dos dados.
> Feature GymSite: decompor o pipeline A0-A9 em sub-agentes orquestrados.

## Conceito aplicado
Orquestrador + sub-agentes especializados (concorrência, demografia, financeiro), cada um com ferramentas próprias, em vez do fluxo linear monolítico.

## Testes de validação

### T02.1 — Roteamento ao sub-agente correto
- Dado "como está a concorrência no Cabo Branco?"
- Então o orquestrador aciona o sub-agente de concorrência (e não o financeiro).

### T02.2 — Ferramenta de dados em tempo real
- Dado uma pergunta que exige dado atual (ex.: data/contexto recente)
- Então o sub-agente chama a ferramenta correspondente em vez de "inventar" o valor.

### T02.3 — Redução de alucinação
- Dado uma pergunta cuja resposta exige dado não disponível
- Então o agente declara a limitação em vez de fabricar número (validar com casos-golden).

### T02.4 — Isolamento de falha
- Dado que o sub-agente de concorrência falha (timeout)
- Então os demais continuam e o orquestrador reporta degradação parcial, sem derrubar a conversa.

### T02.5 — Rastreabilidade
- Então cada resposta registra qual sub-agente/ferramenta a produziu (log/observabilidade).
