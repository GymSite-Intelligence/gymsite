
# tools/competitor_tools.py
"""Inteligência competitiva profunda: busca, reviews, gap analysis."""
import logging
import math
import json
import os
import httpx

logger = logging.getLogger(__name__)
from tools.google_maps_key import get_google_maps_api_key
from tools.maps_tools import calcular_distancia_km, geocode_endereco
from tools.parametros_metodologia import param, param_int
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

DORES_COMUNS_TO_CATEGORIA: dict[str, str] = {
    "muito cheio": "lotacao",
    "lotado": "lotacao",
    "lotação": "lotacao",
    "fila nas máquinas": "lotacao",
    "fila": "lotacao",
    "equipamentos quebrados": "equipamento_problema",
    "quebrado": "equipamento_problema",
    "quebrada": "equipamento_problema",
    "manutenção": "equipamento_problema",
    "sem ar condicionado": "climatizacao",
    "calor": "climatizacao",
    "abafado": "climatizacao",
    "instrutores ruins": "atendimento_ruim",
    "atendimento ruim": "atendimento_ruim",
    "grosseiro": "atendimento_ruim",
    "sem estacionamento": "estacionamento",
    "sem vaga": "estacionamento",
    "mensalidade cara": "preco_alto",
    "caro": "preco_alto",
    "preço alto": "preco_alto",
    "banheiros sujos": "limpeza_higiene",
    "limpeza": "limpeza_higiene",
    "sujo": "limpeza_higiene",
    "sem professor": "ausencia_servico",
    "sozinho": "ausencia_servico",
    "abandonado": "ausencia_servico",
    "música alta": "ruido_alto",
    "barulho": "ruido_alto",
    "cancela plano difícil": "contrato_abusivo",
    "cancelamento": "contrato_abusivo",
    "fidelidade": "contrato_abusivo",
    "multa": "contrato_abusivo",
    "cobrança indevida": "contrato_abusivo",
    "abusivo": "contrato_abusivo",
    "sem aulas coletivas": "ausencia_servico",
    "estrutura velha": "estrutura_envelhecida",
    "antigo": "estrutura_envelhecida",
}

TOPIC_KEYWORD_TO_CATEGORIA: list[tuple[str, str]] = [
    ("lotat", "lotacao"), ("crowd", "lotacao"), ("cheio", "lotacao"), ("busy", "lotacao"),
    ("wait", "lotacao"), ("fila", "lotacao"), ("queue", "lotacao"),
    ("equip", "equipamento_problema"), ("machine", "equipamento_problema"),
    ("manuten", "equipamento_problema"), ("broken", "equipamento_problema"),
    ("air cond", "climatizacao"), ("climat", "climatizacao"), ("hot", "climatizacao"),
    ("calor", "climatizacao"), ("abafado", "climatizacao"),
    ("clean", "limpeza_higiene"), ("higen", "limpeza_higiene"), ("banheiro", "limpeza_higiene"),
    ("sujo", "limpeza_higiene"), ("hygien", "limpeza_higiene"),
    ("staff", "atendimento_ruim"), ("atend", "atendimento_ruim"), ("recep", "atendimento_ruim"),
    ("instrutor", "atendimento_ruim"), ("service", "atendimento_ruim"), ("professor", "atendimento_ruim"),
    ("price", "preco_alto"), ("preço", "preco_alto"), ("preco", "preco_alto"),
    ("caro", "preco_alto"), ("mensal", "preco_alto"), ("expensive", "preco_alto"),
    ("cancel", "contrato_abusivo"), ("contrat", "contrato_abusivo"), ("cobran", "contrato_abusivo"),
    ("multa", "contrato_abusivo"), ("billing", "contrato_abusivo"),
    ("parking", "estacionamento"), ("estacion", "estacionamento"), ("vaga", "estacionamento"),
    ("old", "estrutura_envelhecida"), ("antig", "estrutura_envelhecida"),
    ("noise", "ruido_alto"), ("music", "ruido_alto"), ("barulho", "ruido_alto"), ("ruido", "ruido_alto"),
    ("hour", "horarios_limitados"), ("horário", "horarios_limitados"), ("horario", "horarios_limitados"),
    ("class", "ausencia_servico"), ("aula", "ausencia_servico"), ("personal", "ausencia_servico"),
    ("security", "seguranca"), ("segur", "seguranca"), ("furto", "seguranca"),
]

TAXONOMIA_SOLUCAO: dict[str, str] = {
    "lotacao": "Controle de lotação via app + reserva de horário",
    "equipamento_problema": "Contrato de manutenção preventiva com SLA 24h",
    "climatizacao": "Climatização premium como diferencial de conforto",
    "limpeza_higiene": "Limpeza programada com checklist visível a cada 2h",
    "atendimento_ruim": "Treinamento intensivo + NPS público mensal",
    "preco_alto": "Modelo transparente sem fidelidade nem multa",
    "contrato_abusivo": "Cancelamento digital em 1 clique",
    "estacionamento": "Estacionamento próprio ou parceria com vaga grátis",
    "estrutura_envelhecida": "Renovação anual de equipamentos programada",
    "ruido_alto": "Áreas com DJ + áreas silenciosas separadas",
    "horarios_limitados": "Horário estendido ou 24h em turnos de baixa",
    "ausencia_servico": "Pacote de aulas coletivas + personal de entrada",
    "seguranca": "CFTV + controle de acesso + iluminação perimetral",
}


def _map_topic_keyword_to_categoria(keyword: str) -> str:
    kw = (keyword or "").strip().lower()
    if not kw:
        return "outra"
    for hint, cat in TOPIC_KEYWORD_TO_CATEGORIA:
        if hint in kw:
            return cat
    return "outra"


def _normalize_searchapi_topics(topics: list | None) -> list[dict]:
    out: list[dict] = []
    for raw in topics or []:
        if not isinstance(raw, dict):
            continue
        keyword = (raw.get("keyword") or raw.get("name") or "").strip()
        if not keyword:
            continue
        try:
            mencoes = int(raw.get("reviews") or raw.get("mentions") or raw.get("count") or 0)
        except (TypeError, ValueError):
            mencoes = 0
        cat = _map_topic_keyword_to_categoria(keyword)
        out.append({
            "keyword": keyword,
            "mencoes": mencoes,
            "categoria_dor": cat,
            "topic_id": raw.get("id") or raw.get("topic_id"),
            "fonte": "searchapi_topics",
        })
    out.sort(key=lambda x: x.get("mencoes", 0), reverse=True)
    return out


def _build_temas_insatisfacao(topics: list | None, reviews: list | None = None) -> list[dict]:
    temas = [t for t in _normalize_searchapi_topics(topics) if t.get("categoria_dor") != "outra"]
    if temas:
        return temas[:10]
    if not reviews:
        return []
    agg: dict[str, int] = {}
    for rev in reviews:
        if not isinstance(rev, dict):
            continue
        if int(rev.get("rating") or 3) > 3:
            continue
        cat = (rev.get("categoria_dor") or "").strip()
        if cat and cat != "outra":
            agg[cat] = agg.get(cat, 0) + 1
    return [
        {"keyword": cat, "mencoes": n, "categoria_dor": cat, "fonte": "reviews_baixa_nota"}
        for cat, n in sorted(agg.items(), key=lambda x: -x[1])
    ][:10]


def _sinal_from_rating(rating: int | float | None) -> str:
    try:
        r = int(rating or 3)
    except (TypeError, ValueError):
        r = 3
    if r >= 4:
        return "positivo"
    if r <= 2:
        return "negativo"
    return "neutro"


def _infer_categoria_dor_review(review: dict) -> dict[str, str]:
    rating = review.get("rating", 3)
    texto_low = (review.get("quote_curta") or "").lower()
    for dor in review.get("dores_detectadas") or []:
        if not isinstance(dor, str):
            continue
        cat = DORES_COMUNS_TO_CATEGORIA.get(dor)
        if cat:
            return {
                "categoria_dor": cat,
                "sinal": _sinal_from_rating(rating),
                "confianca_classificacao": "alta",
            }
    for hint, cat in TOPIC_KEYWORD_TO_CATEGORIA:
        if hint in texto_low:
            return {
                "categoria_dor": cat,
                "sinal": _sinal_from_rating(rating),
                "confianca_classificacao": "media",
            }
    try:
        r = int(float(rating or 3))
    except (TypeError, ValueError):
        r = 3
    if r <= 2:
        return {"categoria_dor": "outra", "sinal": "negativo", "confianca_classificacao": "baixa"}
    if r >= 4:
        return {"categoria_dor": "outra", "sinal": "positivo", "confianca_classificacao": "baixa"}
    return {"categoria_dor": "outra", "sinal": "neutro", "confianca_classificacao": "baixa"}


def classificar_dores_reviews_deterministico(concorrentes_com_reviews: list[dict]) -> list[dict]:
    for c in concorrentes_com_reviews:
        if not isinstance(c, dict):
            continue
        place_id = c.get("place_id") or ""
        bundle = _fetch_reviews_bundle(place_id) if place_id else None
        topics = (bundle or {}).get("topics") or c.get("searchapi_topics") or []
        if topics and not c.get("searchapi_topics"):
            c["searchapi_topics"] = _normalize_searchapi_topics(topics)
        if not c.get("temas_insatisfacao"):
            c["temas_insatisfacao"] = _build_temas_insatisfacao(topics, c.get("reviews"))
        for review in c.get("reviews") or []:
            if not isinstance(review, dict):
                continue
            if review.get("categoria_dor"):
                continue
            review.update(_infer_categoria_dor_review(review))
    return concorrentes_com_reviews


def _classificacao_dores_usa_gemini() -> bool:
    return os.getenv("CLASSIFICAR_DORES_GEMINI", "").strip().lower() in ("1", "true", "yes", "on")


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


# tipo_negocio (enum do formulário) → termo natural de busca. O enum cru
# ("crossfit_box") é ruim como query; mapa rotulado (regra de ouro, não hardcode).
_TIPO_NEGOCIO_KW = {
    "academia": "academias",
    "crossfit_box": "crossfit",
    "studio_pilates": "pilates",
    "studio_funcional": "treinamento funcional",
    "outro": "academias",
}
# Tipos do Places que contam como academia tradicional. Mata restaurante/escritório/
# loja (validado por auditoria Maps: Vistta Rooftop, Duets Office Towers caíam fora).
_FITNESS_TYPES = {"gym", "fitness_center"}

