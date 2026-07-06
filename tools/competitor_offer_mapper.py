"""
competitor_offer_mapper.py — extrai oferta concreta de cada concorrente.

PROBLEMA: A6 ReportConsolidator recomenda diferenciais (piscina, área kids)
sem saber o que cada concorrente local já oferece. Em Niterói/Itaipu o
relatório sugeriu "explorar natação e área kids visto a ausência na
concorrência" — mas Tio Sam (concorrente top) tem ambos no site oficial.
Resultado: recomendações imprecisas.

ESTRATÉGIA: pra cada concorrente com site/Instagram público, baixa o HTML
(site via httpx) + perfil Instagram (SearchAPI `engine=instagram_profile`),
extrai texto + meta tags + sinais óbvios (modalidades, preços, diferenciais)
via keyword matching + regex. Retorna payload bruto já normalizado.

NÃO faz LLM aqui — só I/O e parsing determinístico. Mantém o módulo
testável isoladamente e barato (~zero custo). O A3b (determinístico, ex-A3c
fundido) consome este output e mescla os serviços por concorrente.

Limitações conhecidas:
- Instagram público bloqueia bots; o caminho usa SearchAPI `engine=instagram_profile`
  (sem Playwright, sem Outscraper) — plano pago ativo desde 12/06.
- Sites JS-rendered (Smart Fit, Bluefit) retornam HTML vazio — pula
  quando confiabilidade < 0.3.
"""
import asyncio
import json as _json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
FETCH_TIMEOUT_S = 8.0
MAX_TEXTO_CHARS = 12_000
MIN_TEXTO_VALIDO = 200  # textos menores são tipicamente shell/loading screens
INSTAGRAM_PUBLIC_URL = "https://www.instagram.com/{handle}/"

# Outscraper IG fallback — $0.003/perfil. Só ativa se a chave estiver no env.
# Endpoint: https://app.outscraper.com/api-docs#tag/Instagram/operation/InstagramPosts
OUTSCRAPER_API_URL = "https://api.outscraper.com/instagram-data"
OUTSCRAPER_TIMEOUT_S = 30.0
_OUTSCRAPER_CACHE_DIR = Path(__file__).resolve().parent.parent / "competitor_cache"
_OUTSCRAPER_CACHE_TTL_DAYS = 7

# Descoberta de links internos: ranking por relevância de slug/texto.
# Visitamos até MAX_PAGINAS_EXTRAS sequencialmente (não martela host).
MAX_PAGINAS_EXTRAS = 3

# Slugs/textos que provavelmente carregam descrição de oferta.
SLUG_POSITIVO = [
    "modalidades", "planos", "atividades", "aulas", "servicos", "servico",
    "sobre", "complexo", "unidade", "oferece", "academia", "estrutura",
    "infra", "espaco", "espaço", "horarios", "horario",
]
# Slugs a evitar (institucional puro, sem oferta).
SLUG_NEGATIVO = [
    "contato", "fale-conosco", "blog", "noticia", "evento", "politica",
    "termos", "privacidade", "login", "cadastro", "carrinho", "checkout",
    "trabalhe", "carreira", "imprensa", "investidor", "lgpd",
]

# Keywords canônicas — assinalam presença textual. A normalização e
# desambiguação são determinísticas (regex/keyword), sem LLM.
MODALIDADES_KEYWORDS: dict[str, list[str]] = {
    "musculacao":   ["musculação", "musculacao", "weight room", "sala de musculação"],
    "piscina":      ["piscina", "natação", "natacao", "swimming", "hidroginástica", "hidroginastica"],
    "area_kids":    ["kids", "infantil", "crianças", "criancas", "kidsroom", "área kids", "area kids", "espaço kids"],
    "crossfit":     ["crossfit", "cross fit", "wod", " box "],
    "pilates":      ["pilates"],
    "yoga":         ["yoga", "ioga"],
    "spinning":     ["spinning", "bike indoor", "ciclismo indoor"],
    "lutas":        ["muay thai", "muaythai", "jiu jitsu", "jiu-jitsu", "boxe", " mma ", "karate", "karatê",
                     "artes marciais", "arte marcial", "krav maga", "taekwondo", "judô", " judo ", "kickboxing"],
    "funcional":    ["funcional", "treino funcional", "training funcional"],
    "danca":        ["zumba", "ritmos", " dança ", "danca", "ballet", "fitdance"],
    "personal":     ["personal trainer", "personal incluso", "treinamento individual",
                     "treinamento personalizado", "treino personalizado"],
    "avaliacao":    ["avaliação física", "avaliacao fisica", "bioimpedância", "bioimpedancia"],
    "estetica":     ["estética", "estetica", "sauna", "spa"],
    # Nutrição e Recovery: serviços que a ERRC sempre recomenda "Criar" — precisam
    # ser detectados quando o concorrente JÁ oferece, senão viram falso-gap eterno.
    "nutricao":     ["nutrição", "nutricao", "nutricionista", "nutrição esportiva",
                     "nutricao esportiva", "acompanhamento nutricional", "avaliação nutricional",
                     "avaliacao nutricional", "plano alimentar"],
    "recovery":     ["recovery", "recuperação", "recuperacao", "recuperação muscular",
                     "fisioterapia", "fisioterapeuta", "massagem", "massoterapia",
                     "crioterapia", "botas de compressão", "botas de compressao",
                     "liberação miofascial", "liberacao miofascial"],
}

