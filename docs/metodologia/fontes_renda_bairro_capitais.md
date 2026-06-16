# Curadoria — Fontes de renda por bairro nas capitais (institutos/secretarias)

> Suporte ao wire multi-cidade da issue #3 (headroom de renda). Fortaleza já wired (IPECE 272).
> Padrão: **instituto estadual de planejamento/estatística** (equivalente do IPECE) é a fonte primária; **portal de dados municipal** é a secundária. IBGE direto NÃO publica renda por bairro/setor — cada instituto agrega do Censo 2022 no próprio ritmo.

## Legenda confiança
✅ confirmado bairro+renda Censo 2022 · 🟡 provável (instituto existe + tende a ter, **verificar**) · 🔵 fonte própria (não-Censo, ex. PDAD) · 🔴 só Censo 2010 no bairro · ⚪ improvável/sem instituto forte

## Capitais — mercado fitness prioritário
| Capital | UF | Instituto estadual (IPECE-equiv) | Portal municipal | Unidade "bairro" | Renda bairro 2022 | Fonte |
|---|---|---|---|---|---|---|
| **Fortaleza** | CE | **IPECE** | dados.fortaleza.ce.gov.br | bairro (121) | ✅ **wired** | [IPECE Informe 272](https://www.ipece.ce.gov.br/wp-content/uploads/sites/45/2025/08/ipece_informe_272_05_ago2025.pdf) |
| **Rio de Janeiro** | RJ | CEPERJ | **Data.Rio (IPP)** | bairro (164) | 🟡 provável | [Data.Rio Indicadores de Renda](https://www.data.rio/datasets?q=renda+bairros) · [Censo 2022 por bairros](https://www.data.rio/datasets/fd354740f1934bf5bf8e9b0e2b509aa9_2/about) (IPP agrega setor→bairro) |
| **São Paulo** | SP | **Fundação SEADE** | Infocidade / GeoSampa (SMUL) | distrito (96) | 🟡 provável | [SEADE Censo 2022](https://censo2022.seade.gov.br/) · Infocidade (renda por distrito) |
| **Brasília** | DF | **CODEPLAN** | — | Região Administrativa (35) | 🔵 PDAD (própria) | [CODEPLAN PDAD](https://www.codeplan.df.gov.br/pdad/) — renda por RA, bienal, não-Censo mas oficial |
| **Belo Horizonte** | MG | **Fundação João Pinheiro** | PBH / BHMap | bairro/RA | 🟡 verificar | FJP (foco municipal; bairro 2022 incerto) |
| **Curitiba** | PR | IPARDES | **IPPUC** | bairro (75) | 🟡 verificar | [IPARDES](https://www.ipardes.pr.gov.br/) · IPPUC (bairro) |
| **Porto Alegre** | RS | DEE/SPGG | **ObservaPOA** | bairro (94) | 🔴 só 2010 | [ObservaPOA](http://www.observapoa.com.br/) (Censo 2010 no bairro; 2022 pendente) |
| **Salvador** | BA | **SEI-BA** | Prefeitura/CGM | bairro | 🟡 verificar | SEI (Superint. Estudos Econômicos e Sociais BA) |
| **Recife** | PE | **CONDEPE/FIDEM** | dados.recife.pe.gov.br | bairro (94) | 🟡 verificar | Agência CONDEPE/FIDEM |
| **Goiânia** | GO | **IMB** (Mauro Borges) | — | bairro/região | 🟡 verificar | IMB |

## Demais capitais (institutos conhecidos)
| Capital | UF | Instituto/órgão | Renda bairro 2022 |
|---|---|---|---|
| Belém | PA | **FAPESPA** | 🟡 verificar |
| Vitória | ES | **IJSN** (Jones dos Santos Neves) | 🟡 verificar |
| São Luís | MA | **IMESC** | ⚪ improvável |
| Teresina | PI | Fundação **CEPRO** | ⚪ improvável |
| Manaus | AM | SEPLANCTI-AM | ⚪ improvável |
| Florianópolis | SC | IPUF (municipal) | ⚪ improvável |
| Natal/João Pessoa/Maceió/Aracaju | RN/PB/AL/SE | SEPLAG estaduais | ⚪ improvável (sem instituto forte) |
| Cuiabá/Campo Grande | MT/MS | SEPLAN / Semadesc | ⚪ improvável |
| Norte (AC/RO/RR/AP/TO) | — | SEPLAN estaduais | ⚪ improvável |

## Leitura
- **Só Fortaleza está pronto** (IPECE 272, bairro+renda Censo 2022). É a exceção, não a regra.
- **Próximos candidatos reais** (instituto forte + portal): RJ (Data.Rio/IPP), SP (SEADE/Infocidade), DF (CODEPLAN/PDAD). Esses 3 + Fortaleza cobrem os maiores mercados.
- **DF é caso especial:** unidade = Região Administrativa (não bairro), fonte = PDAD própria (não Censo). Tratar como granularidade equivalente.
- Granularidade varia: bairro (RJ/Fortaleza/POA), distrito (SP), RA (DF). O schema `renda_bairro` deve aceitar o rótulo de unidade local.

## Implicação pro wire (issue #3 multi-cidade)
1. Generalizar `ipece_renda_bairro` → `renda_bairro` (colunas: cidade, uf, unidade_label [bairro|distrito|ra], renda, renda_pc, percentil, ano, **fonte por cidade**).
2. `posicionamento_renda.renda_bairro_*` busca por cidade+unidade; sem dado → `sem_renda_local` → A9 cai no fallback municipal (IBGE Censo 2022 per capita, que já temos).
3. Carregar por capital conforme cada instituto for confirmado/parseado. Ordem de payoff: **RJ → SP → DF**, depois BH/Curitiba/Salvador/Recife.
4. Cada carga = 1 loader por fonte (formatos diferentes: PDF IPECE, CSV/GeoJSON Data.Rio, painéis SEADE, PDF/CSV PDAD). Não há padrão nacional — curadoria caso a caso.

## A confirmar (próximo passo de pesquisa, por cidade)
Para RJ/SP/DF: localizar o **arquivo/endpoint** exato (CSV/GeoJSON/XLSX) com renda por bairro/distrito/RA do Censo 2022 (ou PDAD), como feito com o PDF do IPECE 272.
