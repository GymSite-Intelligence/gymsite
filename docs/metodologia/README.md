# docs/metodologia — índice e estado

> Auditoria da pasta. Três naturezas: **VIVO** (consultar e manter), **HISTÓRICO**
> (contexto), **ESTUDO** (material-fonte de decisão). Governança geral: `.agent/rules/P-000_REGRA_MESTRA_MUDANCA.md`.

## VIVO — manter atualizado

| Doc | Assunto | Estado |
|---|---|---|
| `data_lineage.md` | Mapa fonte→tabela→consumidor (carimbo P-000 §5) | ✅ jul/2026 — MRLR, agregadores, lancamento_fetcher; grounding A4 removido |
| `cvm-smartfit-bluefit-2025.md` | Evidência CVM/IR Smart Fit FY25 + Bluefit 9M25 (seed congelado) | ✅ 2026-07-13 — link P-000 §3 |
| `gymsite_schema.md` | Schema GymSite no Supabase compartilhado | ⚠️ nota schemas `gymsite`/`shared` — atualizar antes de pg_dump grande |
| `posicionamento_headroom_premium.md` | Spec headroom de renda | ✅ A9 |
| `ipm_mortalidade_migracao.md` | Matriz A–D + IPM (mortalidade × abertura × migração) | ✅ 2026-08-04 — Brasília parcial; migração RA = gap |
| `fontes_renda_bairro_capitais.md` | Curadoria renda por capital | ok — adicionar "verificado em" ao usar |
| `roadmap_dados_bq_sinergia.md` | 3 apontamentos ADOTAR (BQ) | ok — PNGs em `analise_melhorias_bq/` podem estar ausentes (só `.md` no repo) |
| `prompts/guia_prompts_pipeline.md` | Craft de prompt + Regra ZERO | ✅ canônico — espelhado P-000 §6 |
| `prompts/curador_rag_mercado.md` | Persona-portão RAG público (LGPD) | ✅ 2026-07-06 |
| `prompts/AUDITORIA_PROMPTS_ONDA1.md` | Fila correção prompts (A6 snake_case, scores) | ⚠️ aberto — task #24/#28 |

## HISTÓRICO / a decidir

- Patch A9 aplicado → `docs/handoffs/agent_py_patch_A9_APLICADO.md` (não `agent_py_patch.md` aqui).
- `VEC-378_MIGRACAO_OSM.md` — **parcial:** concorrentes = SearchAPI (não OSM/Places). Geo do Explorar = Nominatim + Valhalla/ORS. OSMnx fluxo pedestre ainda ativo.
- ~~`a9_positioning_strategist.py`~~ — cópia em docs removida; fonte `agents/a9_positioning_strategist.py`.

## ESTUDO

- `analise_melhorias_bq/diferencas_disciplinas_dados.md` — tese 4 disciplinas + BQ (fonte do roadmap).
- `Guia de Engenharia de Prompt Eficaz.pdf` — destilado em `prompts/guia_prompts_pipeline.md`.
- ~~`fig1–3_*.png`~~ — removidos desta pasta (dup em `docs/arquitetura/` ou pitch antigo).

## Relacionados fora da pasta

- `docs/produto/AUDITORIA_RELATORIO_COCO.md` — memória scores + fila correções.
- `agents/specs/` — SPEC_OFERTA_AGREGADORES · SPEC_REFINO_LANCAMENTO_DETERMINISTICO · SPEC_TENDENCIA_CNPJ_BAIRROS.
- `.agent/rules/P-000_REGRA_MESTRA_MUDANCA.md` — deploy (Wrangler + Cloud Run), domínios §8.
