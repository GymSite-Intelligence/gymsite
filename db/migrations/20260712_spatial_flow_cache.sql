-- Cache de análises de fluxo pedestre (Sintaxe Espacial / OSM)
CREATE TABLE IF NOT EXISTS spatial_flow_cache (
    cache_key TEXT PRIMARY KEY,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    radius_m INTEGER NOT NULL DEFAULT 2000,
    network_type TEXT NOT NULL DEFAULT 'walk',
    payload JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spatial_flow_cache_expires
    ON spatial_flow_cache (expires_at);

CREATE INDEX IF NOT EXISTS idx_spatial_flow_cache_lat_lng
    ON spatial_flow_cache (lat, lng);
