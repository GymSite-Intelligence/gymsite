# GymSite + Kimi (OpenClaw) — Guia de Integração

> **Escopo:** Substituir o A0 Deep Research (Gemini → Kimi) e adicionar o A8 Validador Cruzado ao pipeline GymSite Intelligence.

---

## Arquitetura de Integração

```
┌─────────────────────────────────────────────────────────────────┐
│                     GYM SITE PIPELINE                          │
│                                                                  │
│  A0 ContextBuilder ──► A1 GeoScout ──► A2 DemoAnalyst         │
│       │                    │                   │                 │
│       ▼                    ▼                   ▼                 │
│  ┌──────────────┐   ┌──────────┐   ┌──────────────────────┐   │
│  │ Kimi Adapter │   │  Places  │   │    IBGE / BigQuery   │   │
│  │ (OpenClaw)   │   │  API     │   │    Censo 2022        │   │
│  └──────────────┘   └──────────┘   └──────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  A3a CompetitorSearch ──► A3b Analysis ──► A3c Mapper           │
│       │                    │                   │                 │
│       ▼                    ▼                   ▼                 │
│  A4 FinancialEstimator ──► A5 ContactHunter                    │
│       │                                                          │
│       ▼                                                          │
│  A6 ReportConsolidator ──► RELATÓRIO FINAL                      │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ A8 Validador Cruzado (OpenClaw)                          │   │
│  │ • Valida coerência interna                               │   │
│  │ • Verifica fontes externas                               │   │
│  │ • Emite alertas + flag "revisar_manual"                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Supabase Postgres                                        │   │
│  │ • relatorios + validacoes (nova tabela)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Parte 1 — A0 Kimi Adapter (Substitui Deep Research Gemini)

### O que muda

| Antes (Gemini) | Depois (Kimi) |
|----------------|---------------|
| `rodar_deep_research` via Interactions API | `executar_deep_research_kimi()` via OpenClaw |
| 1 chamada síncrona ao Gemini | 5 pesquisas paralelas via `kimi_search` |
| Fonte única (Gemini Search) | Múltiplas fontes independentes |
| Em inglês (prompt traduzido) | Nativo em português brasileiro |

### Arquivos a modificar

#### 1. Copiar `gymsite_a0_kimi_adapter.py` → `tools/a0_kimi_adapter.py`

#### 2. Modificar `agents/a0_context_builder.py`

```python
# ANTES (Gemini Interactions API)
from tools.deep_research_tool import rodar_deep_research

contexto = rodar_deep_research(cidade=cidade, bairro=bairro, tipo=tipo_negocio)
```

```python
# DEPOIS (Kimi via OpenClaw)
from tools.a0_kimi_adapter import A0KimiAdapter

adapter = A0KimiAdapter()
resultado = await adapter.executar(
    cidade=cidade,
    bairro=bairro,
    tipo_negocio=tipo_negocio,
    publico_alvo=publico_alvo,
)
# resultado é 100% compatível com schema do A0 original
contexto = resultado["contexto_mercado"]
insights = resultado["insights_deep_research"]
benchmarks = resultado["benchmarks_setor"]
```

### Opção A — Integração via HTTP (OpenClaw como serviço)

Se o OpenClaw estiver rodando em servidor próprio:

```python
# tools/a0_kimi_adapter.py — versão HTTP
import httpx

class A0KimiAdapter:
    OPENCLAW_URL = "https://seu-openclaw.com/v1/deep-research"
    
    async def _kimi_search(self, query: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.OPENCLAW_URL,
                json={"query": query, "source": "gymsite_a0"},
                headers={"Authorization": "Bearer OPENCLAW_TOKEN"},
                timeout=60.0,
            )
            return resp.json()["result"]
