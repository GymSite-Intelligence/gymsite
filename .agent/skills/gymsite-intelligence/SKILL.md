---
name: gymsite-intelligence
description: Inteligência geoespacial e enriquecimento de dados (CNPJ, CNO, Google Maps, concorrentes) para GymSite Intelligence. Use ao trabalhar com dados de mercado, geocoding, scraping de concorrentes, ou análise de viabilidade. NÃO use para componentes React ou endpoints genéricos.
---

# GymSite Intelligence — Dados e Geointeligência

## Contexto da Stack

- **Geocoding:** Google Maps Platform (Places New, Geocoding, Distance Matrix)
- **CNPJ:** RFB / dados públicos + Apollo.io (enriquecimento)
- **CNO:** Cadastro Nacional de Obras (CSV da RFB, encoding latin-1)
- **Scraping:** Playwright (async/sync) + BeautifulSoup4
- **Distâncias:** `googlemaps` Python SDK + haversine fallback

## Google Maps Platform

### API Keys

```python
from tools.google_maps_key import get_google_maps_api_key, warn_if_missing_maps_key

warn_if_missing_maps_key()  # loga warning se GOOGLE_MAPS_API_KEY ausente
```

### Places New API

```python
from tools.competitor_tools import buscar_academias

result = buscar_academias(
    bairro="Aldeota",
    cidade="Fortaleza",
    raio_metros=3000,
    uf="CE",
)
# Retorna: {concorrentes: [...], erro, fonte_busca_competidores}
```

### Distance Matrix

```python
from tools.distance_matrix_tools import calcular_distancia

dist = calcular_distancia(
    origem_lat=-3.7319,
    origem_lng=-38.5267,
    destino_lat=-3.7456,
    destino_lng=-38.4890,
)
# Retorna: {distancia_m, duracao_min, status}
```

## CNPJ — Dados e Enriquecimento

```python
from tools.cnpj_enrichment import enriquecer_cnpj

payload = enriquecer_cnpj("12345678000199")
# Retorna: {razao_social, nome_fantasia, socios, contato, ...}
```

### Apollo.io (enriquecimento de contato)

```python
from tools.apollo_enrichment import enriquecer_empresa_com_apollo

apollo = enriquecer_empresa_com_apollo("Academia Forte LTDA")
# Retorna: {email_direto, linkedin_url, empresa_match, ...}
```

## CNO — Cadastro Nacional de Obras

```python
from tools.cno_fitness_tools import cruzar_entrantes_obras_cno

obras = cruzar_entrantes_obras_cno(
    cidade="Fortaleza",
    uf="CE",
    dias=90,
)
# Retorna: [{cno, nome_obra, situacao, area, bairro, ...}]
```

### Regras de Cruzamento

- **Área plausível:** 80–5000 m² (fitness comercial)
- **Situação:** 01–04 (em curso) ou 15 (encerrada)
- **Keywords:** ACADEMIA, GINÁSIO, FITNESS, CROSSFIT, ETC.
- **Match por bairro:** CNPJ e CNO no mesmo bairro (normalizado)

## Competitor Intelligence (Scraping)

```python
from tools.competitor_offer_mapper import mapear_oferta_concorrente

oferta = await mapear_oferta_concorrente(
    nome="Smart Fit",
    website="https://smartfit.com.br",
    instagram_handle="@smartfit",
)
# Retorna: {modalidades_keywords, precos_encontrados, diferenciais_keywords, ...}
```

### Regras de Scraping

- Sites JS-rendered (Smart Fit, Bluefit) retornam HTML vazio — fallback para A3c sem LLM
- Instagram público bloqueia bots na maioria dos casos
- Timeout padrão: 30s (Playwright)
- Respeitar `robots.txt` e termos de uso

## Anti-padrões

- ❌ Não chame Google Maps API em loop síncrono — use batch ou cache
- ❌ Não armazene CNPJs completos em logs (LGPD) — mascare os 4 primeiros dígitos
- ❌ Não assuma que CNO CSV existe — verifique `main.is_file()` antes
- ❌ Não ignore rate limits do Google Maps — implemente backoff exponencial

## Cache

```python
# Cache de chamadas Google Maps (TTL 7 dias)
from tools.cache_store import get_cached, set_cached

key = f"places_{bairro}_{cidade}_{raio}"
cached = get_cached(key)
if cached:
    return cached
result = buscar_academias(...)
set_cached(key, result, ttl_days=7)
```
