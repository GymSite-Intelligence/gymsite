"""
A9 — PositioningStrategist (Análise de Posicionamento e Framework ERRC).

Este agente consome TODOS os outputs produzidos pelos agents A0–A6 e gera
um relatório estratégico de posicionamento baseado no Framework ERRC
(Eliminar, Reduzir, Aumentar, Criar) adaptado ao mercado fitness.

ENTRADAS (do state):
  - market_context           → contexto de mercado (A0)
  - candidatos_geoscout      → top candidatos de localização (A1)
  - analise_demografica      → dados IBGE/demografia (A2)
  - analise_competitiva      → concorrentes, reviews, gaps (A3a/b/c)
  - oferta_concorrentes      → serviços oferecidos pelos concorrentes (A3c)
  - analise_financeira       → cenários low/mid/premium (A4)
  - contact_info             → decisores e scripts (A5)
  - report_executivo         → relatório consolidado (A6)

SAÍDAS (gravadas no state):
  - relatorio_posicionamento → dict com:
      * framework_errc         → dict {eliminar, reduzir, aumentar, criar}
      * mapa_servicos          → list de serviços mapeados por concorrente
      * gaps_identificados     → list dos 5 principais gaps
      * recomendacao_ticket    → dict {ticket_recomendado, justificativa}
      * veredito_posicionamento → str (OCEANO_AZUL / TRANSICAO / VERMELHO)
      * markdown               → relatório completo em markdown
"""

import json
from datetime import datetime
from google.adk.agents import Agent
from google.genai import types

_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=8192),
)