```

### Opção B — Integração via mensagem (WebSocket/polling)

Se o OpenClaw estiver conectado ao Kimi/Telegram:

```python
# Envia mensagem para o OpenClaw e aguarda resposta
# (requer implementação de fila/polling no GymSite)
```

### Schema de saída A0 (garantido compatível)

```json
{
  "contexto_mercado": {
    "cidade": "São Paulo",
    "bairro": "Pinheiros",
    "tipo_negocio": "academia",
    "publico_alvo": "premium",
    "tamanho_mercado_local": "Mercado estimado: população economicamente ativa...",
    "tendencias_bairro": ["Demanda crescente por treino funcional..."],
    "indicadores_economicos": {
      "faixa_renda_principal": "R$ 3.500–8.000",
      "densidade_demografica": "alta",
      "crescimento_populacional": "estável"
    },
    "matriz_swot_simplificada": {
      "forcas": ["Alta densidade populacional"],
      "fraquezas": ["Concorrência de redes nacionais"],
      "oportunidades": ["Nicho de boutique fitness"],
      "ameacas": ["Crise econômica"]
    },
    "benchmarks_comparativos": ["Smart Fit no bairro vizinho — 3k membros em 6 meses"]
  },
  "insights_deep_research": "# Análise de Mercado...",
  "benchmarks_setor": {
    "ticket_medio_academia_brasil": "R$ 89–179/mês",
    "ltv_medio_estimado": "R$ 2.500–4.800",
    "custo_aquisicao_cliente": "R$ 120–350",
    "retencao_media": "65–72% (12 meses)",
    "tempo_payback_referencia": "14–24 meses"
  },
  "fontes_verificadas": ["URL1", "URL2"],
  "confidence_score": 0.85
}
```

---

## Parte 2 — A8 Validador Cruzado (Novo agente)

### O que faz

Roda **depois** do A6 ReportConsolidator. Não refaz pesquisa — **verifica** se o relatório final é:
- **Coerente internamente** (payback ≥ break-even, população plausível, etc.)
- **Verificável externamente** (claims podem ser corroboradas por fontes independentes)
- **Livre de extrapolações** (score vs veredito alinhados, bairros alternativos quando necessário)

### Tabela nova no Supabase

```sql
CREATE TABLE validacoes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    relatorio_id uuid NOT NULL REFERENCES relatorios(id) ON DELETE CASCADE,
    org_id uuid NOT NULL REFERENCES organizations(id),
    validacao_id text NOT NULL,
    status_validacao text NOT NULL, -- 'APROVADO_LIMPO', 'APROVADO_MINOR_ISSUES', 'APROVADO_COM_RESSALVAS', 'REPROVADO_VALIDACAO'
    score_validacao decimal(3,2) NOT NULL, -- 0.00–1.00
    alertas jsonb NOT NULL DEFAULT '[]',
    claims_verificadas int NOT NULL,
    claims_com_alertas int NOT NULL,
    fontes_independentes text[] NOT NULL DEFAULT '{}',
    resumo_executivo_validacao text NOT NULL,
    revisar_manual boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    
    CONSTRAINT validacoes_status_check CHECK (
        status_validacao IN ('APROVADO_LIMPO', 'APROVADO_MINOR_ISSUES', 'APROVADO_COM_RESSALVAS', 'REPROVADO_VALIDACAO')
    )
);

-- RLS
ALTER TABLE validacoes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "validacoes_select_org" ON validacoes
    FOR SELECT USING (org_id IN (SELECT user_org_ids()));
CREATE POLICY "validacoes_insert_org" ON validacoes
    FOR INSERT WITH CHECK (org_id IN (SELECT user_org_ids()));
```

### Arquivos a modificar

#### 1. Copiar `gymsite_a8_validator.py` → `agents/a8_validator.py`

#### 2. Modificar `gymsite_intelligence/agent.py` (orquestrador ADK)

```python
# ANTES: pipeline termina no A6
sequential_pipeline = SequentialAgent("GymSitePipeline", [A0, A1, A2, A3a, A3b, A3c, A4, A5, A6])

# DEPOIS: adiciona A8 após o A6
sequential_pipeline = SequentialAgent("GymSitePipeline", [A0, A1, A2, A3a, A3b, A3c, A4, A5, A6, A8])
```

#### 3. Modificar `agents/a6_report_consolidator.py` para passar output ao A8

```python
# No final do A6, antes de persistir:
a8 = A8ValidadorCruzado()
validacao = await a8.validar(
    relatorio_markdown=relatorio_executivo,
    state_json=session.state,
    custo_brl=custo_total,
)

