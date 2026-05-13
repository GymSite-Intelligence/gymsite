# Prompt — Integrar Google Distance Matrix API ao cálculo de frete ANTT

> **Uso:** copie tudo abaixo da linha "---" e cole no chat de um agente que vá implementar a integração. O prompt é auto-suficiente — não exige que o agente leia outros arquivos antes de começar.

---

## Contexto

Trabalho no **GymSite Intelligence** (`C:\Users\marce\gymsite_intelligence`) — pipeline multi-agente Google ADK que produz relatórios de viabilidade comercial pra academias no Brasil. O A4 (FinancialEstimator) calcula CAPEX detalhado, incluindo desde 2026-05-11 uma linha **"Frete equipamentos"** baseada na **Tabela ANTT 6.034/2024** (`tools/antt_tools.py`).

Hoje as distâncias usadas pra calcular o frete são **um dicionário fixo SP→capital da UF** (`DISTANCIA_SP_CAPITAL_KM`). Isso tem 3 problemas:

1. **Não considera a cidade real** — Tamatanduba/Eusébio (CE interior) usa a mesma distância que Fortaleza, mesmo que a rota real seja ±100km diferente.
2. **Não considera múltiplos fornecedores** — Movement (Cotia/SP), Athletic Works (Caxias do Sul/RS), Life Fitness (Pinhais/PR) e Eleiko (importação Santos/SP) ficam em locais distintos. Hoje assumimos tudo sai de SP capital.
3. **Não captura rotas reais** — distância em linha reta vs rota rodoviária podem divergir 30%+ em regiões com geografia adversa (AM, RR, PA).

Quero substituir esse dicionário por chamadas reais à **Google Distance Matrix API**, com cache agressivo pra controlar custo.

## Objetivo

Implementar `tools/distance_matrix_tools.py` que retorna distância rodoviária real entre 2 pontos (origem fornecedor → destino academia), integrado ao `calcular_frete_kit_equipamentos` do `antt_tools.py`. Resultado: frete ANTT preciso por município, considerando o fornecedor principal do kit.

## Decisões de arquitetura (já definidas — não reabrir)

1. **Lib oficial**: usar `googlemaps` (`pip install googlemaps`), não chamadas REST manuais. Cliente Python oficial já trata rate limit, retry e parsing.
2. **Cache em filesystem JSON** (`tools/cache/distance_matrix/<hash>.json`), não Supabase ou Redis. Cache infinito (distâncias rodoviárias não mudam em horizonte de anos). Key = hash MD5 de `f"{origin_lat},{origin_lng}->{dest_lat},{dest_lng}"`.
3. **Geocode usa Places API New** (já temos `tools/competitor_tools.py:geocode_endereco`) — não fazer chamada extra de Geocoding API.
4. **Modo síncrono** — Distance Matrix é rápido (~300ms). Sem `async` pra manter compatibilidade com `_calcular_capex_detalhado` que é síncrono.
5. **Fallback gracioso** — se API falha ou key ausente, cair pro `DISTANCIA_SP_CAPITAL_KM` antigo. Nunca bloquear o pipeline.

## Fornecedores conhecidos (origens prováveis)

| Fornecedor | Cidade/UF | Lat aproximada | Lng aproximada |
|---|---|---|---|
| Movement | Cotia/SP | -23.6037 | -46.9189 |
| Athletic Works | Caxias do Sul/RS | -29.1689 | -51.1796 |
| Life Fitness Brasil | Pinhais/PR | -25.4477 | -49.1903 |
| RHS Equipamentos | Rio Claro/SP | -22.4108 | -47.5611 |
| Eleiko / Rogue / Concept2 (importados) | Santos/SP (porto) | -23.9608 | -46.3331 |
| Generico/proxy | São Paulo capital | -23.5505 | -46.6333 |

Pra MVP, use São Paulo capital como origem default. Em V2, derive origem do `fornecedor` mais frequente nos itens do kit (`frontend/src/data/kits/*.ts` tem `fornecedor` por item).

## Implementação — passos numerados

### 1. Setup

```bash
pip install googlemaps  # adiciona a requirements.txt
```