DIFERENCIAIS_KEYWORDS: dict[str, list[str]] = {
    "ar_condicionado":   ["climatizado", "ar condicionado", "ar-condicionado", "climatização", "climatizacao"],
    "horario_24h":       ["24 horas", "24h", "vinte e quatro horas", "aberto 24"],
    "estacionamento":    ["estacionamento", "vaga gratuita", "vagas"],
    "wifi":              ["wi-fi", "wifi", "wi fi"],
    "vestiario_premium": ["chuveiro quente", "vestiário", "vestiario", "secador"],
    "app":               ["aplicativo", "app exclusivo", "app próprio"],
    "personal_incluso":  ["personal incluso", "personal grátis", "personal gratis"],
    "diaria":            ["diária", "diaria", "day pass", "passe diário"],
    "biometria":         ["biometria", "acesso biométrico"],
    "alunos_24h":        ["acesso liberado", "porta automática"],
}

# Variações comuns de preço BR: R$ 89,90 | R$89 | R$ 89,90/mês | R$ 1.299,90 |
# R$ 159,00 mensal | R$ 2.500,00 anual | "Mensal R$ 159,90" | "Plano anual: R$ 1.499"
# Período pode vir ANTES (group 1) ou DEPOIS (group 3) do valor (group 2).
_PERIODO_ALT = r"mensal|trimestral|trimestre|semestral|semestre|anual|por\s*m[êe]s|por\s*ano|m[êe]s|dia|day"
PRECO_REGEX = re.compile(
    r"(?:(" + _PERIODO_ALT + r")\s*[:\-–]?\s*)?"
    r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)"
    r"(?:\s*/?\s*(" + _PERIODO_ALT + r"))?",
    re.IGNORECASE,
)


def _norm_periodo(p: str | None) -> str:
    p = re.sub(r"\s+", " ", (p or "").lower().strip())
    if not p:
        return "indefinido"
    if "trimestr" in p:
        return "trimestral"
    if "semestr" in p:
        return "semestral"
    if "anual" in p or "ano" in p:
        return "anual"
    if "mensal" in p or "mês" in p or "mes" in p:
        return "mensal"
    if "dia" in p or "day" in p:
        return "diaria"
    return "indefinido"


@dataclass
class OfertaMapeada:
    nome: str
    place_id: Optional[str] = None
    fonte_url: Optional[str] = None
    fonte_instagram: Optional[str] = None
    fonte_url_ok: bool = False
    fonte_instagram_ok: bool = False
    raw_texto: str = ""
    raw_meta_description: str = ""
    titulo_site: str = ""
    modalidades_keywords: list[str] = field(default_factory=list)
    diferenciais_keywords: list[str] = field(default_factory=list)
    precos_encontrados: list[dict] = field(default_factory=list)
    confiabilidade_fonte: float = 0.0
    erros: list[str] = field(default_factory=list)
    # Camada 3 — agregadores (SPEC_OFERTA_AGREGADORES): tier corporativo NUNCA se
    # mistura com preço de balcão (precos_encontrados); campos separados e rotulados.
    fontes_agregador: list[str] = field(default_factory=list)
    tier_agregador: Optional[dict] = None
    rating_agregador: Optional[dict] = None
    comodidades_agregador: list[str] = field(default_factory=list)

    def asdict(self) -> dict:
        return {
            "nome": self.nome,
            "place_id": self.place_id,
            "fonte_url": self.fonte_url,
            "fonte_instagram": self.fonte_instagram,
            "fonte_url_ok": self.fonte_url_ok,
            "fonte_instagram_ok": self.fonte_instagram_ok,
            "raw_texto": self.raw_texto,
            "raw_meta_description": self.raw_meta_description,
            "titulo_site": self.titulo_site,
            "modalidades_keywords": self.modalidades_keywords,
            "diferenciais_keywords": self.diferenciais_keywords,
            "precos_encontrados": self.precos_encontrados,
            "confiabilidade_fonte": self.confiabilidade_fonte,
            "erros": self.erros,
            "fontes_agregador": self.fontes_agregador,
            "tier_agregador": self.tier_agregador,
            "rating_agregador": self.rating_agregador,
            "comodidades_agregador": self.comodidades_agregador,
        }


