
# tools/competitor_tools.py
"""Inteligência competitiva profunda: busca, reviews, gap analysis."""
import logging
import math
import json
import httpx

logger = logging.getLogger(__name__)
from tools.google_maps_key import get_google_maps_api_key
from tools.maps_tools import calcular_distancia_km, geocode_endereco
PLACES_BASE = "https://places.googleapis.com/v1/places"


# ── Vocabulário de serviços e dores do setor fitness ──────────────
SERVICOS_ACADEMIA = [
    "musculação", "musculacao", "spinning", "crossfit", "yoga", "pilates",
    "funcional", "natação", "natacao", "lutas", "boxe", "muay thai", "jiu-jitsu",
    "dança", "danca", "personal trainer", "personal", "nutricionista",
    "avaliação física", "avaliacao fisica", "sauna", "estacionamento",
    "app próprio", "app", "24 horas", "24h", "plano mensal", "plano trimestral",
    "área kids", "area kids", "aulas coletivas", "equipamentos novos",
    "vestiário", "vestiario", "ar condicionado", "climatizado",
]

DORES_COMUNS = [
    "muito cheio", "lotado", "lotação",
    "equipamentos quebrados", "quebrado", "quebrada", "manutenção",
    "sem ar condicionado", "calor", "abafado",
    "instrutores ruins", "atendimento ruim", "grosseiro",
    "sem estacionamento", "sem vaga",
    "mensalidade cara", "caro", "preço alto",
    "fila nas máquinas", "fila",
    "banheiros sujos", "limpeza", "sujo",
    "sem professor", "sozinho", "abandonado",
    "música alta", "barulho",
    "cancela plano difícil", "cancelamento", "fidelidade", "multa",
    "cobrança indevida", "abusivo",
    "sem aulas coletivas",
    "estrutura velha", "antigo",
]


# ── Taxonomia fechada de dores (Task #46 — VEC) ─────────────────────
# Categorias canônicas usadas pelo classificador semântico Gemini.
# Mantidas em PT-BR e em formato slug (sem espaços/acentos) pra agregação
# determinística em `analisar_gap_competitivo`.
DORES_TAXONOMIA = [
    "lotacao",                  # cheio, fila, espera por equipamento
    "equipamento_problema",     # quebrado, sem manutenção, sucateado
    "climatizacao",             # ar condicionado fraco, abafado, calor
    "limpeza_higiene",          # banheiros sujos, falta limpeza
    "atendimento_ruim",         # recepção, instrutor grosseiro
    "preco_alto",               # mensalidade, taxas extras
    "contrato_abusivo",         # cancelamento, multa, cobrança indevida
    "estacionamento",           # sem vaga, vagas pagas
    "estrutura_envelhecida",    # equipamentos antigos, falta reforma
    "ruido_alto",               # música alta, barulho excessivo
    "horarios_limitados",       # não 24h, fechado feriado
    "ausencia_servico",         # falta aula coletiva, sem personal, sem app
    "seguranca",                # furto, falta de segurança no entorno
    "outra",                    # ruído indevido, pinga em outra categoria
]


def _classificar_dor_substring(texto_low: str) -> list[str]:
    """
    Fallback determinístico — substring matching original (DORES_COMUNS).
    Usado quando o classificador semântico Gemini falha ou é desabilitado.
    Retorna lista de strings literais do DORES_COMUNS que casaram.
    """
    return [d for d in DORES_COMUNS if d in texto_low]


def classificar_dores_reviews_batch_gemini(
    concorrentes_com_reviews: list[dict],
    max_chars_por_review: int = 350,
) -> dict:
    """
    Task #46 — Classificador SEMÂNTICO de dores via Gemini Flash em batch único.

    Por que existe: o substring matching (DORES_COMUNS) gera falsos positivos
    cegos ("muito cheio de equipamentos novos" vira dor "muito cheio") e
    falsos negativos ("perdi a paciência com a recepção" não bate nada).
    Substituir por Gemini classificando contra taxonomia fechada elimina
    ambos.

    Por que batch único: classificar 1 review por chamada = 25 chamadas pra
    5 concorrentes × 5 reviews. Em 1 chamada batch (mesmo prompt, todas as
    reviews) o custo cai pra ~1 chamada de ~5k tokens = R$ 0,02.

    Args:
        concorrentes_com_reviews: lista de dicts com chave `nome` e `reviews`
            (cada review tem `quote_curta` e `rating`).
        max_chars_por_review: trunca cada review pra evitar prompt gigante.

    Returns:
        dict { "<nome_concorrente>": { "<idx_review>": {
            "categoria_dor": str,           # uma das DORES_TAXONOMIA
            "sinal": "positivo"|"neutro"|"negativo",
            "confianca": "alta"|"media"|"baixa"
        }}}

        Se Gemini falhar, retorna {} (caller deve usar fallback substring).
    """
    if not concorrentes_com_reviews:
        return {}

    # Monta prompt batch — cada review numerada por (idx_concorrente, idx_review)
    linhas = []
    indice_map = []  # [(nome_concorrente, idx_review_no_concorrente), ...]
    contador = 0
    for c in concorrentes_com_reviews:
        if not isinstance(c, dict):
            continue
        nome = c.get("nome", "?")
        for i, r in enumerate(c.get("reviews") or []):
            if not isinstance(r, dict):
                continue
            quote = (r.get("quote_curta") or "")[:max_chars_por_review]
            if not quote.strip():
                continue
            rating = r.get("rating", 3)
            linhas.append(f"[{contador}] rating={rating} | {quote}")
            indice_map.append((nome, i))
            contador += 1

    if not linhas:
        return {}

    taxonomia_str = ", ".join(DORES_TAXONOMIA)
    prompt = (
        "Classifique cada review de academia abaixo em UMA categoria de dor "
        "(taxonomia fechada). Se o review for elogio ou neutro, use "
        "categoria 'outra' e sinal positivo/neutro.\n\n"
        f"Categorias possíveis: {taxonomia_str}\n\n"
        "Reviews:\n" + "\n".join(linhas) + "\n\n"
        "Responda APENAS um JSON válido (sem markdown fence) no formato:\n"
        '{"classificacoes": [{"id": 0, "categoria_dor": "lotacao", '
        '"sinal": "negativo", "confianca": "alta"}, ...]}\n'
        f"Inclua exatamente {len(linhas)} entradas, uma por review, na ordem "
        "dos IDs."
    )

    # Retry com backoff (mesmo pattern de pesquisar_no_google_grounding) —
    # Gemini Flash free tier limita a 10 RPM. Sem retry, 429 Too Many Requests
    # virava {} silencioso → caller caía pro substring (Run 19 mostrou isso).
    import time as _time
    import random as _random
    backoffs = [3, 8, 20, 45]  # segundos; jitter ±20%
    transient_keywords = (
        "429", "RESOURCE_EXHAUSTED", "quota", "rate limit",
        "503", "UNAVAILABLE", "Too Many Requests", "DEADLINE_EXCEEDED",
    )

    try:
        from google.genai import types as gtypes
        from tools._genai_client import build_genai_client

        try:
            client = build_genai_client()
        except RuntimeError:
            return {}
        last_exc: Exception | None = None
        text = ""
        for tentativa, delay in enumerate(backoffs, start=1):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=gtypes.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                    ),
                )
                text = (getattr(response, "text", "") or "").strip()
                if text:
                    break
                last_exc = RuntimeError("resposta vazia do Gemini")
            except Exception as e:
                last_exc = e
                erro_str = str(e)
                if not any(t in erro_str for t in transient_keywords):
                    break  # erro permanente
                if tentativa < len(backoffs):
                    _time.sleep(delay * _random.uniform(0.8, 1.2))

        if not text:
            return {}  # caller faz fallback pro substring

        data = json.loads(text)
        classificacoes = data.get("classificacoes") or []
    except Exception:
        return {}  # caller faz fallback pro substring

    # Reconstroi mapping {nome_concorrente: {idx_review: classificacao}}
    resultado: dict[str, dict[int, dict]] = {}
    for c in classificacoes:
        if not isinstance(c, dict):
            continue
        idx = c.get("id")
        if not isinstance(idx, int) or idx < 0 or idx >= len(indice_map):
            continue
        nome, idx_review = indice_map[idx]
        cat = c.get("categoria_dor") or "outra"
        if cat not in DORES_TAXONOMIA:
            cat = "outra"
        resultado.setdefault(nome, {})[idx_review] = {
            "categoria_dor": cat,
            "sinal": c.get("sinal") or "neutro",
            "confianca": c.get("confianca") or "media",
        }
    return resultado


def aplicar_classificacao_dores(
    concorrentes_com_reviews: list[dict],
    classificacoes: dict,
) -> list[dict]:
    """
    Aplica o output de `classificar_dores_reviews_batch_gemini` mutando
    cada review com `categoria_dor` (taxonomia) + `sinal` + `confianca`.
    Reviews não classificadas pelo Gemini caem no fallback substring.

    Modifica in-place e retorna a mesma lista (conveniência).
    """
    for c in concorrentes_com_reviews:
        if not isinstance(c, dict):
            continue
        nome = c.get("nome", "?")
        cls_concorrente = classificacoes.get(nome, {})
        for i, r in enumerate(c.get("reviews") or []):
            if not isinstance(r, dict):
                continue
            cls = cls_concorrente.get(i)
            if cls:
                r["categoria_dor"] = cls.get("categoria_dor", "outra")
                r["sinal"] = cls.get("sinal", "neutro")
                r["confianca_classificacao"] = cls.get("confianca", "media")
            else:
                # Fallback substring
                texto_low = (r.get("quote_curta") or "").lower()
                dores_subs = _classificar_dor_substring(texto_low)
                r["categoria_dor"] = "outra" if not dores_subs else "atendimento_ruim"
                r["sinal"] = (
                    "negativo" if r.get("rating", 3) <= 2
                    else "positivo" if r.get("rating", 3) >= 4
                    else "neutro"
                )
                r["confianca_classificacao"] = "baixa"
    return concorrentes_com_reviews


# ── Buscas ─────────────────────────────────────────────────────────
def _buscar_academias_cnpj_bairro(
    bairro: str,
    cidade: str,
    uf: str = "",
    *,
    limit: int = 20,
) -> tuple[list[dict], dict]:
    """Terceiro canal: parque CNPJ fitness no bairro (Supabase RFB)."""
    try:
        from tools.cnpj_fitness_tools import listar_unidades_cnpj_no_bairro

        block = listar_unidades_cnpj_no_bairro(
            cidade, bairro, uf, limit=limit
        )
        if block.get("status") != "ok":
            return [], block
        out: list[dict] = []
        for u in block.get("unidades") or []:
            if not isinstance(u, dict):
                continue
            out.append(
                {
                    "place_id": f"cnpj/{u.get('cnpj', '')}",
                    "nome": u.get("nome", ""),
                    "endereco": u.get("endereco", ""),
                    "lat": 0.0,
                    "lng": 0.0,
                    "distancia_km": 0.0,
                    "rating": None,
                    "num_avaliacoes": 0,
                    "nivel_preco": "",
                    "status": "CNPJ_ATIVO",
                    "tipos": ["gym", "cnpj_fitness"],
                    "telefone": "",
                    "website": "",
                    "tem_24h": False,
                    "horarios": [],
                    "fonte_busca": "cnpj_rfb",
                }
            )
        return out, block
    except Exception as exc:
        return [], {"status": "erro", "motivo": str(exc)}


