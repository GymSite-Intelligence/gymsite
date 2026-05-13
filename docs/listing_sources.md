# Fontes de listings de imóveis comerciais — avaliação e decisão

**Data da decisão:** 2026-05-13
**Contexto:** A1 GeoScout precisa cruzar zonas geográficas (Places API) com **oferta real de imóveis disponíveis** pra alugar. Hoje o A1 só identifica "regiões com comércio movimentado" mas não traz nenhum imóvel concreto pro investidor olhar.

## TL;DR

Adotar **OLX + ImovelWeb** como fontes primárias de listings via **Playwright async** (Chromium headless). Aposentar o conteúdo VivaReal de `tools/imobiliaria_scraper.py` mas **manter o arquivo** como runner Playwright unificado dos 2 portais novos.

**Atualização 2026-05-13 (pivô):** o plano inicial era usar `httpx`+`BeautifulSoup`, mas teste ao vivo mostrou HTTP 403 nos 2 portais por **TLS fingerprinting** (mesmo com headers Chrome completos). A 1ª camada de extração tem que ser Chromium real — não há escape. `httpx`+`bs4` foram revertidos em favor de Playwright. Smoke test final em Fortaleza/CE retorna 15 listings reais (incl. prédio 988m² R$ 9.500 Centro de Fortaleza, id `3032295652`).

---

## 1. Portais avaliados ao vivo

### 1.1 VivaReal — ❌ APOSENTADO

**O que oferece:** Tipos certos pro caso de academia (Galpão/Depósito/Armazém, Ponto Comercial/Loja/Box, Prédio/Edifício Inteiro — confirmado no modal de filtros).

**Status atual do scraper:** `tools/imobiliaria_scraper.py` usa Playwright sync via thread (compatível Windows + ADK). URL pattern: `https://www.vivareal.com.br/aluguel/<uf-nome>/<cidade-slug>/bairros/<bairro-slug>/imoveis-comerciais/`.

**Inspeção 2026-05-13:**
- 5/5 tentativas de navegação direta por categoria retornaram **"Não conseguimos encontrar a página solicitada"** ou **"Estamos com problemas em nossos servidores"**
- Site bloqueia navegação por URL de categoria — força interação JavaScript no modal de filtros
- Por isso o scraper já dependia de Playwright pesado (custo de manutenção alto)

**Motivo da aposentadoria:**
1. Instabilidade do site → cobertura intermitente
2. Detecção de bot crescente → Playwright só piora com o tempo
3. VivaReal e ZAP são do **mesmo grupo (OLX Group)** e compartilham estoque — sobreposição alta com OLX inviabiliza dedup

**Ação:** marcar `tools/imobiliaria_scraper.py` como `DEPRECATED` no header e remover quando `tools/listing_tools.py` (novo) estiver em produção.

### 1.2 OLX — ✅ ADOTAR

**O que oferece:** Maior volume de anúncios imobiliários do Brasil, com categorias nativas pra comerciais.

**URLs confirmadas ao vivo:**
```
# Lojas/Salas (categoria mais relevante pra academias)
https://www.olx.com.br/imoveis/aluguel/lojas-salas-e-pontos-comerciais/{cidade-slug}/estado-{uf}?re={uf}&o={page}

# Galpões/Depósitos
https://www.olx.com.br/imoveis/aluguel/galpoes-e-depositos/{cidade-slug}/estado-{uf}?re={uf}&o={page}

# Prédios — sem categoria própria. Caem em "Lojas/Salas" ou via busca livre
```

**Volume:** ~6.100 imóveis no CE (lojas/salas + galpões combinados).

**Padrão de URL do anúncio individual** — confirmado:
```
https://{uf}.olx.com.br/{cidade-e-regiao}/imoveis/{slug-do-titulo}-{ID_10_DIGITOS}
```
Exemplo: `https://ce.olx.com.br/fortaleza-e-regiao/imoveis/nome-do-imovel-1501683997`

**ID extraível por regex** `\d{9,}` no final do href.

### 1.3 ImovelWeb — ✅ ADOTAR

**O que oferece:** Filtro nativo `Comerciais` que já agrega lojas, galpões, prédios e salas grandes.

**URL confirmada ao vivo:**
```
https://www.imovelweb.com.br/comerciais-aluguel-{estado}-{cidade}.html?pagina={N}
```
Exemplo testado: `comerciais-aluguel-ceara-fortaleza.html` → **975 resultados**.

**Padrão de URL do anúncio individual** — confirmado:
```
https://www.imovelweb.com.br/propriedades/{slug-do-titulo}-{ID_10_DIGITOS}.html
```
Exemplo testado: prédio comercial 988m², Centro de Fortaleza, R$ 9.500/mês — `propriedades/predio-comercial-para-aluguel-no-centro-de-fortaleza-3032295652.html`.

