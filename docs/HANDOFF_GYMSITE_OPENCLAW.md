# Handoff — GymSite + OpenClaw Integration

> **Atualizado:** 2026-05-29 (repo GymSite)
> **Contexto:** A = Kimi/OpenClaw (A0) · B = A8 Validador Cruzado

---

## Status no repositório GymSite

| Entrega handoff | Status | Onde |
|-----------------|--------|------|
| A0 Kimi (5 pesquisas) | ✅ | `tools/kimi_research.py` |
| Delegação A0 gemini↔kimi | ✅ | `tools/research_provider.py` + form `a0_research_provider` |
| Botões Run now | ✅ | `POST /api/canais/*` + `CanalRunPanel` |
| A8 Validador | ✅ | `agents/a8_validator.py` + `tools/a8_runner.py` |
| Hook pós-A6 | ✅ | `_a6_after_agent_callback` |
| Tabela `validacoes` | ✅ migration `20260529_validacoes.sql` |
| `gymsite_a0_kimi_adapter.py` (stub) | ⚠️ legado | usar `kimi_research.py` |
| OpenClaw server | 🔲 | `openclaw_kimi_server.py` (lado Marcelo) |

---

## Contrato HTTP (confirmado)

```
POST {OPENCLAW_URL}/v1/kimi/search
Authorization: Bearer <OPENCLAW_TOKEN>
Content-Type: application/json

{ "query": "...", "source": "gymsite_a0" }

→ 200 { "result": "markdown..." }
```

GymSite envia **5 requests paralelos** por briefing A0.

---

## Configuração (.env) — sem segredos

### GymSite API

```env
A0_RESEARCH_PROVIDER=kimi
OPENCLAW_URL=https://seu-host:8001
OPENCLAW_TOKEN=<definir-no-vault>
KIMI_RESEARCH_FALLBACK=gemini
A8_VALIDATOR_ENABLED=1
A8_USE_KIMI=1
```

### OpenClaw Kimi Server

```env
KIMI_API_KEY=<moonshot-key-no-vault>
OPENCLAW_TOKEN=<mesmo-token-gymsite>
PORT=8001
```

> **Nunca commitar chaves reais** neste arquivo. Rotacione se vazaram em versões antigas do handoff.

---

## A/B no formulário

Em `/relatorios/new` → **Pesquisa de mercado (A0)**:

| Valor | Efeito |
|-------|--------|
| `auto` | Usa `A0_RESEARCH_PROVIDER` do `.env` |
| `gemini` | Deep Research Gemini |
| `kimi` | OpenClaw (`kimi_research`) |

CLI: `python tools/run_relatorio_cli.py --research kimi ...`

---

## A8 — o que valida

- APROVADO com 0 candidatos / 0 concorrentes
- Score vs veredito (`score_bairro`)
- Redes fantasma (`cobertura_redes_a0.tem_redes_fantasma`)
- Coerência payback / break-even / saturação
- Corroboração opcional via OpenClaw (`A8_USE_KIMI=1`)

Persistência: tabela `validacoes` + campo `validacao_a8` no JSON local `metrics/relatorios/<id>.json`.

---

## Próximos passos

1. Subir `openclaw_kimi_server` (porta 8001) e testar `curl`.
2. Configurar `.env` GymSite com `OPENCLAW_URL` + token.
3. Rodar 1 relatório `--research gemini` e 1 `--research kimi` (comparar qualidade/custo).
4. Revisar alertas A8 nas primeiras runs e calibrar severidades se necessário.
5. (Opcional) Exibir bloco A8 no viewer React.

---

## Testes locais

```bash
python tools/test_kimi_research.py
python tools/test_a8_validator.py
python tools/maps_health_check.py
curl http://localhost:8000/api/canais/status
```

---

*Handoff Vectra Clip + integração aplicada no repo gymsite_intelligence.*
