-- Migration: colunas ONR/cartório/modalidade em candidatos
-- supabase_writer envia tipo_imovel_codigo_onr, tipo_imovel_label, modalidade
-- e cartorio desde ~2026-05-29, mas a tabela não tinha as colunas — PostgREST
-- rejeitava o INSERT inteiro e o failsafe engolia: candidatos vazio por 2
-- semanas (mapa sem pins, A5 sem top-1 na tabela).

ALTER TABLE candidatos
  ADD COLUMN IF NOT EXISTS tipo_imovel_codigo_onr INT,
  ADD COLUMN IF NOT EXISTS tipo_imovel_label TEXT,
  ADD COLUMN IF NOT EXISTS modalidade TEXT,
  ADD COLUMN IF NOT EXISTS cartorio JSONB;
