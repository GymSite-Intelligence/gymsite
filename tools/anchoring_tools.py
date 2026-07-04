"""
Sinais de ancoragem urbana e checklist de diligência.

Computa score_ancoragem (0-10) baseado em proximidade de polos geradores de
fluxo (terminais de transporte + atacadistas) ao redor de cada candidato.
Estima visibilidade e detecta avenida principal via heurística determinística
no código (LLM só consome o resultado, sem reinventar regra).

Reusa funções de tools/maps_tools.py — não faz chamadas novas à API Google.
"""
from tools.maps_tools import buscar_imoveis_texto, calcular_distancia_km
from tools.parametros_metodologia import param, param_int


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
        if d < param("ancoragem_dist_forte_m"):
            score += param("ancoragem_pts_forte")
        elif d < param("ancoragem_dist_media_m"):
            score += param("ancoragem_pts_media")
        elif d < param("ancoragem_dist_fraca_m"):
            score += param("ancoragem_pts_fraca")

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


def _calcular_score_geoscout_basico(c: dict, bairro_alvo_chave: str) -> float:
    """Score 0-10 determinístico baseado nos sinais do Place."""
    tipos_set = {str(t).lower() for t in (c.get("tipos") or [])}
    from tools.bairro_normalize import normalizar_bairro

    endereco_chave = normalizar_bairro(c.get("endereco") or "")
    status = (c.get("status") or "").upper()
    rating = c.get("rating")
    num_av = c.get("num_avaliacoes") or 0

    score = 0.0
    if tipos_set & {"supermarket", "car_dealer", "warehouse", "hardware_store"}:
        score += 3
    if any(s in endereco_chave for s in ["av.", "avenida", "rod.", "rodovia"]):
        score += 2
    if status in ("CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"):
        score += 2
    if rating is not None and rating < param("geoscout_rating_baixo") and num_av >= param_int("geoscout_min_avaliacoes"):
        score += 1
    if tipos_set & {"store", "shopping_mall"}:
        score += 1
    if num_av > 200:
        score += 1
    # Bônus +1 se endereço contém o bairro alvo
    if bairro_alvo_chave and bairro_alvo_chave in endereco_chave:
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
    alvo = bairro or cidade
    for query in [
        f"supermercado {alvo}",
        f"concessionária {alvo}",
        f"imóvel comercial aluguel {alvo} {cidade}",
        f"galpão comercial {alvo} {cidade}",
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
    from tools.bairro_normalize import normalizar_bairro

    bairro_chave = normalizar_bairro(bairro or "")
    candidatos: list[dict] = []
    for c in todos:
        if _nome_blacklisted(c.get("nome", "")):
            continue
        c["area_estimada_m2"] = _estimar_area_por_tipo(c.get("tipos", []))
        if c["area_estimada_m2"] == 0:  # restaurant sem âncora
            continue
        c["score_geoscout"] = _calcular_score_geoscout_basico(c, bairro_chave)
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

    # 10. Listings reais (OLX + ImovelWeb via Playwright)
    # Adicionados como candidatos extras com qualidade_sinal="direto-listing"
    # — oferta concreta vale mais que sinal indireto de zona âncora.
    # Geocode em batch p/ ter lat/lng (custo ~$0.05 USD por relatório).
    listings_candidatos = _fetch_listings_como_candidatos(
        cidade=cidade,
        uf=uf,
        tool_context=tool_context,
        lat_fallback=lat,
        lng_fallback=lng,
    )
    candidatos_final = top_10 + listings_candidatos
    candidatos_final.sort(key=lambda x: x.get("score_geoscout", 0), reverse=True)

    # 11. Enriquecimento CNJ Cartório e Classificação ONR/Modalidade
    try:
        from tools.cnj_justica_aberta import resolver_cartorio_por_municipio
        from tools.investigacao_context import inferir_tipo_imovel_candidato

        for c in candidatos_final:
            # 1. Inferir tipo de imóvel se não estiver definido
            if "tipo_imovel_codigo_onr" not in c or c.get("tipo_imovel_codigo_onr") is None:
                inf = inferir_tipo_imovel_candidato(c)
                c["tipo_imovel_codigo_onr"] = inf.get("tipo_imovel_codigo_onr")
                c["tipo_imovel_label"] = inf.get("tipo_imovel_label")
            
            # 2. Modalidade
            if "modalidade" not in c or c.get("modalidade") is None:
                if c.get("qualidade_sinal") == "direto-listing":
                    c["modalidade"] = "locacao"
                else:
                    c["modalidade"] = "incerto"
            
            # 3. Cartório
            c_cidade = c.get("cidade") or cidade
            c_uf = c.get("uf") or uf
            c_bairro = c.get("bairro") or bairro
            
            cart = resolver_cartorio_por_municipio(c_cidade, c_uf, c_bairro)
            c["cartorio"] = cart
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Erro no enriquecimento CNJ/ONR: %s", e)


    from tools.deep_research_tool import (
        executar_investigacoes_candidatos,
        marcar_gatilhos_investigacao,
    )
    from tools.investigacao_context import build_contexto_investigacao

    state = getattr(tool_context, "state", None) if tool_context else None
    input_params = (state.get("input_params") if state else None) or {}
    if not input_params.get("cidade"):
        input_params = {
            **input_params,
            "cidade": cidade,
            "bairro": bairro or "",
            "uf": uf or "",
        }
    contexto_inv = build_contexto_investigacao(input_params)

    marcar_gatilhos_investigacao(candidatos_final)
    investigacoes_resumo = executar_investigacoes_candidatos(
        candidatos_final,
        cidade=cidade,
        bairro=bairro or "",
        uf=uf or "",
        contexto_relatorio=contexto_inv,
        input_params=input_params,
    )

    return {
        "total_candidatos": len(candidatos_final),
        "ancoras_heuristicas": len(top_10),
        "listings_reais": len(listings_candidatos),
        "estrategia": (
            "âncoras comerciais para field research + listings reais "
            "(OLX/ImovelWeb) quando disponíveis — verificar listing_url"
        ),
        "qualidade_sinal": "misto-heuristico+direto-listing",
        "checklist_diligencia": list(CHECKLIST_DILIGENCIA),
        "investigacoes_imoveis": investigacoes_resumo,
        "candidatos": candidatos_final,
        "lat_centro": lat,
        "lng_centro": lng,
        "polos_geradores_count": len(polos),
        "metodologia": (
            "Macro-tool determinística: geocode + nearby search + text search "
            "(supermercado, concessionária) + filtro blacklist + score "
            "GeoScout + score ancoragem (polos geradores) + visibilidade + "
            "avenida + street view + listings OLX/ImovelWeb (Playwright) + "
            "investigação web opcional (o que opera no endereço hoje). "
            "Tudo em 1 chamada — sem function_calls grandes que provocavam MALFORMED."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper: listings reais como candidatos
# ─────────────────────────────────────────────────────────────────────────────

def _anexar_aluguel_mrlr(cands: list[dict], cidade: str, bairro: str) -> list[dict]:
    """Anexa aluguel DETERMINÍSTICO (MRLR/IBAPE-GO) a cada candidato com área.

    Mesma equação e mesma chamada que o A4 (financial_tools usa
    aluguel_deterministico(area, cidade, bairro)) → o aluguel do candidato no A1
    é IDÊNTICO ao que o A4 estima pra mesma praça+área (sem divergência 17k→88k do
    anúncio raspado). `price_raw` continua como referência do anúncio, mas o número
    de decisão é o MRLR. Best-effort: falha de DB degrada limpo (deixa None).
    Memoiza por área (int) — mesmo bairro/cidade só muda pela área.
    """
    bn = (bairro or "").strip()
    if not bn or bn == "(cidade inteira)" or not cands:
        return cands
    try:
        from tools.aluguel_mrlr import aluguel_deterministico
    except Exception:
        return cands
    cache: dict[int, dict] = {}
    for c in cands:
        if c.get("aluguel_estimado"):
            continue
        try:
            area = float(c.get("area_estimada_m2") or 0)
        except (TypeError, ValueError):
            area = 0.0
        if area <= 0:
            continue
        chave = int(round(area))
        m = cache.get(chave)
        if m is None:
            try:
                m = aluguel_deterministico(area_m2=area, cidade=cidade, bairro=bn)
            except Exception:
                m = {"status": "erro"}
            cache[chave] = m
        if m.get("status") == "ok":
            c["aluguel_estimado"] = m.get("aluguel_total")
            c["aluguel_unitario_m2"] = m.get("valor_unitario_m2")
            c["aluguel_fonte"] = m.get("fonte")
    return cands


def _fetch_listings_como_candidatos(
    cidade: str,
    uf: str,
    tool_context,
    lat_fallback: float,
    lng_fallback: float,
) -> list[dict]:
    """Puxa listings OLX+ImovelWeb e converte pra schema de candidato do A1.

    Lê area_min/area_max do `tool_context.state.input_params` quando disponível;
    defaults razoáveis pra academia M (800-1500m²) com folga.

    Roda o scraper async em thread isolada com loop próprio — evita conflito
    com o event loop do ADK Runner que executa esta macro.

    Falha silenciosa: se scraper retornar [], A1 segue só com âncoras. Não
    bloqueia o pipeline.
    """
    import asyncio
    import concurrent.futures
    import logging
    import os
    log = logging.getLogger(__name__)

    state = getattr(tool_context, "state", None) if tool_context else None
    params = (state.get("input_params") if state else None) or {}
    area_min = int(params.get("area_m2_min", 500))
    area_max = int(params.get("area_m2_max", 5000))

    # ── Cascata P1 (bairro-scoped): busca imóvel NO BAIRRO-alvo (não city-wide) ──
    # O scrape OLX/ImovelWeb é city-level ('cidade-e-regiao') → vinha imóvel de
    # Maracanaú num relatório de Cocó. A cascata usa query otimizada por bairro
    # (anúncio individual) + Nominatim (lat/lng grátis). Candidato bairro-correto.
    casc_cands: list[dict] = []
    _bai = (params.get("bairro") or "").strip()
    if _bai and _bai != "(cidade inteira)":
        try:
            from tools.listing_cascata import buscar_candidatos_cascata

            for i, c in enumerate(buscar_candidatos_cascata(cidade, _bai, uf, area_min, area_max)[:10]):
                if not c.get("area_m2"):
                    continue
                casc_cands.append({
                    "place_id": f"cascata_olx_{i}",
                    "nome": f"Imóvel anunciado · {c.get('area_m2')}m² · OLX",
                    "endereco": c.get("endereco") or f"{_bai}, {cidade}, {uf}",
                    "lat": c.get("latitude") or lat_fallback,
                    "lng": c.get("longitude") or lng_fallback,
                    "tipos": ["imovel_anunciado", "comercial", "olx"],
                    "area_estimada_m2": c.get("area_m2"),
                    "score_geoscout": 8.5, "qualidade_sinal": "direto-listing-bairro",
                    "fonte": "cascata", "source": "olx_cascata",
                    "listing_url": c.get("url"), "price_raw": (f"R$ {c.get('preco'):.0f}" if c.get("preco") else None),
                    "modalidade": "locacao", "geocoded": c.get("latitude") is not None,
                    "score_ancoragem": 0.0, "polos_geradores": [],
                    "motivo": f"Imóvel anunciado em {_bai} (OLX, busca por bairro). Acessar listing_url.",
                })
        except Exception as e:
            log.warning("cascata P1 falhou — %s", e)

    # Playwright (OLX/ImovelWeb) FORA do caminho crítico por padrão. Era redundante
    # com a cascata SearchAPI acima (bairro-scoped, mais rápida e precisa) e o maior
    # gargalo do pipeline: timeouts de 45s + Cloudflare block → pipeline estourava 30min.
    # O listing NÃO alimenta a viabilidade (aluguel = MRLR determinístico); a cascata
    # SearchAPI já cobre o valor de exibição (imóvel de exemplo com preço). Opt-in via
    # LISTINGS_PLAYWRIGHT=1 se algum dia valer o custo.
    if os.getenv("LISTINGS_PLAYWRIGHT", "0").strip().lower() not in ("1", "true", "yes"):
        return _anexar_aluguel_mrlr(casc_cands, cidade, _bai)

    # Importa só agora pra evitar custo de import (playwright) quando A1 não
    # usa listings (ex: testes unitários focados em âncoras).
    try:
        from tools.listing_tools import fetch_commercial_listings_async
        from tools.maps_tools import geocode_endereco
    except Exception as e:
        log.warning("listings: imports falharam — %s", e)
        return _anexar_aluguel_mrlr(casc_cands, cidade, _bai)

    def _runner():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                fetch_commercial_listings_async(cidade, uf, area_min, area_max)
            )
        finally:
            loop.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            listings = ex.submit(_runner).result(timeout=180)
    except Exception as e:
        log.warning("listings: scraper falhou — %s", e)
        return _anexar_aluguel_mrlr(casc_cands, cidade, _bai)

    if not listings:
        return _anexar_aluguel_mrlr(casc_cands, cidade, _bai)

    # Limita aos top 15 por área pra controlar custo de geocode
    listings = listings[:15]

    candidatos: list[dict] = []
    for l in listings:
        # Geocode best-effort. Se falhar, usa centro da cidade (fallback útil
        # pra A4 mas ruim pra distância — log explícito pra auditoria).
        c_lat, c_lng = lat_fallback, lng_fallback
        geocoded = False
        if l.address:
            try:
                g = geocode_endereco(l.address)
                if isinstance(g, dict) and g.get("lat") and g.get("lng"):
                    c_lat = float(g["lat"])
                    c_lng = float(g["lng"])
                    geocoded = True
            except Exception:
                pass

        # Street view do imóvel — SÓ quando geocodificado de verdade (coords do
        # endereço). Com fallback de centro de cidade a foto seria do centro,
        # enganosa; nesse caso fica "" e a UI mostra "street view indisponível".
        sv_url = ""
        if geocoded:
            try:
                sv_url = obter_street_view_url(c_lat, c_lng)
            except Exception:
                sv_url = ""

        candidatos.append({
            "place_id": f"listing_{l.source}_{l.listing_id or len(candidatos)}",
            "nome": f"Imóvel anunciado · {l.area_m2}m² · {l.source.upper()}",
            "endereco": l.address or "Endereço não disponível",
            "lat": c_lat,
            "lng": c_lng,
            "tipos": ["imovel_anunciado", "comercial", l.source],
            "area_estimada_m2": l.area_m2,
            # Score base alto — oferta real é sinal direto, não heurístico
            "score_geoscout": 8.5,
            "qualidade_sinal": "direto-listing",
            "fonte": "listing",
            "source": l.source,
            "listing_url": l.listing_url,
            "listing_id": l.listing_id,
            "price_raw": l.price_raw,
            "tipo_imovel_codigo_onr": l.tipo_imovel_codigo_onr,
            "tipo_imovel_label": l.tipo_imovel_label,
            "modalidade": l.modalidade or "locacao",
            "geocoded": geocoded,
            "motivo": (
                f"Imóvel anunciado para aluguel em {l.source.upper()} — "
                f"{l.price_raw or 'preço a confirmar'}. Acessar listing_url "
                f"pra contato direto com a imobiliária."
            ),
            # Campos esperados pelo enriquecimento que NÃO rodam pra listings
            # (Place Details, polos geradores). A5 ContactHunter usa listing_url.
            "score_ancoragem": 0.0,
            "polos_geradores": [],
            "estimativa_visibilidade": "a_confirmar_no_field",
            "avenida_principal": False,
            "street_view_url": sv_url,
            "telefone": "",
            "website": l.listing_url,
        })

    # Cascata (bairro-correto) primeiro; scrape city-level depois. Dedup por listing_url.
    _urls = {c.get("listing_url") for c in casc_cands if c.get("listing_url")}
    candidatos = casc_cands + [c for c in candidatos if c.get("listing_url") not in _urls]
    return _anexar_aluguel_mrlr(candidatos, cidade, _bai)