# Persiste validação junto com o relatório
supabase.table("validacoes").insert({
    "relatorio_id": relatorio_id,
    "org_id": org_id,
    ...validacao,
}).execute()

# Anexa resumo da validação ao relatório final
if validacao["revisar_manual"]:
    relatorio_executivo += "\n\n---\n\n🛑 **REVISÃO MANUAL RECOMENDADA**\n"
    relatorio_executivo += validacao["resumo_executivo_validacao"]
```

#### 4. Modificar `api.py` para expor endpoint de validação

```python
# Novo endpoint para re-validar relatório já existente
@app.post("/v1/relatorios/{relatorio_id}/validar")
async def revalidar_relatorio(relatorio_id: str, user=Depends(get_current_user)):
    # Busca relatório + state
    relatorio = supabase.table("relatorios").select("*,relatorio_outputs(*)").eq("id", relatorio_id).single().execute()
    
    validador = A8ValidadorCruzado()
    resultado = await validador.validar(
        relatorio_markdown=relatorio.data["relatorio_outputs"]["markdown_completo"],
        state_json=relatorio.data["state_dump"],  # você precisa persistir o state
    )
    
    return resultado
```

---

## Parte 3 — Wire entre A0 e A8 (exemplo de execução)

```python
import asyncio
from agents.a0_context_builder import A0ContextBuilder
from agents.a8_validator import A8ValidadorCruzado

async def run_pipeline_com_kimi():
    # A0 com Kimi
    a0 = A0ContextBuilder(adapter="kimi")  # ou default="gemini"
    ctx = await a0.run(cidade="São Paulo", bairro="Pinheiros")
    
    # ... pipeline A1–A6 roda normal ...
    
    # A8 valida o resultado
    a8 = A8ValidadorCruzado()
    validacao = await a8.validar(
        relatorio_markdown=relatorio_final,
        state_json=session.state,
    )
    
    if validacao["revisar_manual"]:
        print("🛑 Alerta crítico detectado — revisar antes de enviar ao cliente")
        for alerta in validacao["alertas"]:
            if alerta["severidade"] == "CRITICO":
                print(f"  CRÍTICO: {alerta['descricao']}")
    
    return validacao

asyncio.run(run_pipeline_com_kimi())
```

---

## Custos estimados

| Componente | Custo por relatório | Nota |
|------------|---------------------|------|
| A0 Gemini (atual) | ~R$ 1,20–1,80 | Interactions API + Search Grounding |
| A0 Kimi | ~R$ 0,30–0,60 | 5 queries `kimi_search` em paralelo |
| A8 Validador | ~R$ 0,15–0,30 | 2–3 queries de validação + parsing local |
| **Economia total** | **~R$ 0,75–1,80** | A0 mais barato; A8 é novo (custo adicional pequeno) |

---

## Testes de integração

```bash
# Teste A0 standalone
cd gymsite_intelligence
python tools/a0_kimi_adapter.py

# Teste A8 standalone
python agents/a8_validator.py

# Teste pipeline completo (smoke)
pytest tests/test_pipeline_a0_a8.py -v
```

---

## Próximos passos

1. **Copiar arquivos** deste pacote para o repo GymSite
2. **Configurar** `OPENCLAW_URL` + `OPENCLAW_TOKEN` no `.env`
3. **Rodar migration** da tabela `validacoes` no Supabase
4. **Testar** com 1 relatório de produção (comparar A0 Gemini vs A0 Kimi)
5. **Ajustar** thresholds do A8 baseado em falsos positivos das primeiras runs

---

## Arquivos entregues

| Arquivo | Destino no GymSite | Propósito |
|---------|-------------------|-----------|
| `gymsite_a0_kimi_adapter.py` | `tools/a0_kimi_adapter.py` | Substitui Deep Research Gemini |
| `gymsite_a8_validator.py` | `agents/a8_validator.py` | Segunda opinião automatizada |
| `INTEGRATION_GUIDE.md` | `docs/INTEGRATION_KIMI.md` | Este documento |

---

*Integração projetada por Vectra Clip (OpenClaw) para GymSite Intelligence.*
*Data: 2026-05-29*
