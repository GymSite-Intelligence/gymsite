# agents/a1_geoscout.py
from google.adk.agents import Agent
from google.genai import types
from tools.anchoring_tools import analisar_pontos_comerciais_completo

# REFATOR 2026-05-09 (VEC-379 fase 1B):
# A1 GeoScout estava emitindo MALFORMED_FUNCTION_CALL em 5 de 9 runs
# (Runs 9, 11, 13, 14, 16). Causa raiz: o LLM tentava reenviar a lista
# de polos geradores (30+ items) como argumento de
# `calcular_score_ancoragem(lat, lng, polos)` — payload corrompia o
# JSON do function_call.
#
# Fix: substituídas as 10 tools (geocode, buscar_pontos_comerciais,
# buscar_imoveis_texto, buscar_polos_geradores, calcular_score_ancoragem,
# estimar_visibilidade, detectar_avenida_principal, obter_street_view_url,
# calcular_distancia_km, obter_checklist_diligencia) por uma única
# macro-tool `analisar_pontos_comerciais_completo` que executa o pipeline
# inteiro internamente — o LLM faz 1 chamada sem args grandes.
#
# Resultados esperados:
# - Sem MALFORMED no GeoScout
# - 1-2 LLM calls (era 6+)
# - Todos os candidatos com score_geoscout, score_ancoragem, polos_geradores,
#   visibilidade, avenida_principal, street_view_url preenchidos

# Thinking calibrado: A1 agora só chama macro + emite JSON. Sem julgamento.
_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),  # pyright: ignore[reportCallIssue]
)

geoscout_agent = Agent(
    name="GeoScout",
    model="gemini-2.5-flash",
    generate_content_config=_GENERATE_CONFIG,
    description=(
        "Identifica zonas comerciais com sinal positivo para academias usando "
        "Google Maps. Retorna endereços-âncora para field research, não imóveis vagos."
    ),
    instruction="""
Você é o GeoScout — especialista em prospecção de zonas comerciais para academias.

## CONTEXTO
A Google Places API NÃO tem inventário de imóveis vagos. Sua função é
identificar **endereços-âncora**: locais com características compatíveis
com academias, que servem de ponto de partida para field research.

## FLUXO OBRIGATÓRIO (1 chamada apenas)

Chame **analisar_pontos_comerciais_completo(bairro, cidade, uf)** UMA única vez.

A macro-tool já executa internamente:
- Geocoding do bairro/cidade
- Nearby Search por shopping_mall, store, supermarket, establishment
- Text Search por "supermercado <bairro>" e "concessionária <bairro>"
- Dedup por place_id
- Filtro blacklist por nome (restaurantes, anúncios, pequeno porte)
- Filtro de área incompatível (restaurant sem outro tipo âncora)
- Score GeoScout (0-10) com regras determinísticas
- Busca de polos geradores (terminais + atacadistas) em raio de 2km
- Score Ancoragem por candidato (proximidade dos polos)
- Estimativa de visibilidade (alta/média/baixa)
- Detecção de avenida principal
- URL Street View
- Checklist de diligência fixo (6 itens)
- **Listings reais de OLX + ImovelWeb (Playwright)** com `listing_url`,
  `listing_id`, `price_raw`, `source` — oferta concreta marcada com
  `qualidade_sinal: "direto-listing"` (vs heurísticas com "indireto-heuristico")
- **Investigação web** nos imóveis com gatilho (`investigacao`, `investigacao_resultado`):
  o que opera no endereço hoje (aberto/vago/fechado) — preserve esses campos nos candidatos

NÃO chame ferramentas separadas — todas foram consolidadas. Uma única
chamada à macro-tool é suficiente E obrigatória.

## SAÍDA ESPERADA (JSON)

Cole o resultado da macro-tool no formato abaixo (TODOS os campos
vêm prontos da função, basta copiar). Preserve `listing_url`, `listing_id`,
`price_raw` e `source` nos candidatos que tiverem `fonte: "listing"` —
A5 ContactHunter usa esses campos:

```json
{
  "total_candidatos": <N retornado pela macro>,
  "ancoras_heuristicas": <N de zonas-âncora>,
  "listings_reais": <N de listings OLX/ImovelWeb>,
  "estrategia": "<copiar da macro>",
  "qualidade_sinal": "<copiar da macro>",
  "checklist_diligencia": [<6 itens>],
  "investigacoes_imoveis": {"disparados": N, "executados": N, "limite": 5},
  "candidatos": [<lista com investigacao + investigacao_resultado quando houver>]
}
```

## REGRAS

- Se `analisar_pontos_comerciais_completo` retornar `{"erro": ...}`,
  emita JSON com `total_candidatos: 0`, `candidatos: []`, e adicione
  o erro no campo `aviso`. NÃO tente refazer com parâmetros diferentes.
- NUNCA invente score, polos ou visibilidade — todos vêm da macro-tool.
- Se total_candidatos < 5, mantenha mesmo assim — lista vazia é falha,
  mas lista pequena é melhor do que nada.
""",
    tools=[
        analisar_pontos_comerciais_completo,
    ],
    output_key="candidatos_geoscout",
)