def _normalizar_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    u = url.strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def _normalizar_handle(handle: Optional[str]) -> Optional[str]:
    if not handle:
        return None
    h = handle.strip().lstrip("@")
    m = re.search(r"instagram\.com/([A-Za-z0-9._]+)", h)
    if m:
        h = m.group(1)
    h = h.split("/")[0].split("?")[0]
    return h if re.match(r"^[A-Za-z0-9._]{1,30}$", h) else None


def _extrair_texto_html(html: str) -> tuple[str, str, str]:
    """Retorna (raw_texto truncado, meta_description, titulo)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    titulo = (soup.title.get_text(strip=True) if soup.title else "")[:200]
    meta_desc = ""
    for sel in [
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ]:
        tag = soup.find("meta", attrs=sel)
        if tag and tag.get("content"):
            meta_desc = tag["content"][:500]
            break
    texto = soup.get_text(separator=" ", strip=True)
    texto = re.sub(r"\s+", " ", texto)
    return texto[:MAX_TEXTO_CHARS], meta_desc, titulo


def _detectar_modalidades(texto: str) -> list[str]:
    t = f" {texto.lower()} "
    return [chave for chave, sinonimos in MODALIDADES_KEYWORDS.items()
            if any(kw in t for kw in sinonimos)]


def _detectar_diferenciais(texto: str) -> list[str]:
    t = f" {texto.lower()} "
    return [chave for chave, sinonimos in DIFERENCIAIS_KEYWORDS.items()
            if any(kw in t for kw in sinonimos)]


def _detectar_precos(texto: str) -> list[dict]:
    achados: list[dict] = []
    seen: set[tuple[float, str]] = set()
    for m in PRECO_REGEX.finditer(texto):
        valor_str = m.group(2)
        if not valor_str:
            continue
        periodo = _norm_periodo(m.group(1) or m.group(3))  # período antes OU depois
        try:
            valor = float(valor_str.replace(".", "").replace(",", "."))
        except ValueError:
            continue
        if not (10 <= valor <= 5000):
            continue
        key = (round(valor, 2), periodo)
        if key in seen:
            continue
        seen.add(key)
        achados.append({"valor_brl": valor, "periodo": periodo})
        if len(achados) >= 8:
            break
    return achados


def _calcular_confiabilidade(o: OfertaMapeada) -> float:
    score = 0.0
    if o.fonte_url_ok:         score += 0.40
    if o.fonte_instagram_ok:   score += 0.30
    if o.modalidades_keywords: score += 0.15
    if o.precos_encontrados:   score += 0.15
    if o.fontes_agregador:     score += 0.20
    return round(min(score, 1.0), 2)


async def _fetch_url(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        r = await client.get(url, follow_redirects=True, timeout=FETCH_TIMEOUT_S)
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    if r.status_code != 200:
        return None
    ct = r.headers.get("content-type", "").lower()
    if "text/html" not in ct and "application/xhtml" not in ct:
        return None
    return r.text


# ─── Outscraper IG fallback (paid, $0.003/perfil) ─────────────────────────

def _outscraper_cache_path(handle: str) -> Path:
    _OUTSCRAPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", handle)[:80] or "anon"
    return _OUTSCRAPER_CACHE_DIR / f"ig_outscraper_{safe}.json"


def _outscraper_cache_load(handle: str) -> Optional[dict]:
    import time
    p = _outscraper_cache_path(handle)
    if not p.exists():
        return None
    age_s = time.time() - p.stat().st_mtime
    if age_s > _OUTSCRAPER_CACHE_TTL_DAYS * 86400:
        return None
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _outscraper_cache_save(handle: str, payload: dict) -> None:
    p = _outscraper_cache_path(handle)
    try:
        p.write_text(_json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _outscraper_extrair_perfil(raw: dict) -> Optional[dict]:
    """
    Outscraper retorna {status, data: [[profile]]}. Extrai o 1º perfil
    e retorna {bio, full_name, external_url, posts_recentes_captions}.
    """
    if not isinstance(raw, dict):
        return None
    data = raw.get("data")
    if not data or not isinstance(data, list):
        return None
    inner = data[0] if data else None
    if isinstance(inner, list) and inner:
        perfil = inner[0]
    elif isinstance(inner, dict):
        perfil = inner
    else:
        return None
    if not isinstance(perfil, dict):
        return None
    captions = []
    for k in ("recent_posts", "posts", "media"):
        items = perfil.get(k)
        if isinstance(items, list):
            for it in items[:5]:
                if isinstance(it, dict):
                    cap = it.get("caption") or it.get("description") or ""
                    if cap:
                        captions.append(str(cap)[:500])
            if captions:
                break
    return {
        "username": perfil.get("username") or perfil.get("user_name"),
        "full_name": perfil.get("full_name") or perfil.get("name"),
        "biography": perfil.get("biography") or perfil.get("bio") or "",
        "external_url": perfil.get("external_url"),
        "followers_count": perfil.get("followers_count"),
        "posts_count": perfil.get("posts_count"),
        "captions": captions,
    }


async def _outscraper_instagram_info(
    client: httpx.AsyncClient, handle: str
) -> Optional[dict]:
    """
    Consulta Outscraper Instagram-Data API. Retorna perfil normalizado
    ou None (sem chave, cache miss + falha, ou perfil não encontrado).
    """
    api_key = os.environ.get("OUTSCRAPER_API_KEY", "").strip()
    if not api_key:
        return None

    cached = _outscraper_cache_load(handle)
    if cached is not None:
        return cached

    try:
        r = await client.get(
            OUTSCRAPER_API_URL,
            params={"query": handle, "async": "false"},
            headers={"X-API-KEY": api_key},
            timeout=OUTSCRAPER_TIMEOUT_S,
        )
    except (httpx.HTTPError, asyncio.TimeoutError):
        return None
    if r.status_code != 200:
        return None
    try:
        raw = r.json()
    except Exception:
        return None
    perfil = _outscraper_extrair_perfil(raw)
    if not perfil:
        return None
    _outscraper_cache_save(handle, perfil)
    return perfil


def _url_base(url: str) -> str:
    """https://www.tiosam.com.br/qualquercoisa → https://www.tiosam.com.br"""
    m = re.match(r"^(https?://[^/]+)", url)
    return m.group(1) if m else url