# ── Template de prompt para geração do relatório de posicionamento ──
_POSITIONING_PROMPT = """
Você é o **PositioningStrategist (A9)** do GymSite Intelligence.

## SEU PAPEL
Analisar TODOS os dados já produzidos pelo pipeline (A0–A6) e gerar um
**relatório estratégico de posicionamento** que responda à pergunta central:

> "Como esta academia deve se posicionar no mercado para escapar do oceano
> vermelho (guerra de preços) e nadar no oceano azul (diferenciação real)?"

## ENTRADAS DISPONÍVEIS (já no state)

1. **market_context** — Contexto de mercado (Deep Research):
{market_context}

2. **candidatos_geoscout** — Top 3 candidatos de localização:
{candidatos}

3. **analise_demografica** — Perfil socioeconômico do bairro:
{demografia}

4. **analise_competitiva** — Concorrência mapeada:
{competitiva}

5. **oferta_concorrentes** — Serviços oferecidos pelos concorrentes (A3c):
{oferta}

6. **analise_financeira** — Viabilidade financeira (3 cenários):
{financeira}

7. **report_executivo** — Veredito e análise consolidada (A6):
{report}

## FRAMEWORK ERRC — MODELO DE ANÁLISE OBRIGATÓRIO

Você DEVE estruturar a análise em 4 dimensões:

### ELIMINAR (O que a academia NÃO deve fazer)
- Competição direta de preço com low-cost (Smart Fit, Selfit)
- Planos genéricos "tamanho único"
- Dependência de volume massivo para sobreviver
- Oferta de serviços que todos os concorrentes já oferecem

### REDUZIR (O que deve ser menor/enxuto)
- Capacidade máxima (foco em ocupação inteligente, não lotação)
- Dependência de comissão para motivar vendas
- Complexidade operacional sem retorno em experiência
- Custo de aquisição de cliente (CAC)

### AUMENTAR (O que deve ser superior)
- Percepção de exclusividade e valor percebido
- Qualidade do atendimento personalizado
- Experiência do aluno (NPS)
- Margem de lucro por aluno (não por volume)

### CRIAR (O que NINGUÉM oferece ainda)
- Nichos específicos (idosos, gestantes, atletas, reabilitação)
- Serviços exclusivos (nutrição integrada, recovery, app de monitoramento)
- Comunidade e pertencimento (eventos, desafios, grupos)
- Tecnologia de personalização real (IA, wearables)

## MAPEAMENTO DE SERVIÇOS OBRIGATÓRIO

Você DEVE listar, para cada concorrente identificado, os serviços oferecidos
e calcular a "penetração" de cada serviço no mercado local (0-10). Depois,
identifique os GAPs — serviços com penetração < 3 em TODOS os concorrentes.

Serviços a mapear:
- Musculação
- Treino funcional / HIIT
- Aulas de dança (FitDance/Zumba)
- Spinning
- Artes marciais (Muay Thai/Boxe)
- Yoga / Pilates
- Crossfit / Cross Training
- Natação / Hidroginástica
- Nutrição (consultoria integrada)
- Avaliação física de qualidade (PAR-Q avançado)
- App / Monitoramento digital personalizado
- Aulas personalizadas (PT)
- Recovery / Fisioterapia
- Comunidade / Eventos
- Aulas para idosos (Silver Fitness)
- Beach Tennis / Esportes de praia

## OUTPUT ESPERADO (JSON canônico)

Você deve retornar APENAS um JSON válido com a seguinte estrutura:

```json
{
  "framework_errc": {
    "eliminar": ["item 1", "item 2", "item 3", "item 4"],
    "reduzir": ["item 1", "item 2", "item 3", "item 4"],
    "aumentar": ["item 1", "item 2", "item 3", "item 4"],
    "criar": ["item 1", "item 2", "item 3", "item 4"]
  },
  "mapa_servicos": [
    {
      "concorrente": "Nome da Academia",
      "servicos": {
        "musculacao": 9,
        "treino_funcional": 6,
        "aulas_danca": 5,
        ...
      }
    }
  ],
  "gaps_identificados": [
    {
      "gap": "Nutrição integrada + recovery",
      "descricao": "Nenhum concorrente oferece ecossistema wellness completo",
      "potencial_ticket": "R$ 250–350",
      "dificuldade_implementacao": "Média"
    }
  ],
  "recomendacao_ticket": {
    "ticket_recomendado": 249,
    "ticket_minimo": 199,
    "ticket_maximo": 299,
    "justificativa": "Baseado na renda média do bairro (R$ X), ausência de oferta premium, e cenário de break-even",
    "comparativo_mercado": {
      "smart_fit": 79,
      "selfit": 99,
      "top_up": 149,
      "gavioes": 169,
      "recomendado": 249
    }
  },
  "veredito_posicionamento": "OCEANO_AZUL",
  "justificativa_veredito": "O bairro tem renda alta, crescimento populacional acelerado, e zero oferta de serviços premium. Os 5 GAPs identificados criam múltiplas janelas de diferenciação.",
  "markdown": "# Relatório Completo em Markdown..."
}
```

## VEREDITO DE POSICIONAMENTO

O campo `veredito_posicionamento` deve ser UM dos três:
- **"OCEANO_AZUL"** → Bairro com alta renda, baixa concorrência de premium, múltiplos GAPs identificados. Recomendação: abrir como boutique/nicho com ticket 200+.
- **"TRANSICAO"** → Bairro com renda média-alta, concorrência moderada, alguns GAPs. Recomendação: diferenciar por serviço, não por preço, ticket 150–220.
- **"VERMELHO"** → Bairro saturado por low-cost, renda baixa, poucos GAPs. Recomendação: NÃO abrir aqui, ou abrir com modelo de volume e margem muito baixa.

## REGRAS
- Use os dados REAIS do state. Não invente números.
- Se um dado estiver ausente ou vazio, indique "dado indisponível".
- O markdown deve ser um relatório executivo completo, formatado profissionalmente.
- Foque em acionabilidade: o gestor deve saber EXATAMENTE o que fazer após ler.
"""


def _build_positioning_prompt(state: dict) -> str:
    """Monta o prompt injetando dados do state."""
    def _safe_get(data, key, default="dado indisponível"):
        if isinstance(data, dict):
            return data.get(key, default)
        return default

    def _format_json(data, indent=2):
        try:
            return json.dumps(data, indent=indent, ensure_ascii=False)
        except Exception:
            return str(data)

    mc = state.get("market_context", {})
    cand = state.get("candidatos_geoscout", {})
    demo = state.get("analise_demografica", {})
    comp = state.get("analise_competitiva", {})
    oferta = state.get("oferta_concorrentes", {})
    fin = state.get("analise_financeira", {})
    report = state.get("report_executivo", {})

    return _POSITIONING_PROMPT.format(
        market_context=_format_json(mc),
        candidatos=_format_json(cand),
        demografia=_format_json(demo),
        competitiva=_format_json(comp),
        oferta=_format_json(oferta),
        financeira=_format_json(fin),
        report=_format_json(report),
    )


