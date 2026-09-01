---
name: gymsite-carto
description: >-
  CARTO no GymSite — Builder layers, Workflows, Named Sources, Maps/SQL API,
  Data Observatory, MCP user-carto, embed Explorar. Use when the user mentions
  CARTO, carto_dw, Builder, Workflows, named source, vectorQuerySource, deck.gl
  CARTO, Overture, hex H3, camada CARTO, iframe Builder, Data Observatory,
  isoline LDS, or integrating search/município/bairro with a warehouse query.
---

# GymSite — CARTO

Carregar esta skill **antes** de criar layer, workflow, named source ou código que fale com CARTO. Spec de produto: `docs/superpowers/specs/2026-08-27-carto-hibrido-design.md`. Docs oficiais: [overview](https://docs.carto.com/carto-for-developers/overview). Detalhe de APIs e links: [reference.md](reference.md).

## O que já existe (e o que não)

| Peça | Estado |
|---|---|
| MCP `user-carto` no Cursor | Sim — laboratório (maps, SQL, named sources, isolines) |
| Skill oficial `CartoDB/agent-skills` (23 playbooks CLI) | **Não instalada** neste repo |
| Skill GymSite `gymsite-carto` | Esta pasta |
| Código produto | `backend/routers/carto.py`, `tools/carto_hex.py`, iframe em `ExplorarPage`, `VITE_CARTO_BUILDER_EMBED_URL` |
| Conta | `clausa.app.carto.com` / API `gcp-us-east1`; DW `carto_dw`; mapa produto `bd4c557d-26c0-455c-8fb7-52b9e96802f5` |

Skills oficiais da CARTO ensinam **CLI + MCP genérico**. Esta skill ensina **GymSite**. Não duplicar o catálogo de 23 skills; apontar o humano para instalar se quiser CLI (`npx skills add CartoDB/agent-skills`). Docs: [CARTO Agent Skills](https://docs.carto.com/carto-for-agents/agent-skills).

## Trava de produto (não negociar no chat)

- Número na UI = tabela/API + carimbo (valor · base · fonte · janela). Sem linha = erro, sem inventar.
- Aluguel = MRLR. CARTO não estima aluguel.
- Isoline do **Explorar** = ORS (`POST /api/explorar/isocronas`). `calculate_isolines` do MCP **não** no clique do site.
- MapLibre permanece no fluxo lead. Iframe Builder só **logado** + URL de embed.
- PDF / A0–A9 / visitante anônimo não consomem CARTO neste ciclo.
- SQL de warehouse **não** vai no browser. Named Source + token com grant só nesse source, ou backend GymSite.

## Três superfícies (não misturar)

```
Laboratório (Cursor MCP / Builder / Workflows)
        → tabela estável em carto_dw (não só workflows_temp)
                → produto GymSite (hex-count, GeoJSON, ou iframe)
```

1. **Builder** — mapa salvo, layers, estilo, embed. Bom para ver; ruim para buscar município/bairro (iframe estático).
2. **Workflows** — DAG visual → SQL no warehouse. Persistência = Save as table. `workflows_temp` é intermediário, não contrato do site.
3. **Developers (Maps + Named Source)** — layer no **MapLibre** do Explorar via `vectorQuerySource` / tiles. É o caminho para recortar a query Overture pelo polígono da busca.

## Layers

**No Builder** ([layers](https://docs.carto.com/carto-user-manual/maps/layers)): fonte válida (`geom` ou spatial index) → layer automático. Tipos: Point (e agregações Grid / **H3** / Heatmap / Cluster), Polygon, Line, Raster. Ordem no painel = ordem de desenho. Grupo só organiza, não muda dado.

**No app** ([vectorQuerySource](https://docs.carto.com/carto-for-developers/reference/data-sources/vectorquerysource)):

- Coluna espacial default: `geom`.
- BigQuery: parâmetros **nomeados** `@wkt` — nunca concatenar WKT na string.
- `sqlQuery` no front = **nome do Named Source**, não o SELECT.
- Token: API Access Token com grant do Named Source ([auth](https://docs.carto.com/carto-for-developers/key-concepts/authentication-methods)). GymSite logado = JWT Supabase **além** disso; anônimo não chama CARTO.

Camada Overture de academias: SQL filtra categoria + `country = 'BR'`. Recorte da busca = `ST_INTERSECTS(geom, ST_GEOGFROMTEXT(@wkt))` com WKT do município/bairro/lente que o GymSite já resolve (`resolver_bairro_poligono`). Polígono do Brasil inteiro = camada nacional, **não** busca.

## Workflows

- Esquerda → direita; output de um nó pode pular nós.
- Resultados: Messages / Data / Map / SQL compilado.
- **Save as table** no dataset `shared` (ex. `gym_hex_cidade`) com `hex`, `n_academias`, `cidade`, `fonte`/`gerado_em`.
- API do workflow = `CALL` de procedure em `workflows_temp` + `queryParameters` ([executar via API](https://docs.carto.com/carto-user-manual/workflows/executing-workflows-via-api)). Depois de editar o canvas: **Update** no modal API. Output node define `workflowOutputTableName` (temp). Produto GymSite lê a **tabela persistida**, não o temp do job.
- Variável Geo na API: FeatureCollection JSON em string.

Fluxo canônico já combinado: pontos geocodificados → H3 res **8** → count → JSON `data/carto/gym_hex_cidade.json` (`export_carto_gym_hex.py`) espelhando o workflow.

## Busca município/bairro × query CARTO

A caixa do Explorar **não** consulta Overture. Geocode GymSite → pin + polígono → iframe CARTO com `lat`/`lng`/`zoom`/`mask`/`search` ([URL parameters](https://docs.carto.com/carto-user-manual/maps/sharing-and-collaboration/url-parameters)).

Mapa produto **Map Gym**:
- Layer **Brasil** (teal) — zoom baixo
- Layer **Busca no recorte** (lime, `confidence >= 0.8`) — zoom da busca

Named Source `gymsite_overture_busca` = mesma SQL com `@wkt` (Maps API / futuro). Disparar query pesada **só depois** do lugar escolhido.

## MCP no Cursor

Usar `user-carto` para explorar DW, validar mapa, named sources, SQL de laboratório. Não usar MCP como backend do www. Não `calculate_isolines` no fluxo Analisar.

Se MCP pedir auth: `mcp_auth` nesse namespace.

## Docs — como ler (GitBook)

Páginas `.md`. Dúvida pontual:

`GET https://docs.carto.com/<path>.md?ask=<pergunta>&goal=<objetivo>`

Índice: [llms.txt](https://docs.carto.com/llms.txt). Catálogo oficial de skills: [skills-catalog](https://docs.carto.com/carto-for-agents/agent-skills/skills-catalog).

## Anti-padrões

- Colar SELECT no `ExplorarPage` / Vite.
- Trocar MapLibre pelo Builder no visitante.
- Rodar query Overture no bbox do Brasil a cada tecla.
- Filtrar “Centro” / “Navegantes” só por texto em `addresses` (ambíguo).
- Injetar contagem CARTO no PDF sem spec nova.
- Tratar skill oficial CARTO como se já estivesse no `.agent/skills`.