def _buscar_academias_overpass(
    lat: float,
    lng: float,
    raio_metros: int,
    *,
    limit: int = 20,
) -> tuple[list[dict], dict]:
    """Retorna (concorrentes, meta_overpass). Lista vazia se fallback desligado ou falhou."""
    try:
        from tools.maps_fallback import (
            fallback_habilitado,
            overpass_fitness_near,
            overpass_fitness_to_concorrentes,
        )

        if not fallback_habilitado():
            return [], {"erro": "MAPS_FALLBACK_ENABLED desligado"}
        fb = overpass_fitness_near(lat, lng, raio_metros, limit=limit)
        if not fb.get("places"):
            return [], fb
        return (
            overpass_fitness_to_concorrentes(fb["places"], lat, lng),
            fb,
        )
    except Exception as exc:
        return [], {"erro": str(exc)}


def buscar_academias(
    bairro: str,
    cidade: str,
    raio_metros: int = 3000,
    uf: str = "",
) -> dict:
    """
    Busca academias e fitness centers num raio do bairro/cidade.
    Recebe strings (bairro, cidade) — geocodifica internamente.

    Ordem: Geocode (Google → Nominatim) → Places Nearby → Overpass OSM.
    Sem chave Google ou com API bloqueada, usa OSM quando MAPS_FALLBACK_ENABLED=1.
    """
    endereco = f"{bairro}, {cidade}, Brasil" if bairro else f"{cidade}, Brasil"
    geo = geocode_endereco(endereco)
    if "error" in geo:
        return {
            "erro": geo["error"],
            "concorrentes": [],
            "fonte_geocode": geo.get("fonte_geocode"),
        }

    lat, lng = geo["lat"], geo["lng"]
    fonte_geocode = geo.get("fonte_geocode", "google")
    api_key = get_google_maps_api_key()

    # ── Tier 0 Geo (Places Aggregate) — só com chave Google ─────────
    # Nearby Search no Places API New tem maxResultCount limitado (ex: 20).
    # Para score competitivo, queremos a densidade REAL no raio.
    agregados: dict = {}
    places_ok = False
    data: dict = {}
    if api_key:
        try:
            from tools.places_aggregate_tools import compute_insight_count_circle

            base = compute_insight_count_circle(
                latitude=lat,
                longitude=lng,
                radius_meters=int(raio_metros),
                included_types=["gym", "fitness_center"],
            )
            hi42 = compute_insight_count_circle(
                latitude=lat,
                longitude=lng,
                radius_meters=int(raio_metros),
                included_types=["gym", "fitness_center"],
                min_rating=4.2,
            )
            agregados = {
                "status": "ok" if "erro" not in base else "erro",
                "count_total": base.get("count") if isinstance(base, dict) else None,
                "count_rating_ge_4_2": hi42.get("count") if isinstance(hi42, dict) else None,
                "radius_meters": int(raio_metros),
                "center": {"lat": lat, "lng": lng},
                "included_types": ["gym", "fitness_center"],
                "erros": [e for e in [base.get("erro"), hi42.get("erro")] if e],
            }
        except Exception:
            agregados = {"status": "erro", "motivo": "exception_import_or_call"}

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                # priceLevel cortado (sem sinal pra gym); hours/contact ficam —
                # tem_24h e a coluna de contato dos concorrentes dependem deles.
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.rating,places.userRatingCount,"
                "places.businessStatus,places.types,"
                "places.regularOpeningHours,places.websiteUri,places.nationalPhoneNumber"
            ),
        }
        body = {
            "locationRestriction": {"circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(raio_metros),
            }},
            "includedTypes": ["gym", "fitness_center"],
            "maxResultCount": 20,
            "languageCode": "pt-BR",
        }
        try:
            with httpx.Client(timeout=15) as c:
                resp = c.post(f"{PLACES_BASE}:searchNearby", json=body, headers=headers)
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                places_ok = resp.status_code == 200 and bool(data.get("places"))
        except Exception as e:
            places_ok = False
            data = {"error": str(e)}

    concorrentes: list[dict] = []
    fonte_busca = "google_places"
    if not places_ok:
        concorrentes, _fb_meta = _buscar_academias_overpass(lat, lng, raio_metros, limit=20)
        if concorrentes:
            fonte_busca = "overpass_osm"
            agregados = {
                **(agregados if isinstance(agregados, dict) else {}),
                "status": "fallback_osm",
                "count_total": len(concorrentes),
                "nota": (
                    "Google Places indisponível ou sem chave — "
                    "contagem via OpenStreetMap (Overpass)"
                ),
            }
        if not concorrentes and bairro.strip():
            concorrentes, _cnpj_meta = _buscar_academias_cnpj_bairro(
                bairro, cidade, uf, limit=20
            )
            if concorrentes:
                fonte_busca = "cnpj_rfb"
                agregados = {
                    **(agregados if isinstance(agregados, dict) else {}),
                    "status": "fallback_cnpj",
                    "count_total": len(concorrentes),
                    "nota": (
                        "Google/OSM sem resultados — parque ativo CNPJ (RFB) no bairro"
                    ),
                }
        if not concorrentes:
            err = (
                data.get("error", {}).get("message")
                if isinstance(data.get("error"), dict)
                else data.get("error")
            )
            if not api_key:
                err = err or "Maps/OSM/CNPJ sem academias no bairro"
            return {
                "erro": f"Busca de academias falhou: {err or 'sem resultados'}",
                "concorrentes": [],
                "fonte_geocode": fonte_geocode,
                "fonte_busca_competidores": "nenhuma",
            }

    for p in (data.get("places") or []) if places_ok else []:
        plat = p.get("location", {}).get("latitude", 0)
        plng = p.get("location", {}).get("longitude", 0)
        horarios = p.get("regularOpeningHours", {})
        periodos = horarios.get("weekdayDescriptions", []) if horarios else []
        tem_24h = any("24" in h for h in periodos) if periodos else False

        concorrentes.append({
            "place_id": p.get("id", ""),
            "nome": p.get("displayName", {}).get("text", ""),
            "endereco": p.get("formattedAddress", ""),
            "lat": plat, "lng": plng,
            "distancia_km": round(calcular_distancia_km(lat, lng, plat, plng), 2),
            "rating": p.get("rating"),
            "num_avaliacoes": p.get("userRatingCount", 0),
            "nivel_preco": p.get("priceLevel", ""),
            "status": p.get("businessStatus", ""),
            "tipos": p.get("types", []),
            "telefone": p.get("nationalPhoneNumber", ""),
            "website": p.get("websiteUri", ""),
            "google_maps_uri": p.get("googleMapsUri", ""),
            "tem_24h": tem_24h,
            "horarios": periodos[:3],
            "fonte_busca": "google_places",
        })
    if places_ok:
        concorrentes.sort(key=lambda x: x["distancia_km"])
        try:
            from tools.maps_tools import obter_detalhes_contato

            for c in concorrentes[:5]:
                pid = c.get("place_id")
                if not pid or str(pid).startswith("osm"):
                    continue
                det = obter_detalhes_contato(pid)
                if isinstance(det, dict) and "erro" not in det:
                    c["telefone"] = det.get("telefone") or c.get("telefone", "")
                    c["website"] = det.get("website") or c.get("website", "")
                    c["tem_24h"] = det.get("tem_24h", c.get("tem_24h", False))
                    c["horarios"] = det.get("horarios") or c.get("horarios", [])
        except Exception as exc:
            logger.debug("enriquecimento Place Details concorrentes: %s", exc)

    total_nearby = len(concorrentes)
    _count_raw = agregados.get("count_total")
    total_agregado = (
        int(_count_raw) if isinstance(_count_raw, (int, float, str)) else None
    )

    redes_osm: list[str] = []
    if fonte_busca == "overpass_osm" and concorrentes:
        try:
            from tools.local_market_facts import inferir_redes_de_concorrentes

            redes_osm = inferir_redes_de_concorrentes(concorrentes)
        except Exception:
            redes_osm = []

    return {
        "bairro": bairro,
        "cidade": cidade,
        "raio_metros": raio_metros,
        "lat_centro": lat, "lng_centro": lng,
        "fonte_geocode": fonte_geocode,
        # `total_encontrados` passa a refletir o melhor estimate disponível
        # para densidade no raio: Aggregate (se disponível) > Nearby (limitado).
        "total_encontrados": total_agregado if total_agregado is not None else total_nearby,
        "total_encontrados_nearby": total_nearby,
        # Contagem agregada (se disponível) — mais fiel que len(concorrentes)
        # quando há >20 academias no raio.
        "total_encontrados_agregado": total_agregado,
        "agregados_competicao_places": agregados,
        "fonte_busca_competidores": fonte_busca,
        "redes_detectadas_osm": redes_osm,
        "concorrentes": concorrentes,
    }


