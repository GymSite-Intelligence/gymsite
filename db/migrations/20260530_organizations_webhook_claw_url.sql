-- Webhook URL do Claw/OpenClaw por organização (módulo de prospecção)
alter table organizations
  add column if not exists webhook_claw_url text;

comment on column organizations.webhook_claw_url is
  'URL inbound do Claw para oportunidades qualificadas (POST /api/prospeccao/webhook/configure).';