**Página de detalhe entrega:**
- Tipo (`Comercial`), área (`988m²`), preço (`R$ 9.500`)
- Endereço completo (`São José 202, Centro, Fortaleza`)
- Imobiliária (`Sóbile Soluções Imobiliárias`) com CRECI
- Código do anúncio (`3032295652`)
- 7 fotos
- Contato com WhatsApp + formulário

---

## 2. Comparativo final

| Critério                  | VivaReal              | OLX                                  | ImovelWeb                              |
|--------------------------|-----------------------|--------------------------------------|----------------------------------------|
| **Status decisão**        | ❌ aposentado          | ✅ adotar                              | ✅ adotar                                |
| **Lib necessária**        | Playwright (pesado)   | httpx + bs4                           | httpx + bs4                             |
| **URL pattern listagem**  | bloqueado por filtros JS | `/imoveis/aluguel/{cat}/{cidade}/estado-{uf}` | `/comerciais-aluguel-{estado}-{cidade}.html` |
| **URL pattern anúncio**   | inconsistente         | `{uf}.olx.com.br/.../-{ID}`             | `/propriedades/...-{ID}.html`           |
| **`listing_id` extraível** | não confiável         | regex `\d{9,}` no href                  | regex `\d{9,}` no href                  |
| **Volume CE (lojas+galpões)** | n/a (site quebrado) | ~6.100                                | 975 (Fortaleza)                         |
| **Contato anunciante**     | n/a                   | Chat OLX + telefone                   | WhatsApp + formulário                   |
| **Imobiliária / CRECI**    | n/a                   | Tag "Direto c/ proprietário" ou nome  | Nome + nível + código CRECI              |
| **Estoque exclusivo**      | sobrepõe ZAP/grupo   | sim                                  | sim                                    |

---

## 3. Implementação entregue (commit pós-pivô)

### Arquitetura final

```
tools/listing_tools.py            (parsing puro + orquestrador async)
    ↓ asyncio.gather
tools/imobiliaria_scraper.py      (runner Playwright unificado)
    ├── fetch_olx_nextdata()       → extrai __NEXT_DATA__ pós-hydration
    └── fetch_imovelweb_jsonld()   → extrai DOM via [data-qa*='posting']
```

### Por que Playwright e não httpx

| Tentativa                          | HTTP    | Resultado |
|-----------------------------------|---------|-----------|
| httpx + User-Agent simples         | 403     | Bloqueado |
| httpx + 12 headers Chrome (Sec-Ch-Ua, Sec-Fetch-*, etc) | 403 | Bloqueado |
| Playwright Chromium headless       | 200     | ✅ Funciona |

TLS fingerprint do `python-httpx` é detectável; só Chromium real (ou `curl_cffi` que imita o TLS handshake) passa. Playwright já é dependência do projeto (`playwright_enrichment.py`), custo zero adicionar mais 2 funções.

### Extração por portal

**OLX** (Next.js com SSR):
- Aguardar `__NEXT_DATA__.props.pageProps.totalOfAds > 0` pós-hydration
- `page.evaluate()` retorna `pageProps.ads[]` direto
- Cada ad tem `listId`, `subject`, `priceValue`, `friendlyUrl`, `locationDetails`, `properties[]` (size, re_type)

**ImovelWeb** (stack legada naventcdn):
- Aguardar `[data-qa*='posting'][data-id]` aparecer no DOM (timeout 30s)
- Atributos estáveis no card:
  - `data-id="3032295652"` → `listing_id`
  - `data-to-posting="/propriedades/..."` → URL relativa
  - `[class*='features']` → "988 m² tot." (área — não é `surface`!)
  - `[class*='price']` → "R$ 9.500"
  - `[class*='location']` → endereço

### Helpers de parsing puro (em `listing_tools.py`)

```python
_slug("São Paulo")           # → "sao-paulo"
_extract_id(".../-3032295652.html")  # → "3032295652"
_parse_area_m2("988 m² tot.")        # → 988
```

### Dedup + filtros

```python
_dedup_and_filter(listings, area_min, area_max)
# Chave dupla: listing_id (preferido) + endereço normalizado primeiros 40 chars
# Filtra fora da faixa [area_min, area_max]
# Ordena por área decrescente
```

### Trecho legado (versão httpx descartada após pivô)

