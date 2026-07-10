-- Task #19 + bug latente: o enum sensibilidade_stress nunca ganhou o valor do
-- stress de ocupação (1.7) — o INSERT do lote inteiro de sensibilidade falhava
-- em silêncio e a tabela está VAZIA em todos os runs. Mesma doença do PGRST204:
-- id novo de stress no código exige valor novo no enum AQUI.
ALTER TYPE public.sensibilidade_stress ADD VALUE IF NOT EXISTS 'ocupacao_aluguel_mais_20pct';
ALTER TYPE public.sensibilidade_stress ADD VALUE IF NOT EXISTS 'fiscal_anexo_v';
