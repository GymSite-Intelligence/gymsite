---
name: mermaid-preview
description: "Garante .mmd existe e dá o passo único do cinema (Preview)"
---

# /mermaid-preview — ir ao cinema

Objetivo: usuário ver o diagrama no Preview do Mermaid Chart **sem Generate IA**.

## Argumentos

- caminho do `.mmd` ou do fonte `.py`/etc.
- se vazio: arquivo focado; se for `.py` e existir `.mmd` irmão, usar o `.mmd`.

## Workflow

1. Se alvo é fonte sem `.mmd` irmão → criar o `.mmd` (mesma lógica de `/mermaid`).
2. Se `.mmd` já existe → não reescrever a menos que usuário peça "atualizar".
3. Responder **só** o ritual do cinema (ordem importa):

   1. Abrir o arquivo `.mmd` no editor (não o `.py`).
   2. `Ctrl+Shift+P` → `MermaidChart: Preview Diagram`
      (ou CodeLens Preview se aparecer no topo do `.mmd`).

4. Lembrar: Preview ≠ Sync cloud. Dashboard = `/mermaid-cloud`.

## Exemplos

- `/mermaid-preview`
- `/mermaid-preview models/pipeline_schemas.mmd`
- `/mermaid-preview @models/pipeline_schemas.py`
