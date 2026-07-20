---
name: mermaid
description: "Gera/atualiza .mmd a partir do arquivo focado ou @path (filme pronto pro Preview)"
---

# /mermaid — criar diagrama local

Transforma o código/fonte indicado num arquivo Mermaid `.mmd` no disco (cinema local).
NÃO depende de GitHub Copilot nem do botão Generate do plugin.

**Skill:** carregar `.cursor/skills/pretty-mermaid/SKILL.md` — formas v11.3+ (`@{ shape }`), dedupe, elk, Preview MermaidChart.

## Argumentos

Texto depois do comando:
- caminho `@arquivo` / path relativo, **ou**
- se vazio: usar o arquivo **focado no editor**

## Workflow

1. Ler o arquivo-fonte (`.py`, `.ts`, `.sql`, docs, etc.).
2. Escolher tipo Mermaid adequado:
   - classes/schemas Pydantic → `classDiagram`
   - fluxo/pipeline/infra → `flowchart TB`
   - sequência de chamadas → `sequenceDiagram`
   - tabelas SQL → `erDiagram`
3. Escrever/atualizar `.mmd` **ao lado do fonte** quando fizer sentido
   (ex.: `models/pipeline_schemas.py` → `models/pipeline_schemas.mmd`),
   senão em `docs/arquitetura/<nome>.mmd`.
4. Responder curto em português:
   - path do `.mmd`
   - dizer: abrir o `.mmd` → comando `MermaidChart: Preview Diagram`
     (ou `Ctrl+Shift+P` só nessa hora) — agente não abre o painel Preview sozinho.
5. NÃO pedir Copilot. NÃO inventar sync cloud aqui — isso é `/mermaid-cloud`.

## Exemplos

- `/mermaid` (com `pipeline_schemas.py` focado)
- `/mermaid @tools/financial_tools.py`
- `/mermaid docs/metodologia/data_lineage.md`
