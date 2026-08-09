# VEC-378 — Migração OSM (Nominatim / Overpass / OpenRouteService)

> Objetivo: reduzir custo marginal por relatório migrando geocoding, POIs e
> distâncias/isócronas do Google Maps Platform para serviços OpenStreetMap,
> sem perder a qualidade comercial (nomes/ratings/reviews) que só o Google tem.
> Premissa: pipeline já determinístico (BaseAgent). OSM entra como camada de
> dados determinística, com Google como fallback de qualidade.

## 1. Princípio de divisão (o que migra e o que NÃO migra)

| Necessidade | Hoje | Depois | Mantém Google? |
|---|---|---|---|
| Endereço para coordenada (A1) | Google Geocoding | Nominatim | fallback |
| POIs/âncoras/infra no raio (A1/A3) | Places Nearby | Overpass | não |
| Distâncias ponto para polo (A1) | Distance Matrix | ORS Matrix | fallback |
| Área de influência (isócrona) | inexistente / raio circular | ORS Isochrones | não |
| Concorrentes: nome/rating/review (A3a/b) | SearchAPI `google_maps` | inalterado | **não** (SearchAPI; Places só fallback) |
| Street View do imóvel (A1) | Google | inalterado | SIM |

## 2. Arquitetura proposta

- Novo módulo tools/osm_tools.py com 3 clientes finos e determinísticos:
  - osm_geocode(endereco) -> {lat,lng,score,confianca}  (Nominatim)
  - osm_pois(lat,lng,raio,categorias) -> [poi...]         (Overpass)
  - osm_matrix(origens,destinos,modo) -> matriz           (ORS Matrix)
  - osm_isocronas(lat,lng,modo,faixas) -> GeoJSON         (ORS Isochrones)
- Camada de cache em Postgres/Supabase: tabela osm_cache
  (chave = hash(tipo+args+grid_arredondado), ttl por tipo).
  POIs e isócronas mudam devagar -> cache agressivo (30-90 dias).
- Feature flags por capacidade (espelhar padrão CONCORRENTES_SOURCE):
  GEOCODER=nominatim|google, POIS_SOURCE=overpass|google,
  MATRIX_SOURCE=ors|google. Default inicial: OSM com fallback Google.

## 3. Self-hosting (decisão de custo vs esforço)

Os endpoints públicos (nominatim.openstreetmap.org, overpass-api.de, ORS público)
têm rate limit e proíbem uso pesado. Para produção em rajada:

- Fase A (rápida): usar públicos só em dev + cache. Em prod, contratar ORS
  gerenciado / Geoapify-Stadia (free tiers generosos) enquanto valida volume.
- Fase B (escala): self-host em Cloud Run/VM:
  - Nominatim (imagem mediagis/nominatim) — só Brasil (brazil-latest.osm.pbf)
  - Overpass (wiktorn/overpass-api) — extrato Brasil
  - ORS (openrouteservice/openrouteservice) — perfis foot-walking + driving-car, BR
  - Registrar como workloads no App Hub (ver roadmap_dados_bq_sinergia).

## 4. Fases de entrega

- Fase 0 — Medir baseline (0,5 dia): instrumentar custo Google atual por
  agente (telemetria já existe em metrics/). Quantos R$/relatório são Geocoding +
  Distance Matrix + Places-de-POI (separar do Places-de-concorrente).
- Fase 1 — Geocoding (1 dia): osm_geocode + flag GEOCODER. Validar em N
  endereços reais de Fortaleza vs Google (erro < 50m aceitável). Fallback Google
  se confiança baixa.
- Fase 2 — POIs/âncoras (2 dias): osm_pois via Overpass para
  transporte/educação/saúde/comércio/estacionamento/âncoras do A1. Tags:
  amenity=bus_station|school|hospital|parking, shop=*, leisure=fitness_centre.
  Substitui Places-de-POI (mantém Places só para concorrentes).
- Fase 3 — Matrix + Isócronas (2 dias): osm_matrix e osm_isocronas.
  Habilita "Área de influência" 5/10/15 min (paridade com OndeAbrir) e score de
  acessibilidade real por tempo de deslocamento.
- Fase 4 — Cache + flags default OSM (1 dia): virar default para OSM,
  Google só fallback. Medir custo pós-migração e atualizar data_lineage.md.

## 5. Impacto esperado

- Geocoding e Distance Matrix -> ~R$ 0 (OSM) vs custo por chamada Google.
- POIs deixam de ser cobrados por item (Overpass = 1 query por categoria).
- Ganho de produto: isócronas reais (área de influência) que hoje não existem.
- Cache derruba chamadas repetidas (mesmo bairro analisado N vezes).

## 6. Riscos e mitigação

- Cobertura OSM irregular em cidades pequenas -> fallback Google por flag.
- Rate limit dos públicos -> cache + self-host na Fase B.
- Licença ODbL: exige atribuição "OpenStreetMap contributors" no relatório/mapa
  e mantém derivados de banco sob ODbL.
- Lock-in invertido: reduz dependência Google, aumenta superfície de infra a manter.

## 7. Integração com BQ / RAG / consultor

- BQ: OSM cobre geo/rotas; BQ continua dono de demografia/PIB/CNO. Sem overlap.
- RAG (Discovery Engine): inalterado — OSM é dado estruturado, não qualitativo.
- /consultor: nova tool opcional mapear_area_influencia (wrappa osm_isocronas),
  exposta ao Gemini junto das 10 atuais. Mantém padrão "tool determinística,
  LLM só veste".
