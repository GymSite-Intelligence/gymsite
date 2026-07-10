# agents/a0_context_builder.py
"""
A0: Context Builder — primeiro agente do pipeline.

Deep Research (qualitativo) + fatos CNPJ/CNO (quantitativo).
Sem interpretação além dos dados retornados pelas tools.
"""
from google.adk.agents import Agent
from google.genai import types
from tools.deep_research_tool import rodar_deep_research
from tools.kimi_research import rodar_kimi_research
from tools.cnpj_fitness_tools import dados_parque_cnpj_para_a0
from tools.local_market_facts import fatos_competicao_local
from tools.market_bundle import carregar_market_bundle

_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=1024),
)


def _a0_override_cnpj_numeros(callback_context):
    """Override DETERMINÍSTICO dos números CNPJ no market_context.

    A0 é LlmAgent (precisa do Deep Research qualitativo), mas o LLM NÃO pode produzir
    número — a instrução manda "Copiar metricas_objetivas", e copiar via LLM arrisca
    transcrição errada/arredondamento sem guardrail. Este callback RE-RODA a tool
    determinística `dados_parque_cnpj_para_a0` e sobrescreve os campos numéricos do CNPJ
    + pluga `arvore_2x2_parque` (que o schema de saída do LLM dropava). Número = sempre da
    tool (banco), nunca da boca do LLM. Mesmo padrão do override do A9. Os campos
    QUALITATIVOS (ticket/aluguel/tendência/insights, do Deep Research) ficam intactos.

    Best-effort: nunca derruba. _attach_telemetry encadeia ANTES do otel/state_dump.
    """
    try:
        from tools.cnpj_fitness_tools import dados_parque_cnpj_para_a0
        from tools.competitor_tools import _parse_market_context

        st = callback_context.state
        mc = _parse_market_context(st.get("market_context"))
        tem_envelope = isinstance(mc.get("market_context"), dict)
        inner = mc.get("market_context") if tem_envelope else mc
        if not isinstance(inner, dict):
            return None

        ip = st.get("input_params") if isinstance(st.get("input_params"), dict) else {}
        cidade = (ip.get("cidade") or inner.get("cidade") or "").strip()
        uf = (ip.get("uf") or inner.get("uf") or "").strip()
        bairro = (ip.get("bairro") or inner.get("bairro") or "").strip()
        if not cidade:
            return None

        tool = dados_parque_cnpj_para_a0(cidade, uf, dias=90, bairro=bairro)
        if not isinstance(tool, dict) or tool.get("status") != "ok":
            return None
        m = tool.get("metricas_objetivas") or {}
        ind = tool.get("indicadores_derivados") or {}

        inner["parque_ativo_total"] = m.get("parque_ativo_total")
        inner["parque_comercial_total"] = m.get("parque_comercial_total")
        inner["academias_ativas_cidade_cnpj"] = m.get("parque_ativo_total")
        inner["novos_cnpj_fitness_90d"] = m.get("novos_cnpj_fitness_90d")
        inner["excluidos_saude_clinica"] = m.get("excluidos_saude_clinica")
        inner["pendentes_validacao"] = m.get("pendentes_validacao")
        inner["composicao_parque"] = m.get("composicao_parque") or {}
        inner["novas_unidades_90d_por_segmento"] = m.get("novas_unidades_90d_por_segmento") or {}
        inner["serie_aberturas_anual"] = m.get("serie_aberturas_anual") or {}
        inner["arvore_2x2_parque"] = tool.get("arvore_2x2_parque")  # plug: o LLM dropava
        inner["fatos_parque_cnpj"] = {
            "fonte": "RFB CNPJ Aberto",
            "metricas": m,
            "indicadores_derivados": ind,
            "cruzamento_cno": tool.get("cruzamento_cno") or {},
            "lacunas": tool.get("lacunas_conhecidas") or [],
        }
        inner["_cnpj_override"] = "deterministico_tool"

        if tem_envelope:
            mc["market_context"] = inner
            st["market_context"] = mc
        else:
            st["market_context"] = inner
    except Exception:
        pass
    return None


