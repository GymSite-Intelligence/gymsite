-- Espelho setor censitário → idade×sexo (Censo 2022, bloco Demografia v01009-v01030),
-- nacional (~450k setores). Populado offline por tools/censo_setor_idade_sexo_loader.py
-- (BQ basedosdados). O extrator perfil_sexo_idade_bairro agrega os setores do bairro
-- (centróide + acumula até a pop-alvo) → pirâmide REAL do bairro, sem o viés do rateio
-- %município (validado: Cocó rico subnotificava 60+ em -37%). Prod-safe (Cloud Run sem BQ).
create table if not exists censo_setor_idade_sexo (
  id_setor     text primary key,
  id_municipio text not null,
  lat          double precision,
  lng          double precision,
  pessoas      integer,
  h_total integer, m_total integer,
  h_15_24 integer, m_15_24 integer,   -- jovem
  h_25_39 integer, m_25_39 integer,   -- core fitness
  h_40_59 integer, m_40_59 integer,   -- maduro
  h_60_mais integer, m_60_mais integer,  -- silver
  updated_at timestamptz default now()
);
create index if not exists idx_csis_municipio on censo_setor_idade_sexo(id_municipio);
alter table censo_setor_idade_sexo enable row level security;  -- service-role only
