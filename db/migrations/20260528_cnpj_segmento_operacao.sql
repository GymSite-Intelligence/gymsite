-- Segmento operacional do parque ativo (academia, estúdio, box, etc.)

alter table cnpj_fitness_estabelecimentos
  add column if not exists segmento_operacao text;

create index if not exists idx_cnpj_fitness_segmento
  on cnpj_fitness_estabelecimentos(segmento_operacao);

comment on column cnpj_fitness_estabelecimentos.segmento_operacao is
  'Segmento inferido: academia | crossfit_box | studio_pilates | studio_funcional | outro';
