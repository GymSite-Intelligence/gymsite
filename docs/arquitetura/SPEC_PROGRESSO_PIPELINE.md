# Spec — Progresso do Pipeline na UI (12/06/2026)

> Pedido: tela "Gerando relatório" com barra de progresso por etapa e copy
> que informe as FONTES (P-001) — a versão antiga anunciava "Deep Research"
> que desde 12/06 está bloqueado (modo bundle estrito).

## Fase 1 — entregue neste commit (polling, sem SSE)

**Backend**
- `relatorios.etapa_atual` (TEXT) + `relatorios.etapas_concluidas` (JSONB
  `[{agente, fim, duracao_s}]`) — migration `relatorios_progresso_pipeline`.
- `tools/pipeline_progress.py`: callbacks before/after agent plugados no
  `_attach_telemetry` (ponto único do agent.py). Fail-safe absoluto.
- `GET /api/relatorios/{id}/status` expõe os 2 campos novos.

**Frontend (`RelatorioAguardandoPage`)**
- Stepper dinâmico: ✅ concluída (com duração real) · ⏳ ativa · ○ pendente.
- Barra ponderada por duração média da fase (A0 5 · A1 15 · paralelo 45 ·
  A5 10 · A6 15 · A9 10), teto 99% até o done.
- Copy por fonte: "Contexto de mercado — IBGE · Receita Federal (CNPJ/CNO)
  · portais de aluguel", etc. Zero codinome de agente na tela.

## Fase 2 — fila da semana (SSE vivo)

- `GET /api/relatorios/{id}/events` (SSE): worker publica eventos por agente
  via Redis pub/sub; front troca polling por EventSource.
- Micro-narrativa com números reais no meio da etapa ("7 concorrentes
  mapeados…", "16 anúncios validados…") — a espera vira demonstração.
- Mesmo canal serve o futuro dashboard de monitoramento contínuo (GTM
  Intelligence, eBook Vetor 6).

## Registro de incidente correlato (12/06)

Três runs seguidos morreram com 429 atribuído ao "Vertex": a causa real era
`gymsite_intelligence/gymsite_intelligence/.env` (env do PACOTE do agente,
que o ADK carrega sozinho) com `GOOGLE_API_KEY` + `USE_VERTEXAI=false` de
um modo dev antigo — sequestrava o pipeline pro free-tier do AI Studio
(~25-50 req/dia no 2.5 Pro). Corrigido: key comentada, vertex=true,
location=global. Lição: env de pacote sobrepõe env raiz no ADK — auditar
os dois ao mudar rota de modelo.
