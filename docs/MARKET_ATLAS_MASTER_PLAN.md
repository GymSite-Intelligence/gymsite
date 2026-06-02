# Market Atlas — Plano mestre de construção

Documento único que integra: ondas vermelho → transição → azul, VM GCP, enrichment cache e frontend estratégico.

## Arquitetura alvo (fase 1)

- **VM GCE** (`southamerica-east1`): API + Redis + cloudflared + volumes (CNO, cache, Playwright)
- **Supabase**: Postgres + Auth + RLS (sem migração para Cloud SQL/Firestore nesta fase)
- **GCS** (opcional fase A): CNO, PDFs, exports Atlas
- **Gemini** (A0–A9): produção; local/fine-tune só após golden ≥30

## Duas lentes na UI

| Lente | Fonte | Pergunta |
|-------|--------|----------|
| Viabilidade do ponto | A6 `veredito` | Abro aqui? |
| Estratégia de mercado | A9 `veredito_posicionamento` | Low-cost ou premium? |

## Ondas de relatórios

Catálogo: [`data/market_waves.csv`](../data/market_waves.csv)

| Wave | Objetivo | Exemplos golden |
|------|----------|-----------------|
| `red` | Credibilidade em mercado saturado | Parangaba, Meireles, Aldeota, Batel |
| `transition` | Escape capital → RM | Eusébio ↔ Fortaleza |
| `blue` | Primeiro premium / interior | Anápolis, Altamira, Eusébio |

## Fases operacionais

1. **F0** — VM + Redis + `market_waves.csv` + migration view
2. **F1** — 8 relatórios vermelho (eval PASS)
3. **F2** — 4 pares transição
4. **F3** — 6 relatórios azul (cache enrichment antes)
5. **F4** — Market Atlas v1 publicável

## Frontend (este repo)

- `/market-atlas` — KPIs oceano + distribuição + tabela por wave
- Dashboard — faixa KPI oceano (A9)
- Viewer — `DualVereditoStrip` (A6 + A9)
- Listagem — coluna oceano quando view exposta

## Metodologia

- ERRC + 5 GAPs: `docs/metodologia/`
- A9 spec: `docs/metodologia/POSITIONING_FRAMEWORK.md`

## Próximo passo imediato

Migration view aplicada. Push do frontend Market Atlas → deploy automático no merge. Rodar ondas F1 no ambiente estável (VM/tunnel).
