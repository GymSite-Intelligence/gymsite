# Design — Ops P0 (geocode hard gate + CUB PR + carimbos + ingest BR)

**Data:** 2026-08-06  
**Âmbito:** Manter fresco/honesto o que muda número no relatório — sem fila nacional de bundles nem sector intel  
**Humano:** Marcelo  
**Abordagem:** Um spec, **3 waves** de implementação  
**Depende de:** `docs/PLAN_HETZNER_VPS_TUNNEL.md` (sair do Cloud Run); ingest CNPJ baixadas já entregue; VEC-378 OSM = **spec separada** (não é Spec C); Spec C polígono bairro = `2026-08-06-spec-c-bairro-poligono-ibge-design.md`

---

## 1. Problema (produto)

1. Se o mapa não achar o ponto do bairro, o bundle ainda sobe — população some e quase ninguém percebe.
2. CUB (R$/m² obra por UF) é tabela manual; sem gate, CAPEX envelhece quieto.
3. PDF/tela ainda sugerem “população oficial do bairro” quando o número é raio em volta do centróide; distrito (SP etc.) pode aparecer como “bairro”.
4. CNPJ/CNO fresco ainda é manual; Google Cloud (hospedeiro) está em depreciação; Receita costuma bloquear download fora do Brasil.
5. Não há alarme se espelhos de renda/PIB/censo (pré-requisito MRLR) sumirem ou envelhecerem.

**Spec B grande (loop mensal CNPJ/CNO + health como projeto isolado):** morta. Residual vira Wave 3 deste P0.

---

## 2. Meta / fora de escopo

### Meta

Pacote ops P0: geocode honesto, CUB com PR+validação, carimbos PDF+front, ingest RFB em VPS Brasil disparado por Supabase, health de espelhos.

### Fora

| Item | Destino |
|---|---|
| Fila nacional de bundles (eixo A) | Spec depois |
| Sector intel URLs→JSON | Spec depois |
| Polígono bairro IBGE (A2+A3a) | **Spec C** — `2026-08-06-spec-c-bairro-poligono-ibge-design.md` |
| Migração OSM / Nominatim primário (VEC-378) | Spec separada (geocode; ≠ Spec C) |
| Scrape automático SindusCon/CUB | Fora (não vale no P0) |
| Novo serviço Cloud Run / gcloud | Fora (GCP depreca) |
| Helper carimbo compartilhado (lib única) | Fora v1 — alinhar PDF+front por contrato de texto |
| IPM completo / migração MCMV | Já fora do ingest baixadas |

---

## 3. Decisões aprovadas

| # | Escolha |
|---|---------|
| Empacotamento | Um spec, 3 waves (W1 → W2 → W3) |
| Spec B grande | Morta; residual = W3 |
| Geocode | **Hard gate:** fail → job falha/alerta; não publica bundle cego |
| OSM | Depois (VEC-378, ≠ Spec C); W1 usa fluxo geocode atual |
| CUB | **PR mensal** + validação `cub_m2`; sem scrape |
| Carimbos | **PDF + front** (`ContextoMercadoCard` / demografia) |
| Cron | Supabase `pg_cron` = **despertador** HTTP (não executa Python) |
| Executor RFB/CNO | **VPS Brasil** (Hostinger NVMe ok; marca não travada no spec) |
| API cutover Cloud Run | Plano Hetzner/túnel separado; W3 não exige API já no BR |
| Scrape CUB | Não |

---

## 4. Waves

### Wave 1 — Geocode hard gate + carimbos

**Geocode (batch / `build_market_bundles`)**

- Sem `lat`/`lng` válido após `geocode_endereco` → job da praça **falha** (ou batch aborta aquela unidade com exit ≠ 0 / alerta).
- Bundle **não** é publicado “mudo” (sem demografia de censo fingindo ok).
- Stamp explícito se necessário em logs/`missing_fields`: `geocode_bairro`.
- Unificar caminho de fallback com política já existente (`MAPS_FALLBACK`); documentar default real no código vs `.env.production.example` (corrigir contradição doc).
- OSM Nominatim como **primário** = fora desta wave.

**Carimbos (PDF + front)**

- População: nunca “oficial do bairro” sem base; texto = raio do centróide · N setores · IBGE Censo 2022 (espelhar espírito de `DemografiaBairroCard` / `censo_setor` `granularidade`).
- PDF: remover/reescrever rótulos tipo “Valor (fonte real do bairro)” / “População (bairro)” quando a base for raio.
- Distrito/RA: quando fonte indicar distrito (SP etc.), UI/PDF expõem **distrito** (ou unidade correta), não “bairro” genérico mentiroso.
- `ContextoMercadoCard` CNPJ: cada métrica exibida com fonte + janela/`as_of` (P-000 valor · base · fonte · janela ou equivalente visível).

**Exemplo de uso:** relatório Cocó deixa de sugerir “60 mil no bairro” e mostra “~60 mil · N setores · raio Xm · IBGE 2022”.

### Wave 2 — CUB PR mensal + gate

