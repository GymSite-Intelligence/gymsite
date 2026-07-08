# docs/metodologia — índice e estado

> Auditoria da pasta em 2026-07-06. Três naturezas de artefato: **VIVO** (consultar e
> manter), **HISTÓRICO** (já executado — contexto), **ESTUDO** (material-fonte de decisão).

## VIVO — manter atualizado

| Doc | Assunto | Estado |
|---|---|---|
| `data_lineage.md` | Mapa fonte→tabela→consumidor (regra do carimbo) | ⚠️ atualizar: falta Wellhub (camada 3), lancamento_fetcher, catálogos MRLR |
| `gymsite_schema.md` | Schema no projeto compartilhado | ⚠️ atualizar ANTES da migração #23 (é o mapa do pg_dump) |
| `posicionamento_headroom_premium.md` | Spec do headroom de renda | ✅ implementado no A9 (status corrigido) |
| `fontes_renda_bairro_capitais.md` | Curadoria de fontes de renda por capital | ok — adicionar "verificado em" ao usar |
| `roadmap_dados_bq_sinergia.md` | 3 apontamentos ADOTAR (BQ) | ok — manter status por apontamento |
| `prompts/curador_rag_mercado.md` | Persona-portão do RAG público (LGPD) | ✅ versionada 2026-07-06 |

## HISTÓRICO / a decidir

- `agent_py_patch.md` — patch do A9 (já aplicado; movido para docs/handoffs/ quando conveniente).
- `VEC-378_MIGRACAO_OSM.md` — plano Maps→OSM. **Decidir**: possivelmente superado pelo
  SearchAPI (~4× mais barato); confrontar custo atual e promover a spec ou arquivar.
- ~~`a9_positioning_strategist.py`~~ — cópia de código REMOVIDA (2026-07-06): código não
  mora em docs; a fonte é `agents/a9_positioning_strategist.py` (histórico no git).

## ESTUDO

- `analise_melhorias_bq/` — tese das 4 disciplinas de dados + arquitetura BQ (fonte do roadmap).
- `fig1–3_*.png` — visuais de posicionamento/oceano azul/ERRC (maio/2026, material de pitch).
- `Guia de Engenharia de Prompt Eficaz.pdf` — guia base; **destilado ✅** em
  `prompts/guia_prompts_pipeline.md` (princípios aplicados aos nossos prompts, com
  exemplos reais do A3b/A6 e checklist de revisão pra PRs que mexem em prompt).

## Relacionados fora da pasta

- `docs/produto/AUDITORIA_RELATORIO_COCO.md` — memória de cálculo dos scores + fila de correções.
- `agents/specs/` — SPEC_OFERTA_AGREGADORES · SPEC_REFINO_LANCAMENTO_DETERMINISTICO ·
  SPEC_TENDENCIA_CNPJ_BAIRROS.