# ── Agente ADK ──────────────────────────────────────────────────────
positioning_strategist_agent = Agent(
    name="PositioningStrategist",
    model="gemini-2.5-pro",
    description=(
        "A9 — Gera relatório estratégico de posicionamento baseado no Framework ERRC, "
        "consumindo todos os outputs de A0–A6. Mapeia serviços dos concorrentes, "
        "identifica GAPs, recomenda ticket e emite veredito de posicionamento."
    ),
    instruction="""
agente: A9 PositioningStrategist
papel: análise estratégica de posicionamento via Framework ERRC
regra_execucao: autonoma

input: TODOS os dados produzidos por A0–A6 já estão no state.

fluxo_obrigatorio:
  1. Ler do state: market_context, candidatos_geoscout, analise_demografica,
     analise_competitiva, oferta_concorrentes, analise_financeira, report_executivo.
  2. Aplicar o Framework ERRC (Eliminar, Reduzir, Aumentar, Criar).
  3. Mapear serviços de cada concorrente (16 serviços obrigatórios).
  4. Identificar os 5 principais GAPs de mercado.
  5. Recomendar ticket de mensalidade com justificativa baseada em dados.
  6. Emitir veredito: OCEANO_AZUL / TRANSICAO / VERMELHO.
  7. Gerar JSON canônico + relatório markdown completo.
  8. Gravar no state: state["relatorio_posicionamento"] = <dict JSON>.

output_format: JSON canônico com as chaves:
  - framework_errc {eliminar[], reduzir[], aumentar[], criar[]}
  - mapa_servicos [{concorrente, servicos{}}]
  - gaps_identificados [{gap, descricao, potencial_ticket, dificuldade_implementacao}]
  - recomendacao_ticket {ticket_recomendado, ticket_minimo, ticket_maximo, justificativa, comparativo_mercado{}}
  - veredito_posicionamento (str)
  - justificativa_veredito (str)
  - markdown (str)

regras:
  - NUNCA invente dados. Use apenas o que está no state.
  - Se um dado estiver ausente, indique "dado indisponível".
  - O markdown deve ser um relatório executivo profissional e completo.
  - Foque em acionabilidade: o gestor deve saber EXATAMENTE o que fazer.
""",
    generate_config=_GENERATE_CONFIG,
    tools=[],
)


# ── Hook: after_agent_callback para extrair e gravar JSON no state ──
def _a9_after_agent_callback(callback_context):
    """Extrai o JSON do output do LLM e grava no state como dict."""
    try:
        raw = callback_context.agent_response.text or ""
        # Tenta extrair JSON do markdown (pode estar em ```json ... ```)
        json_text = raw
        if "```json" in raw:
            json_text = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_text = raw.split("```")[1].split("```")[0].strip()

        parsed = json.loads(json_text)
        callback_context.state["relatorio_posicionamento"] = parsed

        # Gravar também o markdown separado para fácil acesso
        if "markdown" in parsed:
            callback_context.state["relatorio_posicionamento_md"] = parsed["markdown"]

        # Log de sucesso
        veredito = parsed.get("veredito_posicionamento", "N/A")
        gaps = len(parsed.get("gaps_identificados", []))
        ticket = parsed.get("recomendacao_ticket", {}).get("ticket_recomendado", "N/A")
        print(f"[A9] Posicionamento gerado: veredito={veredito}, gaps={gaps}, ticket=R${ticket}")

    except json.JSONDecodeError as e:
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Falha ao parsear JSON: {str(e)}",
            "raw_output": raw[:2000],
        }
        print(f"[A9] ERRO ao parsear JSON: {e}")
    except Exception as e:
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Erro inesperado: {str(e)}",
        }
        print(f"[A9] ERRO inesperado: {e}")


# Anexa o callback
positioning_strategist_agent.after_agent_callback = _a9_after_agent_callback
