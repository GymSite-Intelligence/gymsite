# Spec — Posicionamento por Headroom de Renda (IPECE Censo 2022)

> Status: **especificação** (pré-wire). Fonte de renda: IPECE Informe 272 (Censo 2022, 121 bairros de Fortaleza).
> Relacionado: regra de ouro zero-hardcode (`tools/parametros_metodologia.py`), perfil A/B (`classificar_perfil_bairro`), A9 PositioningStrategist.

## ELI5
Hoje a gente sabe a renda do bairro em número solto (e velho — Censo 2010). Mas pra **decidir como se posicionar** (low-cost? premium?), o que importa não é o número absoluto e sim:
1. **Quão rico é esse bairro COMPARADO ao resto da cidade?** (percentil)
2. **Sobra dinheiro no bolso do morador que os concorrentes atuais NÃO estão capturando?** (headroom)

Se o bairro é rico E os concorrentes só vendem plano barato → tem gente que pagaria premium e ninguém oferece = **oceano azul**. Essa é a métrica-chave.

## Problema
- Renda do bairro hoje = CKAN IDH-Renda **base Censo 2010**, per capita derivada (Atlas). Stale 12 anos.
- Usada só como número absoluto pra `score_demografico` + teto de ticket. **Não embasa posicionamento.**
- O veredito de posicionamento do A9 (`OCEANO_AZUL` / `TRANSICAO` / `VERMELHO`) é **chute do LLM** (sweep de determinismo flagou).

## Fonte nova
- **IPECE Informe 272 (ago/2025)** — renda média **domiciliar** mensal, Censo 2022, 121 bairros + 12 SERs.
  PDF: https://www.ipece.ce.gov.br/wp-content/uploads/sites/45/2025/08/ipece_informe_272_05_ago2025.pdf
- Distribuição Fortaleza: média R$ 3.330,34 · mediana R$ 2.229,66 · σ R$ 2.633,88 · min R$ 1.272,25 (Genibaú) · max R$ 14.775,21 (Guararapes). Cocó R$ 13.372,43.
- **Unidade:** domiciliar. Conversão p/ per capita: `renda_pc = renda_domiciliar / media_moradores_domicilio` (do Censo setor, já espelhado). Cocó: 13.372 / 2,66 ≈ **R$ 5.027 pc**.

## Métricas (3)

### 1. Renda-percentil do bairro (relativa) — `renda_percentil`
Posição do bairro na distribuição dos 121. `renda_percentil ∈ [0,1]`.
- Mapeia tier de modelo por **quartil real da cidade** (substitui `_tier_mercado_por_renda`, hoje cortes hardcoded 2500/4500):
  - `≥ param("renda_percentil_premium")` (0.75) → apto Premium
  - `≥ param("renda_percentil_mid")` (0.40) → Mid
  - abaixo → Low

### 2. Headroom premium (PRINCIPAL) — `headroom_premium` / `headroom_ratio`
Quanto da capacidade de pagar do bairro NÃO está sendo capturada pelos concorrentes atuais.
```
renda_pc          = renda_domiciliar_ipece / media_moradores_censo
ticket_teto       = renda_pc * param("ticket_renda_pct_premium")   # 0.15
ticket_mercado    = mediana(ticket dos concorrentes do bairro)     # A3 planos_precos (âncora-bairro)
headroom_premium  = ticket_teto - ticket_mercado                   # R$/mês
headroom_ratio    = ticket_teto / ticket_mercado                   # x (adimensional)
```
Veredito de posicionamento (DETERMINÍSTICO, cutoffs param):
| condição | veredito | leitura |
|---|---|---|
| `headroom_ratio ≥ param("headroom_ratio_oceano_azul")` (2.0) **e** densidade premium baixa | **OCEANO_AZUL** | bairro rico mal-atendido — posicione Premium/boutique |
| `headroom_ratio ≥ param("headroom_ratio_transicao")` (1.2) | **TRANSICAO** | espaço p/ subir ticket/serviço |
| senão | **VERMELHO** | atendido no preço certo — competir por serviço, não preço |