# Filtro de RELEVÂNCIA por tipo_negocio do form: _FITNESS_TYPES só garante "é fitness",
# deixando crossfit/luta/pilates vazarem num relatório de "academia". ON = sinal genérico
# do alvo; OFF = categorias especializadas que NÃO são o negócio. Concorrente com sinal OFF
# e SEM sinal ON é fora-de-escopo (ex.: "REK CrossFit", "Eikō Artes Marciais" em academia).
# ON = sinal da ESPECIALIDADE (pra alvos especializados, mantém só quem bate).
_TIPO_ON_KW = {
    "crossfit_box": ("crossfit", "cross training", "cross fit"),
    "studio_pilates": ("pilates",),
    "studio_funcional": ("funcional", "treinamento funcional", "personal", "cross training"),
}
# Sinal POSITIVO de fitness no nome (quando o Places/A3b não traz `tipos`): sem
# nenhum destes E sem tipo gym/fitness_center, o candidato é fora-de-domínio
# (parque, praça, arena de beach, shopping) mesmo carregando o bairro no nome.
_FITNESS_NOME_KW = (
    "academia", "fitness", "gym", "studio", "estudio", "training", "treinamento",
    "musculacao", "esporte", "cia atletica", "companhia atletica",
)

# OFF (só p/ alvo genérico 'academia') = categorias especializadas que não são academia.
_TIPO_OFF_ACADEMIA = (
    "crossfit", "cross training", "cross fit", "artes marciais", "jiu", "muay", "boxe",
    "judo", "karate", "taekwondo", "luta", "mma", "pilates", "yoga", "escola de danca",
    "ballet", "dojo", "natacao",
    # Formato 1: studio/funcional/personal não contam como academia tradicional
    "studio", "estudio", "funcional", "personal training", "personalizado",
)


_TIPO_EXCLUDE_ACADEMIA = (
    "crossfit", "studio", "estudio", "pilates", "funcional",
    "jiu", "yoga", "boxe", "mma", "personalizado",
)
_TIPO_PLACES_PADRAO = "gym"

# Contagem nacional: inclusão por distância ao centróide (não string de bairro).
# Evidência jul/2026: Cocó ~3,3 km²; R=1500 vazava vizinho; Meireles/Bessa/Moema.
RAIO_CONCORRENCIA_CANONICO_M = 1000


def exclude_aplicado_tipo(tipo_negocio: str) -> list[str]:
    """Termos excluídos pós-fetch (Formato 1) conforme tipo_negocio do form."""
    tn = (tipo_negocio or "academia").strip().lower()
    if tn == "academia":
        return list(_TIPO_EXCLUDE_ACADEMIA)
    return []


def _formato1_place_token(s: str) -> str:
    """Bairro/cidade na query Formato 1: fold acento + Title Case legível.

    Cocó ≡ Coco → mesma query → mesmo params_hash (search_raw) → mesmo recall.
    """
    from tools.bairro_normalize import fold_texto, formatar_bairro_exibicao

    return formatar_bairro_exibicao(fold_texto(s))


def _query_formato1(tipo_negocio: str, bairro: str, cidade: str, uf: str) -> str:
    """Formato 1 determinístico: '<tipo> no bairro <bairro>, <cidade> - <UF>'.

    Bairro/cidade vão foldados (sem acento) pra unificar cache SearchAPI e recall
    Maps — Cocó e Coco não podem virar dois mundos.
    """
    tn = (tipo_negocio or "academia").strip().lower()
    kw = _TIPO_NEGOCIO_KW.get(tn, "academias")
    termo_q = {
        "academias": "academia",
        "crossfit": "crossfit",
        "pilates": "pilates",
        "treinamento funcional": "treinamento funcional",
    }.get(kw, kw[:-1] if kw.endswith("s") else kw)
    uf_s = (uf or "").strip().upper()
    bairro_q = _formato1_place_token(bairro) if bairro else ""
    cidade_q = _formato1_place_token(cidade) if cidade else ""
    if bairro_q and cidade_q and uf_s:
        return f"{termo_q} no bairro {bairro_q}, {cidade_q} - {uf_s}"
    if bairro_q and cidade_q:
        return f"{termo_q} no bairro {bairro_q}, {cidade_q}"
    return " ".join(x for x in [termo_q, bairro_q, cidade_q, uf_s] if x and str(x).strip())

def _maps_search_url_from_query(query: str) -> str:
    """Formato 2: URL Maps = mesma string da query Formato 1 (1:1 link = query)."""
    from urllib.parse import quote_plus

    return f"https://www.google.com/maps/search/{quote_plus((query or '').strip())}/"


def _filtrar_status_operacional(concorrentes: list[dict]) -> list[dict]:
    """Descarta fechadas. Sem gate de string de bairro (canônico nacional — R do centróide)."""
    if not concorrentes:
        return concorrentes
    out = [c for c in concorrentes if isinstance(c, dict)]

    def _status(s: dict) -> str:
        return str(s.get("status") or s.get("business_status")
                   or s.get("businessStatus") or "").upper()

    operacionais = [s for s in out if "CLOSED" not in _status(s)]
    fechadas = [s for s in out if "CLOSED" in _status(s)]
    if fechadas and operacionais:
        logger.info("filtro status: %d fechada(s) descartada(s) (%s)", len(fechadas),
                    ", ".join(f"{s.get('nome','?')}={_status(s)}" for s in fechadas[:5]))
        out = operacionais
    return out


def _filtrar_status_e_bairro(concorrentes: list[dict], *, bairro: str) -> list[dict]:
    """Compat: só status. `bairro` ignorado (gate string proibido no caminho crítico)."""
    del bairro
    return _filtrar_status_operacional(concorrentes)


def filtrar_concorrentes_bairro_tipo(
    concorrentes: list[dict], *, bairro: str, tipo_negocio: str
) -> list[dict]:
    """Filtro determinístico AUTORITATIVO (A6 / site / tools).

    Inclusão geográfica = raio do centróide em `buscar_academias` (R canônico 1000 m).
    Aqui: status operacional + gate de TIPO (tira pilates/crossfit/luta num relatório
    de academia). `bairro` permanece na assinatura por compat; NÃO filtra por string.
    """
    if not concorrentes:
        return concorrentes
    out = _filtrar_status_operacional(concorrentes)
    del bairro
    tn = (tipo_negocio or "").strip().lower()
    if tn == "academia" or tn in _TIPO_ON_KW:
        on_tipo = [s for s in out if _tipo_relevante(s, tipo_negocio)]
        fora_t = [s for s in out if not _tipo_relevante(s, tipo_negocio)]
        if len(on_tipo) >= 2:
            if fora_t:
                logger.info("filtro tipo '%s': %d on-type, %d fora (%s)", tipo_negocio,
                            len(on_tipo), len(fora_t), ", ".join(s.get("nome", "?") for s in fora_t[:5]))
            out = on_tipo
    return out


def _tipo_relevante(c: dict, tipo_negocio: str) -> bool:
    """Bate o tipo_negocio do form pela CATEGORIA do Google (autoritativa).
    - 'academia' (genérico): fora só se a categoria é uma especialidade DIFERENTE
      (CrossFit/Artes Marciais/Pilates/...). Academia comum c/ piscina fica.
    - especializado (crossfit_box/pilates/funcional): dentro só se categoria/nome bate
      a especialidade. 'outro'/desconhecido → sem filtro."""
    tn = (tipo_negocio or "academia").strip().lower()
    tipos_raw = [str(t) for t in (c.get("tipos") or [])]
    tipos = [t for t in tipos_raw if t not in ("gym", "fitness_center")]
    tipos_blob = _norm_txt(" ".join(tipos))
    nome_blob = _norm_txt(c.get("nome") or "")

    if tn == "academia":
        # Gate POSITIVO primeiro: precisa ter sinal de fitness na categoria do Google
        # OU no nome — sem isso, parque estadual/arena de beach/praça que carregam o
        # bairro no nome passavam só por não estarem na blocklist (bug Cocó 4b211a02).
        tem_tipo_fitness = any(t in _FITNESS_TYPES for t in tipos_raw)
        sinal_blob = nome_blob + " " + tipos_blob
        tem_nome_fitness = any(
            _norm_txt(k) in sinal_blob for k in _FITNESS_NOME_KW
        )
        if not tem_tipo_fitness and not tem_nome_fitness:
            return False
        # categoria especializada (ex.: "Academia de crossfit", "Artes marciais") → fora.
        # Também checa o NOME (o A3b-LLM às vezes dropa `tipos`; REK/Eikō trazem a
        # especialidade no nome). Off-list do nome SEM 'natacao' (academia c/ piscina fica).
        if any(_norm_txt(k) in tipos_blob for k in _TIPO_OFF_ACADEMIA):
            return False
        _OFF_NOME = ("crossfit", "cross training", "cross fit", "artes marciais", "jiu",
                     "muay", "boxe", "judo", "karate", "taekwondo", "mma", "pilates",
                     "ballet", "dojo", "luta livre", "escola de danca",
                     "studio", "estudio", "funcional", "personal training", "personalizado",
                     "checkmat", "gracie", "cordel", "doctorfit", "doctor fit",
                     "boxdelas", "fisiot", "clinica", "beach tennis")
        return not any(_norm_txt(k) in nome_blob for k in _OFF_NOME)
    on = _TIPO_ON_KW.get(tn)
    if not on:  # 'outro' ou tipo sem regra → sem filtro
        return True
    return any(_norm_txt(k) in (tipos_blob + " " + nome_blob) for k in on)


def _norm_txt(s: str) -> str:
    """lower + sem acento, p/ casar bairro dentro de endereço/nome."""
    from tools.bairro_normalize import fold_texto
    return fold_texto(s)


# Keywords PT do engine SearchAPI google_maps (type "Academia"/"Crossfit"/...) →
# injeta "gym" no types adaptado p/ passar no filtro _FITNESS_TYPES (enum EN).
_SEARCHAPI_FITNESS_KW = (
    "academia", "fitness", "ginas", "crossfit", "cross training", "pilates",
    "musculação", "musculacao", "box", "studio", "estúdio", "natação", "natacao",
    "treinamento", "personal", "yoga", "funcional",
)

