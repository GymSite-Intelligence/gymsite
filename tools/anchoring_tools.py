"""
Sinais de ancoragem urbana e checklist de diligência.

Computa score_ancoragem (0-10) baseado em proximidade de polos geradores de
fluxo (terminais de transporte + atacadistas) ao redor de cada candidato.
Estima visibilidade e detecta avenida principal via heurística determinística
no código (LLM só consome o resultado, sem reinventar regra).

Reusa funções de tools/maps_tools.py — não faz chamadas novas à API Google.
"""
from tools.maps_tools import buscar_imoveis_texto, calcular_distancia_km


CHECKLIST_DILIGENCIA = [
    "Confirmar zoneamento para atividade de condicionamento físico",
    "Verificar entrada trifásica de energia",
    "Checar projeto de incêndio aprovado",
    "Medir pé-direito (mínimo 4m)",
    "Confirmar vão livre sem colunas centrais",
    "Negociar 90-120 dias de carência",
]


# Categorias de polos — escopo MVP estrito (terminal + atacadista).
# Expansão (hipermercado, hospital, universidade) fica para v0.5 baseado em medição.
QUERIES_POLOS = {
    "terminal_transporte": [
        "terminal de ônibus",
        "estação metrô",
        "estação BRT",
        "terminal rodoviário",
    ],
    "atacadista": [
        "Atacadão",
        "Sam's Club",
        "Assaí Atacadista",
        "Atacarejo",
        "Maxxi Atacado",
    ],
}


def buscar_polos_geradores(latitude: float, longitude: float,
                            raio_metros: int = 2000) -> list[dict]:
    """
    Busca polos geradores de fluxo (terminais + atacadistas) num raio do bairro.

    Faz Text Search por queries específicas e deduplica por place_id.
    Use UMA VEZ por bairro, não por candidato — os polos são compartilhados.

    Args:
        latitude: lat do centróide do bairro
        longitude: lng do centróide do bairro
        raio_metros: raio de busca (padrão 2km)

    Returns:
        Lista de dicts com {place_id, nome, lat, lng, tipo_polo}.
    """
    seen = set()
    polos = []
    for tipo, queries in QUERIES_POLOS.items():
        for q in queries:
            try:
                resultados = buscar_imoveis_texto(q, latitude, longitude, raio_metros)
            except Exception:
                continue
            for r in resultados or []:
                pid = r.get("place_id", "")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                polos.append({
                    "place_id": pid,
                    "nome": r.get("nome", ""),
                    "lat": r.get("lat", 0),
                    "lng": r.get("lng", 0),
                    "tipo_polo": tipo,
                })
    return polos


def calcular_score_ancoragem(candidato_lat: float, candidato_lng: float,
                              polos: list[dict]) -> dict:
    """
    Score 0-10 baseado em proximidade de polos geradores ao candidato.

    Pesos por distância:
        < 500m  → 3 pts
        < 1km   → 2 pts
        < 2km   → 1 pt
    Soma capada em 10.

    Args:
        candidato_lat: lat do candidato (imóvel-âncora)
        candidato_lng: lng do candidato
        polos: lista retornada por buscar_polos_geradores

    Returns:
        {
            "score_ancoragem": 8.5,
            "polos_geradores": ["Terminal Papicu 320m", "Atacadão Messejana 1.2km"],
            "polos_detalhados": [{nome, distancia_m, tipo_polo, ...}, ...]
        }
    """
    com_distancia = []
    for p in polos or []:
        try:
            d_km = calcular_distancia_km(
                candidato_lat, candidato_lng, p["lat"], p["lng"]
            )
            com_distancia.append({**p, "distancia_m": int(d_km * 1000)})
        except Exception:
            continue

    com_distancia.sort(key=lambda x: x["distancia_m"])

    score = 0.0
    for p in com_distancia:
        d = p["distancia_m"]
        if d < 500:
            score += 3
        elif d < 1000:
            score += 2
        elif d < 2000:
            score += 1

    score = min(score, 10.0)

    polos_formatados = [
        f"{p['nome']} {_fmt_dist(p['distancia_m'])}"
        for p in com_distancia[:3]
    ]

    return {
        "score_ancoragem": round(score, 1),
        "polos_geradores": polos_formatados,
        "polos_detalhados": com_distancia[:3],
    }