Adicionar variável de ambiente:
```
GOOGLE_DISTANCE_MATRIX_API_KEY=AIzaSy...  # ou reusar GOOGLE_MAPS_API_KEY se já habilitada pra Distance Matrix
```

Verificar no Google Cloud Console que a API "Distance Matrix" está habilitada no projeto.

### 2. Criar `tools/distance_matrix_tools.py`

Estrutura mínima esperada:

```python
"""
Google Distance Matrix API — distância rodoviária real entre 2 pontos.

Cache em disco (tools/cache/distance_matrix/*.json) — chave por par
(origem, destino) com tolerância de 0.001° (~100m). Distâncias rodoviárias
não mudam em horizonte de anos; cache infinito é seguro.

Custo: $5/1000 elements (Google Maps Platform pricing 2024).
Com cache, ~80-90% das análises hit cache após 50 cidades cobertas.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Optional

# Origens dos principais fornecedores fitness (lat, lng)
FORNECEDORES_ORIGEM = {
    "movement": (-23.6037, -46.9189),       # Cotia/SP
    "athletic": (-29.1689, -51.1796),        # Caxias do Sul/RS
    "life_fitness": (-25.4477, -49.1903),    # Pinhais/PR
    "rhs": (-22.4108, -47.5611),             # Rio Claro/SP
    "eleiko": (-23.9608, -46.3331),          # Santos/SP
    "default": (-23.5505, -46.6333),         # São Paulo capital
}

_CACHE_DIR = Path(__file__).parent / "cache" / "distance_matrix"

def _cache_key(orig: tuple[float, float], dest: tuple[float, float]) -> str:
    # Snap a 0.001° pra clusters mesma rota
    o_lat = round(orig[0], 3)
    o_lng = round(orig[1], 3)
    d_lat = round(dest[0], 3)
    d_lng = round(dest[1], 3)
    raw = f"{o_lat},{o_lng}->{d_lat},{d_lng}"
    return hashlib.md5(raw.encode()).hexdigest()

def calcular_distancia_rodoviaria(
    origem_lat: float, origem_lng: float,
    destino_lat: float, destino_lng: float,
) -> dict | None:
    """
    Returns:
        {
            "distancia_km": float,
            "duracao_horas": float,
            "fonte": "google_distance_matrix" | "cache",
            "rota_resumo": str,  # ex: "BR-116 via Salvador"
        }
        ou None se API falhar.
    """
    # 1. Tenta cache
    # 2. Se miss, chama googlemaps.Client().distance_matrix(...)
    # 3. Salva no cache
    # 4. Retorna dict
    ...

def distancia_fornecedor_para_cidade(
    fornecedor_key: str,  # "movement" | "athletic" | etc
    destino_lat: float,
    destino_lng: float,
) -> dict | None:
    origem = FORNECEDORES_ORIGEM.get(fornecedor_key, FORNECEDORES_ORIGEM["default"])
    return calcular_distancia_rodoviaria(origem[0], origem[1], destino_lat, destino_lng)
```

### 3. Integrar em `tools/antt_tools.py`

Função `calcular_frete_kit_equipamentos` deve aceitar `destino_lat`, `destino_lng` opcionais. Se fornecidos, usar Distance Matrix; senão, cair no `estimar_distancia_sp_para_uf` (atual).

```python
def calcular_frete_kit_equipamentos(
    valor_kit: float,
    uf_destino: str,
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
    distancia_km: float | None = None,
) -> dict:
    if distancia_km is None:
        if destino_lat and destino_lng:
            try:
                from tools.distance_matrix_tools import distancia_fornecedor_para_cidade
                res = distancia_fornecedor_para_cidade(fornecedor_principal, destino_lat, destino_lng)
                if res:
                    distancia_km = res["distancia_km"]
            except Exception:
                pass
        if distancia_km is None:
            distancia_km = estimar_distancia_sp_para_uf(uf_destino)
    # ... resto da função permanece
```

### 4. Propagar lat/lng no pipeline

No `tools/financial_tools.py:_calcular_capex_detalhado`, aceitar `destino_lat` e `destino_lng` opcionais e passar pro `calcular_frete_kit_equipamentos`. Lat/lng vêm do `top_3_candidatos[0]` do A1 GeoScout — já existem no `session.state["candidatos_geoscout"]`.

