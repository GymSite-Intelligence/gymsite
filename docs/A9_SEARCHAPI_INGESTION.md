# A9 — Ingestão dos JSONs do SearchAPI → Supabase

> Como alimentar o agente A9 com os JSONs de busca do SearchAPI, estruturando e cacheando os dados no Supabase (projeto <SUPABASE_PROJECT>). Ancorado no schema real existente (tabela `competidores` já presente). Complementa `docs/A9_DATA_CONFIDENCE.md`, `docs/A9_CHARTS_TABLES_SPEC.md` e `docs/A9_SKILLS_RELATORIO.md`.

## 1. Engines em uso e mapeamento por agente

| Engine SearchAPI | Sinal de negócio | Agente destino |
|---|---|---|
| `instagram_profile` | presença digital, seguidores, frequência de post, engajamento, locais marcados | A3 (competitor intel) |
| `google_maps_reviews` | reputação: rating, volume, recência, temas de insatisfação | A3 |
| `google_light` (planos/mensalidade) | faixa de preço praticada no mercado | A3b / A7 (qualitativo) |
| `google_light` (site:olx/vivareal — galpão/loja/salão alugar) | referência ORANGE de ocupação (snippet) | **não** A4 Tier 0 — viabilidade = MRLR |

## 2. Fluxo de ingestão (3 camadas)

```
SearchAPI (JSON) ──▶ [RAW] storage imutável ──▶ [NORMALIZE] adapter por engine
                                                        │
                                                        ▼
                                          [CANONICAL] feature store por praça/concorrente
                                                        │
                                                        ▼
                                                  A6/A8 valida ──▶ A9 consome
```

## 3. Camada RAW (imutável + cache)

Tabela de payloads crus, fonte de verdade e base do cache:

```sql
create table if not exists search_raw (
  id              uuid primary key default gen_random_uuid(),
  search_id       text unique not null,   -- search_metadata.id do SearchAPI
  engine          text not null,          -- instagram_profile | google_maps_reviews | google_light
  params_hash     text not null,          -- hash estável dos search_parameters (chave de cache)
  params          jsonb not null,         -- search_parameters
  payload         jsonb not null,         -- corpo completo do JSON
  relatorio_id    uuid,                   -- vincula à praça/relatório
  fetched_at      timestamptz not null default now(),
  expires_at      timestamptz             -- TTL para revalidação
);
create unique index if not exists ux_search_raw_cache on search_raw (engine, params_hash);
create index if not exists ix_search_raw_relatorio on search_raw (relatorio_id);
```

**Cache:** antes de chamar a API, consultar `(engine, params_hash)`; se existir e `now() < expires_at`, reutilizar o payload (evita as buscas repetidas — ex.: mesmo perfil consultado 12min/42min depois). TTL sugerido: reviews 7d, instagram 3d, preços 1d.

## 4. Camada NORMALIZE (adapters por engine)

Cada engine tem um adapter (estende o padrão de `pdf/adapters.py`) que extrai um schema canônico:

| Campo canônico | instagram_profile | google_maps_reviews | google_light |
|---|---|---|---|
| followers | profile.followers | — | — |
| posts_count | profile.posts | — | — |
| eng_rate | média(likes+comments)/posts | — | — |
| rating | — | média(reviews.rating) | — |
| rating_count | — | len(reviews) | — |
| review_recency | — | max(iso_date) | — |
| price_band | — | — | regex de mensalidade no snippet |
| rent_sqm | — | — | regex de aluguel/m² no snippet (ORANGE; **não** substitui MRLR Tier 0) |

Preços extraídos de snippet entram como **estimativa** (selo ORANGE), nunca como dado medido.
**Aluguel de viabilidade (OPEX)** no relatório = `aluguel_deterministico` / MRLR no A4 — ver `.agent/rules/conferencia-fontes-pipeline.md` §2.

## 5. Camada CANONICAL (já existe: tabela `competidores`)

O destino estruturado **já existe** no Supabase. A tabela `competidores` tem campos diretamente compatíveis:

| Coluna existente | Alimentada por |
|---|---|
| `nome`, `endereco`, `bairro_concorrente`, `place_id` | A1/A3 (identificação) |
| `rating_oficial` (numeric), `num_avaliacoes` (int) | google_maps_reviews |
| `reviews` (jsonb) | google_maps_reviews (amostra agregada/anonimizada) |
| `atividade_marketing` (jsonb) | instagram_profile |
| `oferta_mapeada` (jsonb) | google_light (planos/preços) |
| `tem_24h` (bool), `horarios_pico`/`pico_semanal` | derivados |
| `lat`, `lng`, `distancia_km` | A1 (geo) |
| `website`, `telefone`, `whatsapp_link` | google_light / A5 |
| `relatorio_id` (uuid) | chave de vínculo com a praça |

Ou seja: os adapters gravam direto em `competidores` (upsert por `place_id` + `relatorio_id`), mantendo o raw em `search_raw` para auditoria/cache. Insights consolidados podem ir para `ai_insights`.

## 6. Procedimento de upsert (idempotente)

```sql
insert into competidores (relatorio_id, place_id, nome, rating_oficial, num_avaliacoes, reviews, atividade_marketing, oferta_mapeada)
values (:relatorio_id, :place_id, :nome, :rating, :n, :reviews_jsonb, :ig_jsonb, :oferta_jsonb)
on conflict (relatorio_id, place_id) do update set
  rating_oficial = excluded.rating_oficial,
  num_avaliacoes = excluded.num_avaliacoes,
  reviews = excluded.reviews,
  atividade_marketing = excluded.atividade_marketing,
  oferta_mapeada = excluded.oferta_mapeada;
```
(Requer índice/constraint único em `(relatorio_id, place_id)` — verificar antes de aplicar.)

## 7. Confiabilidade e PII

- Cada métrica derivada carrega o `search_id` de origem + `fetched_at` → habilita os selos de confiança e o box metodológico (ver `A9_DATA_CONFIDENCE.md`).
- Recência importa: review/preço antigos rebaixam o selo de TEAL para ORANGE.
- **PII:** reviews e instagram trazem nomes de autores, `tagged_users`, `coauthors`. No campo `reviews`/`atividade_marketing` armazenar **agregados/anonimizados** (rating, temas, contagens) — não expor nomes individuais no PDF.

## 8. Orquestração

- Disparo via `agent_jobs` (tabela existente) por relatório/praça.
- Sequência: A1 resolve place_ids → dispara buscas → grava raw → adapters normalizam → upsert em `competidores` → A8 valida → A9 lê e gera o PDF.
- `ai_usage_tracking` registra custo/uso das chamadas SearchAPI.

---

*Especificação de arquitetura — DDL e nomes a confirmar contra o schema vigente antes de aplicar. Nenhuma credencial/segredo é incluída aqui. Nenhuma fonte real é citada no relatório final; dados são agregados pelos agentes A1–A9.*