def _fmt_dist(metros: int) -> str:
    if metros < 1000:
        return f"{metros}m"
    return f"{metros / 1000:.1f}km"


def estimar_visibilidade(tipos: list[str], endereco: str) -> str:
    """
    Heurística determinística:
        - tipo interno (food_court, dept_store) → "baixa"
        - avenida + tipo com fachada → "alta"
        - avenida OU tipo com fachada → "média"
        - resto → "baixa"

    Args:
        tipos: lista de Place types do Google
        endereco: endereço formatado

    Returns:
        "alta" | "média" | "baixa"
    """
    end_low = (endereco or "").lower()
    em_avenida = any(s in end_low for s in ["av.", "avenida", "rod.", "rodovia"])

    tipos_set = set(tipos or [])
    tipo_interno = bool(tipos_set & {"food_court", "department_store"})
    tipo_fachada = bool(tipos_set & {
        "supermarket", "car_dealer", "store", "hardware_store", "warehouse",
    })

    if tipo_interno:
        return "baixa"
    if em_avenida and tipo_fachada:
        return "alta"
    if em_avenida or tipo_fachada:
        return "média"
    return "baixa"


def detectar_avenida_principal(endereco: str) -> dict:
    """
    True se endereço contém marcador de avenida/rodovia ('Av.', 'Avenida',
    'Rod.', 'Rodovia'). Bool wrappado em dict pra ser uma tool ADK válida
    (precisa retornar JSON-serializável).
    """
    end_low = (endereco or "").lower()
    em_avenida = any(s in end_low for s in ["av.", "avenida", "rod.", "rodovia"])
    return {"avenida_principal": em_avenida}


def obter_checklist_diligencia() -> dict:
    """Retorna o checklist fixo de diligência (6 itens) pra A6 renderizar."""
    return {"checklist_diligencia": list(CHECKLIST_DILIGENCIA)}


# ── Macro-tool consolidadora para A1 GeoScout (VEC-379 fase 1B) ───────
# Elimina function_calls grandes que provocavam MALFORMED em 5/9 runs
# (Runs 9, 13, 16). Anteriormente o LLM tentava passar lista de 30+ polos
# como argumento de calcular_score_ancoragem — payload corrompia o JSON
# do function_call. Agora tudo roda dentro da macro, sem args grandes.

_NOMES_BLACKLIST = (
    # Restaurantes/comida
    "muqueca", "muquecaria", "restaurante", "churrascaria", "pizzaria",
    "burguer", "burger", "lanchonete", "petiscaria", "sushi",
    "açai", "acai", "sorveteria", "padaria", "bistrô", "bistro",
    "pastelaria",
    # Anúncios/genéricos
    "4 sale", "for sale", "to rent", "vende-se", "aluga-se",
    # Pequeno porte
    "boutique", "atelier", "pet shop", "salão", "salao",
    "barbearia", "estética",
)

_AREA_POR_TIPO = {
    "shopping_mall": 8000,
    "supermarket": 1200,
    "car_dealer": 1000,
    "warehouse": 1500,
    "hardware_store": 1000,
    "furniture_store": 1000,
    "store": 800,
    "department_store": 1500,
}


def _nome_blacklisted(nome: str) -> bool:
    nome_low = (nome or "").lower()
    return any(kw in nome_low for kw in _NOMES_BLACKLIST)


def _estimar_area_por_tipo(tipos: list[str]) -> int:
    """Retorna estimativa de área. 0 se incompatível (restaurant sem âncora)."""
    tipos_set = {str(t).lower() for t in (tipos or [])}
    # Incompatível: restaurant/cafe sem outro tipo âncora
    se_pequeno = bool(tipos_set & {"restaurant", "cafe", "bakery", "bar"})
    se_ancora = bool(tipos_set & set(_AREA_POR_TIPO.keys()))
    if se_pequeno and not se_ancora:
        return 0
    # Pega o maior dos tipos âncora disponíveis
    areas = [_AREA_POR_TIPO[t] for t in tipos_set if t in _AREA_POR_TIPO]
    return max(areas) if areas else 600  # fallback


