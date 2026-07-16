# Pipeline — Fontes Determinísticas e SearchAPI Primário (alwaysApply)

> Adotada jul/2026. Ler **ANTES** de mudar `agents/*.py`, `tools/*_tools.py`, macros do pipeline ou contratos de relatório.
> **Canônico completo:** [`.agent/rules/conferencia-fontes-pipeline.md`](conferencia-fontes-pipeline.md) (MRLR, site_agent, agents_site, A7 slot).
> Mapa vivo: [`docs/arquitetura/PIPELINE_AGENTES.md`](../../docs/arquitetura/PIPELINE_AGENTES.md) §7–§9.

## Princípios invioláveis

1. **SearchAPI primário** para Maps, reviews, listings e Instagram no caminho crítico. Places API = fallback explícito (`COMPETIDOR_MAPS_BACKEND`). Playwright/scrape = legado, flag off em prod.
2. **Número no relatório = tool ou banco**, nunca boca de LLM (P-000 §6). A0 override CNPJ; A4 aluguel = MRLR; demografia = IBGE. Mapa: `docs/metodologia/data_lineage.md`.
3. **LLM narra, não coleta dado estruturado** — exceções: A7 grounding; A3b planos (Gemini extrai de snippet SearchAPI). **Reviews A3a:** fetch+card = SearchAPI determinístico; Gemini só refina `categoria_dor` (fallback substring).
4. **Não bloquear gate do pipeline** — passo >60s cold (ex.: osmnx fluxo no A1) vai para A6 async, job pós-pipeline ou cache obrigatório.
5. **Carimbo P-010** em todo número exibido: valor · base · fonte · janela.
6. **Sem fallback fake** — fluxo pedestre: falha honesta `confianca:indisponivel`, nunca grid sintético com score inventado.

## Hierarquia rápida

| Dado | Fonte canônica |
|---|---|
| Concorrentes | SearchAPI `google_maps` |
| Reviews | SearchAPI `google_maps_reviews` + card det. (`_processar_review_card`); `topics[]` agregado (wire pendente); Gemini = refino `categoria_dor` |
| Oferta site/IG | httpx + SearchAPI `instagram_profile` |
| Imóveis candidato | `listing_cascata` (SearchAPI) — **não** alimenta aluguel |
| Aluguel viabilidade | `aluguel_mrlr.py` + `mrlr_modelo.py` (A4 Tier 0; **não** SearchAPI, **não** A7) |
| Aluguel referência batch | ~~removido jul/2026~~ | `tools/9_obsolete/` — viabilidade = MRLR |
| Demografia | IBGE Censo 2022 |
| CNPJ/CNO | RFB/Supabase |
| Fluxo pedestre | OSMnx + Overpass (exceção: não SearchAPI; 1× por relatório, preferir A6) |

## Documentos a revisitar sempre (junto com este arquivo)

| Quando | Ler |
|---|---|
| Novo agente ou macro no pipeline | `conferencia-fontes-pipeline.md` + `PIPELINE_AGENTES.md` + este arquivo |
| Aluguel / MRLR / site landing | `conferencia-fontes-pipeline.md` §2–§4 |
| Nova fonte externa / API | `CLAUDE.md` (fontes de dados) + §7 do PIPELINE_AGENTES |
| Feature espacial / fluxo | `agents/specs/SPEC_FLUXO_PEDESTRE.md` + §8 PIPELINE_AGENTES |
| Mudança UX de número | `.agent/rules/processo-mudanca.md` P-010 |
| Skill pipeline | `.cursor/skills/google-adk-agents/SKILL.md` |

## Checklist pré-merge (pipeline)

- [ ] Fonte primária = SearchAPI ou determinístico?
- [ ] Passo novo duplica fetch de agente posterior?
- [ ] Bloqueia A1 ou ParallelAnalysis?
- [ ] LLM introduzido? Justificado e listado em PIPELINE_AGENTES §6?
- [ ] `PIPELINE_AGENTES.md` §9 atualizado se gap novo?
- [ ] Teste falha antes do fix (`pytest` backend)?

## Dívidas abertas (jul/2026)

- **Fluxo no A1** — remover ou flag off; manter bloco A6 com competidores do state.
- **SearchAPI `topics[]`** — wired jul/2026 em `_fetch_reviews_bundle`.
- **Gemini `categoria_dor`** — off prod; `CLASSIFICAR_DORES_GEMINI=1` só p/ A/B.
- **Calibragem fluxo** Cocó golden vs smoke 26.7.
- **Auditoria Tools — `buscar_imoveis_texto`:** **Approved** + Act-on no código (empty≠Places; A1 listing só cascata). Deploy Cloud Run = Done prod. Ver [`auditoria-tools.md`](auditoria-tools.md).
