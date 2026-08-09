# Brasília no Q1 2026: 2ª em Baixas Absolutas — Mediana de Vida de 5,1 Anos e o Contraste de Renda por RA (PDAD 2024)

Por **GymSite Intelligence** | *Análise de Mercado B2B*

**Ficha:** `data/processed/receita-blog/2026-Q1/brasilia-df.json` · CNAE 9313-1/00 · ângulo **mortalidade** (rank 2)

**Fonte demográfica:** IPEDF CODEPLAN (PDAD Ampliada 2024 via [pdad.ipe.df.gov.br](https://pdad.ipe.df.gov.br/))

---

Brasília encerrou o primeiro trimestre de 2026 consolidando a **2ª posição nacional em encerramentos de empresas (17 baixas)** entre as capitais analisadas na série Top 3. Embora a capital federal apresente saldo positivo (**+14 academias**, fruto de **31 aberturas**), a dinâmica local é marcada por uma elevada rotatividade de CNPJs e por um cenário de **substituição em extremos opostos de renda**.

Com a integração dos dados atualizados de **35 Regiões Administrativas (RAs)** via PDAD 2024, fica evidente que o encerramento no DF não atinge aventureiros do primeiro ano, mas sim operadores consolidados enfrentando realidades econômicas muito distintas.

---

## Destaques

| Indicador | Valor (Q1 2026) |
| --- | --- |
| Parque ativo | 636 |
| Aberturas / Baixas / Saldo | 31 / 17 / **+14** |
| Taxa de entrada | **4,87%** |
| Taxa de churn | **2,67%** |
| Densidade hab./academia | **4.818 → 4.712** |
| Mediana de vida (baixados) | **5,14 anos** |
| Mortalidade &lt; 1 ano | **5,88%** |
| Baixados ≥ 5 anos | **52,94%** |

---

## Movimento e onda

Enquanto o Rio de Janeiro registrou churn de 0,79% e São Paulo de 1,28%, Brasília atingiu **2,67% de churn trimestral** — a mais elevada da série Top 3 (BH 1,68%).

A relação de **1,8 abertura para cada baixa** indica disputa acirrada por alocação de espaço e migração de alunos, não boom virgem.

**Onda:** jan 6 · fev 6 · mar 5 — ritmo estável (ajuste estrutural, não sazonalidade atípica).

**Clusters de bairro (n≥2):**

| Bairro / RA | Baixas | Mediana vida | Renda pc RA (PDAD 2024) | Diagnóstico |
| --- | --- | --- | --- | --- |
| Asa Norte → Plano Piloto | 2 | **4,08 anos** | **R$ 8.654** | Maturidade média — fricção em zona de alto poder aquisitivo |
| Samambaia Sul → Samambaia | 2 | **7,20 anos** | **R$ 680** | Saída tardia — infraestrutura veterana em RA de renda baixa |

> **E daí?** Mortalidade infantil baixa (**5,88%**) vs BH (**40%**): no DF o alerta é **saída de operadores estabelecidos**. Clusters com n≥2 estão em **polos opostos de renda** — renovação no Plano Piloto vs fadiga low-cost na periferia administrativa.

---

## Vida dos baixados (n=17)

| Faixa | Qtd | % |
| --- | --- | --- |
| &lt; 1 ano | 1 | 5,88% |
| 1–3 anos | 4 | 23,53% |
| 3–5 anos | 3 | 17,65% |
| ≥ 5 anos | 9 | 52,94% |

Mediana **5,14 anos**. Mais da metade das saídas ≥ 5 anos — fator de encerramento = perda de competitividade / falta de reinvestimento em unidades veteranas.

---

## Demografia (GymSite / PDAD)

- Pop: **2.996.899** · PIB 2023: **R$ 365,7 bi** · per capita ~**R$ 122.016**
- **Renda por RA (PDAD Ampliada 2024):** **35** RAs no espelho `renda_bairro` · mediana municipal **R$ 1.410** pc
- **Top 3 pc:** Lago Sul **R$ 12.500** · Sudoeste/Octogonal **R$ 10.104** · Lago Norte **R$ 9.534**
- Plano Piloto (Asa Norte/Sul): **R$ 8.654** · Samambaia: **R$ 680**
- Aliases Receita: Asa Norte/Sul → Plano Piloto; Samambaia Sul → Samambaia

Fonte: IPEDF CODEPLAN — mediana ponderada `renda_domiciliar_pc_r` (jul/2024).

> **Ressalva metodológica:** renda no DF é por **Região Administrativa (PDAD 2024)**, não por bairro Receita 1:1. Asa Norte/Sul mapeiam para Plano Piloto; Samambaia Sul para Samambaia. **Não confundir a mediana municipal (R$ 1.410) com ticket no Lago Sul ou no Plano Piloto** — use a RA do cluster.

---

## Interseção de mercado (mortalidade × abertura × migração)

**Status do quadrante:** C — Ilusionismo (saturação competitiva)

- **Mortalidade:** **ALTA** (Churn 2,67% · saída concentrada em veteranos ≥ 5 anos (52,94%))
- **Abertura:** **ALTA** (Entrada 4,87% · 31 unidades)
- **Adensamento (proxy MCMV):** **ALTA** — 25 empreendimentos · **6.863 UH** entregues (subsidiado)
- **IPM:** **124,8** (sinal vermelho &lt; 500) · `migracao_fonte=mcmv_proxy`

> **Diagnóstico:** alta rotação de CNPJs **com** estoque habitacional subsidiado relevante no município. Pelo proxy MCMV o numerador de demanda existe, mas o IPM baixo indica que aberturas/baixas absorvem (e excedem) o sinal de UH — típico de **Cenário C**: investidor vê “cidade que cresce” e entra em mercado já canibalizado. Densidade 4.818 → 4.712 reforça compressão de oferta.
>
> **Caveat:** IPM aqui usa **UH MCMV**, não saldo migratório demográfico. Thresholds 1500/500 são provisórios até calibração. Granularidade = município DF (não RA).

Fonte habitação: Min. Cidades `mcmv_subsidiado_20260630` · Spec: `gymsite/docs/metodologia/ipm_mortalidade_migracao.md`

---

## Checklist

1. Tratar Brasília como mercado de **renovação/substituição** (churn 2,67%) — captação via alunos de concorrentes desatualizados.  
2. Precificar com **RA PDAD**, não com média municipal única (R$ 680 ↔ R$ 12.500).  
3. Operações ≥ 4–5 anos: programar **retrofit** de layout/equipamentos para fugir da estatística de ~53% de saídas veteranas.

---

*Skill `gymsite-blog-receita`. Números = ficha; renda DF = PDAD 2024. PDF: `2026-Q1-brasilia-df-mortalidade.pdf`.*