def _calcular_score_geoscout_basico(c: dict, bairro_alvo_low: str) -> float:
    """Score 0-10 determinístico baseado nos sinais do Place."""
    tipos_set = {str(t).lower() for t in (c.get("tipos") or [])}
    endereco_low = (c.get("endereco") or "").lower()
    status = (c.get("status") or "").upper()
    rating = c.get("rating")
    num_av = c.get("num_avaliacoes") or 0

    score = 0.0
    if tipos_set & {"supermarket", "car_dealer", "warehouse", "hardware_store"}:
        score += 3
    if any(s in endereco_low for s in ["av.", "avenida", "rod.", "rodovia"]):
        score += 2
    if status in ("CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"):
        score += 2
    if rating is not None and rating < 3.5 and num_av >= 30:
        score += 1
    if tipos_set & {"store", "shopping_mall"}:
        score += 1
    if num_av > 200:
        score += 1
    # Bônus +1 se endereço contém o bairro alvo
    if bairro_alvo_low and bairro_alvo_low in endereco_low:
        score += 1

    return round(min(score, 10.0), 1)


def _gerar_motivo(c: dict) -> str:
    """Frase curta justificando por que o candidato é interessante."""
    tipos = c.get("tipos") or []
    em_avenida = any(
        s in (c.get("endereco") or "").lower()
        for s in ["av.", "avenida"]
    )
    if "supermarket" in tipos:
        return f"Supermercado{' em avenida principal' if em_avenida else ''} — investigar disponibilidade ou imóveis vizinhos"
    if "car_dealer" in tipos:
        return "Concessionária — alto pé-direito + área compatível, investigar realocação ou vizinhos"
    if "shopping_mall" in tipos:
        return "Shopping — buscar lojas-âncora internas ou imóveis no entorno"
    if "warehouse" in tipos:
        return "Galpão — área compatível, investigar disponibilidade"
    if "store" in tipos:
        return f"Loja{' em avenida' if em_avenida else ''} — investigar"
    return "Estabelecimento comercial — fazer field research"


