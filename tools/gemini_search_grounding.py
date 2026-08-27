# tools/gemini_search_grounding.py
"""
Wrapper de função (não-AgentTool) para Gemini Search Grounding.

Por que existe:
- AgentTool(A7 MarketResearch) NÃO tem retry built-in
- 503 UNAVAILABLE transient + 429 RESOURCE_EXHAUSTED quebram ParallelAnalysis inteira
- Função custom permite retry com backoff + cache persistente

Otimizações implementadas (VEC-379 fase 1):
1. Cache persistente em disco (TTL 7 dias) — evita refazer mesma query
2. 429 RESOURCE_EXHAUSTED tratado como transient com backoff exponencial
3. Backoff mais agressivo (10/30/60/120/240s) para respeitar rate limits
4. Rate limiter interno (semáforo) — evita disparo paralelo simultâneo

Usar em vez de AgentTool quando precisar de robustez:
    A3, A4 chamam pesquisar_no_google_grounding(query) → str
"""
import os
import time
import asyncio
import hashlib
import json
import random
from pathlib import Path
from typing import Optional

# Modelo padrão para grounding (Pro tem free tier zerado, Flash funciona)
GROUNDING_MODEL = "gemini-3.6-flash"
TIMEOUT_SEGUNDOS = 60

# Backoff exponencial: 5s → 10s → 20s → 40s → 60s (5 tentativas, max 60s).
# Versão anterior era [10,30,60,120,240]s — 240s era espera demais por chamada
# falha (Run 17 levou 11 min só de retry). Limite atual de 60s ainda dá margem
# para o rate limit do Gemini Flash liberar (RPM reseta a cada 60s).
RETRY_BACKOFFS = [5, 10, 20, 40, 60]

# Cache persistente em disco — mesmas queries em runs diferentes reusam
# resultado por até 7 dias, eliminando a maioria das chamadas redundantes
# que estouravam quota.
CACHE_DIR = Path(__file__).resolve().parent.parent / "metrics" / "grounding_cache"
CACHE_TTL_SEGUNDOS = 7 * 24 * 3600  # 7 dias

# Rate limiter interno: semáforo limita disparos paralelos ao mesmo tempo.
# Plano pago padrão Gemini Flash = 15 RPM = 4s entre calls. Com 4 simultâneas
# (A3a + A4 em paralelo), facilmente estoura. Limita a 2 chamadas concorrentes.
_GROUNDING_SEMAPHORE: Optional[asyncio.Semaphore] = None
_GROUNDING_MAX_CONCURRENT = 2

# Lista de erros tratados como transient (para retry).
_TRANSIENT_KEYWORDS = (
    "503", "504", "UNAVAILABLE", "timed out", "high demand",
    "429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "Too Many Requests",
    "DEADLINE_EXCEEDED",
)


def _cache_key(query: str, override: Optional[str] = None) -> str:
    """
    SHA256 da query — chave estável de cache.

    `override` permite passar uma chave canônica derivada de input estruturado
    (ex: hash de `tipo_relatorio:cidade:bairro:concorrente`) para garantir
    cache hit mesmo se a redação da query variar entre runs. Preparado para
    o CRUD futuro onde inputs vêm de formulário, não de prompt livre.
    """
    base = override.strip() if override else query.strip()
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


# Estatísticas de cache — escritas em metrics/grounding_cache_stats.json
# para mensurar efetividade do cache ao longo dos runs.
_STATS_PATH = CACHE_DIR / "_stats.json"


def _bump_stat(key: str) -> None:
    """Incrementa contador de hit/miss em arquivo JSON. Best-effort."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if _STATS_PATH.exists():
            stats = json.loads(_STATS_PATH.read_text(encoding="utf-8"))
        else:
            stats = {"hit": 0, "miss": 0, "error": 0, "primeiro_run": time.time()}
        stats[key] = stats.get(key, 0) + 1
        stats["ultimo_run"] = time.time()
        _STATS_PATH.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _ler_cache(query: str, cache_key_override: Optional[str] = None) -> Optional[str]:
    """Tenta ler cache em disco. Retorna texto se válido (TTL), senão None."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / f"{_cache_key(query, cache_key_override)}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("timestamp", 0)
        if time.time() - ts > CACHE_TTL_SEGUNDOS:
            return None  # expirou
        return data.get("text")
    except Exception:
        return None