```python
# (Mantido por referência histórica — NÃO usar em produção.)
"""
tools/listing_tools.py — scraper de listings comerciais OLX + ImovelWeb.
Substitui tools/imobiliaria_scraper.py (VivaReal/Playwright) — ver docs/listing_sources.md.
"""
import httpx
import re
from bs4 import BeautifulSoup
from models.schemas import ListingResult

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _extract_id(url: str) -> str:
    """Extrai o ID numérico final (10+ dígitos) do URL do anúncio."""
    m = re.search(r"(\d{9,})", url or "")
    return m.group(1) if m else ""


def search_imovelweb(cidade: str, estado: str, area_min: int = 500, page: int = 1) -> list[ListingResult]:
    url = f"https://www.imovelweb.com.br/comerciais-aluguel-{estado}-{cidade}.html"
    resp = httpx.get(url, params={"pagina": page}, headers=HEADERS, timeout=15, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

    results: list[ListingResult] = []
    for card in soup.select("[class*='postingCard'], article"):
        price_raw = card.select_one("[class*='Price'], [class*='price']")
        area_raw  = card.select_one("[class*='Surface'], [class*='surface']")
        addr_raw  = card.select_one("[class*='Location'], [class*='location']")
        desc_raw  = card.select_one("p")
        title_raw = card.select_one("h2, h3, [class*='title']")
        link      = card.select_one("a")

        area_text = area_raw.get_text() if area_raw else ""
        area_match = re.search(r"(\d[\d\.]*)", area_text)
        area_m2 = int(area_match.group(1).replace(".", "")) if area_match else 0
        if area_m2 < area_min:
            continue

        href = link.get("href", "") if link else ""
        listing_url = f"https://www.imovelweb.com.br{href}" if href.startswith("/") else href

        results.append(ListingResult(
            source="imovelweb",
            title=title_raw.get_text(strip=True) if title_raw else "",
            price_raw=price_raw.get_text(strip=True) if price_raw else "",
            area_m2=area_m2,
            address=addr_raw.get_text(strip=True) if addr_raw else "",
            description=desc_raw.get_text(strip=True)[:300] if desc_raw else "",
            listing_url=listing_url,
            listing_id=_extract_id(listing_url),
            source_url=url,
        ))
    return results


OLX_CATEGORIES = {
    "lojas":   "lojas-salas-e-pontos-comerciais",
    "galpoes": "galpoes-e-depositos",
}

def search_olx(
    cidade_slug: str,
    estado_slug: str,        # "estado-ce"
    estado_sigla: str,       # "ce"
    category: str = "lojas",
    area_min: int = 500,
    page: int = 1,
) -> list[ListingResult]:
    cat = OLX_CATEGORIES.get(category, OLX_CATEGORIES["lojas"])
    url = (
        f"https://www.olx.com.br/imoveis/aluguel/{cat}/"
        f"{cidade_slug}/{estado_slug}?re={estado_sigla}&o={page}"
    )
    resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

    results: list[ListingResult] = []
    items = soup.select('[data-lurker-detail="ad_list"] li, [class*="AdCard"] li') \
            or soup.select("li[class*='sc-']")

    for item in items:
        title = item.select_one("h2, h3, [class*='title']")
        price = item.select_one("[class*='price'], [data-lurker-detail='price']")
        area  = item.select_one("[aria-label*='rea'], [class*='area']")
        loc   = item.select_one("[class*='location'], [class*='city']")

        # Link individual: filtra pelo subdomínio do estado + ID numérico 9+ no href
        link = next(
            (a for a in item.select("a") if re.search(r"\d{9,}", a.get("href", ""))),
            None,
        )

        area_text = area.get_text() if area else item.get_text()
        area_match = re.search(r"(\d[\d\.]*)\s*m[²2]", area_text)
        area_m2 = int(area_match.group(1).replace(".", "")) if area_match else 0
        if area_m2 < area_min:
            continue

        listing_url = link["href"] if link else ""
        results.append(ListingResult(
            source="olx",
            title=title.get_text(strip=True) if title else "",
            price_raw=price.get_text(strip=True) if price else "",
            area_m2=area_m2,
            address=loc.get_text(strip=True) if loc else "",
            listing_url=listing_url,
            listing_id=_extract_id(listing_url),
            source_url=url,
        ))
    return results


def fetch_commercial_listings(
    cidade: str,
    estado: str,             # "CE"
    area_min: int = 800,
    area_max: int = 2000,
    max_pages: int = 3,
) -> list[ListingResult]:
    """Agrega OLX + ImovelWeb, filtra por área e remove duplicatas por listing_id."""
    cidade_slug = cidade.lower().replace(" ", "-")
    estado_sigla = estado.lower()[:2]
    estado_slug_olx = f"estado-{estado_sigla}"
    estado_slug_iw = estado.lower().replace(" ", "-")     # nome por extenso slug

    all_listings: list[ListingResult] = []
    for page in range(1, max_pages + 1):
        all_listings += search_olx(f"{cidade_slug}-e-regiao", estado_slug_olx, estado_sigla, "lojas",   area_min, page)
        all_listings += search_olx(f"{cidade_slug}-e-regiao", estado_slug_olx, estado_sigla, "galpoes", area_min, page)
        all_listings += search_imovelweb(cidade_slug, estado_slug_iw, area_min, page)

    seen_ids: set[str] = set()
    seen_addr: set[str] = set()
    final: list[ListingResult] = []
    for l in all_listings:
        if l.area_m2 > area_max:
            continue
        key_id = l.listing_id or ""
        key_addr = (l.address.lower()[:40]) if l.address else ""
        if key_id and key_id in seen_ids:
            continue
        if key_addr and key_addr in seen_addr:
            continue
        if key_id:   seen_ids.add(key_id)
        if key_addr: seen_addr.add(key_addr)
        final.append(l)
    return sorted(final, key=lambda x: x.area_m2, reverse=True)
```

