# tools/deep_research_tool.py
"""
Deep Research integration via google-genai (Gemini Deep Research model).

Características:
- Cache em market_context/{cidade}_{bairro}.md (TTL 7 dias)
- Timeout 5 min com threading (não trava o pipeline ADK)
- Fallback briefing padrão quando API falha ou estoura prazo
- Tools: google_search + url_context (research na web em tempo real)
"""
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# Constantes
CACHE_TTL_DIAS = 7
TIMEOUT_SEGUNDOS = 300  # 5 min
DEEP_RESEARCH_MODEL = "deep-research-max-preview-04-2026"
CACHE_DIR = Path(__file__).resolve().parent.parent / "market_context"


def _slug(s: str) -> str:
    """Converte texto em slug seguro para nome de arquivo."""
    s = s.strip().lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _cache_path(cidade: str, bairro: str) -> Path:
    return CACHE_DIR / f"{_slug(cidade)}_{_slug(bairro)}.md"


def _cache_valido(path: Path) -> bool:
    if not path.exists():
        return False
    idade = time.time() - path.stat().st_mtime
    return idade < CACHE_TTL_DIAS * 24 * 3600


def _briefing_padrao(cidade: str, bairro: str) -> str:
    """Briefing fallback quando Deep Research falha ou expira."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    return f"""# Briefing de Mercado — {bairro}, {cidade}

**Data:** {hoje}
**Status:** Deep Research indisponível — usando briefing padrão

## ⚠️ Aviso
Esta análise foi gerada como fallback. Para dados completos e atualizados,
a API Deep Research precisa estar acessível. Os agentes do pipeline
seguintes operarão com benchmarks setoriais (ACAD/Sebrae) e dados públicos
do IBGE como fonte primária.

## MERCADO FITNESS LOCAL
- Dados não disponíveis em tempo real
- Use benchmarks ACAD: ticket médio nacional R$149,90; redes dominantes
  Smart Fit, Selfit, BlueFit (low cost), Bodytech (mid/premium)

## PERFIL SOCIOECONÔMICO
- Use dados IBGE (DemoAnalyst A2)
- Renda média do estado como proxy quando renda do bairro indisponível

## MERCADO IMOBILIÁRIO COMERCIAL
- Use benchmark `BENCHMARKS_ALUGUEL` em financial_tools.py
- Faixa típica capitais Norte/Nordeste: R$18-60/m²
- Capitais Sul/Sudeste: R$25-150/m²

## REGULAMENTAÇÃO
- Alvará de funcionamento municipal
- Registro CREF (Conselho Regional de Educação Física)
- Norma técnica ABNT NBR 16604 (academias de ginástica)

## TENDÊNCIAS
- Modelo low-cost continua liderando captação por volume
- Premium cresce em bairros de classe média alta
- 24h e operação flexível são diferenciais consolidados
"""


def _build_query(cidade: str, bairro: str) -> str:
    return f"""Pesquise profundamente sobre o mercado fitness em {bairro}, {cidade}, Brasil:

## 1. MERCADO FITNESS LOCAL
- Quais redes de academia operam em {cidade}? Quantas unidades de cada?
- Ticket médio praticado pelas academias em {cidade} (R$/mês)
- Planos de expansão de redes conhecidas para {bairro}?

## 2. PERFIL SOCIOECONÔMICO DE {bairro}
- Renda média dos moradores (fontes: IBGE, reportagens, dados oficiais)
- Faixa etária predominante
- Crescimento populacional recente

## 3. MERCADO IMOBILIÁRIO COMERCIAL
- Preço médio de aluguel comercial por m² em {bairro}, {cidade}
- Tendência: subindo, estável ou caindo?

## 4. REGULAMENTAÇÃO
- Requisitos de alvará para academia em {cidade}
- Exigências do CREF regional

## 5. TENDÊNCIAS FITNESS EM {cidade}
- Notícias recentes sobre abertura/fechamento de academias
- Modalidades mais demandadas

