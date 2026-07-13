# Verificação CVM / IR — Smart Fit & Bluefit (2025)

> Evidência de calibração (P-000 §3). **Não** é regra de governança — números desta janela.
> Auditoria: 2026-07-13. Seeds em `parametros_metodologia` **não** alterados nesta passada.

## Fontes

| Emissor | Documento | Janela | URL / acesso |
|---|---|---|---|
| Smart Fit (SMFT3) | Earnings Release 4T25 (PT) + call | FY 2025 / 4T25 | IR MZIQ — Resultados 4T25 |
| Bluefit | Informações contábeis intermediárias | **9M25 / 3T25** (DF FY25 completo **não** selado aqui) | IR MZIQ Bluefit |

Hierarquia: estes números = **proxy low-cost em escala**. Não extrapolar mid/premium/boutique. Mix “Outras” Smart Fit ≠ take rate Wellhub de academia independente.

## Smart Fit — confirmado

| Métrica | Valor | Base | Decisão seed |
|---|---|---|---|
| Clubes | 2.084 | fim 4T25 | — |
| Membros | 5,21 M | fim 4T25 (agregador **fora** da base de membros) | — |
| Membros / clube | ~2.500 | 5,21 M ÷ 2.084 | — |
| Receita líquida FY25 | R$ 7.241,7 M | earnings | — |
| EBITDA ajustado margem FY25 | **31,7%** | Adj. EBITDA R$ 2.292 M / RL | referência escala; **não** default unidade solo |
| EBITDA adj. margem 4T25 | 31,3% | R$ 610 M | — |
| Mix academias vs “Outras” | **~89% / ~11%** | clubs B2C vs TotalPass/FitMaster/etc. | **não** mapear como mix agregador independente |
| Ticket médio | **só +12% YoY** no 4T25 | release **sem** R$ absoluto | **não mudar** `ticket_low` (89,90) |
| Aluguel/ocupação caixa ÷ RL FY25 | **~19,1%** | Aluguéis ocupação (ex-IFRS bridge) 1.381,2 / 7.241,7 | stress escala; limiar `ocupacao_teto_low=12,5%` / sustentável 15% **ficam** |
| Densidade alunos/m² | **não no IR** | pesquisa usou hipótese 1.200 m² → 2,08 | **não mudar** `matr_m2_low_*` |

Check-in agregador (call): Brasil ~15% dos acessos médios 2025 (vs 11% anos anteriores) — tráfego, **não** % receita de parceiro Wellhub.

## Bluefit — 9M25 confirmado

| Métrica | Valor | Base | Decisão seed |
|---|---|---|---|
| Unidades 3T25 | 184 (129 próprias + 55 franquias) | intermediárias | Exame cita 215 depois — fora desta tabela |
| Alunos ativos 3T25 | 517,4 mil | intermediárias | ~2.800 / unidade |
| Receita líquida 9M25 | R$ 405,8 M | intermediárias | — |
| Pagamentos arrendamento ÷ RL 9M | **~19,0%** | 76,97 / 405,8 | alinha Smart ~19% |
| EBITDA ex-IFRS margem 9M | **16,0%** (3T25: 18,7%) | intermediárias | proxy; FY “18,3%” de pesquisa secundária **não** selado |
| Ticket absoluto | sem R$ CVM nesta passada | — | **não seedar** |

## Pesquisa secundária — rejeitar / aguardar

| Claim | Motivo |
|---|---|
| Ticket Smart Fit R$ 114,50 | Vintage 1T23; 4T25 só publica variação % |
| Densidade 2,08 / 1,76 alunos/m² | Assume área média não publicada no IR |
| Bluefit FY RL R$ 550 M · aluguel 19,35% · 215 un · 493 k alunos | Aguardar DF FY25; 9M já sustenta ~19% arrendamento |
| Take rate 90% / PECLD 0,05% no motor de bairro | Blog / PECLD consolidado ≠ inadimplência independente |
| Mix 11% agregador no A4 independente | “Outras” Smart Fit inclui TotalPass própria |

## Decisão P0-3 (jul/2025)

**Nenhum seed alterado.** Manter ACAD/DEFAULTS em `tools/parametros_metodologia.py`.

Uso permitido dos números CVM:

1. **Narrativa / alerta** — stress aluguel low-cost escala ≈19% vs teto alerta 12,5–15%.
2. **Teto de referência** — margem EBITDA rede ≠ expectativa de unidade independente.
3. **Próxima calibração** — só com ticket/m²/área **absolutos** no IR ou DF FY Bluefit fechado.

## Relacionados

- Regra: `.agent/rules/P-000_REGRA_MESTRA_MUDANCA.md` §3 (benchmarks financeiros)
- Seeds: `tools/parametros_metodologia.py`
- Mapa: `docs/metodologia/data_lineage.md` (hierarquia CVM → ACAD)
