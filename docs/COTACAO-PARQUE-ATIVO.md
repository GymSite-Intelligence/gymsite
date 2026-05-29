# Cotação — Parque ativo (CNPJ) e segmentação

**Pedido:** trocar linguagem de “estoque” / “academias ativas” / “condicionamento físico” por **parque ativo** na experiência do produto; depois mapear **academia, estúdio pilates, box crossfit**, etc.

**Escopo técnico atual (dados):** tabela `cnpj_fitness_estabelecimentos` filtra CNAE **9313100** (RFB). Isso permanece na ingestão; só a **camada de produto** deixa de expor “condicionamento físico” ao usuário final.

---

## Fase 1 — Nomenclatura “parque ativo” (sem condicionamento físico na UI)

| Item | Entrega |
|------|---------|
| Chave canônica `parque_ativo_total` (+ alias legado `academias_ativas_cidade_cnpj`) | `tools/cnpj_fitness_tools.py`, A0/A6 |
| Panorama competitivo: `cnpj_parque_ativo_cidade` (+ alias) | `tools/competitor_tools.py` |
| Labels UI: “Parque ativo (município)”, “Novas unidades (90d)” | `ContextoMercadoCard`, `InteligenciaCompetitivaResumoCard` |
| Tipos TS + leitura com fallback | `useRelatorioDetail.ts` |

**Fora desta fase:** segmentação por tipo, mapa de concentração, narrativa A6 de dinâmica de mercado.

| Esforço | ~2–3 h |
| Status | **Concluída** (chaves + UI) |

---

## Fase 2 — Composição do parque por segmento

| Item | Entrega |
|------|---------|
| `classificar_segmento_cnpj(nome_fantasia, cnaes)` | novo módulo `tools/cnpj_segment_classifier.py` |
| Coluna `segmento_operacao` (migration) ou view materializada | Supabase |
| Agregados: `composicao_parque`, `novas_unidades_90d_por_segmento` | `resumo_cnpj_fitness()` |
| `segmento_operacao` em cada entrante | `listar_entrantes_cnpj_fitness()` |
| UI: chips/legenda por segmento na tabela de entrantes | `EntrantesCnpjTable` |

**Taxonomia (v1.9, sem "outro"):** `academia` \| `crossfit_box` \| `studio_pilates` \| `studio_funcional` \| `studio_bem_estar` \| `lutas` \| `personal_studio` \| `aqua_fitness` + `saude_clinica` (excluída da composição comercial).

**Validação em camadas:**
1. Heurística rica (typos ACADENIA, dança, fisio, etc.) + confiança alta/média/baixa
2. Opcional: `CNPJ_SEGMENT_PLACES_VALIDATE=1` → Google Places nos entrantes (90d)
3. Futuro: razão social via `Empresas*.zip` RFB

**Limitação documentada:** parque = unidades com CNAE 9313100; estúdios só com outro CNAE principal podem ficar de fora.

| Esforço | ~1–1,5 dia |
| Dependência | Fase 1 |
| Status | **Concluída** (classifier + API + UI) |

**Pós-deploy (Supabase):**
```bash
# 1) Aplicar db/migrations/20260528_cnpj_segmento_operacao.sql no projeto
# 2) Preencher coluna nos registros existentes:
python tools/cnpj_segment_backfill.py --cidade Fortaleza --uf CE
```
Sem a migration, segmentação funciona **on read** (nome/CNAE); a coluna acelera consultas futuras.

---

## Fase 3 — Mapa de concentração (zonas + segmento)

| Item | Entrega |
|------|---------|
| Agregação por CEP prefixo / zona cadastrada | tool `mapa_concentracao_fitness` |
| Geocode CEP (cache) | tabela `cnpj_geocode_cache` ou serviço existente |
| JSON `mapa_concentracao` no relatório | A6 + migration `relatorio_outputs` |
| Camada no mapa (cores por segmento) | reutilizar `MapaRelatoriosPage` |

| Esforço | ~2–3 dias |
| Dependência | Fase 2 |

---

## Fase 4 (opcional) — Análise de dinâmica de mercado

Cruzamento CNPJ + IBGE (A2) + saturação Places (A3) + Deep Research (A0); cenários determinísticos + parágrafo A6.

| Esforço | ~1 dia |
| Dependência | Fases 1–2 |

---

## Resumo de investimento

| Fase | O quê | Tempo |
|------|--------|-------|
| **1** | Parque ativo (copy + chaves) | **2–3 h** |
| **2** | Segmentação academia / estúdio / box | **1–1,5 d** |
| **3** | Mapa concentração | **2–3 d** |
| **4** | Dinâmica de mercado (opcional) | **~1 d** |

**MVP recomendado para relatório Fortaleza/Meireles:** Fase 1 + Fase 2 → re-rodar pipeline após carga CNPJ.

---

## Nota de produto

- **Parque ativo** = total de unidades no snapshot CNPJ (município), sem repetir “condicionamento físico” na interface.
- Detalhe técnico (CNAE 9313100) fica em tooltip/nota de rodapé ou documentação interna, não no título da métrica.
- **Saturação no raio** (Places) continua separada — não é “parque ativo”.