def _score_link(href: str, texto_ancora: str) -> int:
    """Heurística simples: + por slug positivo, - por slug negativo."""
    alvo = f"{href.lower()} {texto_ancora.lower()}"
    score = 0
    for kw in SLUG_POSITIVO:
        if kw in alvo:
            score += 2
    for kw in SLUG_NEGATIVO:
        if kw in alvo:
            score -= 3
    return score


def _descobrir_links_internos(home_html: str, url_home: str) -> list[str]:
    """
    Extrai links internos da home, rankeia por relevância, retorna
    top MAX_PAGINAS_EXTRAS URLs absolutas.
    """
    soup = BeautifulSoup(home_html, "html.parser")
    base = _url_base(url_home)
    base_host = re.sub(r"^https?://", "", base).lower()

    candidatos: dict[str, tuple[int, str]] = {}  # url → (score, ancora)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        # Normaliza pra URL absoluta
        if href.startswith("//"):
            url = "https:" + href
        elif href.startswith("/"):
            url = base + href
        elif href.startswith(("http://", "https://")):
            url = href
        else:
            url = base + "/" + href.lstrip("./")

        # Mesmo host apenas
        url_host = re.sub(r"^https?://", "", url).split("/")[0].lower()
        if url_host != base_host:
            continue
        if url == url_home or url == base or url == base + "/":
            continue
        # Filtra fragmentos e queries
        url = url.split("#")[0]

        texto = a.get_text(separator=" ", strip=True)[:80]
        score = _score_link(url, texto)
        if score <= 0:
            continue

        # Mantém o melhor score por URL única
        prev = candidatos.get(url)
        if prev is None or score > prev[0]:
            candidatos[url] = (score, texto)

    # Ordena por score desc, retorna top N
    ordenados = sorted(candidatos.items(), key=lambda kv: kv[1][0], reverse=True)
    return [url for url, _ in ordenados[:MAX_PAGINAS_EXTRAS]]


