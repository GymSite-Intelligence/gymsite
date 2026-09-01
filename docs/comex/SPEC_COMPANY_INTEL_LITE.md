# Company Intel Lite — definição de sucesso (gabarito Logcomex-like)

## Gabarito

Arquivo de sucesso (formato próximo ao Company Intel / export Logcomex):

- `docs/comex/golden/importadores_9506_teus_porto_destino.json` — linhas operacionais
- `docs/comex/golden/importadores_9506_rollup.json` — 1 linha por importador (soma TEU)
- `docs/comex/golden/importadores_9506_meta.json` — totais e filtros do lote

Lote atual: capítulo **9506**, mês **07/2026**, foco **SC** (com algumas linhas Santos), **12 importadores**, **767 TEU**.

### Schema de sucesso (linha)

| Campo | Obrigatório | Origem realista no nosso stack |
|---|---|---|
| `importador` | sim | **não** no Comex Stat — alvo via RFB candidatos + score / base paga |
| `cidade_importador` | sim | Stat `/cities` (proxy sede) + RFB |
| `uf_importador` | sim | Stat + RFB |
| `capitulo_ncm` / SH4 `9506` | sim | Stat |
| `pais_origem` | sim | Stat (`country`) |
| `porto_destino` | sim | Stat URF ≈ porto (Navegantes/Itajaí/Itapoá) |
| `porto_origem` | sim | **fraco** no Stat (país sim; porto estrangeiro não) |
| `exportador_fornecedor` | sim | **não** no Stat — só base BL/paga |
| `total_teus` + 20'/40'/FCL/LCL | sim | Stat kg → TEU estimado (já fazemos) |
| `mes_operacao_fmt` | sim | Stat `monthDetail` |
| `descricao_produto` | opcional | texto NCM/capítulo |

## Critério de sucesso do produto

Não é “bater TEU linha a linha com Logcomex”. É:

1. **Mercado (L0/L1)** — Stat reproduz concentração por UF/cidade/porto/país do lote (sem nomes).
2. **Recall nominal (L2/L3)** — entre os 12 `importador` do gabarito, nosso ranking de candidatos (RFB+sede+CNAE+score) recupera o máximo possível no top-N.
3. **Carimbo** — toda afirmação carrega valor · base · fonte · janela; nunca dizer “importou NCM X” só porque o CNPJ está na cidade quente.

### Scorecard (0–100)

| Bloco | Peso | Como medir |
|---|---|---|
| Cobertura mercado Stat vs meta do lote | 30 | países, portos destino, sedes do golden batem no Stat do período |
| Recall@12 / Recall@50 dos nomes golden | 40 | `norm(importador)` ∈ lista candidatos |
| Precisão top-20 (seed) | 20 | fração do top-20 que está no golden ou seed manual |
| Frescor / reprodutibilidade | 10 | smoke Stat + fixture versionada |

Meta v0: **Recall@50 ≥ 40%** nos 12 nomes (muitos são trading/importadoras reais em SC — esperamos achar no RFB).  
Meta v1: **Recall@50 ≥ 70%** + relatório no schema do rollup (sem exigir fornecedor/porto origem estrangeiro).

### Resultado L2 (corrida `tools/comex_l2_candidatos.py`)

- Fonte: BigQuery `basedosdados.br_me_cnpj` (partição mais recente disponível).
- Artefatos: `docs/comex/l2/candidatos_cidades_golden.json`, `docs/comex/l2/recall_vs_golden.json`.
- **Recall@50 = 11/12 (91,7%)** — miss restante: `U STAR COMERCIO LTDA` (razão social não encontrada ativa nas cidades do gabarito).
- Top ranks: STONE (#1 Itajaí), Life Fitness, AC Comercial, RD Sports, Konnen, First S/A, Senior, Vendemmia…
- Carimbo obrigatório: candidatos ≠ comprovação de importação NCM.

## O que o Stat **não** vai entregar neste gabarito

- Nome `importador`
- `exportador_fornecedor`
- `porto_origem` estrangeiro (Ningbo, Qingdao…)

Esses três campos são o “delta Logcomex”. No lite: ou ficam vazios, ou vêm de fonte comercial explícita (assinatura), nunca fingidos.

## Testes

- `tests/comex/test_golden_importadores_9506.py` — schema + totais do gabarito
- `tests/comex/test_recall_vs_golden.py` — recall de uma lista candidata vs gabarito
- `tools/company_intel_recall.py` — `normalize_importer_name` + `recall_at_k`

## Próximo passo de implementação

1. Manter este gabarito fixo (não regenerar a partir do Stat).
2. Job L1: sedes Stat SH4 9506 × mês alinhado ao golden.
3. Job L2: CNPJs ATIVOS nas cidades do golden (`ITAJAI`, `JOINVILLE`, …) + CNAEs fitness/import.
4. Medir recall dos 12 nomes; iterar score.
