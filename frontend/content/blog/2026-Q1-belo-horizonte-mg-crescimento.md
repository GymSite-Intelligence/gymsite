# Raio-X das Academias em Belo Horizonte (Q1 2026): Boom de Aberturas e o Alerta do “Vale da Morte” no 1º Ano

Por **GymSite Intelligence** | *Análise de Mercado B2B*  
**Ficha:** `data/processed/receita-blog/2026-Q1/belo-horizonte-mg.json` · CNAE 9313-1/00

---

Belo Horizonte iniciou 2026 como polo de expansão do setor de academias. Com **saldo líquido de +51** estabelecimentos no 1º trimestre, a capital mineira ficou na **2ª posição** do ranking de crescimento absoluto (Top 3 do trimestre na série GymSite).

Por trás de **61 aberturas**, a Receita também mostra alerta: **40% das academias baixadas no período fecharam com menos de 1 ano de vida** (`mortalidade_infantil_pct`).

---

## Destaques do trimestre

| Indicador | Valor (Q1 2026) |
| --- | --- |
| Parque ativo mapeado | 596 |
| Novas aberturas | 61 |
| Encerramentos (baixas) | 10 |
| Saldo líquido | **+51** (~**+8,6%** sobre o parque) |
| Taxa de entrada | **10,23%** do parque |
| Taxa de churn (baixas/parque) | **1,68%** |
| Densidade hab./academia (início → fim)* | **4.433 → 4.053** |
| Mediana de vida dos baixados | **2,27 anos** |
| Mortalidade &lt; 1 ano (entre baixados) | **40%** |
| Baixados com ≥ 5 anos | **30%** |

\*Densidade = população IBGE (espelho GymSite) ÷ parque estimado no início (`ativos − saldo`) e ÷ parque no dump (`ativos`).

---

## 1. Expansão e compressão da densidade

Para cada academia encerrada, abriram-se **mais de 6** CNPJs novos (61 ÷ 10).

A densidade caiu de **4.433** para **4.053** habitantes por academia: mais oferta no mesmo município, maior pressão competitiva por aluno.

> **E daí para o gestor?**  
> Erro de ponto ou de proposta de valor fica mais caro. Academia genérica sem diferenciação tende a sofrer mais na atração/retenção — interpretação de mercado, não causalidade prova da Receita.

---

## 2. “Vale da morte”: 40% não passam de 12 meses

Entre os **10** CNPJs baixados com datas válidas:

| Faixa de vida | Qtd | % |
| --- | --- | --- |
| &lt; 1 ano | 4 | 40% |
| 1–3 anos | 2 | 20% |
| 3–5 anos | 1 | 10% |
| ≥ 5 anos | 3 | 30% |

```
[< 1 Ano]    ████████████████████ 40%
[1–3 Anos]   ██████████ 20%
[3–5 Anos]   █████ 10%
[≥ 5 Anos]   ███████████████ 30%
```

**Hipóteses rotuladas** (não estão na ficha Receita — use como checklist de risco):

1. Capex/giro subdimensionados até maturar base de alunos.  
2. Ticket desalinhado da renda da micro-região.  
3. Pressão de redes low-cost no entorno.

Os **30%** de baixas com ≥ 5 anos apontam outro risco: obsolescência / falta de reinvestimento — de novo, hipótese de negócio, não atributo cadastral.

**Onda (3 meses):** jan 2 · fev 4 · mar 4 baixas — volume sobe no fim do trimestre, ainda baixo frente às aberturas.

**Bairros com ≥2 fechamentos no trimestre:** nenhum na ficha (sem cluster estável neste recorte).

---

## 3. Demografia e renda (GymSite / IBGE)

Status GymSite: **ok**.

- População (espelho PIB): **2.415.872**  
- PIB municipal (2023): **R$ 130,2 bi** · per capita ~**R$ 53.893**  
- Renda_pc mediana (471 bairros): ~**R$ 834**  
- Topo renda_pc: Senhor dos Passos (~R$ 13.736) · Belvedere (~R$ 8.302) · Savassi (~R$ 6.914)

### Onde encaixa o modelo?

| Perfil de praça | Leitura (interpretação) |
| --- | --- |
| Alta renda (ex. Belvedere, Savassi) | Boutique / studio / ticket alto |
| Renda perto da mediana municipal | Low-cost / high-value ou academia de bairro |

O contraste mediana × topo de renda é o insight demográfico utilizável no geomarketing — alinhar modelo ao bairro antes do Capex.

---

## Checklist GymSite para quem abre/expande em BH (2026)

1. Geomarketing do bairro: renda_pc + densidade de concorrentes (raio ~1,5 km).  
2. Capital de giro pensado para **12 meses**, não só obra/equipamento.  
3. Monitorar churn de alunos desde o dia 1 (CAC vs LTV) — disciplina operacional além do CNPJ.

---

*Post gerado a partir da ficha determinística + `metricas_calculadas`. Skill: `gymsite-blog-receita`. Números = Receita CNAE 9313100 + GymSite IBGE; hipóteses de causa marcadas como interpretação.*