- Fonte canônica: `data/cub_pilot/cub_estadual_golden.json` (cache `metrics/cache/cub_estadual.json` opcional depois; sem scraper).
- Fluxo: humano (ou script assist **não** publicador) atualiza JSON → PR → gate CI/teste:
  - 27 UFs presentes
  - `cub_m2` > 0
  - `periodo_ref` / `data_coleta` dentro de janela aceitável (ex. ≤ N meses; MS atrasado deve falhar ou exigir nota explícita de proxy)
  - Ratio CUB/SINAPI na faixa histórica (~1.05–1.08; ver `docs/pesquisa/CUB_SINAPI_GOLDEN_REPORT.md`)
- A4 continua `OBRA_REGUA=cub` com fallback SINAPI + `regua_fallback` explícito se UF ausente.
- **Sem** loop scrape SindusCon.

### Wave 3 — Ingest RFB/CNO + health

**Arquitetura**

```
pg_cron (Supabase)  --HTTP X-Cron-Secret-->  endpoint na VPS Brasil
                                              └─ rfb_cnpj_fitness_loader (+ baixadas)
                                              └─ rfb_cno_loader (fresco)
```

- Reusar padrão `gymsite.cron_http_targets` + `internal_cron` (como weekly-market-batch).
- Executor **não** é Postgres; **não** é Cloud Run novo.
- VPS Brasil: Hostinger NVMe 4 (só ingest) ou NVMe 8 (se API+ingest na mesma caixa) — sizing na implementação; IP BR é o requisito.
- GHA US `monthly-receita-batch` (CNO BQ histórico): não fingir “fresco”; docs/nome alinhados.

**Mirror health**

- Job ou endpoint: mínimos de linhas + idade/`as_of` para `renda_bairro`, `municipio_pib`, `censo_setor` (e opcional CNPJ/CNO).
- Falha → alerta (não silêncio antes do relatório depender do espelho).

---

## 5. Critérios de aceite

### Wave 1

- [ ] Geocode fail no batch → não publica bundle cego; falha/alerta observável
- [ ] PDF sem rótulo “população do bairro / fonte real do bairro” sem base de raio/setores
- [ ] Front demografia + `ContextoMercadoCard` alinhados ao contrato de carimbo
- [ ] Distrito não rotulado só como “bairro” quando a unidade for distrito

### Wave 2

- [ ] Teste/gate recusa golden CUB incompleto ou `cub_m2` inválido / ratio fora da faixa
- [ ] Caminho documentado: PR mensal → merge → A4 lê golden
- [ ] Nenhum scraper SindusCon no escopo

### Wave 3

- [ ] Cron Supabase dispara HTTP autenticado para host BR
- [ ] Host BR roda loaders CNPJ (com baixas) + CNO fresco com sucesso em smoke
- [ ] Health de espelhos MRLR falha de forma visível se row-count/`as_of` ruim
- [ ] Zero novo deploy gcloud para este P0

---

## 6. Ordem de implementação

1. **W1** — código only; não bloqueia em VPS  
2. **W2** — gate CUB + runbook PR mensal  
3. **W3** — endpoint + migration cron + bring-up VPS BR + health  

OSM (VEC-378) e fila bundles (A) só depois deste P0.

---

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Hard gate derruba muitas praças se Maps `REQUEST_DENIED` | Corrigir key/fallback documentado; gate revela problema em vez de esconder |
| VPS BR ainda não provisionada | W1/W2 avançam; W3 blocked até IP BR |
| Hetzner EU ≠ BR | API pode ir pra Hetzner; ingest RFB precisa BR ou JSON pré-processado |
| CUB PR esquecido | Gate + lembrete runbook; SINAPI fallback com carimbo |

---

## 8. Referências

- `docs/metodologia/VEC-378_MIGRACAO_OSM.md` — fora deste P0  
- `docs/PLAN_HETZNER_VPS_TUNNEL.md` — cutover API  
- `docs/pesquisa/CUB_SINAPI_GOLDEN_REPORT.md` — faixa ratio  
- `db/migrations/20260727_market_batch_supabase_cron.sql` — padrão cron HTTP  
- `docs/superpowers/specs/2026-08-05-cnpj-json-ingest-baixadas-design.md` — baixadas já no espelho  
- `.agent/rules/spec-self-review.md` — gate canônico de toda design spec  

---

## Self-review

**Data:** 2026-08-06  
**Resultado:** ok (após checklist)

| Check | Achado |
|---|---|
| Placeholder | Nenhum TBD/TODO aberto |
| Consistência | W1/W2/W3 alinhados às decisões (§3); Spec B morta = residual W3 |
| Escopo | 3 waves explícitas; OSM/fila bundles/scrape CUB/gcloud fora |
| Ambiguidade | Host = VPS BR (Hostinger ok); marca não travada — explícito |
| Aceite | Checklist por wave em §5 |
| Fora | §2 tabela + §5 “fora do pronto” |

Correções neste passo: só acrescentar esta seção (regra canônica adotada).
