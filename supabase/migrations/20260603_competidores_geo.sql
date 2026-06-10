-- Coordenadas dos concorrentes (Places / OSM) para mapa municipal no viewer
alter table competidores
  add column if not exists lat numeric(10, 6),
  add column if not exists lng numeric(10, 6),
  add column if not exists distancia_km numeric(8, 2),
  add column if not exists google_maps_uri text;

comment on column competidores.lat is 'Latitude do estabelecimento (Google Places / OSM).';
comment on column competidores.lng is 'Longitude do estabelecimento.';
comment on column competidores.distancia_km is 'Distância ao centro do raio de busca (km).';
comment on column competidores.google_maps_uri is 'Link Google Maps do place.';