Exemplo Cocó: ticket_teto ≈ 5027×0.15 = R$754; concorrentes ~R$100 (Smart Fit/low) → ratio 7,5 → **OCEANO_AZUL premium**.

### 3. Renda de catchment (refino, fase 2) — `renda_catchment_pc`
Academia capta de fora do bairro. Pondera renda dos bairros no raio por distância:
```
renda_catchment_pc = Σ(renda_pc_vizinho * peso_distancia) / Σ pesos
```
Usa os mesmos anéis/raio já em `parametros_metodologia` (anel_peso_*, raio_fronteira_km). Corrige bairro rico que puxa de vizinhança média.

## Params novos (todos categoria `calibracao`, sourced)
| chave | valor | nota |
|---|---|---|
| `renda_percentil_premium` | 0.75 | quartil superior da cidade |
| `renda_percentil_mid` | 0.40 | acima da mediana |
| `headroom_ratio_oceano_azul` | 2.0 | teto sustentável ≥ 2× ticket de mercado |
| `headroom_ratio_transicao` | 1.2 | folga moderada |
| `densidade_premium_max_oceano_azul` | (a calibrar) | nº/densidade de concorrentes premium no raio p/ confirmar gap |

`ticket_renda_pct_premium` (0.15) já existe. Cutoffs recalibráveis na tabela Supabase.

## Dados / espelho
Tabela Supabase `ipece_renda_bairro`:
`bairro · cidade · uf · renda_domiciliar · media_moradores · renda_pc (derivada) · renda_percentil · ranking · ano=2022 · fonte='IPECE Informe 272'`.
Loader: parse do PDF 272 (tabela 121 bairros) → upsert. (Caminho fino/setor descartado: pipeline consome por bairro; renda por setor 2022 não está em API pública do IBGE — só IPECE atrás de portal interativo.)

## Onde pluga
- **Novo** `tools/posicionamento_renda.py`: `avaliar_posicionamento(bairro, cidade, uf, ticket_concorrentes, densidade_premium) -> {renda_pc, renda_percentil, ticket_teto, ticket_mercado, headroom_premium, headroom_ratio, veredito_posicionamento, fonte}`. Determinístico, param-sourced.
- **A9 PositioningStrategist**: consome o `veredito_posicionamento` da tool (NÃO chuta OCEANO_AZUL/VERMELHO); LLM só redige a narrativa ERRC.
- **A4 FinancialEstimator**: `_tier_mercado_por_renda` passa a usar `renda_percentil`.
- **bairro_renda_loader**: renda do bairro passa a vir do IPECE 2022 (per capita derivada), CKAN 2010 vira fallback rotulado. Mantém coerência com perfil A/B + `score_demografico`.
- Persistência: `relatorio_outputs.posicionamento_estrategico` (jsonb já existe).

## Plano de wire (fases)
1. Loader IPECE 272 (121 bairros) → tabela `ipece_renda_bairro` + seed params.
2. `bairro_renda_loader` lê IPECE (per capita 2022) > CKAN 2010 fallback. Re-roda perfil A/B + score com renda fresca.
3. `posicionamento_renda.py` (headroom + percentil) + testes determinísticos.
4. A9/A4 consomem o veredito determinístico. A9 instruction: narrativa só.
5. Catchment (fase 2, opcional).

## Questões abertas / calibração
- `densidade_premium_max_oceano_azul`: definir métrica (nº premium no raio vs param). Precisa do mix de ticket dos concorrentes (A3 `planos_precos`) confiável.
- `ticket_mercado`: quando A3 não traz planos_precos, usar fallback por `nivel_preco`/porte? Rotular confiança.
- Validar cutoffs de `headroom_ratio` contra casos reais (Cocó=azul, Genibaú=low/vermelho).
- IPECE 272 só Fortaleza. Outras cidades: CKAN/IBGE municipal como fallback até achar fonte local equivalente.
