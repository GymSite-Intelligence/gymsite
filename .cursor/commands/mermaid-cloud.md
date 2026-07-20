---
name: mermaid-cloud
description: "Passos Connect + Sync + dashboard Mermaid Chart (nuvem)"
---

# /mermaid-cloud — mandar pro dashboard

Sobe/liga o `.mmd` local com a conta Mermaid Chart (mermaid.ai).
Agente **não** consegue colar token nem clicar Sync por você — dá o checklist certo.

## Argumentos

- path do `.mmd` (preferido)
- se fonte `.py`: usar `.mmd` irmão; se não existir, criar antes (lógica `/mermaid`)

## Pré-requisito

Login Mermaid Chart já feito uma vez (`MermaidChart: Login` + token/OAuth).
Se não logado: parar e pedir login antes do Connect.

## Workflow (ordem importa — prosa clara)

1. Garantir que o `.mmd` existe e está salvo.
2. Pedir ao usuário (checklist clicável na cabeça dele):

   1. Abrir o `.mmd` no editor.
   2. `MermaidChart: Connect Diagram` — liga arquivo ↔ projeto cloud.
   3. `MermaidChart: Sync Diagram` — envia/puxa versão.
   4. `Edit in Mermaid Chart` — abre browser no dashboard.
   Alternativa: sidebar **Mermaid Chart** → Refresh → projeto → Add Diagram → Sync.

3. Não repetir o token no chat. Se login falhar: apontar settings em https://mermaid.ai/app/user/settings e regenerar token (sem colar segredo aqui).

4. Responder com o path do `.mmd` + os 4 passos acima, curto.

## Exemplos

- `/mermaid-cloud`
- `/mermaid-cloud models/pipeline_schemas.mmd`
- `/mermaid-cloud docs/arquitetura/infra_producao.mmd`
