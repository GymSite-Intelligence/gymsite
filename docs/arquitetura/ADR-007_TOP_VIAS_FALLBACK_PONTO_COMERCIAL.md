# ADR-007 — Top Vias de Prospecção como fallback quando não há ponto comercial real

| Campo | Valor |
|---|---|
| Status | **Accepted** (retroativo — decisão já implementada em código antes deste registro) |
| Decisores | GymSite / Marcelo |
| Relacionados | `tools/anchoring_tools.py` (`analisar_pontos_comerciais_completo`), `tools/fluxo_pedestre_tools.py` (`top_vias_por_fluxo`), `agents/a6_report_consolidator.py` (`_tem_candidato_listing_real`, `_alinhar_markdown_ao_estruturado`, `_renderizar_md_top_vias`), `tools/listing_cascata.py`, `tests/agents/test_a1_pirapora_pontos_indeterminado.py` |

## Contexto

O GeoScout (A1) tentava, historicamente, recomendar um **ponto comercial específico** (endereço + área estimada) ancorando a busca em POIs de referência (supermercado, praça, avenida principal etc.) quando não existia um anúncio real de imóvel na região. Essa saída é marcada no candidato com `qualidade_sinal = "indireto-heuristico"` (`tools/anchoring_tools.py:419`).

O teste `tests/agents/test_a1_pirapora_pontos_indeterminado.py` — cujo próprio nome de arquivo é "evidência de deprecação" — documenta o problema encontrado em produção:

> "`analisar_pontos_comerciais_completo` devolve POIs âncora (supermercado etc.) com sinal heurístico, área estimada e, em praças menores, **contaminação fora da cidade**. **Não é ponto comercial decidível p/ relatório.**"

Ou seja: sem um anúncio real por trás (imóvel de fato à venda/aluguel, capturado via `listing_cascata.py`/SearchAPI em OLX e ImovelWeb), a heurística de ancoragem por POI podia:

1. Estimar uma área de imóvel que não corresponde a nenhuma oferta real.
2. Em cidades/praças menores, apontar um ponto **fora dos limites da própria cidade** (erro de geocoding/raio).
3. Entregar um "candidato" com aparência de decisão pronta, mas sem nenhum imóvel real que sustente essa afirmação.

Isso viola a regra mais repetida do projeto: **todo número exibido ao usuário carrega carimbo de fonte** — um endereço específico apresentado com a mesma autoridade de um imóvel real, quando na verdade é uma estimativa por proximidade, é exatamente o tipo de "número sem base rotulada" que a auditoria de relatórios (`docs/produto/AUDITORIA_RELATORIO_COCO.md`) já identificou como problema recorrente do setor.

## Decisão

**O relatório nunca apresenta um ponto heurístico como se fosse um ponto comercial real.** Em vez disso, A6 decide qual seção mostrar com base na existência (ou não) de um candidato com anúncio real:

```python
# agents/a6_report_consolidator.py
def _tem_candidato_listing_real(top_3: list | None) -> bool:
    for c in top_3 or []:
        qs = str(c.get("qualidade_sinal") or "").lower()
        if qs.startswith("direto-listing"):
            return True
    return False
```

- **Existe candidato `direto-listing` / `direto-listing-bairro`** (anúncio real, capturado via `listing_cascata.py` → SearchAPI → OLX/ImovelWeb, com endereço, área e preço reais) → o relatório mostra **"🏆 Top 3 Candidatos"**: endereço específico, aluguel MRLR, payback estimado (`_renderizar_md_top3_candidatos`).
- **Não existe** nenhum candidato com anúncio real → o relatório mostra **"🏆 Top 3 Ruas/Avenidas"** (`_renderizar_md_top_vias`, alimentada por `top_vias_por_fluxo`): um ranking de vias por fluxo de pedestres/veículos, calculado de forma determinística sobre a malha viária real (OpenStreetMap via `osmnx`/space syntax, cache espacial, sem LLM, `attribution: "© OpenStreetMap contributors"`).

A troca acontece na montagem do markdown (`_alinhar_markdown_ao_estruturado`), condicionada a `melhores_vias_prospeccao.status == "ok"` **e** ausência de candidato real **e** a seção "Top 3 Ruas/Avenidas" ainda não estar no texto do LLM.

O código de ancoragem heurística por POI (`anchoring_tools.py`) **não foi removido** — ele continua rodando e pode alimentar outros campos do candidato (ex.: `avenida_principal`, `polos_geradores`). O que mudou é que o relatório final **não usa mais o ponto heurístico isolado como recomendação de endereço** quando não há respaldo de um imóvel real.

### Opções rejeitadas

| Opção | Motivo |
|---|---|
| Manter o ponto heurístico como recomendação principal | Risco documentado de apontar endereço fora da cidade ou área inexistente — quebra a regra de carimbo de fonte |
| Omitir a seção inteira quando não há listing real | Deixa o usuário sem nenhuma orientação acionável para começar a busca de ponto |
| Mostrar ponto heurístico E top vias sempre, lado a lado | Mistura informação de confiança alta (anúncio real) com baixa (estimativa) na mesma seção, sem diferenciação clara para quem lê |

## Consequências

### Positivas

- O relatório nunca apresenta uma estimativa com a mesma autoridade de um dado verificado — alinhado à regra de carimbo (valor · base · fonte · janela).
- Mesmo sem imóvel real disponível na região, o cliente recebe orientação acionável e honesta: "procure nestas vias", em vez de um endereço específico que pode estar errado.
- `top_vias_por_fluxo` é determinístico e reaproveita o motor de fluxo pedestre já existente (cache espacial) — sem custo adicional de LLM ou nova fonte de dado.

### Negativas / trabalho pendente

- Quando não há listing real, o relatório perde a especificidade de endereço — o usuário precisa buscar manualmente nas vias indicadas, um passo a mais no fluxo de decisão.
- `anchoring_tools.py` continua rodando por baixo dos panos mesmo quando seu resultado de ponto específico não vira a recomendação principal — código parcialmente órfão em termos de uso no relatório final (oportunidade futura de simplificação, não tratada aqui).
- O problema de geocoding que causava "contaminação fora da cidade" no método heurístico não foi corrigido — foi contornado (deixou de ser mostrado como recomendação), não resolvido na fonte.

### Fora de escopo (tickets separados)

- Remover ou reescrever `anchoring_tools.py`/`analisar_pontos_comerciais_completo`.
- Corrigir o erro de geocoding/raio que causa candidatos fora dos limites da cidade em praças menores.
- Expandir a cobertura de `listing_cascata.py` para reduzir a frequência de "sem listing real" (mais cidades/fontes).

## Verificação

- [x] `tests/agents/test_a1_pirapora_pontos_indeterminado.py` documenta e reproduz o problema do método heurístico (fração de candidatos `indireto-heuristico` medida e limitada).
- [x] `agents/a6_report_consolidator.py::_tem_candidato_listing_real` gate a exibição de "Top 3 Candidatos" a `qualidade_sinal` iniciando em `"direto-listing"`.
- [x] `agents/a6_report_consolidator.py::_alinhar_markdown_ao_estruturado` troca para "Top 3 Ruas/Avenidas" quando não há candidato real e `melhores_vias_prospeccao.status == "ok"`.
- [x] `tools/fluxo_pedestre_tools.py::top_vias_por_fluxo` é fail-soft (`status: "indisponivel"` sem inventar score) quando a malha OSM falha.