def cross_check_concorrentes_bairro(
    cidade: str, uf: str, bairro: str, tipo_negocio: str,
    *, existentes: list[dict] | None = None,
) -> dict:
    """Cross-check da contagem de concorrentes: busca Google Maps pelos TERMOS DO FORM
    ('{tipo} {bairro} {cidade} {uf}') e aplica o GATE bairro+tipo. Reconcilia o que o
    Google mostra vs o que o pipeline capturou — a contagem gated vira a autoritativa de
    'concorrentes_no_bairro' (satura/score). Dedup por place_id (ChIJ idêntico ao Places).

    Retorna {status, query, google_n, gated_n, no_bairro[], novos[], ja_no_set_n}.
    no_bairro[] = academias gated (place_id, nome, endereco, rating, num_avaliacoes, deep).
    Best-effort: sem key/erro → status indisponivel.

    Mesmo mapa `_TIPO_NEGOCIO_KW` da âncora A3a — evita q duplicada
    (`academia` vs `academias`) e miss de search_raw.
    """
    query = _query_formato1(tipo_negocio, bairro, cidade, uf)
    region = ", ".join(p for p in (cidade, uf) if p)
    raw = _searchapi_maps_textsearch(
        query, max_results=40, region=region, places_type=_TIPO_PLACES_PADRAO,
    )
    if not raw:
        return {"status": "indisponivel", "query": query, "google_n": 0, "gated_n": 0,
                "no_bairro": [], "novos": [], "ja_no_set_n": 0}

    # Adapta pro shape do filtro (nome/endereco/tipos) preservando place_id + métricas.
    adap = [{
        "place_id": r.get("id") or "",
        "nome": (r.get("displayName") or {}).get("text") or "",
        "endereco": r.get("formattedAddress") or "",
        "tipos": r.get("types") or [],
        "rating": r.get("rating"),
        "num_avaliacoes": r.get("userRatingCount") or 0,
    } for r in raw]
    gated = filtrar_concorrentes_bairro_tipo(adap, bairro=bairro, tipo_negocio=tipo_negocio)

    # Dedup vs o set já capturado (place_id). Os que já estão = 'deep' (têm reviews);
    # os novos entram como 'mapeado, não analisado'.
    ids_exist = {
        (c.get("place_id") or c.get("id") or "")
        for c in (existentes or []) if isinstance(c, dict)
    }
    ids_exist.discard("")
    no_bairro, novos = [], []
    for g in gated:
        pid = g.get("place_id") or ""
        deep = bool(pid and pid in ids_exist)
        item = {"place_id": pid, "nome": g.get("nome"), "endereco": g.get("endereco"),
                "rating": g.get("rating"), "num_avaliacoes": g.get("num_avaliacoes"),
                "deep": deep}
        no_bairro.append(item)
        if not deep:
            novos.append(item)
    return {
        "status": "ok", "query": query, "google_n": len(raw), "gated_n": len(no_bairro),
        "no_bairro": no_bairro, "novos": novos, "ja_no_set_n": len(no_bairro) - len(novos),
        "fonte": "SearchAPI google_maps (termos do formulário) + gate raio+tipo",
        "nota": ("Contagem autoritativa = gated_n (R canônico do centróide + tipo). "
                 "google_n = bruto; gate remove off-tipo/fora do raio; ja_no_set = já analisados a fundo."),
    }


def _searchapi_maps_textsearch(
    query: str,
    *,
    max_results: int = 40,
    region: str = "",
    places_type: str = "",
    lat: float | None = None,
    lng: float | None = None,
) -> list[dict]:
    """SearchAPI engine=google_maps → adaptado p/ o MESMO shape do Places searchText
    (places[]). place_id é `ChIJ...` (idêntico ao Places API) → cache/dedup compatíveis.
    Custo ~4× menor. Best-effort: erro/sem key → [].

    Formato 1: `q` = query tipada; `region` ancora cidade/UF; filtro gym pós-fetch."""
    import os as _os

    sa_params: dict = {"q": query, "gl": "br", "hl": "pt-br"}
    if region:
        sa_params["region"] = region
    if places_type:
        sa_params["type"] = places_type
    if lat is not None and lng is not None:
        sa_params["ll"] = f"@{float(lat)},{float(lng)},14z"
    data: dict = {}
    try:
        from tools.search_raw_cache import get_search_raw, set_search_raw

        cached = get_search_raw("google_maps", sa_params)
        if cached:
            data = cached
    except Exception:
        pass

    if not data.get("local_results"):
        key = (_os.getenv("SEARCHAPI_KEY") or "").strip()
        if not key:
            return []
        try:
            from tools.api_cost_tracker import track_api_call

            with track_api_call("descobrir_concorrentes_bairro", "searchapi_google_maps", 1):
                with httpx.Client(timeout=25) as c:
                    data = c.get(
                        "https://www.searchapi.io/api/v1/search",
                        params={"engine": "google_maps", **sa_params},
                        headers={"Authorization": f"Bearer {key}"},
                    ).json()
            try:
                from tools.search_raw_cache import set_search_raw

                if isinstance(data, dict) and data.get("local_results"):
                    set_search_raw("google_maps", sa_params, data)
            except Exception:
                pass
        except Exception as exc:
            logger.debug("searchapi google_maps '%s': %s", query, exc)
            return []

    out: list[dict] = []
    for p in (data.get("local_results") or data.get("places") or [])[:max_results]:
        tipos_raw = p.get("types") or ([p["type"]] if p.get("type") else [])
        blob = _norm_txt(" ".join(tipos_raw) + " " + (p.get("title") or ""))
        eh_fitness = any(_norm_txt(kw) in blob for kw in _SEARCHAPI_FITNESS_KW)
        tipos = (["gym"] if eh_fitness else []) + list(tipos_raw)
        gps = p.get("gps_coordinates") or {}
        horas = p.get("hours")
        weekday = ([horas] if isinstance(horas, str) and horas else
                   list(p.get("open_hours") or {}).copy() if isinstance(p.get("open_hours"), dict)
                   else (p.get("open_hours") if isinstance(p.get("open_hours"), list) else []))
        pid = p.get("place_id") or ""
        out.append({
            "id": pid,
            "displayName": {"text": p.get("title") or ""},
            "formattedAddress": p.get("address") or "",
            "location": {"latitude": gps.get("latitude") or 0.0, "longitude": gps.get("longitude") or 0.0},
            "rating": p.get("rating"),
            "userRatingCount": p.get("reviews") or 0,
            "businessStatus": p.get("open_state") or "",
            "types": tipos,
            "regularOpeningHours": {"weekdayDescriptions": weekday},
            "websiteUri": p.get("website") or "",
            "nationalPhoneNumber": p.get("phone") or "",
            "googleMapsUri": f"https://www.google.com/maps/place/?q=place_id:{pid}" if pid else "",
        })
    return out


def _places_textsearch(
    query: str,
    *,
    max_results: int = 20,
    region: str = "",
    places_type: str = "",
) -> list[dict]:
    """Âncora de concorrentes. Dispatcher: SearchAPI google_maps (default, ~4× barato,
    place_id idêntico) com fallback automático p/ Places API se vazio/erro.
    Força via COMPETIDOR_MAPS_BACKEND=places."""
    import os as _os

    backend = (_os.getenv("COMPETIDOR_MAPS_BACKEND") or "searchapi").strip().lower()
    if backend != "places":
        res = _searchapi_maps_textsearch(
            query, max_results=max_results, region=region, places_type=places_type,
        )
        if res:
            for p in res:
                if isinstance(p, dict):
                    p["_fonte_textsearch"] = "searchapi_google_maps"
            return res
        motivo = "searchapi_vazio_ou_erro"
        logger.warning(
            "maps_textsearch fallback Places query=%r motivo=%s",
            (query or "")[:120],
            motivo,
        )
    out = _places_textsearch_google(query, max_results=max_results)
    for p in out:
        if isinstance(p, dict):
            p["_fonte_textsearch"] = "places_search_new"
    return out


def _places_textsearch_google(query: str, *, max_results: int = 20) -> list[dict]:
    """Places searchText cru → lista de places (estruturado, dado do Google Maps)."""
    api_key = get_google_maps_api_key()
    if not api_key:
        return []
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.rating,places.userRatingCount,places.businessStatus,places.types,"
            "places.regularOpeningHours,places.websiteUri,places.nationalPhoneNumber,"
            "places.googleMapsUri"
        ),
    }
    body = {"textQuery": query, "maxResultCount": max_results,
            "languageCode": "pt-BR", "regionCode": "BR"}
    try:
        # Contabiliza o custo (places:searchText = SKU places_search_new) — a âncora
        # bairro é a principal chamada Places nova por relatório; sem isto, o custo_brl
        # do relatório subestimaria o Places real.
        from tools.api_cost_tracker import track_api_call

        with track_api_call("descobrir_concorrentes_bairro", "places_search_new", 1):
            with httpx.Client(timeout=20) as c:
                data = c.post(f"{PLACES_BASE}:searchText", json=body, headers=headers).json()
    except Exception as exc:
        logger.debug("places textSearch '%s': %s", query, exc)
        return []
    return data.get("places") or []


def _cross_parque_contato(out: list[dict], cidade: str, uf: str, bairro: str) -> list[dict]:
    """Cruza o parque CNPJ: anexa cnpj/telefone aos concorrentes que casam por nome.

    Auditoria Maps mostrou que o parque tem recall baixo (5/14) e ruído (loja/escritório),
    então NÃO é a âncora — é só enrich de contato p/ o A5 (decisor) nos que o Maps achou.
    """
    try:
        from tools.concorrentes_parque_tools import listar_concorrentes_parque

        bloco = listar_concorrentes_parque(cidade, uf, bairro)
    except Exception:
        return out
    if not isinstance(bloco, dict) or bloco.get("status") != "ok":
        return out
    idx: dict[str, dict] = {}
    for c in bloco.get("concorrentes") or []:
        nome = _norm_txt(c.get("nome") or c.get("razao_social") or "")
        if nome:
            idx.setdefault(nome, c)
    for o in out:
        c = idx.get(_norm_txt(o.get("nome") or ""))
        if c:
            o["cnpj"] = c.get("cnpj")
            o["telefone"] = o.get("telefone") or c.get("telefone") or ""
            o["fonte_busca"] = "places_textsearch+cnpj"
    return out