def buscar_reviews_academia(place_id: str, nome_academia: str = "") -> dict:
    """Busca reviews via Places Details API (Places API New)."""
    if not get_google_maps_api_key():
        return {"erro": "GOOGLE_get_google_maps_api_key() não configurada", "reviews": []}

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": "id,displayName,rating,userRatingCount,reviews",
    }
    try:
        with httpx.Client(timeout=15) as c:
            data = c.get(f"{PLACES_BASE}/{place_id}", headers=headers).json()
    except Exception as e:
        return {"erro": f"Details API falhou: {e}", "reviews": []}

    reviews_raw = data.get("reviews", []) or []

    def _publish_time_sort(r: dict) -> float:
        pt = r.get("publishTime")
        if isinstance(pt, (int, float)):
            return float(pt)
        if isinstance(pt, str) and pt:
            try:
                from datetime import datetime

                return datetime.fromisoformat(pt.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return 0.0
        return 0.0

    # Prioriza avaliações ≤3★ (dores) e mantém as mais recentes da amostra API.
    reviews_raw = sorted(
        reviews_raw,
        key=lambda r: (
            0 if (r.get("rating") or 5) <= 3 else 1,
            -_publish_time_sort(r),
        ),
    )
    reviews_processados = []
    for r in reviews_raw[:5]:  # máx 5 reviews por place
        texto = (r.get("text", {}) or {}).get("text", "") or ""
        texto_low = texto.lower()
        rating = r.get("rating", 3)

        dores_detectadas = [d for d in DORES_COMUNS if d in texto_low]
        servicos_mencionados = [s for s in SERVICOS_ACADEMIA if s in texto_low]

        # Texto reduzido para 180 chars — evita MALFORMED_FUNCTION_CALL no Gemini
        # quando o LLM precisa retransmitir essa lista como argumento de
        # analisar_gap_competitivo / analisar_picos_competitivos.
        # O texto completo já é descartado nessas análises (só usamos categorizações);
        # o trecho de 180 chars é suficiente para o A6 montar a quote nominada.
        reviews_processados.append({
            "rating": rating,
            "quote_curta": texto[:180].replace("\n", " ").strip(),
            "sentimento": "positivo" if rating >= 4 else "negativo" if rating <= 2 else "neutro",
            "dores_detectadas": dores_detectadas,
            "servicos_mencionados": servicos_mencionados,
            "autor": (r.get("authorAttribution", {}) or {}).get("displayName", "Anônimo")[:60],
            "data_relativa": r.get("relativePublishTimeDescription", "")[:30],
        })

    return {
        "place_id": place_id,
        "nome": data.get("displayName", {}).get("text", nome_academia),
        "rating_geral": data.get("rating", 0),
        "total_avaliacoes": data.get("userRatingCount", 0),
        "reviews": reviews_processados,
        "total_reviews_analisados": len(reviews_processados),
    }


def montar_perfil_competitivo(concorrente: dict, reviews_processados: list[dict],
                                enrichment_google: dict | None = None) -> dict:
    """
    Monta perfil RICO de UM concorrente — não agregado.
    Junta dados básicos do Places + reviews nominados + enrichment do Google.

    Retorna card por concorrente com:
    - servicos_oferecidos (extraído das reviews)
    - reclamacoes_especificas (com texto original + rating)
    - pontos_fortes (reviews positivas)
    - sentimento_medio
    - dados de enrichment (horários pico, posts, etc) se disponível
    """
    nome = concorrente.get("nome", "Desconhecido")
    enrichment_google = enrichment_google or {}

    # Serviços mencionados em QUALQUER review deste concorrente
    servicos = set()
    reclamacoes_especificas = []
    pontos_fortes = []
    ratings = []

    for r in reviews_processados:
        rating = r.get("rating", 0)
        texto = r.get("texto", "")
        autor = r.get("autor", "Anônimo")
        ratings.append(rating)

        for srv in r.get("servicos_mencionados", []):
            servicos.add(srv)

        # Filtro de recência: dores e pontos fortes só de reviews com ≤ 1 ano.
        # Reviews antigos refletem operação que pode ter mudado.
        review_recente = _review_recente_1ano(r.get("data_relativa"))

        # Reclamações: review negativa (rating <= 3) com dores detectadas, recente
        if review_recente and rating <= 3 and r.get("dores_detectadas"):
            for dor in r["dores_detectadas"]:
                reclamacoes_especificas.append({
                    "dor": dor,
                    "rating": rating,
                    "quote": texto[:200],
                    "autor": autor,
                    "data": r.get("data_relativa", ""),
                })

        # Pontos fortes: review positiva (rating >= 4) com serviços, recente
        if review_recente and rating >= 4 and r.get("servicos_mencionados"):
            pontos_fortes.append({
                "menciona": r["servicos_mencionados"][:3],
                "rating": rating,
                "quote": texto[:150],
            })

    sentimento_medio = round(sum(ratings) / len(ratings), 1) if ratings else 0

    return {
        "nome": nome,
        "endereco": concorrente.get("endereco", ""),
        "rating_oficial": concorrente.get("rating", 0),
        "num_avaliacoes": concorrente.get("num_avaliacoes", 0),
        "tem_24h": concorrente.get("tem_24h", False),
        "telefone": concorrente.get("telefone", ""),
        "website": concorrente.get("website", ""),
        "servicos_oferecidos": sorted(list(servicos)),
        "reclamacoes_especificas": reclamacoes_especificas[:5],  # top 5
        "pontos_fortes_mencionados": pontos_fortes[:3],
        "sentimento_medio_reviews": sentimento_medio,
        "total_reviews_analisadas": len(reviews_processados),
        # Enrichment do Google Knowledge Panel (se disponível)
        "horarios_pico": enrichment_google.get("horarios_pico", {}),
        "pico_semanal": enrichment_google.get("pico_semanal"),
        "vale_semanal": enrichment_google.get("vale_semanal"),
        "atividade_marketing": enrichment_google.get("atividade_marketing", {}),
        "posts_recentes": enrichment_google.get("posts_recentes", []),
        "scraping_status": enrichment_google.get("scraping_status", "nao_executado"),
    }


def analisar_gap_competitivo(concorrentes_com_reviews: list[dict], bairro: str = "") -> dict:
    """Cruza dados de todos os concorrentes para identificar gaps e dores."""
    if not concorrentes_com_reviews:
        return {
            "bairro": bairro,
            "dores_dominantes": [],
            "servicos_nao_oferecidos": [],
            "oportunidades_rankeadas": [],
            "score_oportunidade_mercado": 0.0,
            "resumo": "Nenhum concorrente analisado",
        }

    todas_dores = {}                # {dor: total_count}
    dores_por_academia = {}         # {dor: {academia_nome: count_neste_concorrente}}
    categorias_dor = {}             # {categoria_dor: total_count}
    categorias_por_academia = {}
    servicos_oferecidos = set()
    ratings_por_academia = {}

    for c in concorrentes_com_reviews:
        # Defensivo: pula se LLM passou tipo errado
        if not isinstance(c, dict):
            continue
        nome = c.get("nome", "Desconhecido")
        # rating_geral pode vir None do A3a quando Google Maps não retorna rating
        # (academia recém-criada, ou Place sem reviews). Coalesce para 0.0 evita
        # TypeError em max()/min() abaixo. Bug que produzia A3b OUT=0 — VEC-380.
        rating_raw = c.get("rating_geral")
        ratings_por_academia[nome] = float(rating_raw) if rating_raw is not None else 0.0
        reviews_list = c.get("reviews", [])
        if not isinstance(reviews_list, list):
            continue
        for review in reviews_list:
            if not isinstance(review, dict):
                continue
            dores = review.get("dores_detectadas", []) or []
            servs = review.get("servicos_mencionados", []) or []
            cat = (review.get("categoria_dor") or "").strip()
            if cat and cat.lower() not in ("outra", "outras", ""):
                categorias_dor[cat] = categorias_dor.get(cat, 0) + 1
                if cat not in categorias_por_academia:
                    categorias_por_academia[cat] = {}
                categorias_por_academia[cat][nome] = categorias_por_academia[cat].get(nome, 0) + 1
            if isinstance(dores, list):
                for dor in dores:
                    if not isinstance(dor, str):
                        continue
                    todas_dores[dor] = todas_dores.get(dor, 0) + 1
                    if dor not in dores_por_academia:
                        dores_por_academia[dor] = {}
                    dores_por_academia[dor][nome] = dores_por_academia[dor].get(nome, 0) + 1
            if isinstance(servs, list):
                for srv in servs:
                    if isinstance(srv, str):
                        servicos_oferecidos.add(srv)

    # Prioriza taxonomia semântica (Gemini) quando disponível; fallback substring.
    if categorias_dor:
        dores_rankeadas = sorted(categorias_dor.items(), key=lambda x: x[1], reverse=True)
        dores_por_academia = categorias_por_academia
    else:
        dores_rankeadas = sorted(todas_dores.items(), key=lambda x: x[1], reverse=True)
    gaps_servicos = list(set(SERVICOS_ACADEMIA) - servicos_oferecidos)

    # Mapa dor → solução
    mapa_solucao = {
        "muito cheio": "Controle de lotação via app + reserva de horário",
        "lotado": "Limite de capacidade por turno + agendamento digital",
        "equipamentos quebrados": "Contrato de manutenção preventiva com SLA 24h",
        "quebrado": "Garantia de equipamentos em funcionamento",
        "sem ar condicionado": "Climatização premium como diferencial de conforto",
        "calor": "Ar condicionado central de alta capacidade",
        "instrutores ruins": "Certificação obrigatória + supervisão constante",
        "atendimento ruim": "Treinamento intensivo + NPS público mensal",
        "sem estacionamento": "Estacionamento próprio ou parceria com vaga grátis",
        "mensalidade cara": "Modelo transparente sem fidelidade nem multa",
        "fila nas máquinas": "Monitoramento IoT + redistribuição de equipamentos",
        "banheiros sujos": "Limpeza programada com checklist visível a cada 2h",
        "sem professor": "Ratio aluno/instrutor máximo de 30:1",
        "música alta": "Áreas com DJ + áreas silenciosas separadas",
        "cancela plano difícil": "Cancelamento digital em 1 clique",
        "fidelidade": "Plano mensal sem fidelidade — pagamento por uso",
        "cobrança indevida": "Transparência total — extrato no app + ouvidoria",
        "estrutura velha": "Renovação anual de equipamentos programada",
    }

    oportunidades = []
    for dor, contagem in dores_rankeadas[:8]:
        # Lista nominada de quem mencionou esta dor (top 5)
        mencoes = dores_por_academia.get(dor, {})
        mencionado_por = sorted(
            [{"academia": ac, "vezes": v} for ac, v in mencoes.items()],
            key=lambda x: -x["vezes"],
        )[:5]
        oportunidades.append({
            "dor_identificada": dor,
            "frequencia_mencoes": contagem,
            "mencionado_por": mencionado_por,
            "oportunidade": mapa_solucao.get(dor, f"Resolver: {dor}"),
            "prioridade": "ALTA" if contagem >= 3 else "MEDIA" if contagem >= 2 else "BAIXA",
        })

    # Adiciona gaps de serviço como oportunidades complementares
    for srv in gaps_servicos[:3]:
        oportunidades.append({
            "dor_identificada": f"gap_servico_{srv}",
            "frequencia_mencoes": 0,
            "oportunidade": f"Oferecer {srv} — ausente nos concorrentes locais",
            "prioridade": "MEDIA",
        })

    melhor = max(ratings_por_academia.items(), key=lambda x: x[1]) if ratings_por_academia else ("N/A", 0)
    pior = min(ratings_por_academia.items(), key=lambda x: x[1]) if ratings_por_academia else ("N/A", 0)

    score_oportunidade = min(10.0, len(dores_rankeadas) * 0.8 + len(gaps_servicos) * 0.3)

    # Dores dominantes COM nominação (top 5)
    dores_dominantes_nominadas = []
    for d, c in dores_rankeadas[:5]:
        mencoes = dores_por_academia.get(d, {})
        mencionado_por = sorted(
            [{"academia": ac, "vezes": v} for ac, v in mencoes.items()],
            key=lambda x: -x["vezes"],
        )
        dores_dominantes_nominadas.append({
            "dor": d,
            "mencoes": c,
            "mencionado_por": mencionado_por,
        })

    return {
        "bairro": bairro,
        "total_concorrentes_analisados": len(concorrentes_com_reviews),
        "dores_dominantes": dores_dominantes_nominadas,
        "servicos_nao_oferecidos": gaps_servicos[:8],
        "oportunidades_rankeadas": oportunidades[:10],
        "melhor_avaliada": {"nome": melhor[0], "rating": melhor[1]},
        "pior_avaliada": {"nome": pior[0], "rating": pior[1]},
        "score_oportunidade_mercado": round(score_oportunidade, 1),
        "resumo": f"{len(dores_rankeadas)} dores, {len(gaps_servicos)} serviços ausentes",
    }


# ── Métricas clássicas (usadas pelo Score Geral em a6) ─────────────
def classificar_saturacao(num_concorrentes: int, raio_km: float) -> str:
    area = math.pi * raio_km ** 2
    densidade = num_concorrentes / area if area > 0 else 0
    if densidade < 0.3:   return "BAIXO"
    elif densidade < 0.8: return "MEDIO"
    elif densidade < 1.5: return "ALTO"
    else:                 return "SATURADO"


def panorama_saturacao(
    *,
    total_raio: int,
    total_analisados: int,
    raio_km: float = 3.0,
    cnpj_cidade: int | None = None,
) -> dict:
    """
    Saturação primária = densidade no raio (Places nearby, academia tradicional).
    Secundária = amostra analisada (top 10) + referência CNPJ municipal.
    """
    area = math.pi * raio_km ** 2
    densidade_raio = round(total_raio / area, 2) if area > 0 else 0.0
    return {
        "nivel_saturacao": classificar_saturacao(total_raio, raio_km),
        "nivel_saturacao_amostra": classificar_saturacao(total_analisados, raio_km),
        "total_encontrados_raio": total_raio,
        "total_concorrentes_analisados": total_analisados,
        "densidade_por_km2": densidade_raio,
        "raio_km": raio_km,
        "cnpj_parque_ativo_cidade": cnpj_cidade,
        "cnpj_academias_ativas_cidade": cnpj_cidade,  # alias legado
        "metodologia": (
            f"Saturação principal: {total_raio} academias tradicionais no raio "
            f"{raio_km} km ({densidade_raio}/km²). Amostra aprofundada: "
            f"{total_analisados} unidades (reviews + dores). "
            + (
                f"Parque ativo municipal (CNPJ): {cnpj_cidade} unidades."
                if cnpj_cidade is not None
                else "Parque ativo municipal (CNPJ) indisponível."
            )
        ),
    }


def calcular_score_concorrencia(num_concorrentes: int, rating_medio: float,
                                 saturacao: str) -> float:
    bonus = {"BAIXO": 5.0, "MEDIO": 3.5, "ALTO": 1.5, "SATURADO": 0.0}
    penalidade_qtd = min(num_concorrentes * 0.4, 4.0)
    penalidade_rating = (rating_medio / 5.0) * 2.0 if rating_medio else 1.0
    score = bonus.get(saturacao, 2.0) + (10 - penalidade_qtd * 2) / 10 - penalidade_rating
    return round(max(0.0, min(10.0, score)), 2)


# ── Filtro semântico de academia tradicional (VEC-387 iter 6) ───────
# Google Places `gym` + `fitness_center` retorna tudo: escolas de futebol,
# clínicas de fisioterapia, estúdios de modalidade única (yoga, Muay Thai,
# tênis), clubes esportivos. Inflam o count de "academias na região"
# falsamente. Filtro abaixo aplica regras negativas combinando types + nome
# para isolar academias tradicionais (musculação + cardio + aulas em grupo).

_TYPES_EXCLUSAO_FORTE = {
    "physiotherapist", "doctor", "hospital", "medical_center",
    "dentist", "veterinary_care", "physiotherapy",
}

_NOME_EXCLUSAO_KEYWORDS = (
    # Escolas de esporte / modalidades específicas (não-fitness tradicional)
    "saint-germain", "saint germain", "psg", "paris saint",
    "futebol", "futsal", "soccer", "futbol",
    "tenis", "tênis", "tennis", "padel", "paddle",
    "vôlei", "volei", "volleyball",
    "natação", "natacao", "swimming",
    "hidro", "hidroginás", "hidroginas",
    "pole dance", "pole-dance",
    "escolinha de", "escola de futebol", "escola de tenis", "escola de vôlei",
    # Saúde / clínicas
    "fisio", "clínica", "clinica", "ortopedia", "ortoped",
    "consultório", "consultorio", "podologia", "psicolog",
    "estética", "estetica", "harmonização",
    # Lojas / suplemento (que entram com "academia" no nome mas são lojas)
    "loja de suplement", "suplementos &", "suplemento e",
)

# Modalidades únicas: excluir SE nome não tem qualificador "academia/fit/gym"
_MODALIDADES_UNICAS = (
    "muay thai", "muaythai", "muay-thai",
    "jiu jitsu", "jiu-jitsu", "jiujitsu",
    "karate", "karatê",
    "krav maga", "krav-maga",
    "ballet", "balé",
    "yoga", "ioga",
)

_QUALIFICADORES_ACADEMIA = (
    "academia", "fitness", "gym", "ginás", "ginas",
    "musculação", "musculacao", "fit ", " fit", "smart fit", "bluefit",
    "selfit", "bodytech", "cia athletica", "ayo fit",
    "crossfit", "wellness",
)


def _eh_academia_tradicional(place: dict) -> tuple[bool, str]:
    """
    Decide se um Place do Google é academia tradicional ou ruído (escola de
    esporte, clínica, estúdio de modalidade única).

    Retorna (is_academia, motivo_exclusao). Motivo vazio quando is_academia=True.
    """
    if not isinstance(place, dict):
        return False, "input inválido"

    nome = (place.get("nome") or place.get("displayName", {}).get("text") or "").lower()
    types = place.get("tipos") or place.get("types") or []
    types_set = {str(t).lower() for t in types if t}

    # 1. Exclusão forte por type
    if types_set & _TYPES_EXCLUSAO_FORTE:
        forte = types_set & _TYPES_EXCLUSAO_FORTE
        return False, f"type forte: {next(iter(forte))}"

    # 2. School sem gym exclusivo
    if "school" in types_set and not (
        "gym" in types_set or "fitness_center" in types_set
    ):
        return False, "school exclusivo"

    # 3. Sports club sem gym
    if "sports_club" in types_set and not (
        "gym" in types_set or "fitness_center" in types_set
    ):
        return False, "sports_club sem gym"

    # 4. Exclusão por palavras-chave fortes no nome
    for kw in _NOME_EXCLUSAO_KEYWORDS:
        if kw in nome:
            return False, f"nome contém '{kw}'"

    # 5. Modalidade única — só exclui se NÃO houver qualificador "academia/fit"
    for mod in _MODALIDADES_UNICAS:
        if mod in nome:
            tem_qualificador = any(q in nome for q in _QUALIFICADORES_ACADEMIA)
            if not tem_qualificador:
                return False, f"modalidade única: '{mod}'"

    # 6. Inclusão final: tem que ter type=gym/fitness_center OU keyword no nome
    if types_set & {"gym", "fitness_center", "health"}:
        # confirma que não é "health" puro (clínica que escapou)
        if "health" in types_set and not (
            "gym" in types_set or "fitness_center" in types_set
        ):
            # health sozinho geralmente é clínica
            return False, "health sem gym (provável clínica)"
        return True, ""

    if any(q in nome for q in _QUALIFICADORES_ACADEMIA):
        return True, ""

    return False, "sem indicação de academia"


def filtrar_academias_tradicionais(concorrentes: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Aplica `_eh_academia_tradicional` numa lista de concorrentes do Places.
    Retorna (mantidos, excluidos) — útil para smoke tests e logging.
    """
    mantidos = []
    excluidos = []
    for c in concorrentes:
        ok, motivo = _eh_academia_tradicional(c)
        if ok:
            mantidos.append(c)
        else:
            excluidos.append({**c, "motivo_exclusao": motivo})
    return mantidos, excluidos


# ── Helpers de parsing de endereço (VEC-387) ────────────────────────
def extrair_bairro_endereco(endereco: str) -> str | None:
    """
    Extrai o nome do bairro de um endereço formato Google Places Brasil.

    Formatos comuns esperados:
      - "Av. Eng. Santana Jr., 699 - Cocó, Fortaleza - CE, 60175-657, Brasil"
      - "R. Carlos Vasconcelos, 284 - Meireles, Fortaleza - CE, 60115-170, Brasil"
      - "Rua Tiburcio Cavalcante, 1221, Meireles, Fortaleza - CE, Brasil"

    Retorna o bairro (ex: "Cocó", "Meireles", "Aldeota") ou None se
    não conseguir extrair com confiança. Usado para agrupar concorrentes
    geograficamente no relatório do A6.
    """
    if not endereco or not isinstance(endereco, str):
        return None

    import re

    # Remove sufixo CEP + país pra simplificar parsing
    # Ex: "..., Fortaleza - CE, 60175-657, Brasil" → "..., Fortaleza - CE"
    txt = re.sub(r",\s*\d{5}-?\d{3}.*$", "", endereco)
    txt = re.sub(r",\s*Brasil\s*$", "", txt, flags=re.IGNORECASE)

    # Padrão 1: "rua/av X, 699 - <BAIRRO>, <CIDADE> - <UF>"
    # O bairro vem entre o " - " (após número) e a vírgula seguinte.
    m = re.search(r"-\s*([^,\-][^,]*?),\s*[^,]+?\s*-\s*[A-Z]{2}\s*$", txt)
    if m:
        candidato = m.group(1).strip()
        if 2 <= len(candidato) <= 60 and not candidato.isdigit():
            return candidato

    # Padrão 2: "rua/av X, 1221, <BAIRRO>, <CIDADE> - <UF>"
    # Tudo separado por vírgula. Bairro é o penúltimo antes do "Cidade - UF".
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    if len(parts) >= 3:
        # último deve ser "Cidade - UF"
        ultima = parts[-1]
        if re.match(r".+\s*-\s*[A-Z]{2}\s*$", ultima):
            candidato = parts[-2]
            # Filtra se for número (rua + número virou último antes do bairro)
            if not candidato.replace(".", "").isdigit() and 2 <= len(candidato) <= 60:
                return candidato

    return None


def _aplicar_bairro_concorrente(c: dict) -> None:
    """Preenche bairro_concorrente (+ chave normalizada) a partir do endereço."""
    if not isinstance(c, dict) or c.get("bairro_concorrente"):
        return
    from tools.bairro_normalize import formatar_bairro_exibicao, normalizar_bairro

    raw = extrair_bairro_endereco(c.get("endereco", ""))
    if raw:
        c["bairro_concorrente"] = formatar_bairro_exibicao(raw)
        c["bairro_concorrente_chave"] = normalizar_bairro(raw)


# ── Macro-tool de busca + reconciliação A0 para A3a (VEC-379) ───────
def _parse_market_context(raw):
    """
    Extrai dict de `market_context` aceitando os 3 formatos que o ADK
    pode entregar via output_key:
      1. dict já parseado (caso ideal raro)
      2. JSON string puro
      3. Markdown com bloco ```json ... ``` em volta (formato comum quando
         o LLM emite seguindo `## SAÍDA OBRIGATÓRIA (JSON)` no prompt)

    Retorna {} em qualquer falha. Nunca levanta.
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}

    import json
    import re

    txt = raw.strip()
    # Tenta JSON puro primeiro
    try:
        return json.loads(txt)
    except Exception:
        pass

    # Extrai bloco ```json ... ``` (ou ``` ... ``` sem rótulo)
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", txt, re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass

    # Último recurso: pega o primeiro objeto JSON balanceado no texto
    start = txt.find("{")
    if start >= 0:
        # busca o "}" que fecha o primeiro objeto considerando aninhamento
        depth = 0
        for i in range(start, len(txt)):
            ch = txt[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = txt[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break
    return {}


def _normalizar_nome(s: str) -> str:
    """Lowercase + collapse de espaços para matching de redes."""
    if not s:
        return ""
    return " ".join(str(s).lower().split())


def _matches_rede(nome_concorrente: str, rede_a0: str) -> bool:
    """
    Matching loose entre nome de unidade no Google Maps e rede listada pelo A0.
    Cobre casos como:
      "Academia Smart Fit - Papicu" matches "Smart Fit"
      "Selfit Academias Scopa Platinum" matches "Selfit"
      "Dumbbells Academia 24 HORAS" matches "Dumbbells Academia"

    Regras:
      1. substring case-insensitive em qualquer direção (catch-all)
      2. fallback: primeira palavra significativa (>=4 chars) idêntica
    """
    nc = _normalizar_nome(nome_concorrente)
    ra = _normalizar_nome(rede_a0)
    if not nc or not ra:
        return False
    if ra in nc or nc in ra:
        return True
    nc_tokens = nc.split()
    ra_tokens = ra.split()
    if not nc_tokens or not ra_tokens:
        return False
    primeira_a0 = ra_tokens[0]
    primeira_nc = nc_tokens[0]
    if len(primeira_a0) >= 4 and primeira_a0 == primeira_nc:
        return True
    # Smart Fit também aparece como "smartfit" sem espaço
    if len(ra_tokens) >= 2 and "".join(ra_tokens) in nc.replace(" ", ""):
        return True
    return False


def _avaliacoes_int(c: dict) -> int:
    """Coalesce num_avaliacoes p/ inteiro (None vira 0)."""
    v = (c or {}).get("num_avaliacoes")
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _buscar_rede_geofenced(
    rede: str,
    lat_alvo: float,
    lng_alvo: float,
    raio_max_metros: int,
) -> dict | None:
    """
    Busca a unidade MAIS PRÓXIMA de uma rede dentro do raio do bairro alvo.

    Existe pra corrigir bug encontrado em Eusébio/CE (2026-05-11): a busca
    expandida anterior chamava `buscar_academias(rede, cidade, raio)`, mas o
    geocode interno usava `f"{rede}, {cidade}"` como endereço, caindo numa
    unidade da rede em Fortaleza-centro (~15km de Eusébio). Resultado: trazia
    Selfit/Dumbbells/Porão de Fortaleza como "concorrentes de Eusébio".

    Fix: usar Places Text Search com `locationBias.circle` centrado no
    BAIRRO ALVO + filtro Haversine rígido pós-fetch. Se nenhuma unidade
    da rede estiver dentro do raio, retorna None — nada é trazido de fora.

    Args:
        rede: nome da rede (ex: "Smart Fit", "Selfit").
        lat_alvo, lng_alvo: coordenadas do bairro/cidade alvo da análise.
        raio_max_metros: raio máximo (Haversine) — matches fora são descartados.

    Returns:
        Dict do match mais próximo, ou None se nenhuma unidade no raio.
    """
    if not get_google_maps_api_key():
        return None

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            # Validação de presença da rede no raio: só identidade + posição.
            # Contact/hours/priceLevel cortados — quem usa o dado completo é
            # a busca principal de concorrentes, não este check booleano.
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.rating,places.userRatingCount,"
            "places.businessStatus,places.types"
        ),
    }
    body = {
        "textQuery": f"{rede} academia",
        "includedType": "gym",
        "locationBias": {"circle": {
            "center": {"latitude": lat_alvo, "longitude": lng_alvo},
            "radius": float(raio_max_metros),
        }},
        "maxResultCount": 10,
        "languageCode": "pt-BR",
    }
    try:
        from tools.api_cost_tracker import track_api_call
        with track_api_call("buscar_rede_geofenced", "places_search_new", 1):
            with httpx.Client(timeout=15) as c:
                data = c.post(f"{PLACES_BASE}:searchText", json=body, headers=headers).json()
    except Exception:
        return None

    raio_km = raio_max_metros / 1000.0
    candidatos_no_raio = []
    for p in data.get("places", []):
        nome = (p.get("displayName") or {}).get("text", "") or ""
        if not _matches_rede(nome, rede):
            continue  # text search às vezes retorna academias de outras redes
        plat = (p.get("location") or {}).get("latitude", 0)
        plng = (p.get("location") or {}).get("longitude", 0)
        dist = calcular_distancia_km(lat_alvo, lng_alvo, plat, plng)
        if dist > raio_km:
            continue  # safety net Haversine — locationBias é só viés, não restrição
        horarios = p.get("regularOpeningHours", {}) or {}
        periodos = horarios.get("weekdayDescriptions", []) if horarios else []
        candidatos_no_raio.append({
            "place_id": p.get("id", ""),
            "nome": nome,
            "endereco": p.get("formattedAddress", ""),
            "lat": plat,
            "lng": plng,
            "distancia_km": round(dist, 2),
            "rating": p.get("rating"),
            "num_avaliacoes": p.get("userRatingCount", 0),
            "nivel_preco": p.get("priceLevel", ""),
            "status": p.get("businessStatus", ""),
            "tipos": p.get("types", []),
            "telefone": p.get("nationalPhoneNumber", ""),
            "website": p.get("websiteUri", ""),
            "tem_24h": any("24" in h for h in periodos) if periodos else False,
            "horarios": periodos[:3],
        })

    if not candidatos_no_raio:
        return None

    # Escolhe a unidade MAIS PRÓXIMA — quando a rede tem múltiplas filiais,
    # essa é a competidora real (não a sede ou uma unidade aleatória).
    candidatos_no_raio.sort(key=lambda x: x["distancia_km"])
    return candidatos_no_raio[0]


def buscar_concorrentes_balanceados(
    tool_context,
    bairro: str,
    cidade: str,
    raio_metros: int = 3000,
    raio_expandido_metros: int = 5000,
) -> dict:
    """
    Macro-tool de busca + reconciliação A0 + seleção Top 5 BALANCEADA.

    Executa de forma determinística o que antes estava como YAML descritivo
    no prompt do A3a (e o LLM ignorava inconsistentemente).

    Lê do `tool_context.state["market_context"]` o campo
    `principais_redes_concorrentes` (output do A0). Para cada rede listada
    pelo Deep Research, garante que ao menos UMA unidade esteja no Top 5
    final, mesmo que precise busca expandida.

    Pipeline:
      1. `buscar_academias(bairro, cidade, raio_metros)` — Nearby Search padrão.
      2. Match cada rede do A0 nas unidades já encontradas (substring loose).
      3. Para cada rede do A0 NÃO presente, busca expandida pelo nome da rede
         em raio maior; adiciona a unidade representativa.
      4. Seleção Top 5: primeiro 1 unidade de cada rede do A0 (a com mais
         avaliações), depois preenche slots restantes pelas demais
         ordenadas por num_avaliacoes desc.

    Retorna dict que substitui o output do `buscar_academias` no A3a.
    """
    busca_nearby = buscar_academias(bairro, cidade, raio_metros)
    if "erro" in busca_nearby:
        return {
            **busca_nearby,
            "concorrentes_top_5_balanceados": [],
            "redes_a0_solicitadas": [],
            "redes_a0_cobertas": [],
            "redes_a0_nao_encontradas": [],
        }

    # Centro real do bairro alvo — usado pra geo-fencing da busca expandida.
    # `buscar_academias` já geocodificou e retornou o centro como lat_centro/lng_centro;
    # reaproveitamos pra não pagar 2 geocodes.
    lat_alvo = float(busca_nearby.get("lat_centro") or 0.0)
    lng_alvo = float(busca_nearby.get("lng_centro") or 0.0)

    todas = list(busca_nearby.get("concorrentes") or [])
    # Enriquece cada concorrente com bairro_concorrente extraído do endereço.
    # Permite que A6 agrupe geograficamente e detecte se bairros sugeridos
    # como alternativa estão de fato saturados (VEC-387).
    for c in todas:
        _aplicar_bairro_concorrente(c)

    # Lê redes do A0 do session state
    redes_a0: list[str] = []
    state = getattr(tool_context, "state", None)
    if state is not None:
        ctx = state.get("market_context")
        ctx = _parse_market_context(ctx)
        if isinstance(ctx, dict):
            # market_context pode estar aninhado: {market_context: {principais_redes_concorrentes: [...]}}
            inner_candidate = ctx.get("market_context")
            inner = inner_candidate if isinstance(inner_candidate, dict) else ctx
            raw_redes = inner.get("principais_redes_concorrentes")
            if isinstance(raw_redes, list):
                redes_a0 = [r for r in raw_redes if isinstance(r, str) and r.strip()]

    # Match: redes do A0 já cobertas vs pendentes
    redes_cobertas: list[str] = []
    redes_pendentes: list[str] = []
    for rede in redes_a0:
        if any(_matches_rede(c.get("nome", ""), rede) for c in todas):
            redes_cobertas.append(rede)
        else:
            redes_pendentes.append(rede)

    redes_detectadas_osm = (
        busca_nearby.get("redes_detectadas_osm")
        if isinstance(busca_nearby.get("redes_detectadas_osm"), list)
        else []
    )
    if not redes_cobertas and redes_detectadas_osm:
        redes_cobertas = list(redes_detectadas_osm)
        if redes_a0:
            redes_pendentes = [r for r in redes_a0 if r not in redes_cobertas]
        else:
            redes_pendentes = []

    # Busca expandida para redes pendentes (geo-fenced).
    #
    # IMPORTANTE: a busca expandida FICA centrada no bairro alvo (lat_alvo/lng_alvo),
    # não no nome da rede. Antes do fix de 2026-05-11, chamávamos
    # `buscar_academias(rede, cidade, raio)`, cujo geocode interno transformava
    # "Selfit, Fortaleza" em coordenadas de uma unidade da Selfit em Fortaleza-centro
    # — e daí buscava num raio dali, trazendo academias de Fortaleza-centro como
    # "concorrentes de Eusébio" (~15km de distância real).
    #
    # Agora: searchText geo-fenced pelo bairro alvo. Se NENHUMA unidade da rede
    # estiver no raio expandido (default 5km), a rede vai pra `redes_nao_encontradas`
    # ao invés de ser fabricada com unidade de outra região.
    redes_nao_encontradas: list[str] = []
    for rede in redes_pendentes:
        match = None
        if lat_alvo and lng_alvo:
            match = _buscar_rede_geofenced(
                rede, lat_alvo, lng_alvo, raio_expandido_metros
            )
        if match:
            # Marca origem + distância pra A6 sinalizar no markdown
            match["origem_busca"] = "expandida_a0"
            match["dentro_do_raio_alvo"] = True
            _aplicar_bairro_concorrente(match)
            todas.append(match)
            redes_cobertas.append(rede)
        else:
            # Rede do A0 não tem unidade real no raio alvo — provável erro do
            # Deep Research (rede da capital sem presença no bairro/cidade alvo).
            redes_nao_encontradas.append(rede)

    # Algoritmo determinístico de Top 10 balanceado.
    # Mudança 2026-05-12 (feedback Marcelo): antes era top 5 com regra
    # "1 por rede A0" — em bairros densos isso enchia os 5 slots com redes
    # e sobrava 0-1 vaga pra independentes. Agora alvo é 10, sendo:
    #   - 1 unidade representativa por rede A0 (máx 4)
    #   - Slots restantes (≥6) pra "_outros" (independentes) e demais
    #     unidades das redes, ordenadas por num_avaliacoes desc.
    # Cobre o cenário real: ~70% das academias do Brasil são independentes.
    ALVO_TOTAL = 10
    MAX_REDES_NO_TOP = 4

    def _classify(c: dict) -> str:
        for rede in redes_a0:
            if _matches_rede(c.get("nome", ""), rede):
                return rede
        return "_outros"

    grupos: dict[str, list[dict]] = {}
    for c in todas:
        grupos.setdefault(_classify(c), []).append(c)
    for g in grupos.values():
        g.sort(key=_avaliacoes_int, reverse=True)

    top_5: list[dict] = []
    selecionados_ids: set = set()

    # Passo 1: melhor unidade de cada rede do A0 coberta (até MAX_REDES_NO_TOP).
    redes_no_top = 0
    for rede in redes_cobertas:
        if redes_no_top >= MAX_REDES_NO_TOP:
            break
        candidatos = grupos.get(rede, [])
        if not candidatos:
            continue
        melhor = candidatos[0]
        pid = melhor.get("place_id") or melhor.get("nome")
        if pid not in selecionados_ids:
            top_5.append(melhor)
            selecionados_ids.add(pid)
            redes_no_top += 1

    # Passo 2: preenche slots restantes priorizando "_outros" (independentes)
    # antes de duplicar redes. Ordenado por num_avaliacoes desc.
    if len(top_5) < ALVO_TOTAL:
        # Independentes primeiro
        outros = list(grupos.get("_outros", []))
        outros.sort(key=_avaliacoes_int, reverse=True)
        for c in outros:
            pid = c.get("place_id") or c.get("nome")
            if pid in selecionados_ids:
                continue
            top_5.append(c)
            selecionados_ids.add(pid)
            if len(top_5) >= ALVO_TOTAL:
                break

    # Passo 3: se ainda não atingiu ALVO_TOTAL, complementa com mais unidades
    # das mesmas redes (2ª/3ª unidade de Smart Fit etc.).
    if len(top_5) < ALVO_TOTAL:
        extras_redes: list[dict] = []
        for rede in redes_cobertas:
            extras_redes.extend(grupos.get(rede, [])[1:])
        extras_redes.sort(key=_avaliacoes_int, reverse=True)
        for c in extras_redes:
            pid = c.get("place_id") or c.get("nome")
            if pid in selecionados_ids:
                continue
            top_5.append(c)
            selecionados_ids.add(pid)
            if len(top_5) >= ALVO_TOTAL:
                break

    def _resumo_unidade(c: dict, *, rede: str | None = None) -> dict:
        return {
            "nome": c.get("nome", ""),
            "rating": c.get("rating_oficial") or c.get("rating_geral"),
            "num_avaliacoes": c.get("num_avaliacoes"),
            "endereco": c.get("endereco", ""),
            "bairro": c.get("bairro_concorrente") or extrair_bairro_endereco(c.get("endereco", "")),
            "place_id": c.get("place_id"),
            "is_independente": rede is None,
            "rede_vinculada": rede,
        }

    top_independentes = [
        _resumo_unidade(c) for c in grupos.get("_outros", [])[:5]
    ]
    academias_analisadas: list[dict] = []
    for c in top_5:
        rede = _classify(c)
        rede_label = None if rede == "_outros" else rede
        academias_analisadas.append(_resumo_unidade(c, rede=rede_label))

    return {
        "bairro": bairro,
        "cidade": cidade,
        "raio_metros": raio_metros,
        "total_encontrados": len(todas),
        # Propaga a contagem agregada (quando disponível) para o envelope do A3a/A3b.
        "total_encontrados_agregado": busca_nearby.get("total_encontrados_agregado"),
        # Count do Nearby (limitado por maxResultCount) — útil pra transparência.
        "total_encontrados_nearby": busca_nearby.get("total_encontrados_nearby"),
        "agregados_competicao_places": busca_nearby.get("agregados_competicao_places") or {},
        "concorrentes": todas,
        # Nome legacy mantido pra compat — agora pode ter até 10 itens.
        "concorrentes_top_5_balanceados": top_5,
        "concorrentes_balanceados": top_5,
        "top_independentes": top_independentes,
        "academias_analisadas": academias_analisadas,
        "redes_a0_solicitadas": redes_a0,
        "redes_a0_cobertas": redes_cobertas,
        "redes_a0_nao_encontradas": redes_nao_encontradas,
        "redes_detectadas_osm": redes_detectadas_osm,
        "metodologia": (
            f"Top {len(top_5)} balanceado: até {MAX_REDES_NO_TOP} redes do A0 "
            "(1 unidade cada, a com mais num_avaliacoes), restante preenchido "
            "por academias independentes ordenadas por num_avaliacoes. Redes "
            "do A0 ausentes na busca nearby são reconciliadas via busca expandida."
        ),
    }


def _review_recente_1ano(data_relativa: str | None) -> bool:
    """Retorna True se a review tem até ~1 ano de idade.

    Google Maps Places API retorna `data_relativa` em inglês, mesmo com
    languageCode=pt-BR — depende do idioma original do review. Casos vistos:

        "today" / "yesterday" / "an hour ago" / "2 hours ago"        ← OK
        "a day ago" / "3 days ago"                                   ← OK
        "a week ago" / "X weeks ago"                                 ← OK
        "a month ago" / "X months ago"                               ← OK
        "a year ago" / "X years ago"                                 ← FORA (>= 1 ano)

    Política: reviews com 'year(s) ago' são descartados pra análise de dores.
    Reviews antigos refletem operação que mudou. Sem `data_relativa` definida,
    assume recente (defensive — não quer descartar review legítimo por falta
    de label).
    """
    if not data_relativa:
        return True  # sem label = mantém
    s = data_relativa.strip().lower()
    if not s:
        return True
    # Qualquer forma de "year" indica >= 1 ano (incluindo "a year ago")
    if "year" in s or "ano" in s:
        return False
    return True


def _reviews_baixa_nota_searchapi(place_id: str, max_reviews: int = 10) -> list[dict]:
    """As 10 reviews de MENOR NOTA via SearchAPI (engine google_maps_reviews).

    Promovido do scripts/backfill_reviews_dores.py (12/06) pro pipeline:
    relatório nasce com dores reais em vez das 5 reviews-elogio da Places.
    Sem SEARCHAPI_KEY ou falha → [] (best-effort, nunca bloqueia)."""
    import os as _os

    import requests as _requests

    key = (_os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key or not place_id:
        return []
    try:
        r = _requests.get(
            "https://www.searchapi.io/api/v1/search",
            params={
                "engine": "google_maps_reviews",
                "place_id": place_id,
                "sort_by": "lowest_rating",
                "hl": "pt-br",
                "gl": "br",
                "api_key": key,
            },
            timeout=45,
        )
        r.raise_for_status()
    except Exception:
        return []
    out: list[dict] = []
    for rev in (r.json().get("reviews") or [])[:max_reviews]:
        texto = (rev.get("text") or rev.get("snippet") or "").strip()
        if not texto:
            continue
        try:
            rating = int(float(rev.get("rating") or 3))
        except (TypeError, ValueError):
            rating = 3
        out.append({
            "autor": (rev.get("user") or {}).get("name") or "anônimo",
            "rating": rating,
            "quote_curta": texto[:280],
            "data_relativa": rev.get("date") or "",
        })
    return out


async def _planos_precos_grounding(nome: str, bairro: str, cidade: str) -> list | None:
    """Planos × preços públicos da academia via Gemini Search Grounding.

    Promovido do scripts/backfill_planos_concorrentes.py (12/06). Cache 7d
    por academia (na tool de grounding). Sem preço confiável → None — nada
    inventado (P-004)."""
    import json as _json

    from tools.gemini_search_grounding import pesquisar_no_google_grounding

    query = (
        f"Quais são os planos e preços de mensalidade da academia '{nome}' "
        f"({bairro or cidade}, {cidade})? Pesquise o site oficial e fontes recentes. "
        "Responda APENAS um JSON array (sem markdown), até 4 planos, no formato: "
        '[{"plano": "nome do plano", "preco_mensal": "R$ 99,90", '
        '"inclui": ["item1", "item2"], "fidelidade": "12 meses ou sem fidelidade"}]. '
        "Se não encontrar preços confiáveis, responda []."
    )
    cache_key = f"planos:{cidade.lower()}:{nome.lower()[:40]}"
    texto = await pesquisar_no_google_grounding(query, cache_key=cache_key)
    if not texto:
        return None
    # raw_decode a partir do primeiro '[': para no fim do PRIMEIRO JSON
    # válido — grounding costuma anexar fontes depois do array e um regex
    # guloso até o último ']' quebrava o parse ("Extra data").
    inicio = texto.find("[")
    if inicio < 0:
        return None
    try:
        data, _fim = _json.JSONDecoder().raw_decode(texto[inicio:])
    except _json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    return [p for p in data[:4] if isinstance(p, dict)] or None


# ── Macro-tool consolidadora para A3b (VEC-380) ─────────────────────
def _slim_concorrente(c: dict) -> dict:
    """
    Reduz um concorrente bruto a um payload mínimo seguro.
    Remove campos grandes (enrichment_search_grounding_text, atividade_marketing
    completa, websites longos) que provocavam MALFORMED_FUNCTION_CALL quando
    o LLM tentava reenviá-los como argumento de tool.
    """
    if not isinstance(c, dict):
        return {}
    # Seleção de reviews pro A3b/writer (12/06): baixa nota PRIMEIRO.
    # O corte antigo (só recentes, cap 5) descartava as reviews de menor
    # nota do SearchAPI — as dores reais — porque costumam ser antigas
    # (round 8: banco ficou sem nenhuma review rica). Prioridade:
    # baixa nota recente > baixa nota antiga > recentes, cap 8.
    todas = [r for r in (c.get("reviews") or []) if isinstance(r, dict)]
    baixa_recente = [
        r for r in todas
        if (r.get("rating") or 5) <= 3 and _review_recente_1ano(r.get("data_relativa"))
    ]
    baixa_antiga = [
        r for r in todas
        if (r.get("rating") or 5) <= 3 and not _review_recente_1ano(r.get("data_relativa"))
    ]
    recentes_ok = [
        r for r in todas
        if (r.get("rating") or 5) > 3 and _review_recente_1ano(r.get("data_relativa"))
    ]
    reviews_raw = (baixa_recente + baixa_antiga + recentes_ok)[:8]
    reviews_slim = []
    for r in reviews_raw:
        if isinstance(r, dict):
            reviews_slim.append({
                "rating": r.get("rating"),
                "dores_detectadas": r.get("dores_detectadas") or [],
                "categoria_dor": r.get("categoria_dor"),
                "sinal": r.get("sinal"),
                "confianca_classificacao": r.get("confianca_classificacao"),
                "servicos_mencionados": r.get("servicos_mencionados") or [],
                "quote_curta": (r.get("quote_curta") or "")[:180],
                "autor": r.get("autor"),
                "data_relativa": r.get("data_relativa"),
            })
    am = c.get("atividade_marketing") or {}
    website_raw = (c.get("website") or "").strip()
    lat = c.get("lat")
    lng = c.get("lng")
    try:
        lat_f = float(lat) if lat is not None else None
        lng_f = float(lng) if lng is not None else None
        if lat_f == 0.0 and lng_f == 0.0:
            lat_f, lng_f = None, None
    except (TypeError, ValueError):
        lat_f, lng_f = None, None
    dist = c.get("distancia_km")
    try:
        dist_f = round(float(dist), 2) if dist is not None else None
    except (TypeError, ValueError):
        dist_f = None
    maps_uri = (c.get("google_maps_uri") or "").strip() or None
    return {
        "nome": c.get("nome", "Desconhecido"),
        "place_id": c.get("place_id"),
        "lat": lat_f,
        "lng": lng_f,
        "distancia_km": dist_f,
        "google_maps_uri": maps_uri,
        "endereco": c.get("endereco", ""),
        "bairro_concorrente": c.get("bairro_concorrente") or extrair_bairro_endereco(c.get("endereco", "")),
        "rating_geral": c.get("rating_oficial") or c.get("rating_geral"),
        "num_avaliacoes": c.get("num_avaliacoes"),
        "tem_24h": c.get("tem_24h"),
        # Places API contact data — propaga pra writer salvar em competidores.
        # Truncado em 80 chars pra evitar MALFORMED em websites com query strings longas.
        "telefone": (c.get("telefone") or "").strip() or None,
        "website": website_raw[:200] if website_raw else None,
        "reviews": reviews_slim,
        "horarios_pico": c.get("horarios_pico"),
        "planos_precos": c.get("planos_precos"),
        "servicos_oferecidos": (am.get("servicos_ofertados") or [])[:15] if isinstance(am, dict) else [],
        "reclamacoes_marketing": (am.get("principais_reclamacoes") or [])[:8] if isinstance(am, dict) else [],
        "is_independente": bool(c.get("is_independente")),
        "rede_vinculada": c.get("rede_vinculada"),
    }


# ── Macro-tool consolidadora para A3a (Task #48 VEC) ────────────────
async def analisar_concorrentes_a3a_completo(
    tool_context,
    bairro: str,
    cidade: str,
) -> dict:
    """
    Macro-tool A3a CompetitorSearch — consolida 4 tools em 1 call.

    Por que async: `enriquecer_concorrente_via_google` é coroutine
    (usa Playwright assíncrono). ADK FunctionTool aceita async direto,
    detecta via inspect.iscoroutinefunction.

    Por que existe (Task #48):
    A3a antigo iterava em 9 calls do LLM chamando uma tool por vez por
    concorrente. Cada round-trip acumulava ~17k → 34k tokens. Esta macro
    encapsula tudo em código Python determinístico (1 call de tool).

    Pipeline:
      1. buscar_concorrentes_balanceados — Top 5 com cobertura A0
      2. Filtro semântico academia_tradicional (descarta clínicas)
      3. Para cada concorrente:
          - buscar_reviews_academia (síncrono)
          - await enriquecer_concorrente_via_google (async, Playwright)
      4. classificar_dores_reviews_batch_gemini — 1 Gemini Flash call
         classifica TODAS reviews em batch (Task #46)
      5. aplicar_classificacao_dores — muta in-place

    Retorna `concorrentes_brutos` pronto pro A3b consumir via state.
    """
    import asyncio
    # Importações tardias pra evitar ciclo na inicialização
    from tools.playwright_enrichment import enriquecer_concorrente_via_google

    busca = buscar_concorrentes_balanceados(tool_context, bairro, cidade)
    if "erro" in busca:
        return {
            "erro": busca["erro"],
            "concorrentes_brutos": [],
            "concorrentes_excluidos": [],
            "redes_a0_solicitadas": [],
            "redes_a0_cobertas": [],
            "redes_a0_nao_encontradas": [],
        }

    top_5 = busca.get("concorrentes_balanceados") or busca.get("concorrentes_top_5_balanceados") or []

    # Filtro semântico academia_tradicional
    incluidos: list[dict] = []
    excluidos: list[dict] = []
    for c in top_5:
        eh_academia, motivo = _eh_academia_tradicional(c)
        if eh_academia:
            incluidos.append(c)
        else:
            excluidos.append({"nome": c.get("nome", "?"), "motivo": motivo})

    # Pra cada incluído: reviews (sync) + enrichment (async)
    concorrentes_brutos: list[dict] = []

    async def _processar_um(c: dict) -> dict:
        place_id = c.get("place_id", "")
        nome = c.get("nome", "?")

        # Reviews via Places Details (síncrono — httpx blocking)
        reviews_data = buscar_reviews_academia(place_id, nome)
        reviews = reviews_data.get("reviews", []) if "erro" not in reviews_data else []

        # Enrichment Google Knowledge Panel (async — Playwright).
        # Best-effort: pode falhar por Cloudflare; não bloqueia pipeline.
        enrichment: dict = {}
        try:
            result = await enriquecer_concorrente_via_google(nome, cidade)
            enrichment = result if isinstance(result, dict) else {}
        except Exception as e:
            enrichment = {"scraping_status": f"exception: {type(e).__name__}"}

        # Horários de pico via popular_times_tool (Tier 0 SearchAPI, Tier 1 lib,
        # Tier 2 Playwright). Best-effort — falha vira dados_por_dia vazio,
        # NÃO bloqueia pipeline. Cache 7d por place_id.
        horarios_pico_dict: dict | None = None
        pico_semanal_str: str | None = enrichment.get("pico_semanal")
        atributos_sobre: dict = {}
        if place_id:
            try:
                from tools.maps_tools import obter_atributos_place

                atributos_sobre = obter_atributos_place(place_id) or {}
            except Exception:
                atributos_sobre = {}

        if place_id:
            try:
                from tools.maps_place_id import montar_maps_url_place
                from tools.popular_times_tool import pesquisar_horarios_pico

                maps_url = (
                    c.get("google_maps_uri")
                    or montar_maps_url_place(
                        nome,
                        place_id,
                        c.get("lat"),
                        c.get("lng"),
                    )
                )
                pico_resultado = await pesquisar_horarios_pico(
                    maps_url,
                    place_id,
                    nome=nome,
                    cidade=cidade,
                    lat=c.get("lat"),
                    lng=c.get("lng"),
                )
                if pico_resultado.get("status") == "ok":
                    horarios_pico_dict = pico_resultado.get("dados_por_dia") or None
                    dia_top = pico_resultado.get("dia_mais_movimentado") or {}
                    if dia_top.get("dia") and dia_top.get("hora"):
                        pico_semanal_str = (
                            f"{dia_top['dia'].capitalize()} {dia_top['hora']}h "
                            f"({dia_top.get('percentual', 0)}%)"
                        )
            except Exception as e:
                print(f"[A3a popular_times] {nome}: {type(e).__name__}: {e}")
        if horarios_pico_dict is None:
            horarios_pico_dict = enrichment.get("horarios_pico")

        # Reviews de MENOR NOTA via SearchAPI — Places Details devolve só 5
        # "mais relevantes" enviesadas pro elogio (Smart Fit 1.329 aval sem
        # nenhuma ≤3★). As dores reais moram nas piores; merge dedup.
        if place_id:
            try:
                piores = _reviews_baixa_nota_searchapi(place_id)
                if piores:
                    vistos = {
                        ((r.get("autor") or ""), (r.get("quote_curta") or "")[:60])
                        for r in reviews
                    }
                    reviews = piores + [
                        r for r in reviews
                        if ((r.get("autor") or ""), (r.get("quote_curta") or "")[:60]) not in vistos
                    ]
                    reviews = reviews[:15]
            except Exception as e:
                logger.warning(f"[A3a reviews_baixa_nota] {nome}: {type(e).__name__}: {e}")

        # Planos × preços públicos via grounding (cache 7d por academia).
        # Metodologia analise_mercado_fitness: comparativo plano/preço/oferta
        # é decisão de posicionamento — sem preço confiável, fica None.
        planos_precos: list | None = None
        try:
            planos_precos = await _planos_precos_grounding(
                nome, c.get("bairro_concorrente") or bairro, cidade
            )
        except Exception as e:
            logger.warning(f"[A3a planos_precos] {nome}: {type(e).__name__}: {e}")

        maps_uri = (c.get("google_maps_uri") or "").strip() or None
        return {
            "place_id": place_id,
            "nome": nome,
            "endereco": c.get("endereco", ""),
            "bairro_concorrente": c.get("bairro_concorrente"),
            "lat": c.get("lat"),
            "lng": c.get("lng"),
            "distancia_km": c.get("distancia_km"),
            "google_maps_uri": maps_uri,
            "rating_oficial": reviews_data.get("rating_geral", c.get("rating")),
            "num_avaliacoes": reviews_data.get("total_avaliacoes", c.get("num_avaliacoes", 0)),
            "tem_24h": c.get("tem_24h", False),
            "telefone": c.get("telefone", ""),
            "website": c.get("website", ""),
            "origem_busca": c.get("origem_busca", "nearby"),
            "reviews": reviews,
            "horarios_pico": horarios_pico_dict,
            "pico_semanal": pico_semanal_str,
            "planos_precos": planos_precos,
            "atributos_sobre": atributos_sobre if atributos_sobre and "erro" not in atributos_sobre else None,
            "atividade_marketing": enrichment.get("atividade_marketing"),
            "enrichment_search_grounding_text": enrichment.get("scraping_text"),
        }

    # Processa concorrentes em sequência (Playwright costuma travar com
    # múltiplas instâncias paralelas no Windows; sequencial é seguro)
    for c in incluidos:
        concorrentes_brutos.append(await _processar_um(c))

    # Classificação semântica de dores em BATCH único (Task #46).
    # Roda em thread pra não bloquear event loop (Gemini client é sync).
    classificacoes = await asyncio.to_thread(
        classificar_dores_reviews_batch_gemini, concorrentes_brutos
    )
    aplicar_classificacao_dores(concorrentes_brutos, classificacoes)

    redes_a0 = busca.get("redes_a0_solicitadas") or []
    for c in concorrentes_brutos:
        nome = c.get("nome", "")
        rede_match = next((r for r in redes_a0 if _matches_rede(nome, r)), None)
        c["is_independente"] = rede_match is None
        c["rede_vinculada"] = rede_match

    return {
        "escopo_busca": "academia_tradicional",
        "total_concorrentes": len(concorrentes_brutos),
        # Usa contagem agregada quando disponível (Tier 0 Geo),
        # fallback para o count do Nearby Search (limitado a maxResultCount).
        "total_encontrados_raio": (
            busca.get("total_encontrados_agregado")
            if busca.get("total_encontrados_agregado") is not None
            else busca.get("total_encontrados", 0)
        ),
        "total_encontrados_raio_nearby": busca.get("total_encontrados_nearby"),
        "agregados_competicao_places": busca.get("agregados_competicao_places") or {},
        "top_independentes": busca.get("top_independentes", []),
        "academias_analisadas": busca.get("academias_analisadas", []),
        "concorrentes_brutos": concorrentes_brutos,
        "concorrentes_excluidos": excluidos,
        "redes_a0_solicitadas": busca.get("redes_a0_solicitadas", []),
        "redes_a0_cobertas": busca.get("redes_a0_cobertas", []),
        "redes_a0_nao_encontradas": busca.get("redes_a0_nao_encontradas", []),
        "metodologia": (
            "Top 5 balanceado (1 unidade por rede A0 + complemento por nº "
            "avaliações), filtro semântico academia_tradicional, reviews via "
            "Places Details, enrichment Google (best-effort), classificação "
            "semântica de dores via Gemini Flash em batch único."
        ),
        "classificacao_dores_status": (
            "ok" if classificacoes else "fallback_substring (Gemini falhou)"
        ),
    }


def analisar_concorrentes_completo(tool_context) -> dict:
    """
    Macro-tool consolidadora para A3b CompetitorAnalysis.

    Lê `concorrentes_brutos` direto do `tool_context.state` (output_key do A3a)
    e executa as 4 análises em UMA chamada:
      - analisar_gap_competitivo
      - analisar_picos_competitivos
      - classificar_saturacao
      - calcular_score_concorrencia

    Por que essa tool não recebe `concorrentes_brutos` como argumento:
    o payload do A3a inclui `enrichment_search_grounding_text` (1k+ chars
    por concorrente) que, quando reenviado pelo LLM em function_call,
    provocava MALFORMED_FUNCTION_CALL e A3b OUT=0 (VEC-380). Ao ler do
    state, o function_call vira `analisar_concorrentes_completo()` puro
    sem argumentos — impossível ser malformed.

    Retorna o dict consumido pelo `output_key="inteligencia_competitiva"`
    do A3b. O LLM só precisa adicionar `posicionamento_recomendado` e
    `resumo_executivo` (texto livre) por cima.
    """
    state = getattr(tool_context, "state", None)
    if state is None:
        return {"erro": "tool_context.state indisponível"}

    raw = state.get("concorrentes_brutos")
    bairro = state.get("bairro") or ""
    cidade = state.get("cidade") or ""
    envelope: dict = {}

    # A3a também emite via output_key — pode vir como markdown com ```json fence,
    # mesmo problema do market_context. Reusa o parser robusto.
    if isinstance(raw, list):
        lista = raw
    elif isinstance(raw, dict):
        envelope = raw
        lista = raw.get("concorrentes_brutos") or raw.get("concorrentes") or []
        bairro = bairro or raw.get("bairro") or ""
        cidade = cidade or raw.get("cidade") or ""
    else:
        parsed = _parse_market_context(raw)
        if isinstance(parsed, dict):
            envelope = parsed
            lista = parsed.get("concorrentes_brutos") or parsed.get("concorrentes") or []
            if not bairro:
                bairro = parsed.get("bairro") or ""
            if not cidade:
                cidade = parsed.get("cidade") or ""
        elif isinstance(parsed, list):
            lista = parsed
        else:
            lista = []

    if not lista:
        return {
            "inteligencia_competitiva": {
                "concorrentes_detalhados": [],
                "dores_dominantes": [],
                "servicos_nao_oferecidos": [],
                "oportunidades_rankeadas": [],
                "score_oportunidade_mercado": 0.0,
                "melhor_avaliada": {"nome": "N/A", "rating": 0},
                "pior_avaliada": {"nome": "N/A", "rating": 0},
            },
            "estrategia_counter_programming": {
                "picos_compartilhados": [],
                "vales_compartilhados": [],
                "estrategias_acionaveis": [],
                "concorrentes_com_dados": 0,
            },
            "nivel_saturacao": "BAIXO",
            "rating_medio_concorrentes": 0.0,
            "score_concorrencia": 7.0,
            "aviso": "concorrentes_brutos vazio — análise heurística de fallback",
        }

    slim = [_slim_concorrente(c) for c in lista if isinstance(c, dict)]
    slim = [s for s in slim if s.get("nome") != "Desconhecido" or s.get("reviews")]

    gap = analisar_gap_competitivo(slim, bairro)

    # Importação atrasada: analisar_picos_competitivos vive em outro módulo.
    try:
        from tools.playwright_enrichment import analisar_picos_competitivos
        picos_input = [{"nome": s.get("nome"), "horarios_pico": s.get("horarios_pico")} for s in slim]
        picos = analisar_picos_competitivos(picos_input)
    except Exception as e:
        picos = {
            "picos_compartilhados": [],
            "vales_compartilhados": [],
            "estrategias_acionaveis": [],
            "concorrentes_com_dados": 0,
            "erro": f"analisar_picos_competitivos falhou: {e}",
        }

    # Métricas agregadas
    ratings: list[float] = []
    for s in slim:
        r = s.get("rating_geral")
        if isinstance(r, (int, float)):
            ratings.append(float(r))
    rating_medio = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    num = len(slim)
    total_raio = int(
        envelope.get("total_encontrados_raio")
        or envelope.get("total_encontrados")
        or num
    )
    total_raio_nearby = envelope.get("total_encontrados_raio_nearby")
    try:
        total_raio_nearby = int(total_raio_nearby) if total_raio_nearby is not None else None
    except (TypeError, ValueError):
        total_raio_nearby = None

    cnpj_cidade: int | None = None
    mc_raw = state.get("market_context")
    mc = _parse_market_context(mc_raw) if mc_raw is not None else {}
    nested_mc = mc.get("market_context")
    mc_inner: dict = nested_mc if isinstance(nested_mc, dict) else mc
    val = mc_inner.get("parque_ativo_total")
    if not isinstance(val, int):
        val = mc_inner.get("academias_ativas_cidade_cnpj")
    if isinstance(val, int):
        cnpj_cidade = val
    elif not cidade:
        cidade_raw = mc_inner.get("cidade")
        cidade = cidade_raw if isinstance(cidade_raw, str) else ""
    if cnpj_cidade is None and cidade:
        try:
            from tools.cnpj_fitness_tools import count_parque_ativo

            uf_raw = mc_inner.get("uf")
            uf_mc = uf_raw if isinstance(uf_raw, str) else ""
            cnpj_cidade = count_parque_ativo(cidade, uf_mc)
        except Exception:
            cnpj_cidade = None

    pano = panorama_saturacao(
        total_raio=total_raio,
        total_analisados=num,
        raio_km=3.0,
        cnpj_cidade=cnpj_cidade,
    )
    saturacao = pano["nivel_saturacao"]
    score_conc = calcular_score_concorrencia(total_raio, rating_medio, saturacao)

    # Distribuição geográfica — agrupa concorrentes por bairro_concorrente.
    # Usado pelo A6 para (a) etiquetar concorrentes na seção de inteligência
    # competitiva e (b) filtrar bairros alternativos saturados (VEC-387).
    distribuicao: dict[str, list[str]] = {}
    for s in slim:
        b = s.get("bairro_concorrente") or "Desconhecido"
        distribuicao.setdefault(b, []).append(s.get("nome", "?"))

    distribuicao_geografica = sorted(
        [
            {"bairro": b, "count": len(nomes), "academias": nomes}
            for b, nomes in distribuicao.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )

    return {
        "inteligencia_competitiva": {
            "concorrentes_detalhados": slim,
            "dores_dominantes": gap.get("dores_dominantes", []),
            "servicos_nao_oferecidos": gap.get("servicos_nao_oferecidos", []),
            "oportunidades_rankeadas": gap.get("oportunidades_rankeadas", []),
            "score_oportunidade_mercado": gap.get("score_oportunidade_mercado", 0.0),
            "melhor_avaliada": gap.get("melhor_avaliada", {"nome": "N/A", "rating": 0}),
            "pior_avaliada": gap.get("pior_avaliada", {"nome": "N/A", "rating": 0}),
        },
        "estrategia_counter_programming": picos,
        "nivel_saturacao": saturacao,
        "panorama_competitivo": pano,
        "agregados_competicao_places": envelope.get("agregados_competicao_places") or {},
        "rating_medio_concorrentes": rating_medio,
        "score_concorrencia": score_conc,
        "total_concorrentes_analisados": num,
        "total_encontrados_raio": total_raio,
        "total_encontrados_raio_nearby": total_raio_nearby,
        "top_independentes": envelope.get("top_independentes") or [],
        "academias_analisadas": envelope.get("academias_analisadas") or [],
        "distribuicao_geografica": distribuicao_geografica,
    }