async def _coletar_site_completo(
    client: httpx.AsyncClient, url_home: str
) -> tuple[Optional[str], str, str, str]:
    """
    Baixa home + segue até MAX_PAGINAS_EXTRAS links internos relevantes
    (descobertos dinamicamente a partir do menu da home).

    Returns: (raw_html_home, texto_concatenado, meta_description, titulo)
              ou (None, "", "", "") se a home falhar.
    """
    home_html = await _fetch_url(client, url_home)
    if home_html is None:
        return None, "", "", ""

    texto_home, meta_home, titulo_home = _extrair_texto_html(home_html)
    textos_acumulados = [texto_home]

    urls_extras = _descobrir_links_internos(home_html, url_home)
    for url in urls_extras:
        sub_html = await _fetch_url(client, url)
        if sub_html is None:
            continue
        try:
            sub_texto, _sub_meta, _sub_titulo = _extrair_texto_html(sub_html)
        except Exception:
            continue
        if len(sub_texto) >= MIN_TEXTO_VALIDO:
            textos_acumulados.append(sub_texto)

    texto_final = " ".join(textos_acumulados)[:MAX_TEXTO_CHARS]
    return home_html, texto_final, meta_home, titulo_home


async def mapear_oferta_concorrente(
    *,
    nome: str,
    website: Optional[str] = None,
    instagram_handle: Optional[str] = None,
    place_id: Optional[str] = None,
    cidade: Optional[str] = None,
) -> dict:
    """
    Coleta sinais públicos do site + Instagram do concorrente. Sem LLM.

    Args:
        nome: Nome do concorrente (pra debug/log).
        website: URL do site oficial (com ou sem https://).
        instagram_handle: Handle (@xxx ou URL completa). Opcional.
        place_id: place_id do Google (pra rastreamento). Opcional.

    Returns:
        dict (de OfertaMapeada.asdict()). Sempre retorna — falhas
        ficam em `erros[]` e `confiabilidade_fonte` reflete sucesso.
    """
    o = OfertaMapeada(nome=nome, place_id=place_id)
    o.fonte_url = _normalizar_url(website)
    handle = _normalizar_handle(instagram_handle)
    o.fonte_instagram = f"@{handle}" if handle else None

    # Sem site nem IG NÃO é mais beco sem saída: a camada 3 (agregadores) ainda
    # pode achar o parceiro no Wellhub/Gurupass pelo nome (SPEC_OFERTA_AGREGADORES).
    if not o.fonte_url and not handle:
        o.erros.append("sem_site_nem_instagram")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml",
    }

    textos_pra_analise: list[str] = []

    async with httpx.AsyncClient(headers=headers) as client:
        # Site: home + subpáginas. Sequencial (não martela mesmo host).
        if o.fonte_url:
            home_html, texto_site, meta_site, titulo_site = await _coletar_site_completo(
                client, o.fonte_url
            )
            if home_html is None:
                o.erros.append("fetch_site_falhou")
            elif len(texto_site) < MIN_TEXTO_VALIDO:
                o.erros.append("site_sem_conteudo_util")
            else:
                o.fonte_url_ok = True
                o.raw_texto = texto_site
                o.raw_meta_description = meta_site
                o.titulo_site = titulo_site
                textos_pra_analise.extend([titulo_site, meta_site, texto_site])

        # Instagram: só home pública (subpáginas exigem login).
        # Cascata: 1) fetch público og:tags → 2) SearchAPI engine=instagram_profile.
        # SEM Playwright e SEM Outscraper — IG vem do SearchAPI (mesma fonte do A3a).
        if handle:
            ig_publico_util = False
            ig_url = INSTAGRAM_PUBLIC_URL.format(handle=handle)
            ig_html = await _fetch_url(client, ig_url)
            if ig_html is None:
                o.erros.append("fetch_instagram_publico_falhou")
            else:
                try:
                    texto_ig, meta_ig, titulo_ig = _extrair_texto_html(ig_html)
                except Exception as exc:
                    o.erros.append(f"parse_instagram_falhou:{type(exc).__name__}")
                    texto_ig = meta_ig = titulo_ig = ""
                if bool(meta_ig) or len(texto_ig) >= MIN_TEXTO_VALIDO:
                    ig_publico_util = True
                    o.fonte_instagram_ok = True
                    if not o.raw_meta_description:
                        o.raw_meta_description = meta_ig
                    textos_pra_analise.extend([titulo_ig, meta_ig, texto_ig])
                else:
                    o.erros.append("instagram_publico_sem_conteudo")

            # Fallback SearchAPI (engine=instagram_profile) só se o público não veio útil.
            # get_instagram_profile é síncrono (requests) → to_thread p/ não travar o loop.
            if not ig_publico_util:
                from tools.instagram_profile import get_instagram_profile

                perfil = await asyncio.to_thread(get_instagram_profile, handle)
                if perfil is None:
                    if os.environ.get("SEARCHAPI_KEY", "").strip():
                        o.erros.append("searchapi_instagram_sem_perfil_ou_rate_limit")
                    else:
                        o.erros.append("searchapi_desabilitado_sem_key")
                else:
                    o.fonte_instagram_ok = True
                    bio = perfil.get("bio") or ""
                    full = perfil.get("name") or ""
                    composto = " ".join([full, bio]).strip()
                    if not o.raw_meta_description and bio:
                        o.raw_meta_description = bio[:500]
                    if composto:
                        textos_pra_analise.append(composto)
                    o.erros.append("instagram_via_searchapi")  # marcador, não é erro real

        # Camada 3 — agregadores (Wellhub SSR, Gurupass parcial, TotalPass snippet).
        # Fail-soft total; extras vão pra campos próprios. Textos de agregador ficam
        # num blob SEPARADO: contêm preços de TIER (199/319/439) e de vizinhos — se
        # entrassem no blob geral virariam falso preço de balcão em precos_encontrados.
        textos_agregador: list[str] = []
        try:
            from tools.agregadores_fetcher import coletar_agregadores

            ag = await coletar_agregadores(client, nome, cidade)
            if ag.get("fontes_ok"):
                o.fontes_agregador = ag["fontes_ok"]
                textos_agregador = [t for t in ag.get("textos", []) if t]
                extras = ag.get("extras") or {}
                o.tier_agregador = extras.get("tier_agregador")
                o.rating_agregador = extras.get("rating_agregador")
                o.comodidades_agregador = extras.get("comodidades") or []
                if not handle and extras.get("instagram_handle"):
                    o.fonte_instagram = f"@{extras['instagram_handle']}"
        except Exception as exc:
            o.erros.append(f"agregadores_falhou:{type(exc).__name__}")

    texto_completo = " ".join(t for t in textos_pra_analise if t)
    if texto_completo:
        o.modalidades_keywords = _detectar_modalidades(texto_completo)
        o.diferenciais_keywords = _detectar_diferenciais(texto_completo)
        o.precos_encontrados = _detectar_precos(texto_completo)
    if textos_agregador:
        texto_ag = " ".join(textos_agregador)
        o.modalidades_keywords = sorted(set(o.modalidades_keywords) | set(_detectar_modalidades(texto_ag)))
        o.diferenciais_keywords = sorted(set(o.diferenciais_keywords) | set(_detectar_diferenciais(texto_ag)))

    o.confiabilidade_fonte = _calcular_confiabilidade(o)
    return o.asdict()


