# CARTO — referência (carregar sob demanda)

## Docs âncora

| Tema | URL |
|---|---|
| Developers overview | https://docs.carto.com/carto-for-developers/overview |
| Auth (token / SPA OAuth / M2M) | https://docs.carto.com/carto-for-developers/key-concepts/authentication-methods |
| Named Sources | https://docs.carto.com/carto-user-manual/developers/named-sources |
| Evitar SQL no app | https://docs.carto.com/carto-for-developers/guides/avoid-exposing-sql-queries-with-named-sources |
| vectorQuerySource | https://docs.carto.com/carto-for-developers/reference/data-sources/vectorquerysource |
| Layers (Builder) | https://docs.carto.com/carto-user-manual/maps/layers |
| SQL Parameters (Builder) | https://docs.carto.com/carto-user-manual/maps/sql-parameters |
| Embed + URL params | https://docs.carto.com/carto-user-manual/maps/sharing-and-collaboration/url-parameters |
| Workflows | https://docs.carto.com/carto-user-manual/workflows |
| Workflows via API | https://docs.carto.com/carto-user-manual/workflows/executing-workflows-via-api |
| Data Observatory | https://docs.carto.com/carto-user-manual/data-observatory |
| CARTO for Agents | https://docs.carto.com/carto-for-agents |
| Agent Skills (oficial) | https://docs.carto.com/carto-for-agents/agent-skills |
| Skills catalog (23) | https://docs.carto.com/carto-for-agents/agent-skills/skills-catalog |
| Install skills oficiais | https://docs.carto.com/carto-for-agents/agent-skills/installation |
| Repo skills | https://github.com/CartoDB/agent-skills |
| Índice LLM | https://docs.carto.com/llms.txt |

Maps API cria layers a partir de query, tabela ou tileset. SQL API corre query no warehouse. Named Sources API guarda o alias. Resources API lista maps/workflows/connections.

## Catálogo oficial (não está no GymSite)

Utility: `carto-basics`, `carto-connect-datawarehouse`, `carto-query-datawarehouse`, `carto-explore-datawarehouse`.

Platform: `carto-import-export-data`, `carto-create-workflow`, `carto-find-spatial-data`, `carto-manage-platform`, `carto-create-builder-maps`, `carto-render-inline-map`, `carto-preview-builder-map`, `carto-develop-app`.

Use-case: hotspot, Moran's I, GWR, enrichment, trade area, site selection, territory, routing/OD, geocoding, composite scoring, ArcGIS migration.

Instalar no Cursor/Claude (opcional, CLI autenticado): marketplace `CartoDB/agent-skills` ou `npx skills add CartoDB/agent-skills`. Independente do MCP.

## GymSite — ficheiros

| Ficheiro | Papel |
|---|---|
| `docs/superpowers/specs/2026-08-27-carto-hibrido-design.md` | Spec A/B/C |
| `docs/superpowers/plans/2026-08-27-carto-hibrido.md` | Plano |
| `data/carto/WORKFLOW.md` | Checklist humano Builder/DW |
| `data/carto/gym_hex_cidade.json` | Tabela hex (hoje recorte Fortaleza) |
| `scripts/batch/export_carto_gym_hex.py` | Pontos → H3 res 8 |
| `tools/carto_hex.py` | Lookup lat/lng |
| `backend/routers/carto.py` | `GET/POST /api/carto/hex-count` JWT |
| `frontend/src/lib/cartoHex.ts` | Cliente |
| `frontend/src/routes/ExplorarPage.tsx` | Toggle iframe |
| `frontend/.env.example` | `VITE_CARTO_BUILDER_EMBED_URL` |

Named Source `gymsite_overture_busca` (`@wkt`). Mapa `bd4c557d-…`: datasets Brasil + Busca no recorte (`confidence >= 0.8`). Explorar iframe: `cartoBuscaEmbedUrl` (lat, lng, zoom, mask, search, layers).

## Named Source — padrão BigQuery (Overture recortada)

No console CARTO: Developers → Named Sources. Token: grant **só** este source.

```sql
SELECT geoid, names.primary AS nome, categories.primary AS categoria, confidence, geom
FROM `carto-data.ac_dr11t2te.carto_overture_geography_glo_places_v3`
WHERE categories.primary IN (
  'gym', 'health_and_wellness_club', 'boxing_gym', 'yoga_studio',
  'pilates_studio', 'martial_arts_club', 'fitness_trainer'
)
  AND (operating_status IS NULL OR operating_status = 'open')
  AND EXISTS (
    SELECT 1 FROM UNNEST(addresses.list) AS item
    WHERE item.element.country = 'BR'
  )
  AND ST_INTERSECTS(geom, ST_GEOGFROMTEXT(@wkt))
```

App: `sqlQuery: 'gymsite_overture_gyms_recorte'` + `queryParameters: { wkt: '<POLYGON...>' }`.

`@wkt` vem do polígono GymSite (bairro IBGE, município, ou buffer 500 m / 1 km). Sem WKT, não executar.

## Auth produto vs CARTO

- Explorar anônimo: sem CARTO.
- Explorar logado iframe: mapa público/restrito consciente — nunca mapa privado vazando.
- Layer Developers: token CARTO no **servidor** ou token público **restrito a named sources**; sessão GymSite continua Bearer Supabase no nosso API.
- Hex-count: só JWT GymSite; lê JSON local / `CARTO_HEX_TABLE_PATH`, não o browser→BQ.

## MCP Cursor (`user-carto`)

Descobrir schema com `GetDynamicTools` no namespace. Típico: `explore_data`, `execute_query`, `view_map`, `read_maps`, `create_map` / `update_map`, `manage_named_sources`, `run_workflow`, `calculate_isolines` (só Cursor).

Quota LDS: isoline MCP ≠ produto.
