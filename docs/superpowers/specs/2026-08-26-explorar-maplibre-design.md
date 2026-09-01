# Design — Explorar MapLibre + vector CARTO

**Data:** 2026-08-26  
**Âmbito:** Trocar o motor do mapa em `/explorar` de `pigeon-maps` + raster PNG para MapLibre GL + estilos vector CARTO (Positron / Dark Matter). Camadas de produto e API de análise **não** mudam.  
**Humano:** Marcelo  
**Pai:** [2026-08-07-explorar-mapa-design.md](./2026-08-07-explorar-mapa-design.md) · escolha **B** (2026-08-26)  
**Depende de:** isócronas ORS já no `POST /api/explorar/isocronas`; GeoJSON em `explorarIso.ts`; chrome flutuante inalterado

---

## 1. Problema

O explorador já tem o **modelo visual certo** (isócrona 5/10/15 + lente + pins Maps). O motor atual (`pigeon-maps` + tiles PNG CARTO) não chega na nitidez de rua do OndeAbrir (eles usam vector GL Positron / Dark Matter). Overlay de calor hoje é um **blob CSS** no pin — a spec-pai proíbe calor inventado.

Queremos paridade de **basemap** com OndeAbrir, no nosso domínio, sem Google JS na porta de lead e sem iframe do CARTO Builder.

---

## 2. Decisões travadas

| # | Escolha |
|---|---|
| Motor | **MapLibre GL** no `/explorar` via `maplibre-gl` + `react-map-gl` (entry `react-map-gl/maplibre`) |
| Basemap claro | Raster **OSM** (`tile.openstreetmap.org`) estilo MapLibre **constante** (mesma referência). CARTO vector/PNG exige API key |
| Basemap escuro | Mesmos tiles OSM (chrome da UI continua escuro) |
| Satélite | Raster Esri World Imagery (estilo constante) |
| Isoline | **ORS** no backend. CARTO MCP `calculate_isolines` não pinta o site (quota LDS; MCP só no Cursor) |
| Contrato React | Props de `ExplorarMap` **iguais** (`center`, `zoom`, `pin`, `rivals`, `mapStyle`, `camada`, `lente`, `isoRings`, `onClickMap`, `onZoom`) |
| Página | `ExplorarPage` / barra / painel resultado **sem** mudança de fluxo Analisar. Controles: + botão **Vias** (abaixo) |
| Calor | Toggle permanece. **Sem** radial CSS. Camada on + sem dado = vazio (copy “em breve” no chrome, não no mapa fingindo densidade) |
| Pins | Candidato e rivais = **Marker** HTML (mesmo desenho do pigeon). Cluster GL removido — sumia com o restyle |
| Popup rival | Nome + endereço + rating + N reviews quando existirem |
| Chrome | Painéis carvão+lime opacos; **não** herdam o tema do tile |
| `/mapa` | `GoogleMapOceano` **intocado** |
| CARTO MCP | Não renderiza o Explorar. Uso futuro = tools no backend, fora desta spec |
| Fallback | Se `maplibregl.supported()` for false: recado curto + **pigeon** (dep permanece) |
| Atribuição | OSM nas ruas; satélite © Esri |
| Top Vias (UX) | **Não** no Analisar. Terceiro botão **na mesma fileira** que a pé / carro (`grid-cols-3`), só visível com **Área de influência** on. Toggle independente (não é modo de deslocamento). |

---

## 3. Arquitetura

```
ExplorarPage  --mesmas props-->  ExplorarMap
                                   ├─ WebGL ok → MapLibre Map
                                   │     sources: iso GeoJSON, lente GeoJSON, rivals GeoJSON (cluster)
                                   │     style JSON CARTO ou raster Esri
                                   └─ WebGL fail → pigeon-maps (mesmo GeoJSON de explorarIso)
explorarIso.ts  → influenceFeatureCollection + LENTE_M (inalterado no contrato)
                → tileProvider PNG só no fallback pigeon
                → styleUrl(mapStyle) para MapLibre
```

Unidades:

| Unidade | Faz | Depende |
|---|---|---|
| `styleUrl` / sources Esri | Qual JSON/raster carregar | `MapStyle` |
| `ExplorarMap` GL | Click mapa, zoom, layers, popup, cluster | MapLibre, GeoJSON |
| Fallback pigeon | Mesmo job visual mínimo (iso + pins, sem blob) | `pigeon-maps` |
| `explorarIso.ts` | Polígonos lente/iso | Nada de GL |

Não extrair um “map engine” genérico usado por `/mapa`. Dois mundos: Explorar = OSM/CARTO; relatórios = Google.

---

## 4. Camadas no GL (ordem de paint)