def _gravar_cache(query: str, text: str, cache_key_override: Optional[str] = None) -> None:
    """Grava resultado em cache. Não bloqueia em caso de erro."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / f"{_cache_key(query, cache_key_override)}.json"
        path.write_text(
            json.dumps({
                "timestamp": time.time(),
                "query": query[:200],  # primeiros 200 chars pra debug
                "cache_key_override": cache_key_override,
                "text": text,
            }, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # cache é best-effort


def _executar_grounding_sync(query: str, cache_key_override: Optional[str] = None) -> str:
    """Chamada síncrona com cache + retry. Roda em thread via asyncio.to_thread."""
    from tools.pipeline_model import gemini_side_tools_ok

    if not gemini_side_tools_ok():
        cached = _ler_cache(query, cache_key_override)
        if cached is not None:
            _bump_stat("hit")
            return cached + "\n\n[cache hit]"
        return "[Search Grounding off — Gemini/Vertex desligado no pipeline NVIDIA]"

    # 1. Cache local (disco)
    cached = _ler_cache(query, cache_key_override)
    if cached is not None:
        _bump_stat("hit")
        return cached + "\n\n[cache hit]"

    # 2. LangCache semântico (Redis Cloud)
    from tools.langcache_client import langcache_search, langcache_set

    lc_cached = langcache_search(query)
    if lc_cached is not None:
        _bump_stat("langcache_hit")
        _gravar_cache(query, lc_cached, cache_key_override)
        return lc_cached + "\n\n[langcache hit]"

    _bump_stat("miss")

    from google.genai import types
    from tools._genai_client import build_genai_client, generate_content_resilient

    try:
        client = build_genai_client()
    except RuntimeError as e:
        return f"[ERRO: {e}]"
    config = types.GenerateContentConfig(
        tools=[
            types.Tool(google_search=types.GoogleSearch()),
            types.Tool(url_context=types.UrlContext()),
        ],
    )

    last_error = None
    for tentativa, delay in enumerate(RETRY_BACKOFFS, start=1):
        try:
            response = generate_content_resilient(
                client,
                model=GROUNDING_MODEL,
                contents=query,
                config=config,
                max_retries=3,
                base_delay=4.0,
            )
            # Extrai texto
            text = None
            if hasattr(response, "text") and response.text:
                text = response.text
            elif hasattr(response, "candidates") and response.candidates:
                chunks = []
                for cand in response.candidates:
                    if hasattr(cand, "content") and cand.content:
                        for part in getattr(cand.content, "parts", []) or []:
                            if hasattr(part, "text") and part.text:
                                chunks.append(part.text)
                if chunks:
                    text = "\n".join(chunks)

            if text:
                _gravar_cache(query, text, cache_key_override)
                langcache_set(query, text)
                return text
            last_error = "resposta vazia"
        except Exception as e:
            last_error = e
            erro_str = str(e)
            transient = any(t in erro_str for t in _TRANSIENT_KEYWORDS)
            if not transient:
                break  # erro permanente, não retenta
            if tentativa < len(RETRY_BACKOFFS):
                # Jitter de ±20% para dispersar retries paralelos e evitar
                # thundering herd quando múltiplos agentes batem no rate limit.
                jitter = random.uniform(0.8, 1.2)
                time.sleep(delay * jitter)

    _bump_stat("error")
    return (
        f"[Search Grounding indisponível após {len(RETRY_BACKOFFS)} tentativas: "
        f"{str(last_error)[:200]}]"
    )


def _get_semaphore() -> asyncio.Semaphore:
    """Lazy init do semáforo — precisa ser criado dentro de event loop ativo."""
    global _GROUNDING_SEMAPHORE
    if _GROUNDING_SEMAPHORE is None:
        _GROUNDING_SEMAPHORE = asyncio.Semaphore(_GROUNDING_MAX_CONCURRENT)
    return _GROUNDING_SEMAPHORE


async def pesquisar_no_google_grounding(
    query: str,
    cache_key: Optional[str] = None,
) -> str:
    """
    Faz pesquisa no Google via Gemini Search Grounding com cache + retry/backoff.

    Otimizações:
    - Cache persistente em disco (TTL 7 dias) — evita refazer mesma query
    - 429 RESOURCE_EXHAUSTED + 503 UNAVAILABLE tratados como transient
    - Backoff exponencial com jitter (10/30/60/120/240s)
    - Rate limiter (máx 2 chamadas concorrentes) para respeitar plano Flash 15 RPM
    - `cache_key` opcional: chave canônica derivada de input estruturado
      (ex: "aluguel:fortaleza:meireles:1250m2") — preparado para o CRUD futuro
      onde inputs vêm de formulário, não de prompt livre

    Args:
        query: pergunta em linguagem natural pra pesquisar no Google
        cache_key: chave de cache canônica opcional. Se omitida, usa hash da query.

    Returns:
        Texto da resposta com citações OU mensagem de erro graceful.
    """
    try:
        async with _get_semaphore():
            return await asyncio.to_thread(_executar_grounding_sync, query, cache_key)
    except Exception as e:
        return f"[Erro inesperado em pesquisar_no_google_grounding: {str(e)[:200]}]"


def get_cache_stats() -> dict:
    """Retorna stats de hit/miss/error do cache. Útil pra relatórios de fase."""
    try:
        if _STATS_PATH.exists():
            return json.loads(_STATS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"hit": 0, "miss": 0, "error": 0}


# ── Aluguel comercial — mediana de 3 queries paralelas (Task #47 VEC) ──
import re

# Regex que captura padrões R$/m² em múltiplos formatos.
# Range [5, 500] R$/m² filtra outliers absurdos (preços de venda, m² errado).
#
# Refinamento Fase 1 (Task #58): adicionados 6 patterns adicionais pra
# capturar formatos "R$ X por metro quadrado", "X reais/m2", "X,XX o m²",
# "varia entre X e Y", "média de R$ X", etc. Cobre redação livre do
# Search Grounding com muito mais tolerância.
_ALUGUEL_PATTERNS = [
    # Range "R$ X a R$ Y / m²" — capta os 2 valores (1 e 2)
    re.compile(r"R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\s*(?:a|até|-|–|—|e)\s*R?\$?\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\s*/?\s*m[²2]", re.IGNORECASE),
    # Range "varia entre R$ X e R$ Y" sem /m² explícito perto
    re.compile(r"(?:entre|varia|de|faixa)\s+R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\s+(?:a|até|-|–|—|e)\s+R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\b", re.IGNORECASE),
    # Pontual "R$ X/m²" ou "R$ X / m²" ou "R$X.XX m2"
    re.compile(r"R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\s*[/\\]?\s*m[²2]", re.IGNORECASE),
    # "R$ X por metro quadrado" / "R$ X por m²"
    re.compile(r"R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\s+(?:por\s+)?m(?:[²2]|etro)", re.IGNORECASE),
    # "X reais por m²" / "X reais o metro quadrado"
    re.compile(r"([\d]{1,3}(?:[\.,]\d{1,2})?)\s*reais?\s*(?:o|por|/|\b)\s*m(?:[²2]|etro)", re.IGNORECASE),
    # "média de R$ X" / "mediana R$ X" / "ticket médio R$ X"
    re.compile(r"(?:média|mediana|m[ée]dio|valor\s+m[ée]dio|ticket\s+m[ée]dio)\s+(?:de\s+)?R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\s*/?\s*(?:por\s+)?m?(?:[²2]|etro)?", re.IGNORECASE),
    # "valor do m² em torno de R$ X" / "m² gira em torno de R$ X"
    re.compile(r"(?:m[²2]|metro\s+quadrado).{0,40}?R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)", re.IGNORECASE),
    # "R$ X/m² mensais" / "R$ X mensais por m²"
    re.compile(r"R\$\s*([\d]{1,3}(?:[\.,]\d{1,2})?)\s*(?:mensais?|/mês)?\s*[/\\]?\s*m[²2]", re.IGNORECASE),
]


def _extrair_valores_aluguel_m2(texto: str) -> list[float]:
    """
    Extrai todos os valores numéricos R$/m² mencionados num texto livre.
    Filtra outliers (5 < x < 500). Retorna lista de floats deduplicada.
    """
    valores: set[float] = set()
    for pat in _ALUGUEL_PATTERNS:
        for m in pat.finditer(texto):
            for grupo in m.groups():
                if grupo is None:
                    continue
                try:
                    v = float(grupo.replace(".", "").replace(",", "."))
                except ValueError:
                    continue
                if 5.0 <= v <= 500.0:
                    valores.add(round(v, 2))
    return sorted(valores)


def _mediana(valores: list[float]) -> float:
    """Mediana simples (sem numpy)."""
    if not valores:
        return 0.0
    s = sorted(valores)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return round((s[n // 2 - 1] + s[n // 2]) / 2, 2)


def _percentil(valores: list[float], p: float) -> float:
    """
    Percentil interpolado linear. p em [0, 1]. Pra IQR usar p=0.25 e p=0.75.
    """
    if not valores:
        return 0.0
    s = sorted(valores)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    if f == c:
        return s[f]
    d = k - f
    return s[f] + (s[c] - s[f]) * d


def _filtrar_outliers_iqr(valores: list[float], threshold: float = 1.5) -> tuple[list[float], list[float]]:
    """
    Remove outliers usando regra IQR (Interquartile Range).

    Retorna (valores_filtrados, valores_descartados).
    Em distribuições mistas (comercial + residencial barato), os
    valores residenciais ficam abaixo do limite inferior Q1 - threshold*IQR
    e são descartados pra estabilizar a mediana comercial.

    Threshold padrão 1.5 é o convencional (Tukey). Pra ser mais agressivo
    (descartar mais), usar 1.0.
    """
    if len(valores) < 4:
        # Com < 4 amostras IQR não faz sentido; devolve sem filtrar
        return list(valores), []

    q1 = _percentil(valores, 0.25)
    q3 = _percentil(valores, 0.75)
    iqr = q3 - q1
    limite_inferior = q1 - threshold * iqr
    limite_superior = q3 + threshold * iqr

    mantidos = [v for v in valores if limite_inferior <= v <= limite_superior]
    descartados = [v for v in valores if v < limite_inferior or v > limite_superior]
    return mantidos, descartados


async def pesquisar_aluguel_mediana(
    bairro: str,
    cidade: str,
    uf: str = "",
    area_m2_min: int = 1000,
    area_m2_max: int = 1500,
) -> dict:
    """
    Faz 3 queries Search Grounding em paralelo pedindo aluguel comercial
    e calcula mediana dos valores R$/m² extraídos. Reduz variância de uma
    única consulta (que pode pegar outlier do dia).

    Cada query foca num ângulo diferente:
      1. Geral: "aluguel médio comercial em <bairro>"
      2. Por tipo: "salão comercial / loja grande pra alugar em <bairro>"
      3. Por área: "imóvel comercial 1000-1500m² em <bairro>"

    Args:
        bairro, cidade, uf: localização.
        area_m2_min/max: faixa de área para uma das queries.

    Returns:
        dict {
          "mediana_r_m2": float,        # R$/m² mediana
          "min_r_m2": float,
          "max_r_m2": float,
          "valores_coletados": [float], # todos extraídos das 3 respostas
          "total_queries": 3,
          "queries_com_dados": int,     # quantas extraíram >=1 valor
          "fontes": [{query, n_valores, valores}],
        }

        Se NENHUMA query retornar valores parseáveis, mediana_r_m2=0.0
        (caller deve fallback pro benchmark ACAD).
    """
    local = f"{bairro}, {cidade}" + (f", {uf}" if uf else "")
    queries = [
        (
            f"Qual o aluguel comercial médio por m² em {local} em 2026? "
            f"Cite valores reais com fonte (VivaReal, ZAP, OLX, imobiliárias)."
        ),
        (
            f"Quanto custa alugar um salão comercial ou loja de grande porte "
            f"em {local}? Valores em R$/m² mensais, 2026, fontes."
        ),
        (
            f"Imóveis comerciais entre {area_m2_min} e {area_m2_max} m² para "
            f"alugar em {local}: faixa de preço por m² em 2026, com fontes."
        ),
    ]

    # Cache keys canônicas — independente do texto exato, baseiam-se no
    # input estruturado. Permite reuso entre runs idênticos (CRUD futuro).
    cache_keys = [
        f"aluguel_mediana_v1:geral:{bairro}:{cidade}:{uf}".lower(),
        f"aluguel_mediana_v1:salao:{bairro}:{cidade}:{uf}".lower(),
        f"aluguel_mediana_v1:area:{bairro}:{cidade}:{uf}:{area_m2_min}_{area_m2_max}".lower(),
    ]

    # Dispara em paralelo (semáforo interno do pesquisar_no_google_grounding
    # garante que não passa de _GROUNDING_MAX_CONCURRENT)
    respostas = await asyncio.gather(
        *[
            pesquisar_no_google_grounding(q, cache_key=ck)
            for q, ck in zip(queries, cache_keys)
        ],
        return_exceptions=True,
    )

    fontes: list[dict] = []
    valores_por_query: list[list[float]] = [[], [], []]
    queries_com_dados = 0

    for i, (q, resp) in enumerate(zip(queries, respostas)):
        if isinstance(resp, Exception) or not isinstance(resp, str):
            fontes.append({"query": q[:80], "n_valores": 0, "valores": [], "erro": str(resp)[:100]})
            continue
        if resp.startswith("[Search Grounding indisponível") or resp.startswith("[Erro"):
            fontes.append({"query": q[:80], "n_valores": 0, "valores": [], "erro": resp[:100]})
            continue
        valores = _extrair_valores_aluguel_m2(resp)
        if valores:
            queries_com_dados += 1
            valores_por_query[i] = valores
        fontes.append({
            "query": q[:80],
            "n_valores": len(valores),
            "valores": valores,
            "mediana_query": _mediana(valores) if valores else 0.0,
        })

    # ── Estratégia de detecção de diluição residencial ──
    # Query 0 (geral) costuma pegar imóveis residenciais que diluem a mediana.
    # Se a mediana das queries comerciais (2 ou 3) é >> mediana geral (>1.5×),
    # descartamos a geral pra evitar viés residencial.
    medianas = [_mediana(v) if v else 0.0 for v in valores_por_query]
    mediana_geral = medianas[0]
    medianas_comerciais = [m for m in (medianas[1], medianas[2]) if m > 0]
    descarta_geral = False
    motivo_descarte: str | None = None

    if mediana_geral > 0 and medianas_comerciais:
        # Pega a MAIOR mediana comercial pra comparar (mais conservador)
        max_comercial = max(medianas_comerciais)
        # Threshold reduzido de 1.5× pra 1.33× (era muito conservador — Run Eusébio
        # 11/05 mostrou que diluição sutil não era detectada)
        if max_comercial > 1.33 * mediana_geral:
            descarta_geral = True
            motivo_descarte = (
                f"Mediana geral R$ {mediana_geral:.0f}/m² abaixo da "
                f"comercial R$ {max_comercial:.0f}/m² (>1,33×) → "
                f"provável diluição por imóveis residenciais"
            )

    if descarta_geral:
        # Só queries 2 e 3
        todos_valores = valores_por_query[1] + valores_por_query[2]
    else:
        # Todas as queries com peso 1:2:2 (comerciais valem 2× pq mais
        # específicas pro caso de uso academia 1000-1500m²)
        todos_valores = (
            valores_por_query[0]
            + valores_por_query[1] * 2
            + valores_por_query[2] * 2
        )

    # Filtro IQR no resultado final pra remover outliers extremos remanescentes
    valores_filtrados, valores_descartados = _filtrar_outliers_iqr(
        sorted(todos_valores), threshold=1.5
    )

    # Estimativa final: percentil 60 (não mediana) pra ser mais conservador
    # contra subestimação. Academia precisa de imóvel comercial em avenida
    # principal — geralmente acima da mediana do mercado. Eusébio Run 11/05
    # mostrou que mediana pura subestima quando há mistura de tipos.
    mediana = _percentil(valores_filtrados, 0.60) if valores_filtrados else 0.0
    return {
        "mediana_r_m2": mediana,
        "min_r_m2": min(valores_filtrados) if valores_filtrados else 0.0,
        "max_r_m2": max(valores_filtrados) if valores_filtrados else 0.0,
        "valores_coletados": sorted(set(todos_valores)),
        "valores_filtrados_iqr": sorted(set(valores_filtrados)),
        "valores_descartados_iqr": sorted(set(valores_descartados)),
        "medianas_por_query": medianas,
        "diluicao_residencial_detectada": descarta_geral,
        "motivo_descarte_query_geral": motivo_descarte,
        "total_queries": len(queries),
        "queries_com_dados": queries_com_dados,
        "fontes": fontes,
        "metodologia": (
            "Mediana de R$/m² de 3 queries paralelas Search Grounding. "
            "Detecção de diluição residencial: se mediana geral < 67% da "
            "mediana comercial, descarta a geral. Senão, queries comerciais "
            "recebem peso 2× vs geral. IQR threshold 1.5 remove outliers extremos."
        ),
    }
