# Comparativo CUB x SINAPI - golden states

**UFs pareadas:** 27
**Ratio CUB/SINAPI:** media 1.062 | desvio 0.0095 | faixa [1.0478 - 1.0828]
**Delta% medio (CUB acima SINAPI):** 6.2%
**Obra adaptacao (SINAPI x 0.19) / CUB:** media 17.9% | fator implicito 0.1789

## Top 5 custo m2
- CUB: AC, SC, RJ, RO, RR
- SINAPI: AC, SC, RJ, RO, RR
- Overlap: 5/5 (AC, RJ, RO, RR, SC)

## UFs ancora (piloto CE/PR)

| UF | CUB | SINAPI | Ratio | Delta% | Obra mid | Obra/CUB% |
|---|---:|---:|---:|---:|---:|---:|
| CE * | 1969.47 | 1832.26 | 1.0749 | 7.49% | 348.13 | 17.7% |
| SP | 2205.1 | 2037.2 | 1.0824 | 8.24% | 387.07 | 17.6% |
| PR * | 2224.42 | 2098.17 | 1.0602 | 6.02% | 398.65 | 17.9% |
| RJ | 2290.75 | 2161.7 | 1.0597 | 5.97% | 410.72 | 17.9% |
| MG | 1955.9 | 1849.04 | 1.0578 | 5.78% | 351.32 | 18.0% |
| DF | 2097.04 | 1982.79 | 1.0576 | 5.76% | 376.73 | 18.0% |
| SC | 2374.61 | 2199.78 | 1.0795 | 7.95% | 417.96 | 17.6% |
| PE | 1869.49 | 1726.51 | 1.0828 | 8.28% | 328.04 | 17.5% |
| BA | 1960.63 | 1853.68 | 1.0577 | 5.77% | 352.2 | 18.0% |
| RO | 2288.14 | 2123.43 | 1.0776 | 7.76% | 403.45 | 17.6% |

## Leitura rapida
- CUB sistematicamente **5-8% acima** do SINAPI m2 na mesma UF.
- Ratio CUB/SINAPI **estavel** entre UFs (desvio ~1%).
- Obra adaptacao atual (SINAPI x 0,19) ~ **17,5-18% do CUB** -- trocar regua para CUB x 0,19
  elevaria obra ~**7,5%** sem recalibrar fator.

*Fontes: `data/cub_pilot/cub_estadual_golden.json` + SINAPI snapshot golden/fixture.*
