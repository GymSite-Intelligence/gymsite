# Handoff — GymSite + OpenClaw Integration

> **De:** Vectra Clip (Kimi/OpenClaw) · **Para:** Marcelo / próximo agente  
> **Atualizado:** 2026-05-31 (repo GymSite)  
> **Contexto:** A0 Deep Research via OpenClaw/Kimi · A8 validação cruzada pós-A6

> **Segurança:** versões antigas deste handoff continham `KIMI_API_KEY` e tokens em texto claro.  
> **Rotacione** a chave Moonshot e o `OPENCLAW_TOKEN` no vault; nunca commitar no git.

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
| OpenClaw server | ✅ | `openclaw_kimi_server.py` na **raiz** do repo (não em `frontend/`) |
| `tools/a0_kimi_adapter.py` (stub legado) | ⚠️ | Não copiar — usar `tools/kimi_research.py` |

### O que o handoff Vectra Clip descreve vs este repo

| Entrega handoff | Implementação atual |
|-----------------|---------------------|
| `gymsite_a0_kimi_adapter.py` | **`tools/kimi_research.py`** (HTTP OpenClaw + fallback Gemini) |
| `gymsite_a8_validator.py` | **`agents/a8_validator.py`** + `tools/a8_runner.py` |
| `openclaw_kimi_server.py` | Fora do repo — subir na máquina OpenClaw (porta **8001**) |
| Guia integração | `docs/INTEGRATION_KIMI.md` + este arquivo |

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

### GymSite API (`.env` na raiz; container lê via `docker-compose`)

```env
A0_RESEARCH_PROVIDER=kimi
# Se OpenClaw roda no host Windows/Mac e API no Docker:
OPENCLAW_URL=http://host.docker.internal:8001
# Se exposto na rede com TLS:
# OPENCLAW_URL=https://openclaw.vectracargo.com.br:8001
OPENCLAW_TOKEN=<mesmo-token-do-servidor>
OPENCLAW_KIMI_SEARCH_PATH=/v1/kimi/search
KIMI_RESEARCH_TIMEOUT_SEC=90
KIMI_RESEARCH_FALLBACK=gemini
A8_VALIDATOR_ENABLED=1
A8_USE_KIMI=1
```

Após alterar: `docker compose up -d api` e `curl http://localhost:8000/api/canais/status` → `openclaw_configured: true`.

### OpenClaw Kimi Server (máquina OpenClaw, porta 8001)

**Dev local com Ollama** (sem Moonshot; sem busca web):

```env
KIMI_BACKEND=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
OPENCLAW_TOKEN=<mesmo-token-gymsite>
PORT=8001
KIMI_TIMEOUT_SEC=120
```

**Produção / pesquisa com web** (Moonshot):

```env
KIMI_BACKEND=moonshot
KIMI_API_KEY=<moonshot-no-vault>
OPENCLAW_TOKEN=<mesmo-token-gymsite>
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=kimi-latest
PORT=8001
```

```bash
pip install fastapi uvicorn httpx python-dotenv
uvicorn openclaw_kimi_server:app --host 0.0.0.0 --port 8001
```

Teste:

```bash
curl -X POST http://localhost:8001/v1/kimi/search \
  -H "Authorization: Bearer <OPENCLAW_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query": "demografia bairro Meireles Fortaleza", "source": "gymsite_a0"}'
```

> **Nunca commitar** `KIMI_API_KEY` nem tokens neste repositório.

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
