-- 20260822_access_token_expires_at.sql — TTL do capability token da análise grátis.
-- Leitura anônima via GET /api/site-agent/analise/{id} exige token + não expirado.
-- Idempotente.

alter table gymsite.relatorios
  add column if not exists access_token_expires_at timestamptz;

comment on column gymsite.relatorios.access_token_expires_at is
  'UTC expiry for access_token (site-agent free poll). Null = legacy (treat as expired after deploy hardening).';

create index if not exists idx_relatorios_access_token_expires
  on gymsite.relatorios (access_token_expires_at)
  where access_token is not null;
