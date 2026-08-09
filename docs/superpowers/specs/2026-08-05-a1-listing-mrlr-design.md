# Design — A1 listing + MRLR (tapa lacuna pós-POI)

**Data:** 2026-08-05  
**Âmbito:** Pipeline A0–A9 — substituto do GeoScout POI morto  
**Humano:** Marcelo  
**Depende de:** `2026-08-04-top3-viabilidade-rank-design.md` + kill A1 macro (2026-08-05)

---

## Problema

A1 stub (`status=deprecated`, `candidatos=[]`) removeu lixo (POI âncora / Diadema / área 600).  
Lacuna: relatório sem **pontos reais** pra Top3. Spec Top3 assume lista bruta — lista vazia.

## Decisões

| # | Escolha |
|---|---------|
| Fonte de candidatos | **Só** `listing_cascata.buscar_candidatos_cascata` (SearchAPI google_light, bairro) |
| Onde vive o fetch | **A1** revive corpo (BaseAgent) — não A6 |
| Aluguel decisão | **Só MRLR** (`aluguel_deterministico`) — `price_raw` display only |
| Ranking Top3 | Spec Top3: `0.35×geo + 0.65×payback` no **A6** |
| POI macro | Continua **morta** (`analisar_pontos_comerciais_completo` fora do caminho) |
| Playwright | Continua off (`LISTINGS_PLAYWRIGHT` default) |
| Lista vazia | `status=ok_vazio` + aviso honesto — **não** inventar POI |

### score_geo sem GeoScout POI

Hardcoded `8.5` da cascata antiga = **proibido** (falsa precisão).

```text
geocode bairro 1× → (lat0, lng0)
se listing tem lat/lng:
  d = haversine_m(listing, centróide)
  score_geoscout = clamp(10 * (1 - d/2500), 0, 10)   # 0m→10, ≥2500m→0
senão:
  score_geoscout = 0  # rank vira quase só payback; aviso no item
```

### Gate geografia (anti-Diadema)

Descartar candidato se:

- `endereco` (ou título/url) contém UF/cidade claramente ≠ alvo, **ou**
- lat/lng fora de bbox frouxa do município (quando geocode cidade ok)

Sem endereço utilizável + sem lat → **fora** (não entra na lista).

### Área

- Exigir `area_m2` parseada do listing (já exige em `_fetch_listings_como_candidatos`).
- Sem área → drop. Sem `_estimar_area_por_tipo`.

## Architecture

```
A1 BaseAgent:
  cidade,uf,bairro ← _loc_do_state
  cascata = buscar_candidatos_cascata(...)
  filter cidade/UF + area_m2
  score_geoscout = distância→centróide (não 8.5)
  qualidade_sinal = "direto-listing-bairro"
  anexar MRLR por área (carimbo; price_raw intocado)
  state: candidatos_geoscout_pronto + candidatos_geoscout
        status=ok | ok_vazio

A4: 1× mid (inalterado; lat top1 opcional)

A6: tools/candidato_viabilidade_rank.py
  Top3 enriched (MRLR + payback_est + composto) — spec Top3
```

## Fora de escopo

- Reviver POI / `analisar_pontos_comerciais_completo` no happy path  
- Playwright no caminho crítico  
- A4 × N  
- Mudar fórmula MRLR Tier 0  
- Front redesign além de consumir Top3 enriched  

## Aceite

- [ ] A1 **não** chama macro POI  
- [ ] Candidatos = listings filtrados OU lista vazia honesta  
- [ ] Zero candidato fora da cidade/UF alvo no fixture Pirapora (ou lista vazia)  
- [ ] Nenhum `score_geoscout` constante 8.5  
- [ ] Top3 MD só com MRLR + payback_est quando A4 mid ok  
- [ ] `price_raw` não entra no rank  

## Approaches descartados

| | Ideia | Por quê não |
|---|--------|-------------|
| B | Fetch só no A6 | A4 perde lat top1; A6 fica lento; responsabilidade misturada |
| C | Agente A1b novo | Mais wiring Sequential; A1 stub já existe — reusa slot |

**Recomendação:** Approach A (A1 = cascata + gate; A6 = rank).
