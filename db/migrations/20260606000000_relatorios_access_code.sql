-- Adiciona as colunas de acesso via código para leads na tabela relatorios
ALTER TABLE relatorios
ADD COLUMN IF NOT EXISTS access_code UUID UNIQUE,
ADD COLUMN IF NOT EXISTS access_code_used_at TIMESTAMP WITH TIME ZONE;