def _place_eh_fitness(p: dict) -> bool:
    tipos = p.get("types") or []
    if set(tipos) & _FITNESS_TYPES:
        return True
    nome = (p.get("displayName") or {}).get("text") or p.get("title") or ""
    blob = _norm_txt(" ".join(str(t) for t in tipos) + " " + nome)
    return any(_norm_txt(k) in blob for k in _SEARCHAPI_FITNESS_KW)


def _places_para_concorrentes_bairro(
    places: list[dict],
    *,
    query: str,
    bairro: str,
    lat_centro: float,
    lng_centro: float,
    raio_metros: int = RAIO_CONCORRENCIA_CANONICO_M,
    ring: list[tuple[float, float]] | None = None,
) -> list[dict]:
    """Adapta Places → concorrentes. Gate geo = polígono IBGE (se ring) senão dist ≤ raio."""
    del bairro  # recall hint only — gate geo = ring ou raio
    from tools.bairro_poligono import point_in_ring

    out: list[dict] = []
    raio_m = max(300, min(5000, int(raio_metros or RAIO_CONCORRENCIA_CANONICO_M)))
    for p in places:
        if not _place_eh_fitness(p):
            continue
        end = p.get("formattedAddress", "")
        nome = (p.get("displayName") or {}).get("text") or ""
        loc = p.get("location") or {}
        plat, plng = loc.get("latitude", 0.0), loc.get("longitude", 0.0)
        dist_km = (
            round(calcular_distancia_km(lat_centro, lng_centro, plat, plng), 2)
            if plat else 0.0
        )
        if ring:
            if not plat or not point_in_ring(float(plng), float(plat), ring):
                continue
            gate = "poligono_ibge_bairro"
        else:
            if plat and (dist_km * 1000.0) > raio_m:
                continue
            gate = "raio_1000m"
        periodos = (p.get("regularOpeningHours") or {}).get("weekdayDescriptions", [])
        backend = p.get("_fonte_textsearch") or "places_textsearch"
        out.append({
            "place_id": p.get("id", ""),
            "nome": nome,
            "endereco": end,
            "lat": plat, "lng": plng,
            "distancia_km": dist_km,
            "rating": p.get("rating"),
            "num_avaliacoes": p.get("userRatingCount", 0),
            "nivel_preco": "",
            "status": p.get("businessStatus", ""),
            "tipos": p.get("types") or [],
            "telefone": p.get("nationalPhoneNumber", ""),
            "website": p.get("websiteUri", ""),
            "google_maps_uri": p.get("googleMapsUri", ""),
            "tem_24h": any("24" in h for h in periodos) if periodos else False,
            "horarios": periodos[:3],
            "fonte_busca": backend,
            "_query_formato1": query,
            "gate_espacial": gate,
        })
    return out


