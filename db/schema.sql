-- ============================================================================
-- GymSite Intelligence — Schema v1.0 (Fase 2 CRUD)
-- Multi-tenant baseado no JSON canônico v1.1 do pipeline ADK
--
-- Aplicar via: supabase MCP `apply_migration` OU
--              `psql $DATABASE_URL -f schema.sql`
--
-- Convenções:
-- - Toda tabela tem `org_id` (multi-tenant)
-- - Toda tabela com user-data tem RLS habilitado
-- - Service role bypassa RLS (usado pelo pipeline ADK pra gravar)
-- - Frontend usa anon key + Supabase Auth pra acesso filtrado por org
-- ============================================================================

-- Extensões necessárias
create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;
create extension if not exists vector;  -- pgvector pra RAG futuro (busca semântica)


-- ============================================================================
-- 1. ORGANIZATIONS (tenants)
-- ============================================================================
create table organizations (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  slug text unique not null,
  plano text not null default 'free' check (plano in ('free','pro','enterprise')),
  limite_relatorios_mes integer not null default 5,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table organizations is 'Tenants do sistema. Cada cliente externo (academia, holding) é uma organization.';


-- ============================================================================
-- 2. ORGANIZATION_MEMBERS (link N:N entre auth.users e organizations)
-- ============================================================================
create table organization_members (
  org_id uuid not null references organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner','admin','member','viewer')),
  created_at timestamptz default now(),
  primary key (org_id, user_id)
);

comment on table organization_members is 'Vínculo de usuários a organizações. Um user pode estar em N orgs.';


-- ============================================================================
-- 3. RELATORIOS (header)
-- ============================================================================
create type relatorio_status as enum ('queued','running','done','failed','cancelled');
create type relatorio_tipo as enum (
  'prospeccao_academia',
  'prospeccao_crossfit',
  'prospeccao_studio'
);
create type negocio_tipo as enum (
  'academia',          -- 1000-1500m², modelo tradicional
  'crossfit_box',      -- 300-600m², ticket alto
  'studio_pilates',    -- 150-300m², ticket premium
  'studio_funcional',  -- 200-400m², ticket médio-alto
  'outro'
);

create table relatorios (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,

  tipo_relatorio relatorio_tipo not null default 'prospeccao_academia',
  status relatorio_status not null default 'queued',

  -- Telemetria do pipeline ADK
  adk_run_id text,
  tempo_execucao_segundos integer,
  tokens_total bigint,
  custo_brl numeric(10,2),

  -- Datas
  data_execucao timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  -- Versionamento do schema do pipeline
  schema_version text not null default '1.1',

  -- Markdown completo (renderizado, pra preview rápido)
  markdown_completo text,

  -- Caso failed
  erro_mensagem text,

  -- Notas livres do usuário
  notas_usuario text
);

create index idx_relatorios_org on relatorios(org_id);
create index idx_relatorios_user on relatorios(user_id);
create index idx_relatorios_status on relatorios(status);
create index idx_relatorios_data on relatorios(data_execucao desc nulls last);

comment on table relatorios is 'Header de cada relatório gerado. Demais tabelas penduram dados via relatorio_id.';


-- ============================================================================
-- 4. RELATORIO_INPUTS (formulário CRUD que o usuário preenche)
-- ============================================================================
create table relatorio_inputs (
  relatorio_id uuid primary key references relatorios(id) on delete cascade,

  cidade text not null,
  uf char(2),
  bairro text not null,

  area_m2_min integer not null check (area_m2_min between 50 and 10000),
  area_m2_max integer not null check (area_m2_max between 50 and 10000),
  check (area_m2_max >= area_m2_min),
  -- Schema v1.5: preset Smart Fit-style (pp|p|m|g|gg). Calibra benchmarks
  -- de CAPEX/custos no A4 e contextualiza posicionamento no A6.
  -- text não-constrained pra evolução sem migration.
  tamanho_preset text default 'm',

  publico_alvo text not null default '25-40',  -- "18-25" | "25-40" | "40-60" | "60+"
  -- Schema v1.4: gênero alvo calibra ticket/mix no A4 e posicionamento no A6.
  -- Valores enum-like (sem CHECK constraint pra permitir evolução sem migration).
  genero_alvo text not null default 'misto',
  tipo_negocio negocio_tipo not null default 'academia',

  estacionamento_obrigatorio boolean default true,

  -- Modo crowdsource: bairros indicados pela comunidade têm prioridade
  bairros_indicados jsonb default '[]'::jsonb,

  -- Campos extensíveis sem alterar schema
  metadados jsonb default '{}'::jsonb
);

comment on table relatorio_inputs is 'Inputs do formulário CRUD. 1:1 com relatorios.';


-- ============================================================================
-- 5. RELATORIO_OUTPUTS (saída consolidada, 1:1 com relatorios)
-- ============================================================================
create table relatorio_outputs (
  relatorio_id uuid primary key references relatorios(id) on delete cascade,

  veredito text not null,  -- APROVADO | APROVADO COM RESSALVAS | INVESTIGAR MAIS | REPROVADO

  -- Scores schema v1.1 (2 campos distintos)
  score_bairro numeric(4,2),
  score_top1_candidato numeric(4,2),

  -- Dimensões regionais
  score_demografico numeric(4,2),
  score_concorrencia numeric(4,2),
  score_viabilidade numeric(4,2),

  -- Métricas competitivas
  nivel_saturacao text,
  rating_medio_concorrentes numeric(3,2),
  total_concorrentes_analisados integer,

  -- Recomendação financeira
  modelo_recomendado text,
  aluguel_mensal numeric(12,2),
  fonte_aluguel text,  -- "Search Grounding (mediana de N queries)" | "Benchmark ACAD"
  aluguel_min_m2 numeric(8,2),
  aluguel_max_m2 numeric(8,2),
  aluguel_mediana_m2 numeric(8,2),
  queries_aluguel_com_dados integer default 0,

  -- Textos longos
  posicionamento_recomendado text,
  resumo_executivo text,
  justificativa_financeira text,

  -- Contato/script (do A5)
  contato_decisor jsonb,

  -- Contexto de mercado (do A0 Deep Research)
  market_context jsonb,

  -- Novos entrantes CNPJ fitness — schema v1.7 (lista 90d)
  entrantes_cnpj_90d jsonb not null default '{}'::jsonb,

  -- Obras fitness em andamento no município (CNO) — schema v1.10
  obras_cno_em_curso jsonb not null default '{}'::jsonb,

  -- Cobertura A0 (schema v1.4) — confronta redes solicitadas pelo DR vs
  -- validadas pela busca georreferenciada. Inclui redes_solicitadas,
  -- redes_cobertas, redes_nao_encontradas, tem_redes_fantasma.
  cobertura_redes_a0 jsonb default '{}'::jsonb,

  -- Alertas globais (lista de strings)
  alertas jsonb default '[]'::jsonb,

  -- Embedding pra similarity search (RAG futuro)
  embedding vector(1536)
);

create index idx_outputs_veredito on relatorio_outputs(veredito);
create index idx_outputs_score_top1 on relatorio_outputs(score_top1_candidato desc);

comment on table relatorio_outputs is 'Saída consolidada do relatório (scores, veredito, recomendações).';

-- ============================================================================
-- 10. CNPJ FITNESS (RFB) — SNAPSHOTS MENSAIS (CNAE 9313100)
-- ============================================================================
-- Nota: não é multi-tenant (dado público). Pode ser usado por todos os tenants.
create table if not exists cnpj_fitness_estabelecimentos (
  id uuid primary key default gen_random_uuid(),
  ref_month date not null,
  cnpj text not null,
  municipio_codigo text,
  uf text,
  cidade text,
  cnae_fiscal_principal text,
  cnaes_secundarios text,
  data_inicio_atividade date,
  situacao_cadastral integer,
  data_situacao_cadastral date,
  nome_fantasia text,
  cep text,
  logradouro text,
  numero text,
  complemento text,
  segmento_operacao text,
  created_at timestamptz not null default now()
);

create unique index if not exists uq_cnpj_fitness_ref_cnpj
  on cnpj_fitness_estabelecimentos(ref_month, cnpj);

create index if not exists idx_cnpj_fitness_ref_month
  on cnpj_fitness_estabelecimentos(ref_month);

create index if not exists idx_cnpj_fitness_municipio
  on cnpj_fitness_estabelecimentos(municipio_codigo);

create index if not exists idx_cnpj_fitness_data_inicio
  on cnpj_fitness_estabelecimentos(data_inicio_atividade);


-- ============================================================================
-- 6. CANDIDATOS (Top 3 imóveis, N:1 com relatorios)
-- ============================================================================
create table candidatos (
  id uuid primary key default gen_random_uuid(),
  relatorio_id uuid not null references relatorios(id) on delete cascade,

  posicao smallint not null check (posicao between 1 and 10),
  nome text not null,
  endereco text,
  place_id text,
  tipo text,

  area_estimada_m2 integer,
  lat numeric(10,6),
  lng numeric(10,6),

  score_geoscout numeric(4,2),
  score_ancoragem numeric(4,2),
  score_geral numeric(4,2),

  motivo text,
  estimativa_visibilidade text,
  avenida_principal boolean,
  qualidade_sinal text,

  polos_geradores jsonb default '[]'::jsonb,
  tipos_google jsonb default '[]'::jsonb,

  street_view_url text,
  status_business text,

  -- Contact Data (Places API New). Antes ausente — agora propagado pelo
  -- A1 GeoScout com FieldMask atualizado em maps_tools.py.
  telefone text,
  website text,
  tem_24h boolean default false,

  -- Listing imobiliário (OLX / ImovelWeb) — qualidade_sinal = direto-listing
  listing_url text,
  listing_id text,
  price_raw text,
  listing_source text,

  proximo_passo text,
  created_at timestamptz default now(),

  unique(relatorio_id, posicao)
);

create index idx_candidatos_relatorio on candidatos(relatorio_id, posicao);

comment on table candidatos is 'Imóveis candidatos (Top 3) identificados pelo A1 GeoScout.';


-- ============================================================================
-- 7. COMPETIDORES (concorrentes mapeados, N:1)
-- ============================================================================
create table competidores (
  id uuid primary key default gen_random_uuid(),
  relatorio_id uuid not null references relatorios(id) on delete cascade,

  nome text not null,
  endereco text,
  bairro_concorrente text,
  place_id text,

  rating_oficial numeric(3,2),
  num_avaliacoes integer,
  tem_24h boolean default false,

  -- Reviews enriquecidas com taxonomia semântica (Task #46)
  -- Estrutura de cada review: {rating, quote_curta, autor, data_relativa,
  --   categoria_dor (DORES_TAXONOMIA), sinal (positivo|neutro|negativo),
  --   confianca_classificacao (alta|media|baixa)}
  reviews jsonb default '[]'::jsonb,

  -- Enrichment Google Knowledge Panel
  horarios_pico jsonb,
  pico_semanal text,
  atividade_marketing jsonb,

  origem_busca text default 'nearby',  -- "nearby" | "expandida_a0"
  created_at timestamptz default now()
);

create index idx_competidores_relatorio on competidores(relatorio_id);
create index idx_competidores_bairro on competidores(bairro_concorrente);

comment on table competidores is 'Academias concorrentes do A3a + análise dores semântica.';


-- ============================================================================
-- 8. CENARIOS_FINANCEIROS (3 por relatório: low/mid/premium)
-- ============================================================================
create type cenario_modelo as enum ('low','mid','premium');
create type viabilidade_status as enum ('ALTO','MEDIO','BAIXO','INVIAVEL');

create table cenarios_financeiros (
  id uuid primary key default gen_random_uuid(),
  relatorio_id uuid not null references relatorios(id) on delete cascade,

  modelo cenario_modelo not null,
  ticket_medio numeric(8,2),

  -- ── Demanda (schema v2: 3 calibrações + pico simultâneo) ──
  matriculas_conservador integer,
  matriculas_realista integer,    -- usada como base do cálculo financeiro
  matriculas_agressivo integer,
  matr_por_m2_realista numeric(4,2),  -- pra auditoria
  capacidade_simultanea_pico integer,
  frequencia_semanal_aluno numeric(3,1),
  pico_share numeric(4,3) default 0.25,
  alunos_pico_calculado integer,
  folga_capacidade_pct numeric(5,2),

  -- ── Backward-compat v1 (preservado pra readers antigos) ──
  capacidade_maxima_alunos integer,
  alunos_projetados integer,
  alunos_break_even integer,

  -- ── Receita ──
  ticket_realizado_estimado numeric(8,2),
  taxa_inadimplencia numeric(4,3),     -- 0.060 = 6%
  taxa_cancelamento_mensal numeric(4,3),
  receita_mensal numeric(12,2),

  -- ── Custos detalhados (12 linhas v2) ──
  custo_aluguel numeric(12,2),
  custo_condominio numeric(12,2),
  custo_iptu numeric(10,2),
  custo_energia numeric(10,2),
  custo_agua numeric(10,2),
  custo_internet numeric(8,2),
  custo_folha numeric(12,2),
  custo_manutencao numeric(10,2),
  custo_contabilidade numeric(8,2),
  custo_sistema_gestao numeric(8,2),
  custo_seguro numeric(10,2),
  custo_outros numeric(10,2),
  custos_fixos_total numeric(12,2),

  -- ── Marketing ──
  marketing_pct_faturamento numeric(4,3),
  marketing_mensal numeric(12,2),

  -- ── Resultado ──
  custos_totais numeric(12,2),
  lucro_mensal_estimado numeric(12,2),
  margem_percentual numeric(5,2),

  -- ── Investimento detalhado ──
  capex_equipamentos numeric(14,2),
  capex_obra_adaptacao numeric(14,2),
  capex_projeto_arquitetonico numeric(10,2),
  capex_alvara_e_taxas numeric(10,2),
  capex_contingencia_pct numeric(4,3),
  capex_contingencia_valor numeric(12,2),
  capex_total numeric(14,2),

  capital_giro_meses smallint default 3,
  capital_giro numeric(12,2),
  investimento_total numeric(14,2),
  payback_meses integer,
  tir_anual_pct numeric(5,2),
  vpl_5_anos numeric(14,2),

  -- ── Veredito ──
  viabilidade viabilidade_status,
  justificativa text,

  -- Backward-compat
  capex_estimado numeric(14,2),
  custos_fixos numeric(12,2),

  unique(relatorio_id, modelo)
);

create index idx_cenarios_relatorio on cenarios_financeiros(relatorio_id);
create index idx_cenarios_viabilidade on cenarios_financeiros(viabilidade);

comment on table cenarios_financeiros is 'Cenários low/mid/premium do A4 FinancialEstimator schema v2 (3 rows por relatório). Inclui matrículas em 3 calibrações + pico simultâneo + 12 linhas de custos + CAPEX detalhado + TIR/VPL.';


-- ============================================================================
-- 8a. SENSIBILIDADE_CENARIOS — stress tests (schema v2, 3 rows por cenário)
-- ============================================================================
create type sensibilidade_stress as enum (
  'aluguel_mais_20pct',
  'matriculas_menos_30pct',
  'ticket_menos_15pct'
);

create table sensibilidade_cenarios (
  id uuid primary key default gen_random_uuid(),
  cenario_id uuid not null references cenarios_financeiros(id) on delete cascade,
  relatorio_id uuid not null references relatorios(id) on delete cascade,
  modelo cenario_modelo not null,

  stress_id sensibilidade_stress not null,
  stress_label text not null,
  lucro_mensal numeric(12,2),
  margem_percentual numeric(5,2),
  payback_meses integer,
  viabilidade viabilidade_status,

  unique(cenario_id, stress_id)
);

create index idx_sensibilidade_cenario on sensibilidade_cenarios(cenario_id);
create index idx_sensibilidade_relatorio on sensibilidade_cenarios(relatorio_id);

comment on table sensibilidade_cenarios is 'Stress tests por cenário (3 rows: aluguel +20%, matrículas -30%, ticket -15%). Schema v2.';


-- ============================================================================
-- 9. BAIRROS_ALTERNATIVOS (recomendação A6 quando score baixo)
-- ============================================================================
create table bairros_alternativos (
  id uuid primary key default gen_random_uuid(),
  relatorio_id uuid not null references relatorios(id) on delete cascade,

  bairro text not null,
  motivo text,
  status_competitivo text,  -- "🔴 muito saturado" | "🟡 1 concorrente" | "🟢 sem concorrentes"
  ticket_sugerido text,
  prioridade text check (prioridade in ('ALTA','MEDIA','BAIXA')),

  concorrentes_no_bairro integer,
  academias_existentes jsonb default '[]'::jsonb,

  metodologia text,
  ordem smallint default 0
);

create index idx_bairros_alt_relatorio on bairros_alternativos(relatorio_id, ordem);

comment on table bairros_alternativos is 'Bairros alternativos sugeridos pelo A6 com prioridade ajustada.';


-- ============================================================================
-- TRIGGERS pra `updated_at`
-- ============================================================================
create or replace function _update_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_organizations_updated_at before update on organizations
  for each row execute function _update_updated_at();
create trigger trg_relatorios_updated_at before update on relatorios
  for each row execute function _update_updated_at();


-- ============================================================================
-- HELPER: org_ids do usuário corrente (usado em policies)
-- ============================================================================
create or replace function user_org_ids() returns setof uuid
language sql stable security definer set search_path = public as $$
  select org_id from organization_members where user_id = auth.uid();
$$;


-- ============================================================================
-- RLS (Row Level Security) — multi-tenant isolation
-- ============================================================================
alter table organizations enable row level security;
alter table organization_members enable row level security;
alter table relatorios enable row level security;
alter table relatorio_inputs enable row level security;
alter table relatorio_outputs enable row level security;
alter table candidatos enable row level security;
alter table competidores enable row level security;
alter table cenarios_financeiros enable row level security;
alter table sensibilidade_cenarios enable row level security;
alter table bairros_alternativos enable row level security;

-- Service role bypassa tudo (pipeline grava com service key)
-- Policies abaixo são pro frontend (anon + auth.uid())

-- Organizations: ver as suas
create policy "view own orgs" on organizations
  for select using (id in (select user_org_ids()));

create policy "owners can update orgs" on organizations
  for update using (id in (
    select org_id from organization_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Members: ver os da sua org
create policy "view own org members" on organization_members
  for select using (org_id in (select user_org_ids()));

create policy "owners manage members" on organization_members
  for all using (org_id in (
    select org_id from organization_members
    where user_id = auth.uid() and role in ('owner','admin')
  ));

-- Relatorios: CRUD na própria org
create policy "relatorios CRUD on own org" on relatorios
  for all using (org_id in (select user_org_ids()));

-- Tabelas relacionadas: herdam acesso do relatorio
create policy "inputs follow relatorio" on relatorio_inputs
  for all using (relatorio_id in (
    select id from relatorios where org_id in (select user_org_ids())
  ));

create policy "outputs follow relatorio" on relatorio_outputs
  for all using (relatorio_id in (
    select id from relatorios where org_id in (select user_org_ids())
  ));

create policy "candidatos follow relatorio" on candidatos
  for all using (relatorio_id in (
    select id from relatorios where org_id in (select user_org_ids())
  ));

create policy "competidores follow relatorio" on competidores
  for all using (relatorio_id in (
    select id from relatorios where org_id in (select user_org_ids())
  ));

create policy "cenarios follow relatorio" on cenarios_financeiros
  for all using (relatorio_id in (
    select id from relatorios where org_id in (select user_org_ids())
  ));

create policy "sensibilidade follow relatorio" on sensibilidade_cenarios
  for all using (relatorio_id in (
    select id from relatorios where org_id in (select user_org_ids())
  ));

create policy "bairros_alt follow relatorio" on bairros_alternativos
  for all using (relatorio_id in (
    select id from relatorios where org_id in (select user_org_ids())
  ));


-- ============================================================================
-- VIEWS úteis pro frontend
-- ============================================================================

-- Listagem com header + dados-chave (pra tela de "Meus relatórios")
create or replace view v_relatorios_resumo as
select
  r.id,
  r.org_id,
  r.user_id,
  r.tipo_relatorio,
  r.status,
  r.data_execucao,
  r.tempo_execucao_segundos,
  r.custo_brl,
  i.cidade,
  i.uf,
  i.bairro,
  i.area_m2_min,
  i.area_m2_max,
  i.publico_alvo,
  i.tipo_negocio,
  o.veredito,
  o.score_bairro,
  o.score_top1_candidato,
  o.modelo_recomendado,
  o.aluguel_mediana_m2,
  o.nivel_saturacao,
  r.created_at
from relatorios r
left join relatorio_inputs i on i.relatorio_id = r.id
left join relatorio_outputs o on o.relatorio_id = r.id;

comment on view v_relatorios_resumo is 'View flat para listagem na tela "Meus relatórios".';


-- Comparativo entre bairros da mesma cidade (analytics futuro)
create or replace view v_bairros_aggregate as
select
  i.cidade,
  i.uf,
  i.bairro,
  count(*) as total_relatorios,
  avg(o.score_bairro) as score_bairro_medio,
  avg(o.score_top1_candidato) as score_top1_medio,
  avg(o.aluguel_mediana_m2) as aluguel_mediana_m2_medio,
  mode() within group (order by o.veredito) as veredito_mais_comum,
  max(r.data_execucao) as ultima_execucao
from relatorios r
join relatorio_inputs i on i.relatorio_id = r.id
left join relatorio_outputs o on o.relatorio_id = r.id
where r.status = 'done'
group by i.cidade, i.uf, i.bairro;

comment on view v_bairros_aggregate is 'Agregado por bairro pra dashboards comparativos futuros.';


-- ============================================================================
-- 15. OTIMIZACOES_CUSTO — Governança de propostas de otimização
-- ============================================================================
create type otimizacao_status as enum ('pendente', 'aprovada', 'rejeitada', 'implementada', 'cancelada');
create type otimizacao_tipo as enum ('MODELO_OVERPRICED', 'FLASH_PARA_LITE', 'AGENTE_VORAZ', 'ERRO_REPETIDO', 'CACHE_GEOCODING', 'OUTRO');

create table otimizacoes_custo (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,

  -- Quem criou a proposta (sistema ou usuário)
  criado_por uuid references auth.users(id) on delete set null,
  criado_em timestamptz default now(),

  -- Identificação da proposta
  tipo otimizacao_tipo not null,
  agente text not null,
  modelo_atual text,
  modelo_sugerido text,
  titulo text not null,
  descricao text not null,
  economia_brl_estimada numeric(10,4) not null default 0,
  severidade text not null check (severidade in ('alta', 'media', 'baixa')),

  -- Status do workflow
  status otimizacao_status not null default 'pendente',

  -- Aprovação
  aprovado_por uuid references auth.users(id) on delete set null,
  aprovado_em timestamptz,
  justificativa_aprovacao text,

  -- Implementação
  implementado_por uuid references auth.users(id) on delete set null,
  implementado_em timestamptz,
  resultado_observacao text,
  economia_brl_real numeric(10,4),

  -- Metadata
  referencia_dados jsonb  -- snapshot dos dados que geraram a proposta
);

create index idx_otimizacoes_org on otimizacoes_custo(org_id);
create index idx_otimizacoes_status on otimizacoes_custo(status);
create index idx_otimizacoes_agente on otimizacoes_custo(agente);
create index idx_otimizacoes_severidade on otimizacoes_custo(severidade);

comment on table otimizacoes_custo is 'Propostas de otimização de custo do pipeline. Workflow: pendente → aprovada → implementada (ou rejeitada/cancelada).';

-- RLS
alter table otimizacoes_custo enable row level security;

create policy "otimizacoes follow org" on otimizacoes_custo
  for all
  to authenticated
  using (org_id in (select org_id from organization_members where user_id = auth.uid()))
  with check (org_id in (select org_id from organization_members where user_id = auth.uid()));

-- Função: gerar propostas automaticamente a partir do endpoint /api/custos/optimizations
-- O backend usa service_role key para inserir; o frontend usa anon key + RLS.
