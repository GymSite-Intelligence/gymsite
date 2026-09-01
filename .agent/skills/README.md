# GymSite Intelligence — Workspace de Skills

Este diretório contém as **Agent Skills** especializadas para o projeto **GymSite Intelligence**, otimizadas para o ecossistema Antigravity.

## Estrutura

```
.agent/skills/
├── README.md                          # Este arquivo
├── catalog/
│   ├── sla-defaults.ts                # AgentRole (Product…Design)
│   └── skills-catalog.ts              # Catálogo P-000 / ROT (skill → role → step)
├── gymsite-backend/SKILL.md           # FastAPI, Pydantic, Supabase
├── gymsite-frontend/SKILL.md          # React, TanStack, shadcn/ui
├── gymsite-pipeline/SKILL.md          # Google ADK, agentes A0–A9
├── gymsite-intelligence/SKILL.md      # Google Maps, CNPJ, CNO, scraping
├── gymsite-carto/SKILL.md             # CARTO Builder, Workflows, Named Sources, Explorar
├── gymsite-reporting/SKILL.md         # ReportLab, matplotlib, PDF
├── gymsite-prospecting/SKILL.md       # Prospecção, pipeline, webhooks
├── gymsite-devops/SKILL.md            # Hetzner VPS/Tunnel, Wrangler/Pages, env
└── gymsite-testing/SKILL.md           # pytest (.venv) + tsc; Vitest/Playwright quando existir
```

## Catálogo de skills (governança)

Fonte de verdade skill → `agentRole` → passo ROT: [`catalog/skills-catalog.ts`](catalog/skills-catalog.ts).

- Pilares review (Strategy → Docs) + Design UX + Produtividade (P-000).
- Helpers: `allSkills()`, `skillsForRole()`, `skillKeyForRotStep()`, `catalogSummary()`.
- Skills **domínio GymSite** (`gymsite-*`) ficam nas pastas acima — não entram no mapa ROT do catálogo.
- Skills Cursor espelho: `.cursor/skills/<id>/SKILL.md` (ex.: `pretty-mermaid`).

## Como Funciona

O Antigravity carrega automaticamente o **metadata** (`name` + `description`) de todas as skills ao iniciar uma sessão. Quando você faz uma solicitação relacionada a uma skill, o agente:

1. **Detecta** a skill mais relevante pela descrição
2. **Carrega** o conteúdo completo do `SKILL.md` no contexto
3. **Segue** as instruções, padrões de código e anti-padrões da skill

### Exemplos de Ativação

| Sua solicitação | Skill ativada |
|---|---|
| "Crie um endpoint para listar relatórios" | `gymsite-backend` |
| "Adicione paginação na tabela de prospecção" | `gymsite-frontend` |
| "O agente A3 está falhando, depure" | `gymsite-pipeline` |
| "Busque concorrentes no bairro Aldeota" | `gymsite-intelligence` |
| "Camada CARTO / Named Source / Workflows" | `gymsite-carto` |
| "Gere um gráfico de payback" | `gymsite-reporting` |
| "Mude o status da oportunidade para fechado" | `gymsite-prospecting` |
| "Configure deploy de produção" | `gymsite-devops` + `/deploy` |
| "Crie testes para o endpoint de prospecção" | `gymsite-testing` |

## Adicionando Novas Skills

1. Crie uma pasta: `mkdir .agent/skills/nome-da-skill`
2. Crie o arquivo `SKILL.md` com frontmatter YAML:

```markdown
---
name: nome-da-skill
description: Descrição curta de quando usar esta skill. Use ao... NÃO use quando...
---

# Título

## Use esta skill quando
- ...

## NÃO use esta skill quando
- ...

## Instruções
1. ...

## Anti-padrões
- ❌ Não...
```

3. Reinicie a sessão do agente para que a nova skill seja detectada.

## Convenções do Projeto

- **Backend:** Python 3.14, FastAPI, Pydantic v2, Supabase
- **Frontend:** React 19, TypeScript, TanStack Router/Query, shadcn/ui, Tailwind
- **Agentes:** Google ADK, Gemini Flash, session state puro (A0–A9)
- **Deploy:** Hetzner VPS + Cloudflare Tunnel + Wrangler/Pages — ver `/deploy` e P-000 §7–§8
- **Estilo:** Minimalista, funcional, sem over-engineering
