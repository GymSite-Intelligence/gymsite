-- Migration: colunas de listing imobiliário em candidatos (OLX / ImovelWeb)
-- Aplicar via Supabase SQL editor ou: supabase db push

alter table candidatos
  add column if not exists listing_url text,
  add column if not exists listing_id text,
  add column if not exists price_raw text,
  add column if not exists listing_source text;

comment on column candidatos.listing_url is 'URL clicável do anúncio (OLX/ImovelWeb) quando qualidade_sinal=direto-listing';
comment on column candidatos.listing_id is 'ID numérico do portal (dedup key)';
comment on column candidatos.price_raw is 'Preço como exibido no portal (ex: R$ 28.000/mês)';
comment on column candidatos.listing_source is 'Portal de origem: olx | imovelweb';