A macro `analise_financeira_a4_completo` precisa carregar lat/lng do candidato top-1 e passar adiante. Buscar como `state.get("candidatos_geoscout", {}).get("candidatos", [{}])[0]` e extrair `lat`/`lng`.

### 5. Testes

Criar `test_distance_matrix.py` que valida:

1. **Cache hit**: chamada repetida não bate na API (mocka via `unittest.mock`).
2. **SP→CE coerente**: distância real SP capital → Fortaleza ≈ 2.700-3.000 km (rota terrestre).
3. **Fallback gracioso**: quando key ausente, retorna `None` em vez de levantar exception.
4. **Cache em disco**: arquivo `.json` é gravado após primeira chamada bem-sucedida.

Validação end-to-end:

```python
from tools.antt_tools import calcular_frete_kit_equipamentos

# Eusébio centro (lat -3.889, lng -38.454)
r = calcular_frete_kit_equipamentos(
    valor_kit=600000,
    uf_destino="CE",
    destino_lat=-3.889,
    destino_lng=-38.454,
    fornecedor_principal="movement",
)
print(r["frete_estimado_real"])
# Esperado: R$ ~40-45k (Distance Matrix retorna ~2.900km, similar ao dict atual)
```

## Custo estimado

- Distance Matrix: **$5/1000 elements** = $0,005 por par origem-destino
- Por relatório novo: 1 chamada (1 fornecedor × 1 destino) = **$0,005 ≈ R$ 0,03**
- Cache hit após primeira análise daquele bairro: $0
- Estimativa mensal (100 relatórios novos, 60% bairros novos): ~$0,30/mês ≈ R$ 1,70

Pricing referência: https://developers.google.com/maps/documentation/distance-matrix/usage-and-billing

## Riscos / pontos de atenção

1. **API key compartilhada**: se reusar `GOOGLE_MAPS_API_KEY` (mesma do Places e Geocoding), garantir que Distance Matrix está habilitada no Cloud Console. Senão API retorna 403.
2. **Quota diária**: free tier do Google Maps Platform inclui $200/mês — pra GymSite (volume baixo), essencialmente grátis. Mas configurar **billing alert** em $5/mês como salvaguarda.
3. **Limite de elementos por chamada**: 25 origens × 25 destinos = 625 elementos. Pra GymSite usamos sempre 1×1, longe do limite.
4. **Cache invalidation**: distâncias raramente mudam, mas se inaugurar/fechar grande rodovia (raro), cache fica desatualizado. Aceitável — pode invalidar manualmente deletando o `.json`.

## Critério de "pronto"

- [ ] `tools/distance_matrix_tools.py` criado com cache em disco
- [ ] `requirements.txt` atualizado com `googlemaps`
- [ ] Variável de ambiente documentada no `.env.example`
- [ ] `calcular_frete_kit_equipamentos` aceita lat/lng opcionais
- [ ] Macro `analise_financeira_a4_completo` carrega lat/lng do candidato top-1 e propaga
- [ ] Teste unitário com mock validando cache + fallback
- [ ] Teste manual em Eusébio mostra distância ≈ 2.900km (não a estimativa fixa 2.900 do dict)
- [ ] Aviso no output do frete cita "fonte: Google Distance Matrix" quando API foi usada (vs "estimativa por UF")

## Não fazer

- ❌ Refatorar o `antt_tools.py` além do necessário pra plugar lat/lng.
- ❌ Adicionar feature de "roteamento otimizado" (multi-stop) — escopo de V2.
- ❌ Substituir o dict `DISTANCIA_SP_CAPITAL_KM` por completo. Mantém como fallback.
- ❌ Adicionar webhook ou job de refresh — cache infinito é OK.

## Arquivos a tocar

```
tools/distance_matrix_tools.py    [novo]
tools/antt_tools.py               [add lat/lng opcionais]
tools/financial_tools.py          [propaga lat/lng até _calcular_capex_detalhado]
agents/a4_financial_estimator.py  [instrução: extrair lat/lng do candidato top-1]
requirements.txt                  [+ googlemaps]
.env.example                      [+ GOOGLE_DISTANCE_MATRIX_API_KEY]
tests/test_distance_matrix.py     [novo]
```
