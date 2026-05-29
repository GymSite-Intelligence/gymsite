# Kimi Research + botões Run now

## Kimi no pipeline A0

1. No `.env`:
   ```env
   A0_RESEARCH_PROVIDER=kimi
   OPENCLAW_URL=https://seu-openclaw.exemplo.com
   OPENCLAW_TOKEN=...
   OPENCLAW_KIMI_SEARCH_PATH=/v1/kimi/search
   KIMI_RESEARCH_FALLBACK=gemini
   ```

2. `rodar_deep_research` delega automaticamente para `rodar_kimi_research`.
3. O A0 também expõe a tool `rodar_kimi_research` para refresh explícito.

Sem `OPENCLAW_URL`, com `KIMI_RESEARCH_FALLBACK=gemini`, cada query usa Gemini grounded.

## Botões Run now (formulário)

Em `/relatorios/new`, após escolher município + bairro:

| Botão | Endpoint | O que faz |
|-------|----------|-----------|
| Kimi Research | `POST /api/canais/kimi-research` | 5 pesquisas → cache markdown A0 |
| Google Places | `POST /api/canais/places` | `buscar_academias` (fluxo normal) |
| OSM / Overpass | `POST /api/canais/osm` | só Overpass no raio |
| CNPJ RFB | `POST /api/canais/cnpj` | parque fitness no bairro |

Diagnóstico: `GET /api/canais/status`

## A8 (validação pós-A6)

- `agents/a8_validator.py` — regras determinísticas + Kimi opcional
- Roda automaticamente após A6 (`A8_VALIDATOR_ENABLED=1`)
- Resultado em `validacoes` (Supabase) e `validacao_a8` no JSON do relatório
- API detail: `GET /api/relatorios/{id}` inclui `validacao_a8`

## A/B pesquisa A0

No form: **Pesquisa de mercado (A0)** → `gemini` | `kimi` | `auto`

## OpenClaw — contrato HTTP

`POST {OPENCLAW_URL}{OPENCLAW_KIMI_SEARCH_PATH}`

```json
{ "query": "...", "source": "gymsite_a0" }
```

Resposta:

```json
{ "result": "markdown ou texto..." }
```

Campos aceitos: `result`, `text`, `content`, `markdown`, `output`.
