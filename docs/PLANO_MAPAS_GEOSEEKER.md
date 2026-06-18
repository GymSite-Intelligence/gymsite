# Plano: Aproveitar o GeoSeeker (AI Studio) na camada de Mapas do GymSite

> Documento de analise + ROI. Origem: review do app de exemplo "GeoSeeker"
> (Google AI Studio) cruzado com o que ja existe no repositorio gymsite.
> Foco: a rota de mapas existente esta subutilizada — onde ela ganha valor real.

## 1. Resumo executivo

O GeoSeeker e um jogo (esconde-esconde com o Gemini no Google Maps) e **nao**
se integra ao GymSite. Seu valor para nos e **referencial**: ele demonstra tres
padroes — (a) Gemini com saida JSON estruturada, (b) mapa Google em React,
(c) proxy de Street View no backend.

Conclusao central: **o GymSite ja implementa os tres padroes, e de forma mais
madura e segura que o exemplo.** Portanto o trabalho util **nao e copiar** o
GeoSeeker, e sim **explorar melhor a rota de mapas que ja existe** e que hoje
esta subutilizada. Este plano lista o que reaproveitar (pouco), o que ja temos
(muito) e onde investir com melhor ROI.

## 2. O que ja existe no GymSite (inventario)

Camada de mapas (frontend):
- `frontend/src/routes/MapaRelatoriosPage.tsx` (~900 linhas): pins por bairro
  (geocode bairro+cidade), clusters de pins co-localizados com tolerancia por
  zoom, lentes "viabilidade"/"mercado", filtros por veredito/cidade, modo
  comparar, e `StreetViewPreview`.
- `frontend/src/components/maps/GoogleMapOceano.tsx`: Google Maps JS + heatmap
  (deck.gl) por "oceano"; fallback `pigeon-maps` (OSM) quando a chave nao esta
  disponivel ou `VITE_MAP_PROVIDER=pigeon`.
- `frontend/src/components/maps/MapaMunicipioMercado.tsx`: mapa de mercado por
  municipio (heatmap, clusters, lente A6/A9).
- `frontend/src/routes/MarketAtlasPage.tsx`: catalogo de ondas (red/transition/
  blue) ligado a golden cases.

Camada de mapas (backend / tools):
- `tools/maps_js_config.py`: entrega a chave **JS publica** (restrita por
  REFERRER, so Maps JavaScript API) ao frontend via `useMapsJsConfig`.
- `tools/maps_street_view.py`: **proxy de Street View ja existente**
  (`/api/maps/street-view`), com chave SERVER separada da chave JS.
- `tools/maps_tools.py`: Places (New) + Geocoding + Street View, com **cache em
  disco** (TTL 12h) para conter custo.
- `tools/maps_health.py`: health-check das APIs de mapas.
- `frontend/src/components/domain/CandidatoCard.tsx`: ja renderiza Street View
  do candidato de prospeccao.

Camada de IA (Gemini) — multi-agente (Google ADK):
- Agentes a0..a9 (`agents/`): GeoScout, ContextBuilder, CompetitorAnalysis,
  CompetitorMapper, ReportConsolidator, PositioningStrategist, etc.
- `tools/_genai_client.py`: `generate_content_resilient` (retry + backoff +
  tratamento de resource-exhausted) — robustez que o GeoSeeker nao tem.
- Deep research, Google Search grounding e engine conversacional ja presentes.

## 3. O que o GeoSeeker tem vs. o que o GymSite ja tem

| Padrao do GeoSeeker | Estado no GymSite | Veredito |
|---|---|---|
| Gemini com JSON Schema | Multi-agente ADK + client resiliente | GymSite **superior** |
| Mapa Google em React | GoogleMapOceano + heatmap deck.gl + fallback OSM | GymSite **superior** |
| Proxy Street View | `/api/maps/street-view` + chave server separada + cache | GymSite **superior** |
| Chave no localStorage / query string | Split JS(referrer) vs server(IP) | GymSite **mais seguro** |
| Zonas geograficas fixas | Geocode real bairro+cidade dos relatorios | GymSite **superior** |

Ou seja: **nada do codigo do GeoSeeker precisa ser portado.** O unico
ganho conceitual aproveitavel e a *ideia de UX* de "pista + contexto visual"
(o Street View como evidencia ao lado do dado), que ja temos parcialmente.

## 4. Onde a rota de mapas esta subutilizada (gaps)

1. **Street View como evidencia de campo no relatorio**: o proxy existe, mas o
   mapa de relatorios usa pouco. Falta amarrar Street View do endereco-ancora
   dentro do A6/A9 e do PDF.
2. **Heatmap sem leitura guiada**: o heatmap "oceano" existe, mas nao ha uma
   sintese textual ("o que este mapa esta dizendo") gerada por Gemini.
3. **GeoScout (a1) -> mapa**: o GeoScout ja identifica zonas-ancora, mas o
   output nao alimenta visivelmente a rota de mapas como camada navegavel.
4. **Custo/observabilidade**: cache existe em `maps_tools`, mas sem painel de
   gasto por API (Places/Geocoding/StreetView) para decisao de ROI.

## 5. Iniciativas priorizadas por ROI

### ROI Alto / Esforco Baixo
- **R1. Street View no relatorio A6/A9 + PDF**: reusar `/api/maps/street-view`
  para inserir a foto do endereco-ancora no relatorio. Reaproveita 100% do que
  existe. Valor: torna o relatorio mais "tangivel" para o cliente. Custo extra
  ~0 (proxy + cache ja prontos).
- **R2. Sintese do heatmap via Gemini**: alimentar o mapa com um paragrafo
  "leitura do territorio" usando `generate_content_resilient` + JSON
  estruturado. Baixo esforco, alto efeito percebido.

### ROI Medio / Esforco Medio
- **R3. GeoScout como camada navegavel no mapa**: pins das zonas-ancora do a1
  sobre o GoogleMapOceano, com lente dedicada. Conecta prospeccao -> mapa.
- **R4. Painel de custo de Maps APIs**: expor gasto por API reusando
  `maps_health`/`maps_tools` para guiar decisao de cache/TTL.

### ROI Baixo (descartar por ora)
- **R5. Portar codigo do GeoSeeker**: sem ganho — ja temos versao superior.
- **R6. Modo "jogo"/gamificacao do mapa**: fora do escopo de negocio.

## 6. Recomendacoes de seguranca (validas tambem ao olhar o GeoSeeker)

- Manter o split de chaves: JS (referrer) vs SERVER (Places/Geocoding/SV).
  O GeoSeeker erra ao trafegar a key por query string — **nao** replicar isso.
- Nao expor chave SERVER ao cliente; Street View sempre via proxy.
- Geracao/rotacao de chaves e billing: feitos manualmente no Google Cloud
  (fora do escopo de automacao).

## 7. Proximos passos sugeridos

1. Validar este plano e escolher o lote inicial (sugestao: R1 + R2).
2. R1: ligar Street View do endereco-ancora ao A6/A9 e ao builder de PDF.
3. R2: prompt + JSON schema para "leitura do territorio" no mapa.
4. Medir efeito (qualidade percebida do relatorio) antes de R3/R4.

---
_Gerado a partir de review do GeoSeeker (AI Studio) + inventario do repositorio.
Nenhum codigo do exemplo foi portado; o foco e melhor uso do que ja existe._
