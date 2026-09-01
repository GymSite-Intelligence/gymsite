# CARTO — gym_hex_cidade (Fase A)

Checklist operacional para manter a tabela H3 de academias por cidade em sync com o GymSite. Não exige deploy de código.

## 1. Importar pontos no CARTO DW

- Importar GeoJSON ou CSV dos mesmos pontos de academia no dataset **`shared`** (conexão **`carto_dw`**).

## 2. Workflow `gym_hex_cidade`

Criar ou atualizar o workflow com o nome **`gym_hex_cidade`**:

1. **H3** (resolução **8**) sobre a geometria dos pontos.
2. **Group by** `hex` (e `cidade` se disponível na fonte).
3. **Count** → coluna `n_academias`.
4. **Save as table** (tabela persistida no DW — **não** apenas resultado temporário).

Colunas esperadas na tabela salva:

| Coluna        | Descrição                          |
|---------------|------------------------------------|
| `hex`         | Índice H3 res 8                    |
| `n_academias` | Contagem de academias no hex       |
| `cidade`      | Nome da cidade                     |
| `gerado_em`   | Timestamp (se o nó do workflow permitir) |

## 3. Mapa no Builder

- Mapa de produto (não o demo “Retail Store Performance”):
  - ID: `bd4c557d-26c0-455c-8fb7-52b9e96802f5`
  - Editor: [clausa.app.carto.com/builder/…](https://clausa.app.carto.com/builder/bd4c557d-26c0-455c-8fb7-52b9e96802f5)
- Camadas: **Brasil** (Overture, zoom país) + **Busca no recorte** (mesma base, `confidence >= 0.8`, lime, zoom da busca).
- Named Source `gymsite_overture_busca` (SQL com `@wkt`) para Maps API.
- Privacidade: mapa de produto **público** (Share → Public) para o iframe do Explorar logado.
  - Viewer: [clausa.app.carto.com/map/bd4c557d-26c0-455c-8fb7-52b9e96802f5](https://clausa.app.carto.com/map/bd4c557d-26c0-455c-8fb7-52b9e96802f5)
  - Colar esse `/map/{id}` em `VITE_CARTO_BUILDER_EMBED_URL` (não usar `/builder/`).
  - Embed: [docs CARTO](https://docs.carto.com/carto-user-manual/maps/sharing-and-collaboration/embedding-maps).

## 4. Sincronizar com o GymSite

Após cada execução bem-sucedida do workflow:

- Exportar a tabela do CARTO **ou**
- Copiar `n_academias` (e demais colunas) para `data/carto/gym_hex_cidade.json`

Schema do JSON local (mesmo contrato da API futura):

```json
{
  "h3_res": 8,
  "fonte": "gym_hex_cidade",
  "gerado_em": "<ISO8601 UTC>",
  "rows": [
    { "hex": "<h3_index>", "n_academias": 0, "cidade": "<nome>" }
  ]
}
```

Isso mantém a API em sync até existirem credenciais BigQuery.

## 5. LDS / isolines

- **Não** habilitar LDS isolines neste mapa para cliques de produto.

## 6. Aceite (Fase A)

- [x] Mapa público: `https://clausa.app.carto.com/map/bd4c557d-26c0-455c-8fb7-52b9e96802f5`
- [ ] Hex + pins visíveis no Builder.
- [ ] Re-executar o workflow produz tabela atualizada.
- [ ] MCP `explore_data` encontra a tabela `gym_hex_cidade` no DW.
