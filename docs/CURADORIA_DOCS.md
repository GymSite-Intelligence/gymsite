# Curadoria da pasta `docs/` — veredito por arquivo

> Data: 2026-06-22. Total varrido: 182 arquivos. Decisão por arquivo: **INGEST** (em qual store/
> agente) · **KEEP-DEV** (fica no repo, não vira RAG) · **DELETE** (candidato — você confirma).
> ⚠️ Nada foi deletado: deleção é destrutiva → você clica.

## 🔴 Alerta de vazamento (ler antes de ingerir)
O agente **Mercado roda na landing PÚBLICA** (degustação, prospect anônimo). Vários `analise_*`
são **inteligência interna do GymSite** (posicionamento, preço, ERRC, análise de concorrentes
SaaS). **Ingerir isso no store público `gymsite-market-docs` VAZA estratégia pro cliente.**
→ Recomendo **2 baldes**:
- `gymsite-market-docs` (público) = só **fato de mercado neutro** (franquias, demografia, dores do setor).
- **store nova `gymsite-consultor-docs`** (interno) = BI/estratégia, usada só pelo **consultor logado** — nunca pela degustação.

---

## ✅ INGEST — conhecimento de domínio

### A) `gymsite-market-docs` (PÚBLICO — Mercado/Regulatório, seguro p/ degustação)
| arquivo | motivo |
|---|---|
| docs/arquitetura/mapeamento_franquias_academia_brasil.md | Panorama 15 redes de franquia (fato público) |
| docs/arquitetura/faixa_ouro_3645_estrategia.md | Oportunidade demográfica 36-45 (dado de setor) |
| docs/arquitetura/analise_mercado_fitness_fortaleza.md | Dores/gaps reais do mercado local |
| docs/arquitetura/comunicacao_dados_fitness.md | Como comunicar viabilidade com dado (genérico) |

### B) `gymsite-consultor-docs` (INTERNO — só consultor logado, NÃO degustação)
| arquivo | motivo |
|---|---|
| docs/arquitetura/analise_gymsite_posicionamento.md | Posicionamento próprio do GymSite |
| docs/arquitetura/POSITIONING_FRAMEWORK.md | ERRC/oceano azul do GymSite |
| docs/arquitetura/analise_precificacao_oceano_azul.md | Estratégia de preço |
| docs/produto/PESQUISA_PRICING_BENCHMARK.md | Pricing de concorrentes + decisão de tier |
| docs/arquitetura/analise_competitiva_cortex_intelligence.md | Análise de concorrente SaaS |
| docs/arquitetura/analise_metodologia_pedro_matteucci.md | Metodologia comercial de venda |
| docs/arquitetura/INTELIGENCIA_COMPETITIVA_FITNESS.md | Inteligência competitiva do setor |
| docs/arquitetura/apendice_monitoramento_integrado.md | Monitoramento de reputação (método) |
| docs/arquitetura/apendice_pe_faixaouro_comunicacao.md | Inteligência faixa-ouro (interno) |

### C) `gymsite-obra-docs` (Arquiteto/Engenheiro) — já ingerido
| arquivo | status |
|---|---|
| docs/agente/agentes_site/rag/engenharia_obra_academia_ref.txt | ✅ ingerido hoje |
| docs/agente/agentes_site/rag/engenharia_layout_academia_ref.txt | ✅ ingerido hoje |
| docs/arquitetura/CATEGORIAS_TAREFAS.md | candidato — processo real de abertura (3 tipos) |

> `INGEST:equip` (Técnico): **nenhum doc novo** — o catálogo já cobre. (FRETE_BENCHMARK era frete da Vectra, não academia → ver DELETE.)

---

## 🗑️ DELETE — candidatos (confirma antes; eu não deleto)

### Binários inúteis pra RAG / bloat
| arquivo | motivo |
|---|---|
| docs/Estudo.zip | zip binário |
| docs/agente/gymsite_agents.zip | handoff frontend já consumido |
| docs/arquitetura/Kimi_Agent_Zonas especiais Fortaleza.zip | zip binário |
| docs/metodologia/Analise de melhorias BQ.zip | zip binário |
| docs/agente/index.pdf | untracked, origem desconhecida — confirmar |

### Ebooks / PDFs irrelevantes (provável copyright, fora de escopo)
| arquivo | motivo |
|---|---|
| docs/arquitetura/Manual-Vibe-Coding.pdf | manual de coding, off-topic |
| docs/arquitetura/BENNY MATHIASON LEWI PRO2022.pdf | origem/uso desconhecidos |
| docs/arquitetura/[eBook] - BRAND - Gestão de Reputação na Era da IA Generativa.pdf | ebook genérico |
| docs/arquitetura/[eBook] Planejamento de Vendas B2B...2026.pdf | ebook genérico |

### Duplicatas
| arquivo | motivo |
|---|---|
| docs/mapeamento_franquias_academia_brasil.md | dup de docs/arquitetura/mapeamento_franquias_academia_brasil.md |
| docs/mapeamento_franquias_academia_brasil.pdf | dup (PDF) do .md |
| docs/metodologia/fig1_*.png · fig2_*.png · fig3_*.png (11 arquivos) | dups dos mesmos fig*.png em docs/arquitetura/ |
| docs/metodologia/a9_positioning_strategist.py | cópia velha de agents/a9_positioning_strategist.py |

### Transitórios / fora de escopo
| arquivo | motivo |
|---|---|
| docs/reference/chat-export-1780439081874.json | export de chat transitório |
| docs/FRETE_BENCHMARK.md | frete ANTT da Vectra Cargo — não é academia |

---

## 📌 KEEP-DEV (fica no repo, NÃO vira RAG)
Todo o resto (~100 arquivos): specs de pipeline (PIPELINE_AGENTES, DETERMINIZACAO_NARRADOR_A9,
SPEC_*), deploy/infra (DEPLOY_GCP_CLOUDFLARE, GITHUB_ACTIONS_SETUP, CLOUDFLARE*, VERTEX_SETUP,
GOOGLE_MAPS_SETUP), PRDs e planos (MVP-PRD, PLANO_*, PLAN_*, produto/*), integrações (INTEGRACAO_VECTRA,
INTEGRATION_KIMI, HANDOFF_*), schema/dados (SCHEMA_USER_PROJECT, COMPILADO_FONTES_DADOS, data_lineage,
fontes_renda_bairro_capitais), telemetria/custo (TELEMETRIA_E_SANITIZACAO, GOVERNANCA_CUSTO,
AUDITORIA_CUSTO_LLM, POLITICA_CUSTOS), A9_*_SPEC/design, código .py (docs/gymsite_a0_kimi_adapter,
gymsite_a8_validator), SQL, mockups, langcache-api.yaml, csv de séries. São doc/infra interna —
úteis ao time, irrelevantes/ruidosos como conhecimento de RAG.

> Charts `.png` em docs/arquitetura/ e docs/metodologia/analise_melhorias_bq/: KEEP-DEV (assets de
> relatório). Os duplicados entre as duas pastas → ver DELETE.
