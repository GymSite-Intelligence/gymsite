-- Migration: 20260529_candidato_cartorios.sql
-- Add ONR and Cartorio columns to the candidatos table

alter table candidatos
  add column if not exists tipo_imovel_codigo_onr integer,
  add column if not exists tipo_imovel_label text,
  add column if not exists modalidade text,
  add column if not exists cartorio jsonb;

comment on column candidatos.tipo_imovel_codigo_onr is 'Código ONR do tipo de imóvel comercial.';
comment on column candidatos.tipo_imovel_label is 'Label textual do tipo de imóvel comercial (ex: Galpão, Loja, Sala).';
comment on column candidatos.modalidade is 'Modalidade comercial do imóvel (locacao | venda | incerto).';
comment on column candidatos.cartorio is 'Objeto JSON com dados públicos da serventia de registro de imóveis competente.';
