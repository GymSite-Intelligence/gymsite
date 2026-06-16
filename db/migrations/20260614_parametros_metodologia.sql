-- Parâmetros de metodologia (REGRA DE OURO: zero hardcode). Todo fator de cálculo
-- com fonte/método, recalibrável. Lido por tools/parametros_metodologia.py.
-- Ver feedback regra-ouro-zero-hardcode + PLANO_ENRIQUECIMENTO_RELATORIO §1.0.

create table if not exists public.parametros_metodologia (
  nome          text primary key,
  valor         double precision not null,
  fonte         text not null,
  data_coleta   date,
  metodo        text,
  unidade       text,
  updated_at    timestamptz not null default now()
);
alter table public.parametros_metodologia enable row level security;

insert into public.parametros_metodologia (nome, valor, fonte, data_coleta, metodo, unidade) values
 ('ocupacao_studio', 1.5, 'IBGE PNAD + ajuste tipologia studio', '2026-06-14', 'media_domiciliar_ajustada', 'moradores/unidade'),
 ('ocupacao_1_2_dorm', 2.2, 'IBGE PNAD + ajuste 1-2 dorm', '2026-06-14', 'media_domiciliar_ajustada', 'moradores/unidade'),
 ('ocupacao_3_mais_dorm', 3.0, 'IBGE PNAD + ajuste 3+ dorm', '2026-06-14', 'media_domiciliar_ajustada', 'moradores/unidade'),
 ('ocupacao_default', 2.8, 'fallback_IBGE_media_domiciliar_BR', '2026-06-14', 'media_nacional', 'moradores/unidade'),
 ('m2_por_unidade', 75.0, 'fallback_proxy_unidade_media+area_comum', '2026-06-14', 'proxy_area_construida', 'm2/unidade'),
 ('penetracao_geral', 0.045, 'ACAD/Panorama Fitness Brasil', '2026-06-14', 'penetracao_mercado', 'fracao'),
 ('penetracao_bairro_ab', 0.10, 'ACAD (bairro alta renda A/B)', '2026-06-14', 'penetracao_mercado_segmentada', 'fracao'),
 ('market_share_default', 0.15, 'fallback_conservador (A4/aneis recalibra)', '2026-06-14', 'quota_raio_estimada', 'fracao'),
 ('inadimplencia_default', 0.06, 'fallback_ACAD_com_recorrencia', '2026-06-14', 'benchmark_setorial', 'fracao'),
 ('meses_entrega', 30, 'fallback_mediana_obra_24_36m', '2026-06-14', 'mediana_tempo_obra', 'meses'),
 ('janela_compra_equipamento_meses', 4, 'fallback_3_6m_antes_entrega', '2026-06-14', 'lead_time_compra', 'meses')
on conflict (nome) do nothing;