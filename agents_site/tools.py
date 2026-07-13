"""
Ferramentas dos agentes do site (degustação na landing) — versão ADK.

Cada função é envolvida como FunctionTool pelo ADK (passada em `tools=[...]`).
Reusa o código JÁ validado de RAG (Vertex AI Search / Discovery Engine) e de
concorrência (Google Maps), garantindo grounding: o agente SÓ cita código de
modelo / spec / contagem que veio DESTAS funções, nunca de memória.

Auth: ADC (mesmo caminho que já roda em prod no Cloud Run).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("gymsite.agents_site.tools")


def _nivel_saturacao(n: int) -> str:
    if n <= 5:
        return "baixo"
    if n <= 12:
        return "medio"
    return "alto"


def dimensionar_cardio_por_pico(
    pico_simultaneo: int,
    pct_cardio_min: float = 0.20,
    pct_cardio_max: float = 0.25,
    fator_fila_min: float = 0.6,
    fator_fila_max: float = 0.7,
    mix_esteira: float = 0.45,
    mix_eliptico: float = 0.20,
    mix_bike: float = 0.20,
    mix_escada: float = 0.15,
) -> dict:
    """Calcula de forma DETERMINÍSTICA a faixa de aparelhos de cardio a partir do pico
    simultâneo, no modelo TOLERA-FILA (fator_fila < 1: nem todos usam no mesmo instante).
    Use SEMPRE para QUANTIDADE de cardio — nunca calcule de cabeça.

    Fórmula: cardio_total = pico × %cardio × fator_fila; depois divide no MIX
    (esteira/elíptico/bike/escada). Mix padrão 45/20/20/15. Premissas ajustáveis.

    Args:
        pico_simultaneo: alunos ao mesmo tempo no pico (ex.: 300).
        pct_cardio_min/max: fração do pico em cardio (padrão 0.20–0.25).
        fator_fila_min/max: tolerância de fila/rotação (padrão 0.6–0.7; <1 = tolera fila).
        mix_esteira/eliptico/bike/escada: divisão do parque de cardio (somam 1.0).

    Returns:
        dict com faixas (mín/máx/médio) de cardio_total e de cada tipo, + premissas.
    """
    p = max(0, int(pico_simultaneo))
    car_min = p * pct_cardio_min * fator_fila_min
    car_max = p * pct_cardio_max * fator_fila_max

    def _faixa(frac: float) -> dict:
        lo, hi = car_min * frac, car_max * frac
        return {"min": round(lo), "max": round(hi), "medio": round((lo + hi) / 2)}

    return {
        "cardio_total": {"min": round(car_min), "max": round(car_max)},
        "esteiras": _faixa(mix_esteira),
        "elipticos": _faixa(mix_eliptico),
        "bikes": _faixa(mix_bike),
        "escadas": _faixa(mix_escada),
        "premissas": {
            "modelo": "tolera-fila",
            "pct_cardio": [pct_cardio_min, pct_cardio_max],
            "fator_fila": [fator_fila_min, fator_fila_max],
            "mix": {"esteira": mix_esteira, "eliptico": mix_eliptico, "bike": mix_bike, "escada": mix_escada},
        },
        "nota": "Premissas de PLANEJAMENTO (não catálogo). Modelo tolera-fila (fator_fila<1). Ajuste ao público.",
    }


def dimensionar_musculacao(
    pico_simultaneo: int,
    pct_musculacao: float = 0.65,
    fator_concorrencia: float = 1.4,
    alerta_acima_de: float = 1.7,
) -> dict:
    """Estações de musculação por pico (revezamento saudável). Use SEMPRE para "quantas
    estações/máquinas de musculação" — não estime de cabeça.

    Fórmula: estações = (pico × %musculação) / fator_concorrência.
    fator_concorrência = alunos por máquina (1.4 ideal; acima de 1.7 = superlotação).

    Args:
        pico_simultaneo: alunos ao mesmo tempo no pico (ex.: 300).
        pct_musculacao: fração do pico na musculação (padrão 0.65).
        fator_concorrencia: alunos/máquina alvo (padrão 1.4).
        alerta_acima_de: limiar de superlotação (padrão 1.7).
    """
    p = max(0, int(pico_simultaneo))
    n_forca = p * pct_musculacao
    fc = fator_concorrencia if fator_concorrencia > 0 else 1.4
    return {
        "estacoes": round(n_forca / fc),
        "alunos_musculacao_pico": round(n_forca),
        "premissas": {"pct_musculacao": pct_musculacao, "fator_concorrencia": fc, "limite_alerta": alerta_acima_de},
        "alerta_superlotacao": fc > alerta_acima_de,
        "nota": "Premissa de PLANEJAMENTO. fator_concorrência = alunos/máquina (1.4 ideal; >1.7 superlota).",
    }


def calcular_equipamentos_por_area(
    area_disponivel_m2: float,
    footprint_m2: float = 0.0,
    comprimento_cm: float = 0.0,
    largura_cm: float = 0.0,
    folga_passagem_pct: float = 0.5,
    fator_circulacao: float = 0.60,
) -> dict:
    """Calcula de forma DETERMINÍSTICA quantas máquinas cabem numa área, respeitando
    folga de passagem e circulação. Use SEMPRE para "quantos equipamentos cabem em X m²"
    — nunca estime de cabeça.

    O FOOTPRINT da máquina DEVE vir do catálogo (informe footprint_m2 OU comprimento_cm +
    largura_cm obtidos via consultar_catalogo_equipamentos). Folga e circulação são
    benchmarks de PLANEJAMENTO (não estão no catálogo).

    Fórmula:
        area_util   = area_disponivel × fator_circulacao        (desconta corredores/parede/recepção)
        area_unit   = footprint × (1 + folga_passagem_pct)      (espaço de acesso por máquina)
        n_maquinas  = piso(area_util ÷ area_unit)

    Args:
        area_disponivel_m2: área do salão (ou do bloco) dedicada a esse equipamento, em m².
        footprint_m2: área de ocupação da máquina em m² (se já souber). Senão use as dimensões.
        comprimento_cm, largura_cm: dimensões da máquina (do catálogo) p/ derivar o footprint.
        folga_passagem_pct: espaço de acesso ao redor da máquina (padrão 0.5 = +50%).
        fator_circulacao: fração útil do salão após corredores/parede (padrão 0.65).

    Returns:
        dict com n_maquinas, area_util_m2, area_por_maquina_m2, footprint_m2, premissas e nota.
    """
    if footprint_m2 and footprint_m2 > 0:
        fp = float(footprint_m2)
    elif comprimento_cm and largura_cm:
        fp = (float(comprimento_cm) / 100.0) * (float(largura_cm) / 100.0)
    else:
        return {"erro": "Informe footprint_m2 OU comprimento_cm + largura_cm (do catálogo)."}

    area_util = max(0.0, float(area_disponivel_m2)) * float(fator_circulacao)
    area_unit = fp * (1.0 + float(folga_passagem_pct))
    n = int(area_util // area_unit) if area_unit > 0 else 0
    return {
        "n_maquinas": n,
        "footprint_m2": round(fp, 2),
        "area_por_maquina_m2": round(area_unit, 2),
        "area_util_m2": round(area_util, 1),
        "premissas": {
            "folga_passagem_pct": folga_passagem_pct,
            "fator_circulacao": fator_circulacao,
        },
        "nota": (
            "Footprint vem do catálogo (dado real). Folga ~0,80 m (ANVISA Manual de Fiscalização "
            "Sanitária, Seção VII) / 0,6-0,9 m (NSCA); circulação ~40% (boas práticas + NBR 9050). "
            "Premissas de PLANEJAMENTO, ajustáveis — projeto executivo deve ser validado por "
            "engenheiro/arquiteto e vigilância sanitária local."
        ),
    }


def consultar_catalogo_equipamentos(pergunta: str) -> dict:
    """Consulta os CATÁLOGOS de fornecedores de equipamento de academia (Matrix,
    Life Fitness, Total Health) na base de conhecimento. Use SEMPRE antes de citar
    qualquer modelo, código, especificação, dimensão ou carga máxima de um equipamento.

    Args:
        pergunta: o que buscar no catálogo, em linguagem natural
            (ex.: "leg press 45 graus Life Fitness", "esteira Matrix dimensões").

    Returns:
        dict com `resultados` (lista de {titulo, uri, trecho}), `n_docs` e `fonte`.
        Se vier vazio, o modelo NÃO existe no catálogo — não invente.
    """
    from tools.discovery_engine_tools import buscar_catalogos_equipamentos
    try:
        return buscar_catalogos_equipamentos(pergunta, n=4)
    except Exception as e:  # noqa: BLE001
        logger.exception("consultar_catalogo_equipamentos falhou")
        return {"resultados": [], "n_docs": 0, "erro": f"{type(e).__name__}: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# DADOS / VIABILIDADE — port do consultor_engine (Fase 0 da migração ADK).
# Reusam os mesmos tools.* por baixo; params explícitos p/ o schema do ADK.
# (reviews/oferta/relatório dependem de cache/estado → Fase 2.)
# ─────────────────────────────────────────────────────────────────────────────

async def pesquisar_contexto_mercado(cidade: str, bairro: str, uf: str, tipo_negocio: str = "academia") -> dict:
    """Contexto qualitativo do mercado fitness no bairro: renda, tendências, parque CNPJ/RFB,
    fatos de competição local. Use para "como está o mercado lá", "qual a renda do bairro",
    "o mercado fitness está crescendo".

    NÃO use para aluguel de viabilidade/OPEX: o bundle pode trazer `aluguel_portais` (referência
    batch, não decisão). Para "quanto custa o aluguel" / payback / investimento → chame
    `estimar_investimento` (A4 → MRLR IBAPE-GO determinístico).

    Args:
        cidade, bairro, uf: localização (uf = sigla de 2 letras).
        tipo_negocio: academia | crossfit_box | studio_pilates (padrão academia).
    """
    import asyncio
    try:
        from tools.market_bundle import carregar_market_bundle
        from tools.cnpj_fitness_tools import dados_parque_cnpj_para_a0
        from tools.local_market_facts import fatos_competicao_local
        from datetime import datetime, timezone
        bundle, cnpj_data, local = await asyncio.gather(
            asyncio.to_thread(carregar_market_bundle, cidade, bairro, uf),
            asyncio.to_thread(dados_parque_cnpj_para_a0, cidade, uf, 90, bairro),
            asyncio.to_thread(fatos_competicao_local, cidade, bairro, uf),
        )
        return {"cidade": cidade, "bairro": bairro, "uf": uf, "bundle": bundle,
                "parque_cnpj": cnpj_data, "competicao_local": local,
                "fonte": "market_bundle + CNPJ/RFB + OSM",
                "data_coleta": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    except Exception as e:  # noqa: BLE001
        logger.exception("pesquisar_contexto_mercado falhou")
        return {"erro": f"{type(e).__name__}: {e}"}


async def buscar_pontos_comerciais(cidade: str, bairro: str, uf: str,
                                   area_min_m2: int = 500, area_max_m2: int = 2000) -> dict:
    """Imóveis comerciais e zonas âncora (shoppings, avenidas) adequados a academia no bairro.
    Retorna candidatos com endereço, área, score de localização e aluguel DETERMINÍSTICO (MRLR).

    `aluguel_estimado` / `aluguel_unitario_m2` = mesma equação MRLR do A4 (`aluguel_mrlr.py`).
    `price_raw` do anúncio SearchAPI/portal é só referência do listing — nunca entra na fórmula.

    Args:
        cidade, bairro, uf: localização.
        area_min_m2, area_max_m2: faixa de área pretendida.
    """
    import asyncio
    try:
        from tools.anchoring_tools import analisar_pontos_comerciais_completo

        class _StateShim:
            def __init__(self, state: dict):
                self.state = state

        shim = _StateShim({"bairro": bairro, "cidade": cidade,
                           "input_params": {"bairro": bairro,
                                            "area_m2_min": int(area_min_m2),
                                            "area_m2_max": int(area_max_m2)}})
        res = await asyncio.to_thread(analisar_pontos_comerciais_completo, shim, bairro, cidade, uf)
        return res if isinstance(res, dict) else {"candidatos": [], "total_candidatos": 0}
    except Exception as e:  # noqa: BLE001
        logger.exception("buscar_pontos_comerciais falhou")
        return {"erro": f"{type(e).__name__}: {e}"}


async def analisar_demografia(cidade: str, bairro: str, uf: str) -> dict:
    """Demografia IBGE Censo 2022: população por faixa etária, renda média domiciliar,
    público potencial fitness, score demográfico. Use para "quem mora no bairro",
    "qual a faixa etária", "público potencial", "score demográfico".
    """
    import asyncio
    try:
        from tools.ibge_tools import analise_demografica_completa
        res = await asyncio.to_thread(analise_demografica_completa, cidade, uf, "18-45", bairro)
        return res if isinstance(res, dict) else {"erro": "IBGE indisponível"}
    except Exception as e:  # noqa: BLE001
        logger.exception("analisar_demografia falhou")
        return {"erro": f"{type(e).__name__}: {e}"}


async def estimar_investimento(cidade: str, bairro: str, uf: str, area_m2: float = 1150.0,
                               tipo_negocio: str = "academia", tamanho_preset: str = "",
                               genero_alvo: str = "misto") -> dict:
    """Investimento inicial (CAPEX + OPEX) em 3 cenários (low/mid/premium), payback, margem
    e aluguel via MRLR IBAPE-GO (determinístico — Tier 0 do A4). Use para "quanto custa abrir",
    "qual o investimento", "payback", "viabilidade financeira", "quanto é o aluguel".

    Aluguel OPEX = `aluguel_deterministico` sobre espelhos `renda_bairro` + `municipio_pib`.
    Portal/SearchAPI NÃO alimentam a fórmula de viabilidade.

    Args:
        cidade, bairro, uf, area_m2: localização e área pretendida.
        tipo_negocio, tamanho_preset (p|m|g|gg, vazio = inferir por área), genero_alvo.
    """
    import asyncio
    try:
        from tools.financial_tools import analise_financeira_a4_completo
        a = float(area_m2 or 1150.0)
        preset = tamanho_preset or ("p" if a < 500 else "m" if a < 1500 else "g" if a < 3000 else "gg")
        res = await analise_financeira_a4_completo(
            bairro, cidade, uf, a,
            area_m2_min=int(a * 0.8), area_m2_max=int(a * 1.2),
            tipo_negocio=tipo_negocio, tamanho_preset=preset,
        )
        return res if isinstance(res, dict) else {"erro": "Financeiro indisponível"}
    except Exception as e:  # noqa: BLE001
        logger.exception("estimar_investimento falhou")
        return {"erro": f"{type(e).__name__}: {e}"}


def consultar_engenharia_obra(pergunta: str) -> dict:
    """Consulta a base de ENGENHARIA DE OBRA, PROJETO ARQUITETÔNICO e LAYOUT de academia
    (normas ABNT, licenças, estrutura/laje, instalações, acústica, incêndio, acessibilidade,
    sanitários/vestiários, pisos, etapas de projeto, checklists retrofit × obra do zero). Use
    SEMPRE antes de afirmar uma exigência de obra, norma, valor estrutural ou regra de projeto.

    Args:
        pergunta: o que buscar em linguagem natural (ex.: "carga de laje academia NBR 6120",
            "alvará de reforma vs construção", "sanitários por lotação", "isolamento acústico peso").

    Returns:
        dict com `resultados` (lista de {titulo, uri, trecho}), `n_docs` e `fonte`.
        Vazio = a base não cobre; oriente consultar engenheiro/arquiteto e órgão local, não invente.
    """
    import os
    from tools.discovery_engine_tools import buscar_conhecimento
    engine = os.environ.get("DISCOVERY_OBRA_ENGINE_ID", "gymsite-obra-app")
    try:
        r = buscar_conhecimento(pergunta, n=5, engine_id=engine)
        r["fonte"] = "Vertex AI Search (engenharia de obra / projeto)"
        return r
    except Exception as e:  # noqa: BLE001
        logger.exception("consultar_engenharia_obra falhou")
        return {"resultados": [], "n_docs": 0, "erro": f"{type(e).__name__}: {e}"}


def calcular_sanitarios_por_lotacao(
    lotacao: int,
    pessoas_por_conjunto: int = 20,
    pct_acessivel: float = 0.05,
) -> dict:
    """ESTIMATIVA determinística e NÃO-OFICIAL de peças sanitárias por lotação, pela regra
    genérica de código de obras. É PLANEJAMENTO — NÃO é a exigência legal.

    Regra genérica: 1 bacia + 1 lavatório a cada `pessoas_por_conjunto` (padrão 20; reunião
    pode usar 50), dividido 50/50 por gênero; no masculino até 50% das bacias viram mictórios;
    mínimo 5% acessível (NBR 9050). O número OFICIAL vem do Código de Obras do MUNICÍPIO (via
    `consultar_engenharia_obra` ou fonte oficial), que costuma ser ASSIMÉTRICO por gênero e mais
    rígido — ex.: João Pessoa exige mais bacias femininas que o 50/50 daqui. NUNCA apresentar
    este resultado como a contagem legal: rotular como estimativa e mandar confirmar no COE do
    município. Para "quantos banheiros preciso" num município específico, priorizar a base/COE
    sobre esta estimativa.

    Args:
        lotacao: ocupação máxima simultânea da edificação (pessoas).
        pessoas_por_conjunto: pessoas por conjunto bacia+lavatório (padrão 20).
        pct_acessivel: fração acessível (padrão 0.05 = 5%).

    Returns:
        dict com bacias/lavatórios ESTIMADOS, `tipo="estimativa_nao_oficial"` e `aviso`.
    """
    import math
    lot = max(0, int(lotacao))
    ppc = max(1, int(pessoas_por_conjunto))
    conjuntos = math.ceil(lot / ppc) if lot else 0
    por_genero = math.ceil(conjuntos / 2) if conjuntos else 0
    acessiveis = max(1, math.ceil(conjuntos * float(pct_acessivel))) if conjuntos else 0
    return {
        "tipo": "estimativa_nao_oficial",
        "aviso": (
            "Estimativa 50/50 simétrica de PLANEJAMENTO — NÃO é a exigência legal. O Código de "
            "Obras (COE) do município pode exigir números diferentes e ASSIMÉTRICOS por gênero "
            "(ex.: João Pessoa). Confirme no COE municipal antes de projetar."
        ),
        "bacias_total": conjuntos,
        "lavatorios_total": conjuntos,
        "bacias_por_genero": por_genero,
        "lavatorios_por_genero": por_genero,
        "mictorios_masc_possiveis": por_genero // 2,
        "pecas_acessiveis_min": acessiveis,
        "premissas": {"pessoas_por_conjunto": ppc, "pct_acessivel": pct_acessivel},
        "nota": (
            "Regra genérica (ex.: COE-SP LM 17.202/19): ~1 bacia+1 lavatório/20 pessoas; reunião "
            "pode usar /50. 5% acessível (NBR 9050). Número oficial = COE do município."
        ),
    }


def consultar_base_regulatoria(pergunta: str) -> dict:
    """Consulta a base REGULATÓRIA dedicada (documentos CONFEF/CREF, Lei 9.696/1998,
    anuidades, registro PJ, licenças de funcionamento). Use SEMPRE antes de afirmar uma
    exigência legal, valor de anuidade, prazo ou regra.

    Aponta pro engine `gymsite-regulatorio-app` (store gymsite-regulatorio-docs) — NÃO o
    market. Antes disso caía no default market e respondia CREF com doc de mercado.

    Args:
        pergunta: o que buscar, em linguagem natural
            (ex.: "registro CREF pessoa jurídica", "Lei 9.696 quem pode dar aula").

    Returns:
        dict com `resultados` (lista de {titulo, uri, trecho}), `n_docs` e `fonte`.
        Se vier vazio, a base não cobre — oriente confirmar no CREF/prefeitura, não invente.
    """
    import os
    from tools.discovery_engine_tools import buscar_conhecimento
    engine = os.environ.get("DISCOVERY_REGULATORIO_ENGINE_ID", "gymsite-regulatorio-app")
    try:
        r = buscar_conhecimento(pergunta, n=4, engine_id=engine)
        r["fonte"] = "Vertex AI Search (regulatório CREF/Lei)"
        return r
    except Exception as e:  # noqa: BLE001
        logger.exception("consultar_base_regulatoria falhou")
        return {"resultados": [], "n_docs": 0, "erro": f"{type(e).__name__}: {e}"}


def consultar_base_mercado(pergunta: str) -> dict:
    """Consulta a base de MERCADO (metodologia GymSite, benchmarks do setor, franquias,
    tendências, dores). Use para "como vocês calculam viabilidade", "tendência do setor",
    "boas práticas" — NÃO para exigência legal (isso é `consultar_base_regulatoria`).

    Aponta pro engine `gymsite-market-app` (default). Separada da regulatória pra não
    misturar fato de mercado com norma legal.

    Returns:
        dict com `resultados` (lista de {titulo, uri, trecho}), `n_docs` e `fonte`.
        Se vier vazio, a base não cobre — diga com transparência, não invente.
    """
    from tools.discovery_engine_tools import buscar_conhecimento
    try:
        return buscar_conhecimento(pergunta, n=4)
    except Exception as e:  # noqa: BLE001
        logger.exception("consultar_base_mercado falhou")
        return {"resultados": [], "n_docs": 0, "erro": f"{type(e).__name__}: {e}"}


def buscar_concorrentes(
    cidade: str,
    bairro: str,
    uf: str = "",
    tipo_negocio: str = "academia",
    raio_metros: int = 1500,
) -> dict:
    """Conta e lista academias concorrentes num raio do bairro (Google Maps ao vivo).
    Use para responder saturação/concorrência do entorno com NÚMERO REAL — nunca estime
    a quantidade de cabeça.

    Args:
        cidade: cidade (ex.: "Fortaleza").
        bairro: bairro de referência (ex.: "Cocó").
        uf: sigla do estado, opcional (ex.: "CE").
        tipo_negocio: "academia" | "crossfit" | "studio_pilates" | "studio_funcional".
        raio_metros: raio de busca em metros (300 a 5000; padrão 1500).

    Returns:
        dict com `total_concorrentes` (int), `nivel_saturacao` (baixo|medio|alto) e
        `concorrentes` (top 8 por distância: nome, endereco, distancia_m, rating, avaliacoes).
    """
    from tools.competitor_tools import buscar_academias
    try:
        raio = max(300, min(5000, int(raio_metros)))
        res = buscar_academias(bairro, cidade, raio, uf or "", tipo_negocio)
    except Exception as e:  # noqa: BLE001
        logger.exception("buscar_concorrentes falhou")
        return {"total_concorrentes": 0, "nivel_saturacao": "desconhecido",
                "concorrentes": [], "erro": f"{type(e).__name__}: {e}"}

    brutos = res.get("concorrentes") or []
    itens = []
    for c in brutos:
        if not isinstance(c, dict):
            continue
        itens.append({
            "nome": c.get("nome") or c.get("name") or c.get("displayName") or "?",
            "endereco": c.get("endereco") or c.get("address") or c.get("formattedAddress"),
            "distancia_m": c.get("distancia_m") or c.get("distance_m") or c.get("distancia"),
            "rating": c.get("rating") or c.get("nota"),
            "avaliacoes": c.get("num_avaliacoes") or c.get("avaliacoes") or c.get("user_ratings_total"),
        })
    total = len(itens)
    itens.sort(key=lambda x: x["distancia_m"] if x["distancia_m"] is not None else 99_999)
    return {
        "total_concorrentes": total,
        "nivel_saturacao": _nivel_saturacao(total),
        "concorrentes": itens[:8],
    }
