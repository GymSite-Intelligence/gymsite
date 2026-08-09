# Design — RAG dados determinísticos + LLM só leitura

**Data:** 2026-08-04  
**Âmbito:** `agents_site/tools.py` (+ facades Discovery) e contrato com A0–A9 / chat especialistas  
**Humano:** Marcelo  

---

## Problema

Hoje misturam-se três coisas no mesmo arquivo e nos prompts:

1. **Números vivos** (Maps, IBGE, CNPJ, MRLR, fórmulas) — já determinísticos.
2. **Texto qualitativo** (normas, catálogos, metodologia) — Eros-first, ainda com fallback Vertex Discovery (`VERTEX_RAG_ENABLED`).
3. **LLM** — às vezes “inventa” quando RAG vazio / Vertex dunning / tool str.

Vertex Discovery = legado billing; números sem carimbo = doença Cocó; LLM narrando fora da tool = mentira.

## Objetivo

Arquitetura em **3 camadas**:

| Camada | Papel | Quem escreve número/fato |
|--------|--------|---------------------------|
| **L1 Dados** | Tools determinísticas (Maps, IBGE, CNPJ, MRLR, fórmulas) | Código / banco / API — **nunca** LLM |
| **L2 Corpus** | Recuperação de trechos curados (Eros ou corpus local versionado) | Índice/arquivo com **carimbo** no doc |
| **L3 Leitura** | LLM só resume/cita o que L1+L2 devolveram | Prosa — se L1/L2 vazio → “base não cobre” |

Nome de produto: **RAG de dados determinísticos** = L1+L2; LLM = leitor, não fonte.

## Fora de escopo

- Trocar SearchAPI/MRLR/IBGE (já canônicos).
- DistilBERT/NLP barato (handoff 2026-08-02).
- Redesign UI crachá (`agentes.ts`) — paralelo UI DNA.
- Ingest manual Eros Técnico (ops) — listado como dependência, não como código neste plano.

## Approaches

| | Abordagem | Prós | Contras |
|---|-----------|------|---------|
| A | Só matar Vertex + manter Eros | Rápido | Corpus Eros ainda sem carimbo obrigatório; tools.py monólito |
| B | **L1/L2/L3 + corpus local fallback + cortar imports Vertex das facades** | Offline-friendly; carimbo; teste sem Eros | Mais trabalho de retrieve local |
| C | Reescrever tudo em BM25 local, abandonar Eros | Controle total | Perde retrieval semântico já pago; duplica ops |

**Recomendação: B.** Eros continua L2 primário; corpus `docs/agente/agentes_site/rag/*.txt` = fallback determinístico (grep/BM25/chunks); Vertex some do caminho quente; LLM prompts reforçam “só leitura”.

## Contrato tool (L1 e L2)

Todo retorno público:

```text
status: ok | vazio | erro | indisponivel
fonte: string estável (nunca "Vertex…" em prod)
n_docs / total / ... conforme tipo
carimbo opcional em cada número: { valor, base, fonte, janela }
aviso_usuario: só se status ≠ ok (PT-BR, sem billing GCP)
```

L2 chunks: `{ titulo, trecho, uri?, fonte, janela? }` — LLM cita `fonte`, não inventa.

## Inventário `agents_site/tools.py` (estado 2026-08-04)

### L1 — determinístico (manter; endurecer carimbo/coerce)

| Tool | Backend |
|------|---------|
| `buscar_concorrentes` | SearchAPI/Maps |
| `analisar_demografia` | IBGE |
| `pesquisar_contexto_mercado` | market_bundle + CNPJ + OSM |
| `buscar_pontos_comerciais` | anchoring + MRLR |
| `estimar_investimento` | A4 / MRLR |
| `dimensionar_cardio_por_pico` | fórmula |
| `dimensionar_musculacao` | fórmula |
| `calcular_equipamentos_por_area` | fórmula + footprint |
| `calcular_sanitarios_por_lotacao` | fórmula (estimativa) |
| `gerar_planta_layout_zonas` | layout engine |
| `analisar_reviews_e_dores` | fetch det. + refine categoria (opcional LLM) |

### L2 — RAG qualitativo (sair Vertex de vez)

| Tool | Primário | Fallback hoje | Alvo |
|------|----------|---------------|------|
| `consultar_base_mercado` | Eros MERCADO | Discovery stub | Eros → corpus local mercado |
| `consultar_base_regulatoria` | Eros REGULATORIO | Discovery | Eros → `rag/regulatorio_*.txt` |
| `consultar_engenharia_obra` | Eros ENGENHARIA | Discovery | Eros → `rag/engenharia_*.txt` |
| `consultar_catalogo_equipamentos` | Eros TECNICO (vazio) | Discovery stub | Eros TECNICO → stub honesto / corpus técnico |
| `consultar_eros_*` | Edge `knowledge-ask` | — | intacto + Arquiteto→Engenharia |

### Pipeline A0–A9

Não usa `agents_site/tools.py` RAG diretamente; usa `tools/*` + LLM via `PIPELINE_LLM_PROVIDER`.  
Mesmo **princípio L1/L3**: números = tool; A6/A9 narram. Plano referencia coerção `dias` (já feita) e prompts “só leitura”.

## Aceite

1. `VERTEX_RAG_ENABLED` default off; facades **não importam** Discovery no caminho feliz (nem quando Eros falha — só stub ou corpus local).
2. Toda tool L1 de número devolve carimbo ou campos base/fonte/janela já existentes.
3. Chat: Reg/Eng/Mercado com `fonte` Eros ou corpus local; Técnico sem 403 Vertex.
4. Doc `SPEC_RAG_AGENTES_SITE.md` atualizado: engines Vertex → grupos Eros + corpus.
5. Testes: facades Eros-first; corpus local sem rede; coerce args LLM-str.

## Relação com handoff

Estende `docs/handoffs/2026-08-04-vertex-off-eros-rag-parallel.md` Trilha A: não só “Eros-first”, mas **projeto L1/L2/L3** + corte limpo Vertex + fallback local.