def analisar_pontos_comerciais_completo(
    tool_context,
    bairro: str,
    cidade: str,
    uf: str = "",
) -> dict:
    """
    Macro-tool consolidadora do A1 GeoScout — executa o pipeline inteiro
    (geocode → busca → score → ancoragem → visibilidade) em UMA chamada.

    Por que existe (VEC-379 fase 1B): function_calls com `polos` como
    argumento corrompiam JSON em 5/9 runs (MALFORMED_FUNCTION_CALL).
    Agora tudo roda dentro de uma função Python — o LLM faz 1 chamada
    sem args grandes.

    Args:
        bairro: bairro alvo (ex: "Meireles"). Se vazio, busca cidade inteira.
        cidade: cidade (ex: "Fortaleza")
        uf: UF (ex: "CE"). Opcional.

    Returns:
        Dict com candidatos top-10 enriquecidos + checklist + estatísticas.
    """
    # Imports locais para evitar circular dependency
    from tools.maps_tools import (
        geocode_endereco,
        buscar_pontos_comerciais,
        buscar_imoveis_texto,
        obter_street_view_url,
        obter_detalhes_contato,
    )

    # 1. Geocode
    if bairro:
        endereco = f"{bairro}, {cidade}, {uf}, Brasil" if uf else f"{bairro}, {cidade}, Brasil"
        raio = 2500
    else:
        endereco = f"{cidade}, {uf}, Brasil" if uf else f"{cidade}, Brasil"
        raio = 5000

    try:
        geo = geocode_endereco(endereco)
    except Exception as e:
        return {"erro": f"geocode falhou: {e}", "candidatos": []}

    if not isinstance(geo, dict) or "error" in geo:
        return {"erro": geo.get("error") if isinstance(geo, dict) else "geocode invalido",
                "candidatos": []}

    lat, lng = geo.get("lat"), geo.get("lng")
    if lat is None or lng is None:
        return {"erro": "lat/lng ausentes", "candidatos": []}

    # 2. Nearby + 3. Text searches âncoras
    candidatos_brutos = []
    try:
        candidatos_brutos.extend(buscar_pontos_comerciais(lat, lng, raio) or [])
    except Exception:
        pass
    for query in [
        f"supermercado {bairro or cidade}",
        f"concessionária {bairro or cidade}",
    ]:
        try:
            candidatos_brutos.extend(buscar_imoveis_texto(query, lat, lng, raio) or [])
        except Exception:
            continue

    # 4. Dedup por place_id
    by_id: dict[str, dict] = {}
    for c in candidatos_brutos:
        if not isinstance(c, dict):
            continue
        pid = c.get("place_id")
        if pid and pid not in by_id:
            by_id[pid] = c
    todos = list(by_id.values())

    # 5. Filtro blacklist + área incompatível
    bairro_low = (bairro or "").lower().strip()
    candidatos: list[dict] = []
    for c in todos:
        if _nome_blacklisted(c.get("nome", "")):
            continue
        c["area_estimada_m2"] = _estimar_area_por_tipo(c.get("tipos", []))
        if c["area_estimada_m2"] == 0:  # restaurant sem âncora
            continue
        c["score_geoscout"] = _calcular_score_geoscout_basico(c, bairro_low)
        candidatos.append(c)

    # 6. Top 10 por score
    candidatos.sort(key=lambda x: x.get("score_geoscout", 0), reverse=True)
    top_10 = candidatos[:10]

    # 7. Polos geradores (1 chamada por rodada)
    try:
        polos = buscar_polos_geradores(lat, lng, 2000)
    except Exception:
        polos = []

    # 8. Enriquecimento por candidato (em loop interno — sem function_call grande)
    for c in top_10:
        c_lat = c.get("lat", lat)
        c_lng = c.get("lng", lng)
        try:
            ancoragem = calcular_score_ancoragem(c_lat, c_lng, polos)
            c["score_ancoragem"] = ancoragem["score_ancoragem"]
            c["polos_geradores"] = ancoragem["polos_geradores"]
        except Exception:
            c["score_ancoragem"] = 0.0
            c["polos_geradores"] = []
        c["estimativa_visibilidade"] = estimar_visibilidade(
            c.get("tipos", []), c.get("endereco", "")
        )
        c["avenida_principal"] = detectar_avenida_principal(
            c.get("endereco", "")
        )["avenida_principal"]
        try:
            c["street_view_url"] = obter_street_view_url(c_lat, c_lng)
        except Exception:
            c["street_view_url"] = ""
        c["qualidade_sinal"] = "indireto-heuristico"
        c["motivo"] = _gerar_motivo(c)

    # 9. Enrichment Place Details (Contact Data) — APENAS para Top 3.
    # Custo extra: ~$0.01 por análise (3 requests Place Details SKU Contact).
    # Por que só Top 3: A5 ContactHunter usa apenas o #1, mas Top 3 dá
    # margem se o user trocar candidato no frontend. Limitar a 3 mantém
    # o orçamento baixo enquanto cobre o caso de uso prático.
    #
    # NOTA: searchNearby da Places API New não retorna Contact Data
    # confiavelmente mesmo com FieldMask correto — Place Details
    # individual é o método correto.
    for c in top_10[:3]:
        pid = c.get("place_id")
        if not pid:
            continue
        try:
            detalhes = obter_detalhes_contato(pid)
            if isinstance(detalhes, dict) and "erro" not in detalhes:
                # Mescla preservando dados que já vieram do searchNearby
                # (caso a API retorne ambos)
                c["telefone"] = detalhes.get("telefone") or c.get("telefone", "")
                c["telefone_intl"] = detalhes.get("telefone_intl", "")
                c["website"] = detalhes.get("website") or c.get("website", "")
                c["tem_24h"] = detalhes.get("tem_24h", c.get("tem_24h", False))
                c["horarios"] = detalhes.get("horarios") or c.get("horarios", [])
                c["aberto_agora"] = detalhes.get("aberto_agora")
                c["business_status"] = detalhes.get("business_status") or c.get("status", "")
        except Exception:
            pass  # best-effort — não bloqueia pipeline

    return {
        "total_candidatos": len(top_10),
        "estrategia": "âncoras comerciais para field research — não imóveis garantidamente vagos",
        "qualidade_sinal": "indireto-heuristico",
        "checklist_diligencia": list(CHECKLIST_DILIGENCIA),
        "candidatos": top_10,
        "lat_centro": lat,
        "lng_centro": lng,
        "polos_geradores_count": len(polos),
        "metodologia": (
            "Macro-tool determinística: geocode + nearby search + text search "
            "(supermercado, concessionária) + filtro blacklist + score "
            "GeoScout + score ancoragem (polos geradores) + visibilidade + "
            "avenida + street view. Tudo em 1 chamada — sem function_calls "
            "grandes que provocavam MALFORMED."
        ),
    }
