# SPEC — A2 DemoAnalyst store / latência v2

---
id: spec-a2-store-v2
agente: DemoAnalyst
versao: 2.0
data: 2026-07-16
fonte: agents/a2_demo_analyst.py
diagrama: agents/specs/SPEC_a2_store_v2.mmd · agents/a2_demo_analyst.mmd
---

## 1. Forma

**BaseAgent** determinístico (sem LLM). Macro: `analise_demografica_completa` (+ opcional perfil sexo×idade + densidade setor).

Retest `6bb90ff7`: **7,8s** — não é long-pole.

## 2. Granularidade

| Passo | Fonte | Store histórico? | Nota |
|---|---|---|---|
| pop / faixa / renda muni | IBGE REST / espelho | semi (`renda_bairro` + censo) | CPU+HTTP curto |
| `enrich_demografia_bairro` | `renda_bairro` IBGE 2022 → CKAN → piloto | **sim** | alinhado bundle |
| `perfil_sexo_publico_fitness` | BQ/espelho | semi | best-effort |
| `demografia_setor_censo` | `censo_setor` | **sim** | flag `A2_FONTE` |
| insights | template Python | — | zero LLM |

## 3. Dívida

Score ainda pode misturar CKAN 2010 no path legado (comentário no agente). Bundle A0 já prioriza bairro; A2 deve consumir mesma `renda_bairro` (já faz via enrich).

## 4. Act-on

Nenhum urgente pra wall-clock. Opcional: documentar carimbo renda no score; alinhar SPEC_A2 com IBGE 2022 only.