1. Basemap (vector ou satélite)  
2. Isócronas m15 → m10 → m5 (fill + line tracejada; cores já em `ISO_STYLE`)  
3. Círculo/anel da lente (stroke azul, fill none) quando camada influência e lente ≠ só bairro sem ring — **mesma regra** `lenteCircle` de hoje  
4. Clusters + rivais (circle)  
5. Pin candidato (circle maior, lime, acima dos rivais)  
6. **Top Vias** (se toggle on + `status=ok`): LineString das vias ranqueadas (vermelho = maior fluxo, igual PDF). Sem coords = sem linha, lista no painel se houver nome.

Camada `calor`: não adiciona layer de densidade. Influência off: sources iso/lente vazios **e** some a fileira a pé/carro/**vias**. Toggle vias persiste em `localStorage` (`explorar-top-vias`) mas só pinta com influência on + pin.

**Controles — fileira influência**

| Botão | Job |
|---|---|
| Ícone pessoa | `modo=pe` (isócrona a pé) |
| Ícone carro | `modo=carro` (isócrona carro) |
| Ícone via (Route) | liga/desliga overlay + fetch `top_vias_por_fluxo` |

Pé/carro = radio. Vias = **checkbox** (lime quando on). Osmnx frio: botão mostra espera; fail-soft some overlay + não inventa ranking. Analisar **não** espera vias.

Click no mapa: igual hoje (fecha popup, `onClickMap`). Click no rival: popup; não dispara novo pin.

---

## 5. Dados e erros

- Iso rings: mesmo `useExplorarIsocronas`. Sem ring = sem fill daquela faixa (não inventar círculo de minutos).  
- Style JSON CARTO falhou (rede): manter último estilo válido ou cair no fallback pigeon após 1 falha visível.  
- WebGL off (VM / GPU): fallback pigeon **sem** blob de calor.  
- Satélite: labels de rua somem (raster). Aceito. Overlays iso/pins continuam.

---

## 6. Teste e aceite

| Critério | Passa se |
|---|---|
| Motor | `/explorar` usa MapLibre quando WebGL existe |
| Estilos | Claro = Positron vector; escuro = Dark Matter; satélite = Esri no mesmo mapa |
| Influência | 3 faixas ORS + lente; a pé/carro troca ring; 3º botão Vias ao lado do carro |
| Top Vias | Overlay só com influência + toggle on; Analisar não bloqueia; indisponível = vazio honesto |
| Calor | Nenhum radial/gradient no pin; toggle não pinta densidade falsa |
| Pins | N rivais = N da legenda; cluster some no zoom in; candidato lime |
| Página | Analisar / absorção / gate degustação iguais |
| Google | `/mapa` sem diff de motor |
| Preview | Rota local ou HTML de referência; Marcelo vê **antes** do merge (preview-aprovacao) |
| Types | `cd frontend && npx tsc --noEmit` |
| Unit | `explorarIso.test.ts` continua; `styleUrl` coberto se função pura nova |

---

## 7. Waves desta spec

**Wave 1:** deps + `ExplorarMap` MapLibre + estilos + iso/lente/pins/cluster + calor honesto (vazio) + fallback WebGL + preview.

**Wave 1b (Top Vias no Explorar):** botão ao lado do carro + layer linhas + lista curta no painel se Analisar já abriu; API fail-soft; **não** PDF degustação/logado nesta wave (já B5 no PDF pipeline).

**Wave 2 (spec futura):** coroplético IBGE; polígono bairro; PDF degustação com `_top_vias_ctx` se o JSON do Explorar tiver o bloco; lista na tela do relatório logado (ler A6, sem 2ª osmnx).

---

## 8. Fora

- Google Maps JS no Explorar  
- deck.gl heatmap de relatórios  
- CARTO Builder / MCP `create_map` na página  
- LDS `calculate_isolines`  
- Score 0–10  
- PDF  
- Trocar Nominatim/SearchAPI  
- Redesenhar o painel Controles além da fileira 3 botões + copy calor “em breve”  
- Top Vias como 3º **modo** de isócrona (pé/carro continuam radio)

---

## 9. Self-review

**Data:** 2026-08-26  

| Check | Resultado |
|---|---|
| Placeholder | Sem TBD. Wave 2 nomeada e **fora** do aceite da wave 1 |
| Consistência | Spec-pai (OSM/CARTO, calor sem inventar, iso ORS) + escolha B alinhados |
| Escopo | Um plano: só motor + overlays do Explorar |
| Ambiguidade | Satélite = Esri **dentro** do MapLibre (não pigeon). Calor on = vazio, não blob |
| Aceite | Tabela §6 testável |
| Fora | §8 explícito |

**Correções no rascunho:** satélite = raster MapLibre. Isoline CARTO MCP fora. **2026-08-26 (2):** Top Vias = 3º botão ao lado do carro (toggle), não no Analisar; wave 1b.
