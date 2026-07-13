# `tools/9_obsolete/` — legado fora do caminho crítico

> P-000 §3: **aluguel viabilidade = MRLR Tier 0** (`tools/aluguel_mrlr.py`). Conteúdo aqui não substitui MRLR.

## O que vive aqui

| Artefato | Era usado para | Substituído por |
|---|---|---|
| `aluguel_municipio_portais.py` | Tier 1 portais (ZAP/Viva/OLX) + **`bundle.aluguel_portais`** no batch | **MRLR** (A4 Tier 0); listings SearchAPI só para candidato |
| `fixtures/aluguel_portais/` | testes HTML dos portais | — |
| `test_aluguel_*.py` | regressão do scraper | testes MRLR em `tools/test_aluguel_mrlr.py` |

## O que ainda importa o shim `tools/aluguel_municipio_portais.py`

- **A4 fallback** (`financial_tools.analise_financeira_a4_completo`): Tier 1 portais **somente** se MRLR `status!=ok` — candidato a remoção futura.
- **Não** entra mais no `market_bundle` batch nem em `cached_aluguel_portais`.

## Regra para agentes

Antes de reativar qualquer módulo desta pasta: ler `.agent/rules/conferencia-fontes-pipeline.md` e P-000 §3.