from tools.agent_factory import build_llm_agent
context_builder_agent = build_llm_agent(
    name="ContextBuilder",
    model="gemini-2.5-flash",
    generate_content_config=_GENERATE_CONFIG,
    description=(
        "Constrói contexto de mercado (Deep Research + fatos CNPJ/CNO) "
        "sem inferências além dos dados das tools."
    ),
    instruction="""
Você é o ContextBuilder — primeiro agente do pipeline GymSite Intelligence.

## REGRA ZERO — SEM INTERPRETAÇÃO INVENTADA
- Se a tool não retornou o dado, use `"dados_nao_disponiveis"` ou omita o campo.
- PROIBIDO: achismos, "parece que", oportunidades/riscos sem fonte explícita.
- PROIBIDO a palavra **estoque** — use **parque ativo** (unidades no CNPJ) e
  **aberturas recentes** / **fluxo de aberturas** (novas unidades 90d).
- Você **consolida e cruza fatos** das tools; não é consultor criativo.

## FLUXO
1. Extrair cidade, bairro, uf, genero_alvo, tipo_negocio, tamanho_preset.
2. **`carregar_market_bundle(cidade, bairro, uf)` primeiro** — se retornar briefing com
   `<!-- market_bundle` (sem `status=missing`), use como `briefing_completo_md` e preencha
   demografia/aluguel a partir do texto. **Não** chame `rodar_deep_research` se o bundle estiver completo.
3. Só se bundle `missing` (inexistente) ou `missing_fields` contiver lacuna SUBSTANTIVA
   (aluguel_medio_m2, ticket_medio, tendencia) → `rodar_deep_research` ou `rodar_kimi_research`.
   **EXCEÇÃO — não chame DR** quando os únicos missing forem `renda_media_bairro` e/ou
   `competicao_osm`: o Deep Research comprovadamente não entrega renda por bairro
   (caso Parangaba) e a concorrência real vem do A3a (Places) adiante no pipeline.
   Nesses casos use `"dados_nao_disponiveis"` e siga — pagar pesquisa cara por lacuna
   que ela não preenche é desperdício.
4. `dados_parque_cnpj_para_a0(cidade, uf, dias=90, bairro=bairro)` — fatos CNPJ + CNO.
5. `fatos_competicao_local(cidade, bairro, uf)` — marcas no raio via OSM (se geocode ok), salvo cache/skip.
6. Montar JSON. Bundle/DR → ticket, aluguel, tendência (qualitativo).
   `principais_redes_concorrentes` = **somente** `redes_detectadas_osm` da tool local.
   Se a tool local falhar ou retornar lista vazia, use `[]` — **não** copie redes do DR.
   Tool CNPJ → números e composição. Tool CNO → área m² só onde houver match.

## SAÍDA (JSON)
O schema abaixo é REFERÊNCIA de estrutura. Sua resposta final deve ser SOMENTE o
objeto JSON — sem markdown, sem fence ```, começando por { e terminando por }.
```json
{
  "market_context": {
    "cidade": "",
    "bairro": "",
    "uf": "",
    "ticket_medio_mercado": "",
    "aluguel_medio_m2": "",
    "renda_media_bairro": "",
    "faixa_etaria_predominante": "",
    "genero_alvo": "misto",
    "tipo_negocio": "academia",
    "tamanho_preset": "m",
    "principais_redes_concorrentes": [],
    "tendencia_mercado": "crescimento|estavel|retracao",
    "regulamentacao_resumo": "",
    "insights_estrategicos": ["fato+fonte 1", "fato+fonte 2", "fato+fonte 3"],
    "parque_ativo_total": 0,
    "parque_comercial_total": 0,
    "novos_cnpj_fitness_90d": 0,
    "excluidos_saude_clinica": 0,
    "pendentes_validacao": 0,
    "composicao_parque": {},
    "novas_unidades_90d_por_segmento": {},
    "academias_ativas_cidade_cnpj": 0,
    "serie_aberturas_anual": {},
    "fatos_parque_cnpj": {
      "fonte": "RFB CNPJ Aberto",
      "metricas": {},
      "indicadores_derivados": {},
      "cruzamento_cno": {},
      "lacunas": []
    },
    "fonte_entrantes": "",
    "fonte": "market_bundle + CNPJ/CNO (tools)",
    "data_coleta": "YYYY-MM-DD",
    "cached": false,
    "briefing_completo_md": ""
  }
}
```

## REGRAS CNPJ (tool)
- Copiar `metricas_objetivas` nos campos escalares correspondentes.
- `fatos_parque_cnpj.metricas` = cópia estruturada das métricas.
- `fatos_parque_cnpj.indicadores_derivados` = só o que a tool calculou
  (ex.: taxa_renovacao_parque_90d_pct, segmento_dominante_parque).
- Se `divergencia_parque_vs_aberturas=true`, registrar em `fatos_parque_cnpj`
  como fato ("parque dominado por X; aberturas 90d por Y") — sem recomendar ação.

## REGRAS CNO (tool, se pasta disponível)
- `cruzamento_cno` = resumo_match + até 5 entrantes com `area_m2_obra` preenchida.
- Capacidade alunos = benchmark MATRICULADOS_POR_M2 do pipeline (já na tool).
- Se `sem_obra` > 0, listar em `lacunas` — não estimar m² por chute.

## INSIGHTS
- Cada insight = 1 frase com **fonte** entre parênteses: (Deep Research), (CNPJ), (CNO).
- Pelo menos 1 insight deve citar número CNPJ; pelo menos 1 pode vir do DR.
- Sem palavra "estoque".

## DEGRADAÇÃO
- DR indisponível → campos DR como dados_nao_disponiveis; CNPJ ainda preenche se ok.
- CNPJ indisponível → lacunas explicam; não inventar parque.
""",
    tools=[
        carregar_market_bundle,
        rodar_deep_research,
        rodar_kimi_research,
        dados_parque_cnpj_para_a0,
        fatos_competicao_local,
    ],
    output_key="market_context",
    after_agent_callback=_a0_override_cnpj_numeros,
)