def _descobrir_concorrentes_bairro(
    tipo_negocio: str, bairro: str, cidade: str, uf: str,
    lat_centro: float, lng_centro: float,
    raio_metros: int = RAIO_CONCORRENCIA_CANONICO_M,
    id_municipio: str | None = None,
) -> list[dict]:
    """Formato 1: query tipada + gate polígono IBGE (se houver) ou dist ≤ raio + types fitness."""
    query = _query_formato1(tipo_negocio, bairro, cidade, uf)
    region = ", ".join(p for p in (cidade, uf) if p)
    places = _places_textsearch(
        query, max_results=40, region=region, places_type=_TIPO_PLACES_PADRAO,
    )
    ring = None
    try:
        from tools.bairro_poligono import resolver_bairro_poligono

        poly = resolver_bairro_poligono(
            id_municipio=id_municipio, bairro=bairro or "", cidade=cidade, uf=uf,
        )
        ring_cand = poly.get("ring") if poly else None
        if ring_cand:
            ring = ring_cand
    except Exception:
        ring = None
    out = _places_para_concorrentes_bairro(
        places,
        query=query,
        bairro=bairro,
        lat_centro=lat_centro,
        lng_centro=lng_centro,
        raio_metros=raio_metros,
        ring=ring,
    )
    cruzados = _cross_parque_contato(out, cidade, uf, bairro)
    return filtrar_concorrentes_bairro_tipo(
        cruzados, bairro=bairro or "", tipo_negocio=tipo_negocio or "academia",
    )


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
    raio_metros: int = RAIO_CONCORRENCIA_CANONICO_M,
    uf: str = "",
    tipo_negocio: str = "academia",
    id_municipio: str | None = None,
) -> dict:
    """
    Busca academias e fitness centers num raio do bairro/cidade.
    Recebe strings (bairro, cidade) — geocodifica internamente.

    Ordem: Geocode (Google → Nominatim) → Places Nearby → Overpass OSM.
    Sem chave Google ou com API bloqueada, usa OSM quando MAPS_FALLBACK_ENABLED=1.
    Com polígono IBGE resolvido: gate inclusão = point-in-polygon (Spec C).
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
    if not id_municipio:
        try:
            from tools.ibge_tools import buscar_municipio

            _mun = buscar_municipio(cidade, uf or "")
            id_municipio = (_mun or {}).get("codigo") or id_municipio
        except Exception:
            pass
    fonte_geocode = geo.get("fonte_geocode", "google")
    api_key = get_google_maps_api_key()

    # ── Tier 0 Geo (Places Aggregate) — só com chave Google ─────────
    # Nearby Search no Places API New tem maxResultCount limitado (ex: 20).
    # Para score competitivo, queremos a densidade REAL no raio.
    agregados: dict = {}
    places_ok = False
    data: dict = {}
    if api_key:
        # areaInsights (Places Aggregate) é CARO (~R$37/dia, 2 chamadas/run) e só
        # alimenta a densidade regional 3km = CONTEXTO. A saturação/veredito vêm da
        # CONTAGEM no BAIRRO (textSearch gated), não daqui. Desligado por default;
        # PLACES_AGGREGATE_ENABLED=1 religa. Off → densidade regional fica None
        # (contexto, já de-enfatizado no relatório). Custo > sinal.
        if os.getenv("PLACES_AGGREGATE_ENABLED", "0").strip().lower() in ("1", "true", "yes"):
            try:
                from tools.places_aggregate_tools import compute_insight_count_circle

                base = compute_insight_count_circle(
                    latitude=lat, longitude=lng, radius_meters=raio_metros,
                    included_types=["gym", "fitness_center"],
                )
                hi42 = compute_insight_count_circle(
                    latitude=lat, longitude=lng, radius_meters=raio_metros,
                    included_types=["gym", "fitness_center"],
                    min_rating=param("benchmark_rating_bem_avaliada"),
                )
                agregados = {
                    "status": "ok" if "erro" not in base else "erro",
                    "count_total": base.get("count") if isinstance(base, dict) else None,
                    "count_rating_ge_4_2": hi42.get("count") if isinstance(hi42, dict) else None,
                    "radius_meters": raio_metros,
                    "center": {"lat": lat, "lng": lng},
                    "included_types": ["gym", "fitness_center"],
                    "erros": [e for e in [base.get("erro"), hi42.get("erro")] if e],
                }
            except Exception:
                agregados = {"status": "erro", "motivo": "exception_import_or_call"}
        else:
            agregados = {"status": "desabilitado_custo", "count_total": None}

    def _do_nearby() -> None:
        nonlocal data, places_ok
        from tools.api_cost_tracker import track_api_call

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
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
            with track_api_call("buscar_academias_nearby", "places_search_new", 1):
                with httpx.Client(timeout=15) as c:
                    resp = c.post(f"{PLACES_BASE}:searchNearby", json=body, headers=headers)
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    places_ok = resp.status_code == 200 and bool(data.get("places"))
        except Exception as e:
            places_ok = False
            data = {"error": str(e)}

        # searchNearby (Places New 3km) agora é LAZY: no caminho default (âncora-bairro)
        # o resultado era DESCARTADO (retorna o textSearch/SearchAPI). Só roda quando é o
        # caminho radius OU o textSearch-bairro volta vazio (fallback). Corte de Places New
        # SEM mudar dado — resultado já era jogado fora no default. Antes: untracked → agora
        # rastreado (places_search_new) quando roda.
    if api_key:
        _conc_src_pre = os.getenv("CONCORRENTES_SOURCE", "").strip().lower()
        _ancora_bairro_pre = _conc_src_pre not in ("radius", "nearby", "raio", "municipio")

        # Eager SÓ no caminho radius (sem âncora-bairro). No default fica lazy (fallback).
        if not (_ancora_bairro_pre and bairro.strip()):
            _do_nearby()

    # ── Âncora bairro (DEFAULT) ──────────────────────────────────────────────
    # textSearch "{tipo} {bairro} {cidade} {uf}" (dado Google Maps, bairro-scoped) +
    # filtro types fitness + filtro bairro + cross parque CNPJ (contato). Resolve o
    # anchoring município/raio: a Nearby 3km puxava bairros adjacentes (AYO Guararapes,
    # Max Forma/BlueFit Aldeota num relatório de Cocó). Auditoria Maps: textSearch acha
    # 14 reais em Cocó vs parque-only 5 (recall) e sem o lixo (escritório/restaurante).
    # `agregados` (densidade 3km) fica como contexto regional.
    # É o DEFAULT quando há bairro; opt-out explícito (raio 3km) via
    # CONCORRENTES_SOURCE in {radius,nearby,raio,municipio}.
    _conc_src = os.getenv("CONCORRENTES_SOURCE", "").strip().lower()
    _usar_ancora_bairro = _conc_src not in ("radius", "nearby", "raio", "municipio")
    if _usar_ancora_bairro and bairro.strip():
        base_bairro = _descobrir_concorrentes_bairro(
            tipo_negocio, bairro, cidade, uf, lat, lng, raio_metros=raio_metros,
            id_municipio=id_municipio,
        )
        if base_bairro:
            base_bairro.sort(key=lambda x: -(x.get("num_avaliacoes") or 0))
            _cnt = agregados.get("count_total") if isinstance(agregados, dict) else None
            return {
                "bairro": bairro, "cidade": cidade, "raio_metros": raio_metros,
                "lat_centro": lat, "lng_centro": lng,
                "fonte_geocode": fonte_geocode,
                "total_encontrados": len(base_bairro),
                "total_encontrados_nearby": len(base_bairro),
                "total_encontrados_agregado": int(_cnt) if isinstance(_cnt, (int, float)) else None,
                "agregados_competicao_places": agregados if isinstance(agregados, dict) else {},
                "fonte_busca_competidores": "places_textsearch_bairro+cnpj",
                "redes_detectadas_osm": [],
                "concorrentes": base_bairro,
                "nota_fonte": (
                    "Âncora query bairro + inclusão dist≤{raio}m do centróide + gate tipo; "
                    "parque CNPJ cruza contato. Densidade regional = contexto."
                ).format(raio=raio_metros),
            }
        # textSearch vazio → AGORA roda o Places nearby (lazy) como fallback 3km.
        if api_key:
            _do_nearby()

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


def _processar_review_card(texto: str, rating: int, autor: str, data_rel: str) -> dict:
    """Normaliza 1 review (qualquer fonte) p/ o card: dores/serviços/sentimento."""
    texto = (texto or "").replace("\n", " ").strip()
    texto_low = texto.lower()
    return {
        "rating": rating,
        "quote_curta": texto[:180].strip(),
        "sentimento": "positivo" if rating >= 4 else "negativo" if rating <= 2 else "neutro",
        "dores_detectadas": [d for d in DORES_COMUNS if d in texto_low],
        "servicos_mencionados": [s for s in SERVICOS_ACADEMIA if s in texto_low],
        "autor": (autor or "Anônimo")[:60],
        "data_relativa": (data_rel or "")[:30],
    }


# Memo in-process por place_id — bundle {reviews, topics} compartilhado no run.
_REVIEWS_BUNDLE_MEMO: dict[str, dict | None] = {}


def _unwrap_reviews_cache_payload(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {"reviews": [], "topics": []}
    raw = payload.get("reviews")
    if isinstance(raw, dict) and "reviews" in raw:
        return {
            "reviews": raw.get("reviews") or [],
            "topics": raw.get("topics") or [],
        }
    if isinstance(raw, list):
        return {"reviews": raw, "topics": payload.get("topics") or []}
    return {"reviews": [], "topics": payload.get("topics") or []}


def _fetch_reviews_bundle(place_id: str) -> dict | None:
    """Reviews do concorrente — prefer google_maps_place (1 call c/ pico).

    Ordem: memo → cache_reviews → cache_places_details.review_results →
    google_maps_reviews (só se place sem reviews ou A3A_FORCE_REVIEWS_ENGINE=1).
    """
    import os as _os

    if not place_id:
        return None
    if place_id in _REVIEWS_BUNDLE_MEMO:
        return _REVIEWS_BUNDLE_MEMO[place_id]
    try:
        from tools.cache_store import get_reviews

        hit = get_reviews(place_id)
        if hit.hit and isinstance(hit.payload, dict):
            bundle = _unwrap_reviews_cache_payload(hit.payload)
            if bundle.get("reviews"):
                _REVIEWS_BUNDLE_MEMO[place_id] = bundle
                return bundle
    except Exception:
        pass

    force_reviews = (_os.getenv("A3A_FORCE_REVIEWS_ENGINE") or "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if not force_reviews:
        try:
            from tools.searchapi_maps_place import (
                get_or_fetch_maps_place,
                reviews_raw_from_maps_place,
                seed_reviews_cache_from_place,
            )

            place_raw = get_or_fetch_maps_place(place_id)
            place_revs = reviews_raw_from_maps_place(place_raw)
            if place_revs:
                seed_reviews_cache_from_place(place_id, place_raw)
                bundle = {"reviews": place_revs, "topics": []}
                _REVIEWS_BUNDLE_MEMO[place_id] = bundle
                return bundle
        except Exception:
            pass

    sa_params = {
        "place_id": place_id,
        "sort_by": "lowest_rating",
        "hl": "pt-br",
        "gl": "br",
    }
    try:
        from tools.search_raw_cache import get_search_raw

        cached = get_search_raw("google_maps_reviews", sa_params)
        if isinstance(cached, dict) and (cached.get("reviews") or cached.get("topics")):
            bundle = {
                "reviews": cached.get("reviews") or [],
                "topics": cached.get("topics") or [],
            }
            _REVIEWS_BUNDLE_MEMO[place_id] = bundle
            try:
                from tools.cache_store import set_reviews

                set_reviews(place_id, bundle["reviews"], topics=bundle["topics"])
            except Exception:
                pass
            return bundle
    except Exception:
        pass

    key = (_os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        _REVIEWS_BUNDLE_MEMO[place_id] = None
        return None
    try:
        from tools.api_cost_tracker import track_api_call

        with track_api_call("reviews_concorrente", "searchapi_google_maps_reviews", 1):
            with httpx.Client(timeout=45) as c:
                data = c.get(
                    "https://www.searchapi.io/api/v1/search",
                    params={"engine": "google_maps_reviews", **sa_params},
                    headers={"Authorization": f"Bearer {key}"},
                ).json()
        revs = data.get("reviews") or []
        topics = data.get("topics") or []
        bundle = {"reviews": revs, "topics": topics}
    except Exception:
        _REVIEWS_BUNDLE_MEMO[place_id] = None
        return None
    _REVIEWS_BUNDLE_MEMO[place_id] = bundle
    try:
        from tools.cache_store import set_reviews

        if revs or topics:
            set_reviews(place_id, revs, topics=topics)
    except Exception:
        pass
    try:
        from tools.search_raw_cache import set_search_raw

        if isinstance(data, dict):
            set_search_raw("google_maps_reviews", sa_params, data)
    except Exception:
        pass
    return bundle


def _fetch_reviews_raw(place_id: str) -> "list | None":
    """Compat: retorna só reviews[] do bundle compartilhado."""
    bundle = _fetch_reviews_bundle(place_id)
    if bundle is None:
        return None
    return bundle.get("reviews") or []


def _reviews_searchapi_card(place_id: str, max_reviews: int = 5) -> list[dict] | None:
    """Reviews via SearchAPI (raw compartilhado cacheado), shape do card. None se
    sem key/erro (→ caller cai pro Places)."""
    if not place_id:
        return None
    raw = _fetch_reviews_raw(place_id)
    if raw is None:
        return None

    import re as _re_html

    out: list[dict] = []
    for rev in (raw or [])[:max_reviews]:
        texto = (rev.get("text") or rev.get("snippet") or "")
        texto = _re_html.sub(r"<br\s*/?>", " ", texto, flags=_re_html.IGNORECASE)
        texto = _re_html.sub(r"<[^>]+>", "", texto)
        if not texto.strip():
            continue
        try:
            rating = int(float(rev.get("rating") or 3))
        except (TypeError, ValueError):
            rating = 3
        out.append(_processar_review_card(
            texto, rating, (rev.get("user") or {}).get("name") or "Anônimo", rev.get("date") or ""
        ))
    return out


def buscar_reviews_academia(place_id: str, nome_academia: str = "") -> dict:
    """Reviews do concorrente. Dispatcher: SearchAPI google_maps_reviews (default) com
    fallback Places Details. COMPETIDOR_MAPS_BACKEND=places força o Google."""
    import os as _os

    if (_os.getenv("COMPETIDOR_MAPS_BACKEND") or "searchapi").strip().lower() != "places":
        sa = _reviews_searchapi_card(place_id)
        if sa:
            return {"place_id": place_id, "nome": nome_academia, "reviews": sa,
                    "total_reviews_analisados": len(sa), "fonte_reviews": "searchapi"}

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
        review_recente = _review_recente_6m(r.get("data_relativa"))

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
            reviews_list = []
        for tema in c.get("temas_insatisfacao") or []:
            if not isinstance(tema, dict):
                continue
            cat = (tema.get("categoria_dor") or "").strip()
            if not cat or cat.lower() in ("outra", "outras"):
                continue
            try:
                mencoes = int(tema.get("mencoes") or 1)
            except (TypeError, ValueError):
                mencoes = 1
            categorias_dor[cat] = categorias_dor.get(cat, 0) + mencoes
            if cat not in categorias_por_academia:
                categorias_por_academia[cat] = {}
            categorias_por_academia[cat][nome] = categorias_por_academia[cat].get(nome, 0) + mencoes
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
            "oportunidade": mapa_solucao.get(dor) or TAXONOMIA_SOLUCAO.get(dor) or f"Resolver: {dor}",
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

    score_oportunidade = min(10.0, len(dores_rankeadas) * param("score_oport_peso_dores")
                             + len(gaps_servicos) * param("score_oport_peso_gaps"))

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
    if densidade < param("saturacao_densidade_baixo"):   return "BAIXO"
    elif densidade < param("saturacao_densidade_medio"): return "MEDIO"
    elif densidade < param("saturacao_densidade_alto"):  return "ALTO"
    else:                                                return "SATURADO"


def classificar_saturacao_bairro(num_no_bairro: int) -> str:
    """Saturação pela CONTAGEM de concorrentes NO BAIRRO (cross-check gate), não pela
    densidade no raio 3km (que dilui — 20 no raio virava BAIXO). Bandas recalibráveis.
    Ex.: 7 academias num bairro = ALTO."""
    n = int(num_no_bairro or 0)  # coage: anotação não garante int em runtime (JSON pode trazer "7")
    if n >= param_int("saturacao_bairro_saturado_min"):  return "SATURADO"
    if n >= param_int("saturacao_bairro_alto_min"):      return "ALTO"
    if n >= param_int("saturacao_bairro_medio_min"):     return "MEDIO"
    return "BAIXO"


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
    bonus = {
        "BAIXO": param("score_conc_bonus_baixo"),
        "MEDIO": param("score_conc_bonus_medio"),
        "ALTO": param("score_conc_bonus_alto"),
        "SATURADO": param("score_conc_bonus_saturado"),
    }
    penalidade_qtd = min(num_concorrentes * param("score_conc_penalidade_por_conc"),
                         param("score_conc_penalidade_teto"))
    penalidade_rating = (
        (rating_medio / 5.0) * param("score_conc_rating_mult")
        if rating_medio else param("score_conc_rating_default")
    )
    score = bonus.get(saturacao, 2.0) + (10 - penalidade_qtd * 2) / 10 - penalidade_rating
    return round(max(0.0, min(10.0, score)), 2)


# ── Filtro semântico de academia tradicional (VEC-387 iter 6) ───────
# Google Places `gym` + `fitness_center` retorna tudo: escolas de futebol,
# clínicas de fisioterapia, estúdios de modalidade única (yoga, Muay Thai,
# tênis), clubes esportivos. Inflam o count de "academias na região"
# falsamente. Filtro abaixo aplica regras negativas combinando types + nome
# para isolar academias tradicionais (musculação + cardio + aulas em grupo).

# Types de inclusão = "isto É academia". Inclui os tokens EN do Places API novo
# E os PT do SearchAPI (engine=google_maps). O bug VEC: o gate só tinha EN, mas o
# caminho barato (SearchAPI) devolve type em português ("Academia", "Sala de
# fitness") → a inclusão-por-tipo virava código morto e cortava academia real de
# nome neutro (CT Greenlife, TBOX, Parque Esportes). Ver _eh_academia_tradicional.
_TYPES_GYM = {
    # EN (Places API novo)
    "gym", "fitness_center",
    # PT (SearchAPI google_maps)
    "academia", "sala de fitness", "academia de ginástica", "academia de ginastica",
    "centro de treinamento", "centro de condicionamento físico",
    "centro de condicionamento fisico", "programa de condicionamento",
    "ciclismo indoor", "clube de saúde", "clube de saude", "health club",
}

_TYPES_EXCLUSAO_FORTE = {
    # Médico/saúde (EN — Places novo)
    "physiotherapist", "doctor", "hospital", "medical_center",
    "dentist", "veterinary_care", "physiotherapy",
    # Parques / áreas naturais (PT — SearchAPI). Distinguem "Parque Estadual do
    # Cocó" (parque) de "Parque Esportes" (type=Academia → entra). Só o type separa.
    "parque estadual", "parque ecológico", "parque ecologico", "parque municipal",
    "parque", "parque aquático", "parque aquatico", "reserva ecológica",
}

# Types de modalidade única (PT). Excluídos só se NÃO houver type-gym junto nem
# qualificador no nome — academia multiesporte com piscina é flag, não exclusão.
_TYPES_MODALIDADE = {
    "estúdio de pilates", "estudio de pilates",
    "estúdio de yoga", "estudio de yoga",
    "escola de natação", "escola de natacao",
    "escola de futebol", "escola de tênis", "escola de tenis",
    "escola de dança", "escola de danca", "quadra de tênis", "quadra de tenis",
}

_NOME_EXCLUSAO_KEYWORDS = (
    # Escolas de esporte / modalidades específicas (não-fitness tradicional)
    "saint-germain", "saint germain", "psg", "paris saint",
    "futebol", "futsal", "soccer", "futbol",
    "tenis", "tênis", "tennis", "padel", "paddle",
    "vôlei", "volei", "volleyball",
    "pole dance", "pole-dance",
    "escolinha de", "escola de futebol", "escola de tenis", "escola de vôlei",
    # Saúde / clínicas
    "fisio", "clínica", "clinica", "ortopedia", "ortoped",
    "consultório", "consultorio", "podologia", "psicolog",
    "estética", "estetica", "harmonização",
    # Lojas / suplemento (que entram com "academia" no nome mas são lojas)
    "loja de suplement", "suplementos &", "suplemento e",
)

# Modalidades únicas: excluir SE nome não tem qualificador "academia/fit/gym".
# Aquáticas/lutas aqui (não na exclusão forte) porque academia COM piscina/luta é
# multiesporte (Apêndice D: flag, não exclusão). Ex.: "Academia VS Club - Musculação,
# natação" fica (tem qualificador); "Centro de Natação X" sai (sem qualificador).
_MODALIDADES_UNICAS = (
    "muay thai", "muaythai", "muay-thai",
    "jiu jitsu", "jiu-jitsu", "jiujitsu",
    "karate", "karatê",
    "krav maga", "krav-maga",
    "ballet", "balé",
    "yoga", "ioga",
    "pilates",
    "natação", "natacao", "swimming",
    "hidroginás", "hidroginas",
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

    # Buckets canônicos (EN do Places novo + PT do SearchAPI no mesmo vocabulário).
    tem_gym_tipo = bool(types_set & _TYPES_GYM)
    tem_qualificador = any(q in nome for q in _QUALIFICADORES_ACADEMIA)

    # 1. Exclusão forte por type (médico EN + parque PT)
    if types_set & _TYPES_EXCLUSAO_FORTE:
        forte = types_set & _TYPES_EXCLUSAO_FORTE
        return False, f"type forte: {next(iter(forte))}"

    # 2. School sem gym exclusivo
    if "school" in types_set and not tem_gym_tipo:
        return False, "school exclusivo"

    # 3. Sports club sem gym
    if "sports_club" in types_set and not tem_gym_tipo:
        return False, "sports_club sem gym"

    # 4. Exclusão por palavras-chave fortes no nome
    for kw in _NOME_EXCLUSAO_KEYWORDS:
        if kw in nome:
            return False, f"nome contém '{kw}'"

    # 5. Modalidade única por TYPE (PT) — pilates/natação/yoga studio. Exclui só se
    #    não houver type-gym nem qualificador (academia multiesporte com piscina fica).
    if types_set & _TYPES_MODALIDADE and not tem_gym_tipo and not tem_qualificador:
        mod = next(iter(types_set & _TYPES_MODALIDADE))
        return False, f"type modalidade única: '{mod}'"

    # 6. Modalidade única por NOME — mesma regra, via nome
    for mod in _MODALIDADES_UNICAS:
        if mod in nome and not tem_qualificador:
            return False, f"modalidade única: '{mod}'"

    # 7. Inclusão final: type-gym (EN ou PT) OU qualificador no nome.
    if tem_gym_tipo:
        return True, ""

    # "health" sozinho (sem gym) costuma ser clínica → não inclui por type.
    if "health" in types_set and not tem_gym_tipo:
        return False, "health sem gym (provável clínica)"

    if tem_qualificador:
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
    return " ".join(s.lower().split())


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

    SearchAPI google_maps primeiro; Places searchText só se SearchAPI vazio
    ou sem match no raio (Haversine). Nada é trazido de fora do raio.
    """
    raio_km = raio_max_metros / 1000.0
    query = f"{rede} academia"

    def _pick_from_adapted(places: list[dict], *, fonte: str) -> dict | None:
        candidatos_no_raio = []
        for p in places:
            nome = (p.get("displayName") or {}).get("text", "") or ""
            if not _matches_rede(nome, rede):
                continue
            plat = (p.get("location") or {}).get("latitude", 0)
            plng = (p.get("location") or {}).get("longitude", 0)
            dist = calcular_distancia_km(lat_alvo, lng_alvo, plat, plng)
            if dist > raio_km:
                continue
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
                "fonte_busca": fonte,
            })
        if not candidatos_no_raio:
            return None
        candidatos_no_raio.sort(key=lambda x: x["distancia_km"])
        return candidatos_no_raio[0]

    sa = _searchapi_maps_textsearch(query, max_results=10)
    hit = _pick_from_adapted(sa, fonte="searchapi_google_maps")
    if hit:
        return hit

    if not get_google_maps_api_key():
        return None

    logger.warning(
        "rede_geofenced fallback Places rede=%r motivo=searchapi_vazio_ou_sem_match_raio",
        (rede or "")[:80],
    )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.rating,places.userRatingCount,"
            "places.businessStatus,places.types"
        ),
    }
    body = {
        "textQuery": query,
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

    adapted = []
    for p in data.get("places", []):
        adapted.append({
            "id": p.get("id", ""),
            "displayName": p.get("displayName") or {},
            "formattedAddress": p.get("formattedAddress", ""),
            "location": p.get("location") or {},
            "rating": p.get("rating"),
            "userRatingCount": p.get("userRatingCount", 0),
            "priceLevel": p.get("priceLevel", ""),
            "businessStatus": p.get("businessStatus", ""),
            "types": p.get("types", []),
            "nationalPhoneNumber": p.get("nationalPhoneNumber", ""),
            "websiteUri": p.get("websiteUri", ""),
            "regularOpeningHours": p.get("regularOpeningHours") or {},
        })
    return _pick_from_adapted(adapted, fonte="places_search_new")



def buscar_concorrentes_balanceados(
    tool_context,
    bairro: str,
    cidade: str,
    raio_metros: int = RAIO_CONCORRENCIA_CANONICO_M,
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
    # tipo_negocio/uf vêm do market_context (form) — necessários p/ a âncora bairro
    # (textSearch "{tipo} {bairro} {cidade} {uf}"). Default seguro se ausente.
    _tn, _uf = "academia", ""
    _st0 = getattr(tool_context, "state", None)
    if _st0 is not None:
        _mc0 = _parse_market_context(_st0.get("market_context"))
        if isinstance(_mc0, dict):
            _in0: dict = _mc0
            _inner_mc = _mc0.get("market_context")
            if isinstance(_inner_mc, dict):
                _in0 = _inner_mc
            _tn = (_in0.get("tipo_negocio") or "academia")
            _uf = (_in0.get("uf") or _st0.get("uf") or "")
    busca_nearby = buscar_academias(bairro, cidade, raio_metros, uf=_uf, tipo_negocio=_tn)
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
    # Modo âncora bairro (flag): NÃO faz busca expandida. A expandida (raio 5km)
    # re-puxa redes A0 de bairros adjacentes (ex.: Gaviões Aldeota num relatório de
    # Cocó), desfazendo o anchoring que a âncora bairro garantiu. Rede A0 sem unidade
    # no bairro vira `não_encontrada` (sinal honesto), não é fabricada de outra região.
    _modo_ancora_bairro = os.getenv("CONCORRENTES_SOURCE", "").strip().lower() == "parque"
    redes_nao_encontradas: list[str] = []
    for rede in redes_pendentes:
        match = None
        if not _modo_ancora_bairro and lat_alvo and lng_alvo:
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


_JANELA_DOR_MESES = 6  # dor pra posicionamento só vale recente (≤6m); >6m a academia pode ter consertado


def _review_recente_6m(data_relativa: str | None, meses: int = _JANELA_DOR_MESES) -> bool:
    """Retorna True se a review tem até ~`meses` (default 6) de idade.

    REGRA DE PRODUTO: dor pra insight de POSICIONAMENTO só vale se recente — dor de
    >6 meses é stale (a academia pode já ter consertado), não orienta o usuário.

    Google Maps/SearchAPI retorna `data_relativa` no idioma do review (PT/EN). Casos:
        "today" / "yesterday" / "X days/weeks/hours ago"             ← recente
        "a month ago" (=1) / "X months ago" se X<=meses              ← recente
        "X months ago"/"há X meses" se X>meses                       ← FORA
        "a/X year(s) ago" / "há X ano(s)"                            ← FORA

    Sem `data_relativa` = assume recente (defensivo — não descarta review legítimo
    por falta de label).
    """
    if not data_relativa:
        return True
    import re as _re

    s = data_relativa.strip().lower()
    if not s:
        return True
    if "year" in s or "ano" in s:   # >= 1 ano, fora
        return False
    # "X months ago" / "há X meses" / "X mês(es)" — fora se X > meses
    m = _re.search(r"(\d+)\s*(months?|m[êe]s(?:es)?)", s)
    if m:
        return int(m.group(1)) <= meses
    return True  # "a month ago", semanas, dias, horas → recente


def _reviews_baixa_nota_searchapi(place_id: str, max_reviews: int = 10) -> list[dict]:
    """As 10 reviews de MENOR NOTA via SearchAPI (engine google_maps_reviews).

    Promovido do scripts/backfill_reviews_dores.py (12/06) pro pipeline:
    relatório nasce com dores reais em vez das 5 reviews-elogio da Places.
    Sem SEARCHAPI_KEY ou falha → [] (best-effort, nunca bloqueia).
    Usa o fetch RAW compartilhado (memo + cache) — antes batia o place_id de novo,
    duplicando a chamada que _reviews_searchapi_card já fez."""
    raw = _fetch_reviews_raw(place_id) or []
    import re as _re_html

    out: list[dict] = []
    for rev in raw[:max_reviews]:
        texto = (rev.get("text") or rev.get("snippet") or "").strip()
        # SearchAPI devolve <br> e tags HTML cruas dentro do texto da review
        texto = _re_html.sub(r"<br\s*/?>", " ", texto, flags=_re_html.IGNORECASE)
        texto = _re_html.sub(r"<[^>]+>", "", texto)
        texto = _re_html.sub(r"\s+", " ", texto).strip()
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


def _planos_precos_searchapi(nome: str, bairro: str, cidade: str) -> list | None:
    """Planos × preços via SearchAPI (engine=google_light): puxa os organic_results
    (título/snippet/link) e EXTRAI o JSON de planos com Gemini. Determinístico na coleta
    (SearchAPI, não LLM-grounding que vinha None), barato. None se sem key/resultado."""
    import os as _os

    key = (_os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return None
    q = f'{nome} planos preço mensalidade {bairro or cidade} {cidade}'
    try:
        from tools.api_cost_tracker import track_api_call

        with track_api_call("planos_precos", "searchapi_google_light", 1):
            with httpx.Client(timeout=25) as c:
                data = c.get(
                    "https://www.searchapi.io/api/v1/search",
                    params={"engine": "google_light", "q": q, "gl": "br", "hl": "pt-br"},
                    headers={"Authorization": f"Bearer {key}"},
                ).json()
    except Exception as exc:
        logger.debug("searchapi google_light planos '%s': %s", nome, exc)
        return None

    orgs = data.get("organic_results") or []
    blob = "\n".join(
        f"{o.get('title','')} — {o.get('snippet','')} ({o.get('link','')})"
        for o in orgs[:8] if isinstance(o, dict)
    ).strip()
    # KB de respostas (some engines retornam 'answer_box'/'knowledge_graph')
    if isinstance(data.get("answer_box"), dict):
        blob = str(data["answer_box"].get("answer") or "") + "\n" + blob
    if not blob or "R$" not in blob and "plano" not in blob.lower():
        return None
    try:
        import json as _json

        from tools._genai_client import build_genai_client, generate_content_resilient

        prompt = (
            "Resultados de busca sobre planos/mensalidades de uma academia. Extraia em "
            "JSON array PURO (sem markdown), até 4 planos REAIS achados no texto:\n"
            '[{"plano":"<nome>","preco_mensal":"R$ X","inclui":["..."],'
            '"fidelidade":"<12 meses|sem fidelidade|null>"}]\n'
            "Use SÓ preços/planos explícitos no texto. NÃO invente. Sem preço confiável → [].\n\n"
            f"ACADEMIA: {nome} ({cidade})\nBUSCA:\n{blob[:6000]}"
        )
        client = build_genai_client()
        resp = generate_content_resilient(
            client, model="gemini-2.5-flash", contents=[prompt], max_retries=2, base_delay=3.0)
        txt = (resp.text or "").strip()
        ini = txt.find("[")
        if ini < 0:
            return None
        arr, _ = _json.JSONDecoder().raw_decode(txt[ini:])
        if isinstance(arr, list) and arr:
            return [p for p in arr[:4] if isinstance(p, dict) and p.get("preco_mensal")] or None
    except Exception as exc:
        logger.debug("planos searchapi extração '%s': %s", nome, exc)
    return None


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
        if (r.get("rating") or 5) <= 3 and _review_recente_6m(r.get("data_relativa"))
    ]
    baixa_antiga = [
        r for r in todas
        if (r.get("rating") or 5) <= 3 and not _review_recente_6m(r.get("data_relativa"))
    ]
    recentes_ok = [
        r for r in todas
        if (r.get("rating") or 5) > 3 and _review_recente_6m(r.get("data_relativa"))
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
        "temas_insatisfacao": (c.get("temas_insatisfacao") or [])[:10],
        "searchapi_topics": (c.get("searchapi_topics") or [])[:10],
        "horarios_pico": c.get("horarios_pico"),
        "planos_precos": c.get("planos_precos"),
        "instagram_profile": c.get("instagram_profile"),
        "servicos_ig": c.get("servicos_ig"),  # serviços detectados nas captions do IG → ERRC
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
      4. classificar_dores_reviews_deterministico — SearchAPI topics + card
      5. classificar_dores_reviews_batch_gemini — só se CLASSIFICAR_DORES_GEMINI=1

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

    # Cap de enriquecimento: reviews + pico + details + planos rodam SEQUENCIAL
    # por concorrente — long-pole do parallel block. Default 3 (SPEC_a3a_store_v2 /
    # Act-on); override via MAX_ENRIQUECIMENTO. Resto fica na lista só com Maps básico.
    _max_enriq = max(1, int(os.getenv("MAX_ENRIQUECIMENTO", "3")))
    if len(incluidos) > _max_enriq:
        incluidos.sort(key=_avaliacoes_int, reverse=True)
        incluidos = incluidos[:_max_enriq]

    # Pra cada incluído: reviews (sync) + enrichment (async)
    concorrentes_brutos: list[dict] = []

    async def _processar_um(c: dict) -> dict:
        import time as _time

        place_id = c.get("place_id", "")
        nome = c.get("nome", "?")
        _t0 = _time.perf_counter()
        _steps: dict[str, float] = {}

        def _mark(label: str, started: float) -> float:
            now = _time.perf_counter()
            _steps[label] = round((now - started) * 1000)
            return now

        # 1× google_maps_place (cache) — alimenta pico + reviews antes das etapas.
        _t = _t0
        _place_raw: dict | None = None
        if place_id:
            try:
                from tools.searchapi_maps_place import (
                    get_or_fetch_maps_place,
                    seed_reviews_cache_from_place,
                )

                _place_raw = get_or_fetch_maps_place(place_id)
                if _place_raw:
                    seed_reviews_cache_from_place(place_id, _place_raw)
            except Exception as e:
                logger.debug("[A3a maps_place] %s: %s", nome, e)
        _t = _mark("maps_place", _t)

        # Reviews via Places Details (síncrono — httpx blocking)
        reviews_data = buscar_reviews_academia(place_id, nome)
        reviews = reviews_data.get("reviews", []) if "erro" not in reviews_data else []
        _t = _mark("reviews", _t)

        # Knowledge Panel Playwright — OFF no hot-path prod (SPEC_market_bundle_v2).
        # Store histórico = SearchAPI reviews/maps; Playwright só se flag explícita.
        enrichment: dict = {}
        _pw = (os.getenv("COMPETITOR_PLAYWRIGHT_ENRICH") or "0").strip().lower()
        if _pw in ("1", "true", "yes", "on"):
            try:
                result = await enriquecer_concorrente_via_google(nome, cidade)
                enrichment = result if isinstance(result, dict) else {}
            except Exception as e:
                enrichment = {"scraping_status": f"exception: {type(e).__name__}"}
        else:
            enrichment = {"scraping_status": "playwright_skip_hot_path"}
        _t = _mark("playwright", _t)

        # Horários de pico via popular_times_tool (Tier 0 SearchAPI, Tier 1 lib,
        # Tier 2 Playwright). Best-effort — falha vira dados_por_dia vazio,
        # NÃO bloqueia pipeline. Cache: Supabase TTL 7d (+ FS local).
        horarios_pico_dict: dict | None = None
        pico_semanal_str: str | None = enrichment.get("pico_semanal")
        atributos_sobre: dict = {}
        # Places Details Atmosphere (SKU caro): skip se listing Maps já trouxe
        # telefone ou website (Act-on A3a). Force com A3A_FETCH_ATRIBUTOS=1.
        _fetch_attr = (os.getenv("A3A_FETCH_ATRIBUTOS") or "0").strip().lower() in (
            "1", "true", "yes", "on",
        )
        _tem_contato = bool((c.get("telefone") or "").strip() or (c.get("website") or "").strip())
        if place_id and (_fetch_attr or not _tem_contato):
            try:
                from tools.maps_tools import obter_atributos_place

                atributos_sobre = obter_atributos_place(place_id) or {}
            except Exception:
                atributos_sobre = {}
        elif place_id and _tem_contato:
            atributos_sobre = {}
        _t = _mark("atributos", _t)

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
                    place_raw=_place_raw,
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
        _t = _mark("pico", _t)

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
        _t = _mark("reviews_baixa", _t)

        # Planos × preços BALCÃO: site oficial → google_light+Gemini → grounding.
        # Site-first (Smart Fit JSON) evita light+LLM quando HTML já tem preço.
        planos_precos: list | None = None
        try:
            import asyncio as _asyncio

            from tools.planos_site_fetcher import fetch_planos_from_website

            _bai = c.get("bairro_concorrente") or bairro
            _site = (c.get("website") or "").strip()
            planos_precos = await _asyncio.to_thread(fetch_planos_from_website, _site)
            if not planos_precos:
                planos_precos = await _asyncio.to_thread(
                    _planos_precos_searchapi, nome, _bai, cidade
                )
            if not planos_precos:
                planos_precos = await _planos_precos_grounding(nome, _bai, cidade)
        except Exception as e:
            logger.warning(f"[A3a planos_precos] {nome}: {type(e).__name__}: {e}")
        _t = _mark("planos", _t)

        # Instagram público via SearchAPI (12/06): atividade de marketing REAL
        # (followers/posts/bio). Site e IG são COMPLEMENTARES — duas rotas de
        # descoberta auditáveis: (a) o "website" já é instagram.com/<user>;
        # (b) o site oficial linka o IG no HTML (rodapé/header). Nunca chuta
        # username por nome. Substitui o scraping Playwright do A3c.
        instagram_profile: dict | None = None
        servicos_ig: list | None = None
        ig_metricas: dict | None = None
        try:
            from tools.competidor_intel_cache import get_or_fetch_ig_intel
            from tools.instagram_profile import (
                descobrir_instagram_no_site,
                extrair_username_instagram,
            )
            from tools.parametros_metodologia import param_int

            site = c.get("website") or ""
            ig_user = extrair_username_instagram(site)
            if not ig_user and site:
                ig_user = await asyncio.to_thread(descobrir_instagram_no_site, site)
            if ig_user:
                # Cache persistente (Supabase, por place_id) — reusa entre bairros/relatórios
                # dentro do TTL; pré-processa posts + extrai serviços das captions (substrato
                # da ERRC) + métricas de marketing. Substitui o fetch raw sem cache.
                intel = await asyncio.to_thread(
                    get_or_fetch_ig_intel, place_id, ig_user,
                    cidade=cidade, bairro=(c.get("bairro_concorrente") or bairro),
                    ttl_dias=param_int("ig_cache_ttl_dias"),
                    planos_precos=planos_precos,
                )
                if isinstance(intel, dict):
                    instagram_profile = intel.get("profile")  # shape compat (followers/bio...)
                    ig_metricas = intel.get("metricas")
                    servicos_ig = intel.get("servicos")  # chaves p/ a ERRC (nutricao/recovery...)
        except Exception as e:
            logger.warning(f"[A3a instagram] {nome}: {type(e).__name__}: {e}")
        _t = _mark("ig", _t)

        maps_uri = (c.get("google_maps_uri") or "").strip() or None
        bundle = _fetch_reviews_bundle(place_id) if place_id else None
        topics_raw = (bundle or {}).get("topics") or []
        searchapi_topics = _normalize_searchapi_topics(topics_raw)
        temas_insatisfacao = _build_temas_insatisfacao(topics_raw, reviews)
        _mark("topics", _t)
        _total_ms = round((_time.perf_counter() - _t0) * 1000)
        logger.info(
            "[A3a enrich timing] %s total_ms=%s steps_ms=%s planos=%s ig=%s",
            nome,
            _total_ms,
            _steps,
            bool(planos_precos),
            bool(instagram_profile),
        )
        print(
            f"[A3a enrich timing] {nome} total_ms={_total_ms} steps_ms={_steps} "
            f"planos={bool(planos_precos)} ig={bool(instagram_profile)}",
            flush=True,
        )
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
            "searchapi_topics": searchapi_topics,
            "temas_insatisfacao": temas_insatisfacao,
            "fonte_reviews": reviews_data.get("fonte_reviews"),
            "horarios_pico": horarios_pico_dict,
            "pico_semanal": pico_semanal_str,
            "planos_precos": planos_precos,
            "instagram_profile": instagram_profile,
            "servicos_ig": servicos_ig,
            "ig_metricas": ig_metricas,
            "atributos_sobre": atributos_sobre if atributos_sobre and "erro" not in atributos_sobre else None,
            "atividade_marketing": enrichment.get("atividade_marketing"),
            "enrichment_search_grounding_text": enrichment.get("scraping_text"),
        }

    # Processa concorrentes em sequência (Playwright costuma travar com
    # múltiplas instâncias paralelas no Windows; sequencial é seguro)
    for c in incluidos:
        concorrentes_brutos.append(await _processar_um(c))

    classificar_dores_reviews_deterministico(concorrentes_brutos)
    classificacoes: dict = {}
    if _classificacao_dores_usa_gemini():
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
            "SearchAPI google_maps_reviews (sort lowest_rating) + topics[] + card "
            "determinístico (categoria_dor), enrichment Google (best-effort)"
            + (
                ", refino Gemini se CLASSIFICAR_DORES_GEMINI=1"
                if _classificacao_dores_usa_gemini()
                else ""
            )
            + "."
        ),
        "classificacao_dores_status": (
            "gemini_refinamento" if classificacoes else "deterministico_searchapi"
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

    # Filtro determinístico de BAIRRO: a busca balanceada usa raio 3-5km + redes do A0,
    # que vazam bairros vizinhos (Papicu/Meireles em Cocó). O relatório é POR BAIRRO →
    # mantém só quem é do bairro-alvo (match no bairro_concorrente OU no endereço).
    # Salvaguarda: se sobrar <2, mantém todos (lista esparsa > lista vazia) — rotulado.
    alvo_norm = _norm_txt(bairro or "")
    if alvo_norm:
        def _do_bairro(s: dict) -> bool:
            bc = _norm_txt(s.get("bairro_concorrente") or "")
            end = _norm_txt(s.get("endereco") or "")
            return (alvo_norm in bc) or (bc in alvo_norm and bc != "") or (alvo_norm in end)
        no_bairro = [s for s in slim if _do_bairro(s)]
        fora = [s for s in slim if not _do_bairro(s)]
        if len(no_bairro) >= 2:
            if fora:
                logger.info("A3a filtro bairro '%s': %d no bairro, %d vizinhos descartados (%s)",
                            bairro, len(no_bairro), len(fora),
                            ", ".join(s.get("nome", "?") for s in fora[:5]))
            slim = no_bairro

    # Filtro de RELEVÂNCIA por tipo_negocio do form: tira off-type (CrossFit/Artes
    # Marciais/Pilates num relatório de "academia"). Mesma salvaguarda <2.
    tipo_negocio = ""
    try:
        _st_raw = getattr(tool_context, "state", None)
        st: dict = _st_raw if isinstance(_st_raw, dict) else {}
        _ip = st.get("input_params")
        ip: dict = _ip if isinstance(_ip, dict) else {}
        tipo_negocio = (st.get("tipo_negocio") or ip.get("tipo_negocio") or "").strip()
        if not tipo_negocio:
            mc = _parse_market_context(st.get("market_context"))
            inner: dict = mc
            _inner_mc = mc.get("market_context")
            if isinstance(_inner_mc, dict):
                inner = _inner_mc
            tipo_negocio = (inner.get("tipo_negocio") or "") or ""
    except Exception:
        tipo_negocio = ""
    _tn_norm = (tipo_negocio or "").strip().lower()
    if _tn_norm == "academia" or _tn_norm in _TIPO_ON_KW:
        on_tipo = [s for s in slim if _tipo_relevante(s, tipo_negocio)]
        fora_t = [s for s in slim if not _tipo_relevante(s, tipo_negocio)]
        if len(on_tipo) >= 2:
            if fora_t:
                logger.info("A3a filtro tipo '%s': %d on-type, %d fora descartados (%s)",
                            tipo_negocio, len(on_tipo), len(fora_t),
                            ", ".join(s.get("nome", "?") for s in fora_t[:5]))
            slim = on_tipo

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


# ── Task #26: régua da praça pro ticket do catálogo ────────────────────────────

_AGREGADOR_KW = ("wellhub", "gympass", "gurupass", "totalpass", "agregador")


def _parse_preco_brl(v) -> float | None:
    """'R$ 319,99' / '319,99' / 319.99 → float. None se não parsear."""
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    import re as _re

    m = _re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:\.\d{2})?)", v)
    if not m:
        return None
    s = m.group(1)
    try:
        return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)
    except ValueError:
        return None