Entregue relatório estruturado em markdown com fontes (URLs ou nome de portais)
ao final de cada seção. Foque em dados quantitativos (números, faixas, datas).
"""


# Fallback usa gemini-2.5-flash (free tier OK; pro está bloqueado em quota=0).
# Quando a conta tiver billing ativo, considere mudar para "gemini-2.5-pro"
# (resposta mais profunda) ou para o modelo deep-research-max quando ele
# for exposto na Interactions API pública.
FALLBACK_MODEL = "gemini-2.5-flash"


def _extrair_texto(response) -> str:
    """Extrai texto de resposta google-genai (handles vários formatos)."""
    if hasattr(response, "text") and response.text:
        return response.text
    if hasattr(response, "candidates") and response.candidates:
        chunks = []
        for cand in response.candidates:
            if hasattr(cand, "content") and cand.content:
                for part in getattr(cand.content, "parts", []) or []:
                    if hasattr(part, "text") and part.text:
                        chunks.append(part.text)
        if chunks:
            return "\n".join(chunks)
    return ""


def _executar_deep_research(query: str) -> str:
    """
    Chamada efetiva à API Gemini Deep Research.

    Estratégia em 2 tiers:
    1. Tenta Interactions API (chats) com modelo deep-research preview
    2. Se modelo não disponível ou erro, fallback para gemini-2.5-pro
       com google_search + url_context (research grounded "lite")
    """
    from google.genai import types
    from tools._genai_client import build_genai_client

    client = build_genai_client()

    config = types.GenerateContentConfig(
        tools=[
            types.Tool(google_search=types.GoogleSearch()),
            types.Tool(url_context=types.UrlContext()),
        ],
    )

    # ── Tier 1: Interactions API (chats) com deep-research model ──
    try:
        chat = client.chats.create(model=DEEP_RESEARCH_MODEL, config=config)
        response = chat.send_message(query)
        texto = _extrair_texto(response)
        if texto:
            return texto
    except Exception as e:
        primeiro_erro = e

    # ── Tier 2: fallback gemini-2.5-flash com retry exponencial ──
    # 503 Service Unavailable é transitório. Tenta 3x com backoff 2/4/8s.
    backoffs = [2, 4, 8]
    ultimo_erro_tier2 = None
    for tentativa, delay in enumerate(backoffs, start=1):
        try:
            response = client.models.generate_content(
                model=FALLBACK_MODEL,
                contents=query,
                config=config,
            )
            texto = _extrair_texto(response)
            if texto:
                return texto
            ultimo_erro_tier2 = "Resposta vazia"
        except Exception as e:
            ultimo_erro_tier2 = e
            erro_str = str(e)
            # Só faz sentido retry em erros transitórios
            transient = any(t in erro_str for t in ["503", "UNAVAILABLE", "timed out", "504"])
            if not transient:
                break
            if tentativa < len(backoffs):
                time.sleep(delay)

    raise RuntimeError(
        f"Deep Research falhou em ambos os tiers. "
        f"Tier1 ({DEEP_RESEARCH_MODEL}): {primeiro_erro}. "
        f"Tier2 ({FALLBACK_MODEL}, {len(backoffs)} tentativas): {ultimo_erro_tier2}"
    )


def rodar_deep_research(cidade: str, bairro: str) -> str:
    """
    Executa Deep Research para o par (cidade, bairro), com cache + timeout + fallback.

    Returns:
        Markdown com briefing de mercado. Sempre retorna algo — nunca lança exceção.
    """
    # 1) Cache hit?
    cache = _cache_path(cidade, bairro)
    if _cache_valido(cache):
        return cache.read_text(encoding="utf-8")

    # 2) Executar com timeout
    query = _build_query(cidade, bairro)
    resultado = None

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_executar_deep_research, query)
            try:
                resultado = future.result(timeout=TIMEOUT_SEGUNDOS)
            except FuturesTimeout:
                resultado = None
    except Exception:
        resultado = None

    # 3) Salvar cache se sucesso
    if resultado:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            header = (
                f"<!-- Deep Research cache\n"
                f"     cidade: {cidade}\n"
                f"     bairro: {bairro}\n"
                f"     data: {datetime.now().isoformat()}\n"
                f"-->\n\n"
            )
            cache.write_text(header + resultado, encoding="utf-8")
        except Exception:
            pass  # cache é nice-to-have; resultado já foi obtido
        return resultado

    # 4) Fallback briefing
    return _briefing_padrao(cidade, bairro)