if __name__ == "__main__":
    import json
    import sys

    casos = [
        {
            "nome": "Tio Sam",
            "website": "https://www.tiosam.com.br/",
            "instagram_handle": None,
            "place_id": "smoke_tiosam",
        },
        {
            "nome": "Body Armor Piratininga",
            "website": None,
            "instagram_handle": "bodyarmour.piratininga",
            "place_id": "smoke_bodyarmor",
        },
        {
            "nome": "Sem fonte",
            "website": None,
            "instagram_handle": None,
            "place_id": "smoke_none",
        },
    ]

    async def _run_smoke() -> int:
        falhas = 0
        for c in casos:
            print(f"\n=== {c['nome']} ===")
            out = await mapear_oferta_concorrente(**c)
            preview = {**out}
            if preview.get("raw_texto") and len(preview["raw_texto"]) > 240:
                preview["raw_texto"] = preview["raw_texto"][:240] + "...[truncated]"
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            if c["nome"] == "Tio Sam":
                if not out["fonte_url_ok"]:
                    print(">>> FALHA: site Tio Sam não retornou")
                    falhas += 1
                elif "piscina" not in out["modalidades_keywords"] or "area_kids" not in out["modalidades_keywords"]:
                    print(f">>> ATENÇÃO: esperado piscina+area_kids, achou {out['modalidades_keywords']}")
                else:
                    print(">>> OK: piscina + area_kids detectados na Tio Sam")
        return falhas

    sys.exit(asyncio.run(_run_smoke()))