def confronto_ticket_praca(
    ticket_cenario: float, concorrentes: list[dict], banda: float = 0.4
) -> dict | None:
    """Mediana dos preços de BALCÃO da praça (planos_precos, excluindo tiers de
    agregador) confrontada com o ticket do cenário recomendado (catálogo, #26).
    Não recalcula nada — devolve o confronto pro A6 alertar quando a razão sai
    da banda (default ±40%). Preço de agregador fica fora: é tier corporativo,
    não mensalidade de balcão (decisão do quadro de planos, run b7199c7c)."""
    import statistics

    valores: list[float] = []
    for c in concorrentes or []:
        if not isinstance(c, dict):
            continue
        for p in c.get("planos_precos") or []:
            if not isinstance(p, dict):
                continue
            blob = f"{p.get('plano') or ''} {p.get('fonte') or ''}".lower()
            if any(k in blob for k in _AGREGADOR_KW):
                continue
            v = _parse_preco_brl(p.get("preco_mensal"))
            if v and 10 <= v <= 5000:
                valores.append(v)
    if not valores or not ticket_cenario:
        return None
    mediana = round(statistics.median(valores), 2)
    razao = round(float(ticket_cenario) / mediana, 3) if mediana else None
    return {
        "mediana_balcao": mediana,
        "n_precos": len(valores),
        "ticket_cenario": round(float(ticket_cenario), 2),
        "razao": razao,
        "fora_banda": razao is not None and not (1 - banda <= razao <= 1 + banda),
        "banda": banda,
    }