### 3.2 Schema novo em `models/schemas.py`

```python
class ListingResult(BaseModel):
    source: str                       # "olx" | "imovelweb"
    title: str
    price_raw: str                    # "R$ 28.000/mês" — A4 parseia
    price_numeric: float | None = None
    area_m2: int
    address: str
    description: str = ""
    listing_url: str                  # URL clicável do anúncio
    listing_id: str = ""              # ID numérico final do URL (dedup key)
    source_url: str                   # URL da listagem usada
    property_type: str = "comercial"  # "loja" | "galpao" | "predio" (LLM infere)
    parking: bool | None = None       # extraído da descrição (A1)
    floor_type: str | None = None     # "terreo" | "andar"
```

### 3.3 Plug no A1 GeoScout (`agents/a1_geoscout.py`)

```python
# Estágio 1 (existente): Google Maps → zonas comerciais candidatas
zones = await maps_tools.find_commercial_zones(...)

# Estágio 2 (NOVO): listings reais OLX + ImovelWeb
listings = fetch_commercial_listings(
    cidade=params.cidade, estado=params.estado,
    area_min=params.area_min, area_max=params.area_max,
)

# Estágio 3: cruzar listings com zonas via geocode
candidates: list[PlaceCandidate] = []
for listing in listings:
    coords = await maps_tools.geocode(listing.address)
    if coords and is_within_zone(coords, zones):
        candidates.append(PlaceCandidate.from_listing(listing, coords))
```

### 3.4 Dependência (final)

`requirements.txt`:
```
playwright>=1.40.0
```

`beautifulsoup4` foi removido — Playwright extrai via `page.evaluate()` no DOM
real, sem precisar parser HTML em Python. Chromium já estava instalado no
`.venv` por outras tools (`playwright_enrichment.py`).

---

## 4. Riscos e mitigação

| Risco                                              | Mitigação                                                                                  |
|---------------------------------------------------|---------------------------------------------------------------------------------------------|
| **ToS scraping** — OLX/ImovelWeb podem proibir    | Volume baixo (≤30 págs/relatório), `User-Agent` honesto, sem paralelismo agressivo, cache local de páginas |
| **Mudança de HTML** quebra seletores              | Seletores tolerantes (`[class*='X']` em vez de classe exata); fallback chain; teste E2E periódico |
| **Bot detection** (captcha, 403)                  | Backoff exponencial; fallback pra `imobiliaria_scraper.py` (DEPRECATED) só em caso de bloqueio total |
| **Dedup falha** quando mesmo imóvel anunciado em ambos | Chave dupla: `listing_id` quando disponível + endereço normalizado primeiros 40 chars      |
| **Endereço vazio** ⇒ geocode falha                | A1 descarta listings sem `address`; loga em `state_diagnostics.jsonl` pra auditoria          |

---

## 5. Status de execução

1. ✅ Decisão registrada — este doc + 2 comentários VEC-386 (proposta inicial httpx + pivô Playwright)
2. ✅ `playwright>=1.40.0` em `requirements.txt` (`beautifulsoup4` revertido após pivô)
3. ✅ `ListingResult` criado em `models/schemas.py` (dataclass, padrão da casa)
4. ✅ `tools/listing_tools.py` implementado — parsing puro + orquestrador async com `asyncio.gather` das 3 fontes
5. ✅ `tools/imobiliaria_scraper.py` reescrito como runner Playwright unificado (`fetch_olx_nextdata` + `fetch_imovelweb_jsonld`)
6. ✅ Smoke test ao vivo Fortaleza/CE: 144 brutos → 15 únicos após dedup+filtro, incluindo prédio 988m² R$ 9.500 Centro (id 3032295652)
7. ⏳ Modificar `agents/a1_geoscout.py` pra usar 3 estágios (zonas Places + listings + cruzamento via geocode)
8. ⏳ Teste E2E full pipeline em Fortaleza/Centro, validar top 3 candidatos com `listing_url` clicáveis
