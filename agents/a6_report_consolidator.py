# agents/a6_report_consolidator.py
"""A6: Consolidador final — relatório executivo markdown com gap + bairros alternativos + crowdsource."""
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger("gymsite.a6")
from pathlib import Path
from google.adk.agents import Agent
from google.genai import types
from tools.utils_tools import obter_data_atual
from tools.token_telemetry import before_agent_callback as _telemetry_before

# Thinking calibrado: A6 sintetiza outputs de 5 agentes anteriores, decide
# bairros alternativos quando score_geral < 6, escolhe o veredito final
# e renderiza tabelas complexas com regras condicionais. Síntese pesada —
# thinking alto melhora consistência e tie-breaker do Top 3.
# tools=[] — sem function_calling_config necessário (não chama tools).
_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=8192),  # pyright: ignore[reportCallIssue]
)


# ── Mapa de bairros alternativos por cidade (acionado quando score < 6) ──
#
# Estrutura em 2 níveis:
# - Capitais/cidades grandes: bairros internos como alternativas
# - Cidades pequenas/metropolitanas: bairros próprios + cidades vizinhas da
#   mesma RM (Região Metropolitana). Ex: Eusébio → próprios bairros +
#   Maracanaú, Caucaia, Pacatuba (RMF).
BAIRROS_ALTERNATIVOS = {
    # ── RMF (Fortaleza) ──────────────────────────────────────────────
    "fortaleza": [
        {"bairro": "Cocó / Guararapes",
         "motivo": "Alto poder aquisitivo, baixa oferta fitness premium"},
        {"bairro": "Papicu / Edson Queiroz",
         "motivo": "Crescimento imobiliário acelerado, público jovem"},
        {"bairro": "Cidade dos Funcionários / Cambeba",
         "motivo": "Classe média consolidada, poucos concorrentes"},
        {"bairro": "Maraponga / Montese",
         "motivo": "Alta densidade populacional, ticket low-cost viável"},
    ],
    "eusébio": [
        {"bairro": "Centro Eusébio",
         "motivo": "Núcleo urbano consolidado, fluxo comercial alto"},
        {"bairro": "Tamatanduba",
         "motivo": "Polo comercial Shopping Eusébio, alta demanda"},
        {"bairro": "Coaçu",
         "motivo": "Terrazo Shopping, residencial classe média-alta"},
        {"bairro": "Coité",
         "motivo": "Expansão imobiliária, condomínios fechados Cidade Alpha"},
        {"bairro": "Pajuçara",
         "motivo": "Residencial em consolidação, ticket médio viável"},
        {"bairro": "Aquiraz (cidade vizinha)",
         "motivo": "RMF, baixa concorrência fitness, Porto das Dunas"},
    ],
    "caucaia": [
        {"bairro": "Centro Caucaia",
         "motivo": "Alta densidade urbana, comércio consolidado"},
        {"bairro": "Jurema",
         "motivo": "Classe média, baixa oferta premium"},
        {"bairro": "Tabuba / Cumbuco",
         "motivo": "Turismo + crescimento residencial"},
    ],
    "maracanaú": [
        {"bairro": "Centro Maracanaú",
         "motivo": "Hub industrial, fluxo trabalhador, low-cost viável"},
        {"bairro": "Pajuçara Maracanaú",
         "motivo": "Conjuntos habitacionais, alto volume"},
    ],
    "aquiraz": [
        {"bairro": "Porto das Dunas",
         "motivo": "Crescimento turístico + condomínios alta renda"},
        {"bairro": "Centro Aquiraz",
         "motivo": "Núcleo urbano histórico, comércio local"},
    ],

    # ── RMSP (São Paulo) ─────────────────────────────────────────────
    "sao paulo": [
        {"bairro": "Tatuapé / Mooca",
         "motivo": "Classe média alta, demanda por academias premium"},
        {"bairro": "Santo André / São Bernardo (ABC)",
         "motivo": "ABC paulista em expansão fitness"},
        {"bairro": "Osasco / Carapicuíba",
         "motivo": "Mercado low-cost subatendido"},
        {"bairro": "Guarulhos",
         "motivo": "Crescimento populacional + aeroporto = fluxo garantido"},
    ],
    "guarulhos": [
        {"bairro": "Centro Guarulhos",
         "motivo": "Hub comercial RMSP, alto fluxo"},
        {"bairro": "Vila Galvão / Macedo",
         "motivo": "Classe média consolidada"},
    ],
    "osasco": [
        {"bairro": "Centro Osasco",
         "motivo": "Hub comercial região oeste RMSP"},
        {"bairro": "Bela Vista / Vila Yara",
         "motivo": "Classe média-alta, demanda premium"},
    ],

    # ── RMRJ (Rio de Janeiro) ────────────────────────────────────────
    "rio de janeiro": [
        {"bairro": "Méier / Tijuca",
         "motivo": "Zona Norte consolidada, baixa oferta premium"},
        {"bairro": "Campo Grande / Bangu",
         "motivo": "Mercado low-cost de alto volume"},
        {"bairro": "Niterói (cidade vizinha)",
         "motivo": "Poder aquisitivo elevado, concorrência moderada"},
    ],
    "niterói": [
        {"bairro": "Icaraí / Santa Rosa",
         "motivo": "Alto poder aquisitivo, demanda premium"},
        {"bairro": "São Francisco",
         "motivo": "Classe média-alta, residencial vertical"},
    ],

    # ── DF e outras capitais ─────────────────────────────────────────
    "brasília": [
        {"bairro": "Águas Claras",
         "motivo": "Maior densidade demográfica do DF, classe média alta"},
        {"bairro": "Taguatinga",
         "motivo": "Alta circulação, mercado low-cost consolidado"},
        {"bairro": "Sudoeste",
         "motivo": "Plano Piloto, alto poder aquisitivo"},
    ],
    "belo horizonte": [
        {"bairro": "Buritis / Estoril",
         "motivo": "Bairros em expansão, classe média alta"},
        {"bairro": "Pampulha",
         "motivo": "Tradição esportiva, público fitness consolidado"},
        {"bairro": "Contagem / Nova Lima (cidades vizinhas)",
         "motivo": "RMBH, baixa concorrência"},
    ],
    "salvador": [
        {"bairro": "Pituba / Itaigara",
         "motivo": "Classe média-alta consolidada"},
        {"bairro": "Lauro de Freitas (cidade vizinha)",
         "motivo": "RMS, crescimento residencial"},
    ],
    "curitiba": [
        {"bairro": "Batel / Água Verde",
         "motivo": "Alto poder aquisitivo, demanda premium"},
        {"bairro": "Cabral / Juvevê",
         "motivo": "Classe média consolidada"},
    ],
    "recife": [
        {"bairro": "Boa Viagem / Pina",
         "motivo": "Zona Sul de alta renda"},
        {"bairro": "Olinda (cidade vizinha)",
         "motivo": "RMR, mercado consolidado"},
    ],

    # ── RMJP (João Pessoa) ───────────────────────────────────────────
    "joao pessoa": [
        {"bairro": "Tambaú",
         "motivo": "Praia nobre, alto poder aquisitivo, ticket premium viável"},
        {"bairro": "Cabo Branco",
         "motivo": "Praia, classe alta, baixa oferta fitness premium"},
        {"bairro": "Miramar",
         "motivo": "Classe média-alta consolidada, eixo orla"},
        {"bairro": "Torre",
         "motivo": "Comercial e residencial classe média-alta, fluxo garantido"},
        {"bairro": "Bancários",
         "motivo": "Público universitário UFPB + classe média, ticket médio acessível"},
        {"bairro": "Altiplano",
         "motivo": "Expansão imobiliária recente, renda alta, baixa concorrência"},
        {"bairro": "Mangabeira",
         "motivo": "Alta densidade populacional, mercado low-cost subatendido"},
    ],
    "cabedelo": [
        {"bairro": "Intermares",
         "motivo": "Praia, expansão residencial, público jovem classe média"},
        {"bairro": "Centro Cabedelo",
         "motivo": "Porto, comércio consolidado, fluxo garantido"},
    ],
    "santa rita": [
        {"bairro": "Centro Santa Rita",
         "motivo": "Segunda cidade da RMJP, mercado low-cost consolidado"},
    ],
    "bayeux": [
        {"bairro": "Centro Bayeux",
         "motivo": "RMJP, alta densidade urbana, ticket low-cost viável"},
    ],
}

# Mapeia cidade → outras cidades da mesma RM (Região Metropolitana).
# Usado pra sugerir cidades vizinhas quando o bairro alvo é em município pequeno.
REGIAO_METROPOLITANA: dict[str, list[str]] = {
    "fortaleza": ["eusébio", "caucaia", "maracanaú", "aquiraz", "pacatuba", "horizonte"],
    "eusébio": ["fortaleza", "aquiraz", "pacatuba"],
    "caucaia": ["fortaleza", "maracanaú"],
    "maracanaú": ["fortaleza", "caucaia", "pacatuba"],
    "aquiraz": ["eusébio", "fortaleza"],
    "sao paulo": ["guarulhos", "osasco", "santo andré", "são bernardo", "carapicuíba"],
    "guarulhos": ["sao paulo", "arujá"],
    "osasco": ["sao paulo", "carapicuíba", "barueri"],
    "rio de janeiro": ["niterói", "duque de caxias", "nova iguaçu", "são gonçalo"],
    "niterói": ["rio de janeiro", "são gonçalo"],
    "belo horizonte": ["contagem", "nova lima", "betim"],
    "salvador": ["lauro de freitas", "camaçari"],
    "recife": ["olinda", "jaboatão dos guararapes"],
    "joao pessoa": ["cabedelo", "santa rita", "bayeux", "conde", "lucena"],
    "cabedelo": ["joao pessoa", "santa rita"],
    "santa rita": ["joao pessoa", "bayeux"],
    "bayeux": ["joao pessoa", "santa rita"],
}


def _norm_cidade(cidade: str) -> str:
    """
    Lowercase + strip + remove acentos pra lookup robusto.
    'São Paulo' → 'sao paulo', 'Eusébio' → 'eusebio'.
    """
    from tools.bairro_normalize import normalizar_bairro

    return normalizar_bairro(cidade)


def detectar_bairro_que_eh_cidade(bairro: str, cidade: str) -> str | None:
    """
    Detecta caso comum: user escreve cidade=Fortaleza, bairro=Eusebio,
    mas Eusébio é município separado da RM (não bairro de Fortaleza).
    Retorna sugestão de correção ou None se não houver ambiguidade.
    """
    bairro_low = _norm_cidade(bairro)
    cidade_low = _norm_cidade(cidade)

    # Bairros que são na verdade municípios da mesma RM
    municipios_rm = REGIAO_METROPOLITANA.get(cidade_low, [])
    for mun in municipios_rm:
        mun_norm = _norm_cidade(mun)
        if mun_norm in bairro_low or bairro_low in mun_norm:
            return (
                f"⚠️ '{bairro}' parece ser o município {mun.title()} (cidade vizinha "
                f"de {cidade}), não um bairro. Próxima análise: rode como "
                f"cidade='{mun.title()}', bairro='Centro' (ou bairro específico do município)."
            )
    return None


def resolver_cidade_efetiva(cidade: str, bairro: str) -> tuple[str, bool]:
    """
    Resolve o município ALVO efetivo quando o `bairro` informado é na verdade
    nome de um município da RM da `cidade`.

    Bug que motivou (2026-05-11): A0 trata "Eusébio" como bairro de Fortaleza.
    A6 puxa BAIRROS_ALTERNATIVOS["fortaleza"] → sugere Cocó/Papicu/Maraponga
    (todos de Fortaleza-cidade), nada de Eusébio-município.

    Retorna:
        (cidade_efetiva, foi_corrigida):
            cidade_efetiva = município alvo real (pra get_bairros_alternativos)
            foi_corrigida = True se trocou a cidade, False se mantém original
    """
    cidade_norm = _norm_cidade(cidade)
    bairro_norm = _norm_cidade(bairro)
    if not bairro_norm:
        return (cidade, False)

    municipios_rm = REGIAO_METROPOLITANA.get(cidade_norm, [])
    for mun in municipios_rm:
        mun_norm = _norm_cidade(mun)
        # Match: bairro É o município, ou contém substring exata
        if (
            bairro_norm == mun_norm
            or mun_norm in bairro_norm
            or bairro_norm in mun_norm
        ):
            return (mun, True)
    return (cidade, False)


def get_bairros_alternativos(cidade: str) -> list:
    """
    Retorna lista de bairros alternativos para a cidade.

    Estratégia em 3 camadas:
    1. Match exato no BAIRROS_ALTERNATIVOS (cidade conhecida)
    2. Cidades da mesma Região Metropolitana (se cidade menor)
    3. Fallback genérico ("Centro Expandido" + "Bairros em expansão")

    Comparação tolerante a acentos: 'Eusébio' bate com 'eusébio' OU 'eusebio'.
    """
    cidade_low = _norm_cidade(cidade)

    # 1. Match direto — normaliza ambos lados pra ser tolerante a acentos
    for key, bairros in BAIRROS_ALTERNATIVOS.items():
        if _norm_cidade(key) in cidade_low:
            return bairros

    # 2. Procura cidades da RM que estejam no nosso mapa
    for cidade_rm in REGIAO_METROPOLITANA.keys():
        if _norm_cidade(cidade_rm) in cidade_low:
            return BAIRROS_ALTERNATIVOS.get(cidade_rm, [])

    # 3. Fallback genérico — cidade não mapeada; marcar para frontend
    return [
        {"bairro": "Centro Expandido",
         "motivo": "Alta densidade comercial e fluxo garantido",
         "_e_fallback": True},
        {"bairro": "Bairros em expansão imobiliária recente",
         "motivo": "Novos empreendimentos = público novo, sem concorrência consolidada",
         "_e_fallback": True},
    ]


def _classificar_status_competitivo(count: int) -> tuple[str, str]:
    """Mapeia contagem de academias para (status_label, prioridade)."""
    if count >= 5:
        return "🔴 muito saturado", "BAIXA"
    if count >= 2:
        return "🔴 saturado", "BAIXA"
    if count == 1:
        return "🟡 1 concorrente mapeado", "MEDIA"
    return "🟢 sem concorrentes mapeados", "ALTA"


def _bairro_alvo_da_busca(state) -> str:
    """Extrai bairro alvo do market_context para evitar contar academias do
    bairro que originou a pesquisa como saturação de bairros alternativos."""
    if state is None:
        return ""
    try:
        from tools.competitor_tools import _parse_market_context
        ctx = _parse_market_context(state.get("market_context"))
        if isinstance(ctx, dict):
            inner = ctx.get("market_context") if isinstance(ctx.get("market_context"), dict) else ctx
            return (inner.get("bairro") or "").strip()  # pyright: ignore[reportOptionalMemberAccess]
    except Exception:
        logger.warning(
            "A6 market_context fallback falhou ao extrair bairro alvo",
            exc_info=True,
            extra={"agent": "A6", "context": "_bairro_alvo_da_busca"},
        )
    return ""


def bairros_alternativos_inteligentes(tool_context) -> dict:
    """
    Tool determinística que avalia bairros alternativos com base em pesquisa
    REAL no Google Places — não apenas no que o A3a coletou no raio do bairro alvo.

    Por que mudou (VEC-387 iteração 5):
    versões anteriores cruzavam `BAIRROS_ALTERNATIVOS` com `distribuicao_geografica`
    do A3b, que só conhece academias dentro do raio de 3km do bairro alvo.
    Bairros alternativos como Maraponga (~12km do Meireles) ficavam de fora
    da busca e eram marcados como "🟢 sem concorrentes mapeados — ALTA",
    quando na realidade Google mostra dezenas de academias lá.

    Agora: para cada bairro alternativo, faz `buscar_academias()` em raio
    de 2km (Google Places → fallback Overpass/OSM se API bloqueada).
    Se a busca falhar, tenta OSM de novo antes de cair na distribuição do A3b.

    Lê do session state:
      - market_context.cidade (output do A0)
      - market_context.bairro (bairro alvo, para excluir da busca)
      - inteligencia_competitiva.distribuicao_geografica (mantido como
        input complementar para o A6 renderizar tabela de distribuição
        no raio original de 3km — separado da pesquisa por bairro alt)

    Retorna:
      - bairros_alternativos: cada item enriquecido com count REAL,
        `academias_existentes`, `status`, `prioridade_ajustada`,
        `metodologia` ("busca real" ou "fallback distribuicao_geografica"
        se busca falhou)
      - distribuicao_geografica: pass-through do A3b
    """
    from tools.competitor_tools import (
        _parse_market_context,
        buscar_academias,
        _eh_academia_tradicional,
    )

    state = getattr(tool_context, "state", None)
    cidade = ""
    uf = ""
    distribuicao: list = []

    if state is not None:
        ctx = _parse_market_context(state.get("market_context"))
        if isinstance(ctx, dict):
            inner_candidate = ctx.get("market_context")
            inner = inner_candidate if isinstance(inner_candidate, dict) else ctx
            cidade = (inner.get("cidade") or "").strip()
            uf = (inner.get("uf") or "").strip()

        ic = _parse_market_context(state.get("inteligencia_competitiva"))
        if isinstance(ic, dict):
            distribuicao = ic.get("distribuicao_geografica") or []
            if not distribuicao:
                inner_ic = ic.get("inteligencia_competitiva")
                if isinstance(inner_ic, dict):
                    distribuicao = inner_ic.get("distribuicao_geografica") or []

    from tools.bairro_normalize import normalizar_bairro, partes_bairro_alvo

    bairro_alvo = _bairro_alvo_da_busca(state)
    bairro_alvo_chave = normalizar_bairro(bairro_alvo)

    # ── Cross-município fix ──────────────────────────────────────────
    # Quando o A0 trata o município alvo como bairro (caso Eusébio dentro
    # de Fortaleza), resolver_cidade_efetiva detecta e troca a cidade pra
    # o município real. Bairros alternativos passam a ser DO município
    # alvo, não da capital. Aviso geográfico vai pro output pro A6
    # renderizar no markdown.
    cidade_efetiva, cidade_foi_corrigida = resolver_cidade_efetiva(cidade, bairro_alvo)
    aviso_geografico = None
    if cidade_foi_corrigida:
        aviso_geografico = (
            f"Análise originalmente endereçada como '{bairro_alvo} / {cidade}', "
            f"mas '{bairro_alvo}' é município da RM de {cidade} (não bairro). "
            f"Bairros alternativos foram derivados de {cidade_efetiva.title()} "
            f"(município efetivo), não da capital."
        )

    # Fallback index — se busca real falhar, cai pro método antigo
    saturados_fallback: dict[str, int] = {}
    academias_fallback: dict[str, list[str]] = {}
    for d in distribuicao:
        if not isinstance(d, dict):
            continue
        b_low = (d.get("bairro") or "").lower().strip()
        if b_low:
            saturados_fallback[b_low] = int(d.get("count") or 0)
            academias_fallback[b_low] = d.get("academias") or []

    # Usa cidade_efetiva (não a original) pra buscar bairros + pra geocodar
    # as buscas Places de cada bairro alternativo.
    base = get_bairros_alternativos(cidade_efetiva)
    cidade_para_busca = cidade_efetiva
    enriquecidos: list[dict] = []

    for entry in base:
        bairro_alt = entry.get("bairro", "")
        e_fallback = entry.get("_e_fallback", False)
        # Bairros compostos "Cocó / Guararapes" — usamos o primeiro como query
        # principal mas guardamos a lista pra fallback e label
        partes = [
            p.strip()
            for p in bairro_alt.replace("/", ",").split(",")
            if p.strip()
        ]
        if not partes:
            continue

        bairro_principal = partes[0]
        partes_chave = set(partes_bairro_alvo(bairro_alt) or [normalizar_bairro(p) for p in partes])
        count_total = 0
        academias_existentes: list[str] = []
        place_ids_vistos: set = set()
        fontes_busca: list[str] = []
        fonte_dominante = ""
        metodologia = "busca real (raio 2km, filtros: academia tradicional + match de bairro)"

        try:
            for parte in partes:
                resultado = buscar_academias(
                    parte, cidade_para_busca, raio_metros=2000, uf=uf or "CE"
                )
                concorrentes = resultado.get("concorrentes") or []
                fonte_parte = resultado.get("fonte_busca_competidores") or ""

                # Canal 2: OSM — se Places falhou mas geocode ok
                if not concorrentes and resultado.get("erro"):
                    try:
                        from tools.competitor_tools import _buscar_academias_overpass
                        from tools.maps_tools import geocode_endereco

                        geo_p = geocode_endereco(f"{parte}, {cidade_para_busca}, Brasil")
                        if "error" not in geo_p:
                            osm_list, _ = _buscar_academias_overpass(
                                geo_p["lat"], geo_p["lng"], 2000, limit=20
                            )
                            if osm_list:
                                concorrentes = osm_list
                                fonte_parte = "overpass_osm"
                    except Exception:
                        logger.warning(
                            "A6 fallback OSM (Overpass) falhou para parte=%s",
                            parte,
                            exc_info=True,
                            extra={"agent": "A6", "context": "bairros_osm_fallback"},
                        )

                # Canal 3: CNPJ RFB — parque ativo no bairro (Supabase)
                if not concorrentes:
                    try:
                        from tools.competitor_tools import _buscar_academias_cnpj_bairro

                        cnpj_list, cnpj_blk = _buscar_academias_cnpj_bairro(
                            parte, cidade_para_busca, uf or "CE", limit=25
                        )
                        if cnpj_list:
                            concorrentes = cnpj_list
                            fonte_parte = "cnpj_rfb"
                    except Exception:
                        logger.warning(
                            "A6 fallback CNPJ RFB falhou para parte=%s",
                            parte,
                            exc_info=True,
                            extra={"agent": "A6", "context": "bairros_cnpj_fallback"},
                        )

                if fonte_parte:
                    fontes_busca.append(fonte_parte)
                if not concorrentes and resultado.get("erro"):
                    raise RuntimeError(resultado.get("erro"))

                for c in concorrentes:
                    if not isinstance(c, dict):
                        continue
                    pid = c.get("place_id") or c.get("nome", "")
                    if pid in place_ids_vistos:
                        continue

                    # Filtro semântico: exclui escolas de futebol, clínicas,
                    # estúdios de modalidade única (VEC-387 iter 6 — solicitado
                    # pelo dono do produto após contagem manual em Montese
                    # mostrar 20 academias tradicionais vs 34 no count cru)
                    eh_academia, motivo = _eh_academia_tradicional(c)
                    if not eh_academia:
                        continue

                    # Match de bairro: academia precisa estar em um dos
                    # sub-bairros da entrada (ex: Maraponga ou Montese, não
                    # Parangaba que é vizinha). Se bairro_concorrente vazio,
                    # mantém (benefit of doubt — endereço pode estar truncado).
                    bairro_concorrente = ""
                    try:
                        from tools.competitor_tools import extrair_bairro_endereco

                        bairro_concorrente_raw = (
                            extrair_bairro_endereco(c.get("endereco", "")) or ""
                        )
                        bairro_concorrente = normalizar_bairro(bairro_concorrente_raw)
                    except Exception:
                        logger.debug(
                            "A6 extrair_bairro_endereco skip",
                            exc_info=True,
                            extra={"agent": "A6", "context": "extrair_bairro_endereco"},
                        )
                    if bairro_alvo_chave and bairro_concorrente == bairro_alvo_chave:
                        continue

                    # Match de bairro com tolerância: se bairro_concorrente
                    # não bate com nenhuma parte da entrada, ainda mantém SE
                    # o nome da academia menciona alguma das partes
                    # (ex: "TP FITNESS ACADEMIAS | MARAPONGA" sem bairro
                    # extraído deve contar como Maraponga).
                    usa_fallback_geo = (
                        fonte_parte in ("overpass_osm", "cnpj_rfb")
                        or c.get("fonte_busca") in ("overpass_osm", "cnpj_rfb")
                    )
                    if bairro_concorrente and bairro_concorrente not in partes_chave:
                        nome_low = normalizar_bairro(c.get("nome") or "")
                        nome_bate_bairro = any(p in nome_low for p in partes_chave)
                        if not nome_bate_bairro and not usa_fallback_geo:
                            continue
                    place_ids_vistos.add(pid)
                    count_total += 1
                    nome_academia = c.get("nome", "?")
                    if nome_academia not in academias_existentes:
                        academias_existentes.append(nome_academia)
        except Exception as e:
            # Último recurso: distribuição do raio do bairro alvo (A3b) — incompleta
            # para bairros distantes; não tratar como "sem concorrentes" confiável.
            metodologia = (
                f"fallback distribuicao_geografica (busca Maps/OSM falhou: "
                f"{type(e).__name__}) — contagem pode estar subestimada"
            )
            count_total = 0
            academias_existentes = []
            fonte_dominante = ""
            for parte in partes:
                p_low = parte.lower()
                count_total += saturados_fallback.get(p_low, 0)
                academias_existentes.extend(academias_fallback.get(p_low, []))

        # Cap acadêmico: se busca real retornou >20, é provavelmente região
        # comercial densa — cap em 20 pra não estourar a tabela
        if len(academias_existentes) > 10:
            academias_existentes = academias_existentes[:10] + [f"... (+{len(academias_existentes) - 10})"]

        status, prioridade = _classificar_status_competitivo(count_total)

        if not fonte_dominante:
            if "google_places" in fontes_busca:
                fonte_dominante = "google_places"
            elif "overpass_osm" in fontes_busca:
                fonte_dominante = "overpass_osm"
            elif "cnpj_rfb" in fontes_busca:
                fonte_dominante = "cnpj_rfb"
            else:
                fonte_dominante = ""
        if fonte_dominante == "overpass_osm":
            metodologia = (
                f"{metodologia} | fonte: OpenStreetMap (Google Places indisponível)"
            )
        elif fonte_dominante == "cnpj_rfb":
            metodologia = (
                f"{metodologia} | fonte: CNPJ RFB parque ativo (Maps/OSM indisponíveis)"
            )
        elif fonte_dominante == "google_places":
            metodologia = f"{metodologia} | fonte: Google Places"

        # Fallback genérico: nome de bairro vago → busca retorna 0, mas o 0
        # não é confiável. Sinaliza explicitamente pra UI não exibir como ALTA.
        if e_fallback:
            metodologia = "fallback genérico — cidade não mapeada, bairro não verificável no Google Places"
            dados_confiaveis_flag = False
        else:
            dados_confiaveis_flag = fonte_dominante in ("google_places", "overpass_osm", "cnpj_rfb")

        row = {k: v for k, v in entry.items() if not k.startswith("_")}  # remove markers internos
        enriquecidos.append({
            **row,
            "bairro_principal_busca": bairro_principal,
            "concorrentes_no_bairro": count_total,
            "academias_existentes": academias_existentes,
            "status": status,
            "prioridade_ajustada": prioridade,
            "metodologia": metodologia,
            "fonte_busca_competidores": fonte_dominante or None,
            "dados_confiaveis": dados_confiaveis_flag,
        })

    # Reordena: ALTA > MEDIA > BAIXA. Empate → menor count.
    pri_order = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
    enriquecidos.sort(
        key=lambda x: (
            pri_order.get(x["prioridade_ajustada"], 3),
            x["concorrentes_no_bairro"],
        )
    )

    return {
        "cidade": cidade,
        "cidade_efetiva": cidade_efetiva,
        "cidade_foi_corrigida": cidade_foi_corrigida,
        "aviso_geografico": aviso_geografico,
        "bairro_alvo": bairro_alvo,
        "distribuicao_geografica": distribuicao,
        "bairros_alternativos": enriquecidos,
    }


def _precompute_entrantes_cnpj(callback_context) -> dict:
    """Carrega lista de entrantes CNPJ (90d) para o relatório — sem LLM."""
    from tools.cnpj_fitness_tools import listar_entrantes_cnpj_fitness
    from tools.competitor_tools import _parse_market_context

    state = getattr(callback_context, "state", {}) or {}
    raw_mc = state.get("market_context")
    mc = _parse_market_context(raw_mc)
    inner_mc = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
    if not isinstance(inner_mc, dict):
        inner_mc = {}

    cidade = (inner_mc.get("cidade") or state.get("cidade") or "").strip()
    uf = (inner_mc.get("uf") or state.get("uf") or "").strip()
    if not cidade:
        return {"status": "indisponivel", "motivo": "cidade_ausente", "entrantes": []}

    # Snapshot RFB no Supabase apenas — Receita/Apollo sob demanda na UI do relatório.
    return listar_entrantes_cnpj_fitness(cidade, uf, dias=90, limit=50)


def _precompute_obras_cno(callback_context) -> dict:
    """Obras fitness em andamento (CNO) — nome, m², bairro, data início."""
    import os
    from pathlib import Path

    from tools.competitor_tools import _parse_market_context

    state = getattr(callback_context, "state", {}) or {}
    raw_mc = state.get("market_context")
    mc = _parse_market_context(raw_mc)
    inner_mc = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
    if not isinstance(inner_mc, dict):
        inner_mc = {}

    cidade = (inner_mc.get("cidade") or state.get("cidade") or "").strip()
    uf = (inner_mc.get("uf") or state.get("uf") or "").strip()
    if not cidade:
        return {"status": "indisponivel", "motivo": "cidade_ausente", "obras": []}

    cno_dir = (os.getenv("CNO_DATA_DIR") or "").strip()
    if not cno_dir or not Path(cno_dir).is_dir():
        cno_dir_host = (os.getenv("CNO_DATA_DIR_HOST") or "").strip()
        if cno_dir_host and Path(cno_dir_host).is_dir():
            cno_dir = cno_dir_host
    if not cno_dir or not Path(cno_dir).is_dir():
        return {"status": "nao_configurado", "motivo": "CNO_DATA_DIR ausente", "obras": []}

    try:
        from tools.cno_fitness_tools import (
            calcular_benchmark_tempo_obra_cno,
            listar_obras_fitness_em_curso,
            slim_obras_para_relatorio,
        )

        bairro_alvo = (inner_mc.get("bairro") or state.get("bairro") or "").strip()
        cidade_efetiva, _ = resolver_cidade_efetiva(cidade, bairro_alvo)

        bench = calcular_benchmark_tempo_obra_cno(
            cno_dir=cno_dir, cidade=cidade_efetiva, uf=uf
        )
        # Escopo municipal — não filtrar só o bairro do relatório.
        block = listar_obras_fitness_em_curso(
            cno_dir=cno_dir,
            cidade=cidade_efetiva,
            uf=uf,
            limit=40,
            benchmark_tempo=bench,
            bairro_filtro=None,
        )
        slim = slim_obras_para_relatorio(block, benchmark_tempo=bench)
        if isinstance(slim, dict) and bairro_alvo:
            slim["bairro_relatorio"] = bairro_alvo
        return slim
    except Exception as exc:
        return {"status": "erro", "motivo": str(exc), "obras": []}


def _a6_precompute_callback(callback_context):
    """
    Pre-computa `bairros_alternativos_inteligentes` ANTES do LLM rodar e injeta
    o resultado em `callback_context.state["bairros_alternativos_pronto"]`.

    Por si só, isso NÃO basta — ADK não expõe state automaticamente ao LLM.
    Por isso há também o `_a6_before_model_callback` (logo abaixo) que usa
    `llm_request.append_instructions()` para empurrar o markdown pronto direto
    para o system prompt do modelo.

    Histórico do bug (VEC-387):
    - Run 11 (eac816f649d1): A6 ignorou a tool — gerou Cocó como 🟢 ALTA
    - Run 12 (0b0f2fe3): callback populou state, mas LLM ainda gerou 🟢 ALTA
      porque o state não era visível no prompt.

    Também invoca `_telemetry_before` no fim para preservar `run_id` no CSV.
    """
    start = time.perf_counter()

    try:
        result = bairros_alternativos_inteligentes(callback_context)
        callback_context.state["bairros_alternativos_pronto"] = result
    except Exception:
        logger.error(
            "A6 precompute bairros_alternativos falhou — seção será omitida ou fabricada pelo LLM",
            exc_info=True,
            extra={"agent": "A6", "step": "precompute_bairros"},
        )

    try:
        callback_context.state["entrantes_cnpj_pronto"] = _precompute_entrantes_cnpj(
            callback_context
        )
    except Exception:
        logger.error(
            "A6 precompute entrantes_cnpj falhou",
            exc_info=True,
            extra={"agent": "A6"},
        )

    try:
        callback_context.state["obras_cno_pronto"] = _precompute_obras_cno(callback_context)
    except Exception:
        logger.error(
            "A6 precompute obras_cno falhou",
            exc_info=True,
            extra={"agent": "A6"},
        )

    try:
        _telemetry_before(callback_context)
    except Exception:
        logger.warning(
            "A6 telemetry_before falhou",
            exc_info=True,
            extra={"agent": "A6"},
        )

    elapsed = time.perf_counter() - start
    logger.info(
        "A6 precompute completed in %.2fs",
        elapsed,
        extra={"agent": "A6"},
    )


def _escape_md_pipe(s) -> str:
    """
    Substitui `|` por `/` em strings que vão pra dentro de células de tabela
    markdown. Sem isso, nomes como "Greenlife Academias | Maraponga" quebram
    a coluna e a linha inteira do A6 fica truncada (Run 14 / cd8e85e038aa
    apresentou esse bug em produção — coluna Ticket+Prioridade desapareceu).
    """
    if s is None:
        return ""
    return str(s).replace("|", "/")


def _renderizar_secao_bairros_alternativos(pronto: dict) -> str:
    """
    Renderiza markdown determinístico das seções "Distribuição Geográfica"
    e "Bairros Alternativos" usando `bairros_alternativos_pronto`.

    Saída pronta para ser anexada à system instruction do A6 via
    `_a6_before_model_callback`. Garante que o LLM receba os valores
    ja calculados em formato literal — sem chance de inventar status.
    """
    if not isinstance(pronto, dict):
        return ""

    distribuicao = pronto.get("distribuicao_geografica") or []
    alternativos = pronto.get("bairros_alternativos") or []

    linhas: list[str] = []

    # ── Distribuição geográfica ─────────────────────────────────
    linhas.append("## SEÇÃO PRÉ-COMPUTADA — DISTRIBUIÇÃO GEOGRÁFICA")
    linhas.append("")
    linhas.append(
        "Use LITERALMENTE os valores abaixo na seção "
        "'📍 Distribuição Geográfica dos Concorrentes'. "
        "NÃO recalcule, NÃO altere a contagem, NÃO invente."
    )
    linhas.append("")
    if distribuicao:
        linhas.append("| Bairro | Nº academias | Quais |")
        linhas.append("|---|---|---|")
        for d in distribuicao:
            if isinstance(d, dict):
                bairro = _escape_md_pipe(d.get("bairro", "?"))
                count = d.get("count", 0)
                academias = [_escape_md_pipe(a) for a in (d.get("academias", []) or [])]
                linhas.append(f"| {bairro} | {count} | {', '.join(academias)} |")
    else:
        linhas.append("*(distribuicao_geografica vazia — nenhum concorrente analisado)*")
    linhas.append("")

    # ── Bairros alternativos ────────────────────────────────────
    linhas.append("## SEÇÃO PRÉ-COMPUTADA — BAIRROS ALTERNATIVOS")
    linhas.append("")
    linhas.append(
        "Use LITERALMENTE os valores abaixo na seção "
        "'🗺️ Bairros Alternativos Recomendados'. "
        "PROIBIDO inventar status competitivo ou prioridade — esses campos "
        "vêm de cálculo determinístico cruzando o competitive set real."
    )
    linhas.append("")
    if alternativos:
        linhas.append(
            "Status competitivo vem de **busca real por bairro** (raio 2km): "
            "1) **Google Places** (preferencial); 2) **OpenStreetMap** se Maps falhar; "
            "3) **CNPJ RFB** (parque ativo no bairro, Supabase) se Maps+OSM vazios. "
            "Não extrapola só o raio do bairro alvo (fallback A3* = baixa confiança)."
        )
        linhas.append("")
        linhas.append("| Bairro | Motivo | Status competitivo | Ticket sugerido | Prioridade |")
        linhas.append("|---|---|---|---|---|")
        for b in alternativos:
            if not isinstance(b, dict):
                continue
            bairro = _escape_md_pipe(b.get("bairro", "?"))
            motivo = _escape_md_pipe(b.get("motivo", "—"))
            status = _escape_md_pipe(b.get("status", "—"))
            count = b.get("concorrentes_no_bairro", 0)
            ticket = _escape_md_pipe(b.get("ticket_sugerido") or b.get("ticket") or "mid")
            prioridade = _escape_md_pipe(b.get("prioridade_ajustada", b.get("prioridade", "MEDIA")))
            academias = [_escape_md_pipe(a) for a in (b.get("academias_existentes") or [])]
            sufixo = f" ({count} academia{'s' if count != 1 else ''}: {', '.join(academias)})" if academias else f" ({count})"
            linhas.append(
                f"| {bairro} | {motivo} | {status}{sufixo} | {ticket} | {prioridade} |"
            )
        primeiro_alta = next(
            (b for b in alternativos if b.get("prioridade_ajustada") == "ALTA"),
            None,
        )
        if primeiro_alta:
            linhas.append("")
            linhas.append(
                f"**Bairro recomendado para investigação prioritária (PRÉ-CALCULADO):** "
                f"{primeiro_alta.get('bairro')} "
                f"({primeiro_alta.get('concorrentes_no_bairro', 0)} concorrentes mapeados)"
            )
        else:
            linhas.append("")
            linhas.append(
                "**ATENÇÃO**: nenhum bairro alternativo restou com prioridade ALTA — "
                "todos têm concorrentes mapeados. Sinalize isso no relatório e "
                "recomende levantar mais opções regionais."
            )
    else:
        linhas.append("*(bairros_alternativos vazio — pre-computação não retornou dados)*")
    linhas.append("")

    linhas.append(
        "**REGRA INVIOLÁVEL**: ao renderizar essas duas seções no relatório final, "
        "copie o conteúdo das tabelas acima palavra por palavra (incluindo emojis "
        "🔴/🟡/🟢 e prioridades ALTA/MEDIA/BAIXA). O único campo que você pode "
        "AJUSTAR livremente é a justificativa textual de 2-3 linhas após a tabela "
        "de Bairros Alternativos."
    )

    return "\n".join(linhas)


def _renderizar_secao_ofertas_mapeadas(oferta_raw, concorrentes: list) -> str:
    """
    Renderiza markdown das ofertas reais mapeadas via A3c CompetitorMapper.
    Anexado ao system instruction do A6 para que o LLM use os dados reais
    de planos, mensalidades e diferenciais em vez de silêncio/reviews apenas.
    """
    if not oferta_raw or not concorrentes:
        return ""

    import json
    if isinstance(oferta_raw, str):
        txt = oferta_raw.strip()
        if txt.startswith("```"):
            lines = txt.split("\n")
            txt = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
        try:
            oferta_raw = json.loads(txt)
        except Exception:
            logger.warning(
                "A6 oferta_concorrentes JSON inválido em _renderizar_secao_ofertas_mapeadas",
                exc_info=True,
                extra={"agent": "A6", "context": "_renderizar_ofertas_json"},
            )
            return ""

    if not isinstance(oferta_raw, dict):
        return ""

    mapeamento = oferta_raw.get("oferta_concorrentes") or oferta_raw
    if not isinstance(mapeamento, dict):
        return ""

    oferta_lookup = {}
    for k, v in mapeamento.items():
        if isinstance(v, dict):
            if k:
                oferta_lookup[str(k).lower()] = v
            nome_no_oferta = v.get("nome")
            if nome_no_oferta:
                oferta_lookup[str(nome_no_oferta).lower()] = v

    linhas = ["## SEÇÃO PRÉ-COMPUTADA — MENSALIDADES E DIFERENCIAIS REAIS DOS CONCORRENTES"]
    linhas.append("")
    linhas.append(
        "Use as informações de mensalidades, planos e diferenciais abaixo para preencher "
        "o campo 'Serviços oferecidos' e adicionar detalhes de preços em cada card de "
        "concorrente na seção '## 🥊 Inteligência Competitiva — Concorrente por Concorrente'. "
        "Se houver silêncio ou ausência de dados abaixo para um concorrente específico, "
        "use a informação que você possui no estado ou marque como não disponível/—."
    )
    linhas.append("")

    encontrou_algum = False
    for c in concorrentes:
        if not isinstance(c, dict):
            continue
        nome = c.get("nome", "?")
        place_id = c.get("place_id")
        nome_lower = (c.get("nome") or "").lower()

        oferta = None
        if place_id:
            oferta = oferta_lookup.get(str(place_id).lower())
        if not oferta and nome_lower:
            oferta = oferta_lookup.get(nome_lower)

        if oferta:
            encontrou_algum = True
            linhas.append(f"### Concorrente: {nome}")
            
            # Preços
            faixa = oferta.get("faixa_preco_brl")
            precos_str = "Não disponível nos sites/redes sociais"
            if isinstance(faixa, dict):
                p_min = faixa.get("plano_mensal_min")
                p_max = faixa.get("plano_mensal_max")
                if p_min is not None or p_max is not None:
                    p_min_f = float(p_min) if p_min is not None else 0.0
                    p_max_f = float(p_max) if p_max is not None else 0.0
                    if p_min_f == p_max_f and p_min_f > 0:
                        precos_str = f"A partir de R$ {p_min_f:.2f}/mês"
                    elif p_min_f > 0 or p_max_f > 0:
                        p_min_show = p_min_f if p_min_f > 0 else p_max_f
                        p_max_show = p_max_f if p_max_f > 0 else p_min_f
                        if p_min_show == p_max_show:
                            precos_str = f"A partir de R$ {p_min_show:.2f}/mês"
                        else:
                            precos_str = f"De R$ {p_min_show:.2f} a R$ {p_max_show:.2f}/mês"
            
            planos = oferta.get("planos") or []
            planos_list = []
            for pl in planos:
                if isinstance(pl, dict):
                    p_nome = pl.get("nome", "Plano")
                    p_valor = pl.get("preco") or pl.get("valor_brl")
                    if p_valor is not None:
                        try:
                            planos_list.append(f"{p_nome}: R$ {float(p_valor):.2f}/mês")
                        except (ValueError, TypeError):
                            planos_list.append(f"{p_nome}: R$ {p_valor}/mês")
            if planos_list:
                precos_str += f" ({', '.join(planos_list)})"

            linhas.append(f"- **Preços e Planos:** {precos_str}")

            # Modalidades e diferenciais
            modalidades = oferta.get("modalidades") or []
            diferenciais = oferta.get("diferenciais") or []
            
            servicos = []
            if modalidades:
                servicos.append(f"Modalidades: {', '.join(modalidades)}")
            if diferenciais:
                servicos.append(f"Diferenciais: {', '.join(diferenciais)}")
            
            servicos_str = " | ".join(servicos) if servicos else "Não especificado"
            linhas.append(f"- **Serviços Oferecidos:** {servicos_str}")

            obs = oferta.get("observacoes")
            if obs:
                linhas.append(f"- **Observações do Site/IG:** {obs}")
            linhas.append("")

    if not encontrou_algum:
        return ""

    return "\n".join(linhas)


def _renderizar_secao_novos_entrantes(entrantes_block: dict) -> str:
    """
    Renderiza o markdown determinístico da seção de Novos Entrantes com decisores.
    """
    if not isinstance(entrantes_block, dict) or entrantes_block.get("status") != "ok":
        return ""

    entrantes = entrantes_block.get("entrantes") or []
    if not entrantes:
        return ""

    linhas = ["## SEÇÃO PRÉ-COMPUTADA — NOVOS ENTRANTES DE MERCADO (CNPJ)"]
    linhas.append("")
    linhas.append(
        "Use LITERALMENTE a tabela abaixo na seção '## 🏢 Novos Entrantes de Mercado (CNPJ)' "
        "do seu relatório. NÃO altere dados, contatos ou links do LinkedIn."
    )
    linhas.append("")
    linhas.append("| Abertura | Nome Fantasia / Razão Social | Segmento | Bairro | Contato PJ | Decisor / Sócio Administrador | CNPJ |")
    linhas.append("|---|---|---|---|---|---|---|")

    for e in entrantes:
        if not isinstance(e, dict):
            continue

        # Abertura
        abertura = e.get("data_abertura") or "—"
        try:
            dt = datetime.strptime(abertura, "%Y-%m-%d")
            abertura = dt.strftime("%d/%m/%Y")
        except Exception:
            logger.debug(
                "A6 formatação data_abertura skip",
                exc_info=True,
                extra={"agent": "A6", "context": "_renderizar_novos_entrantes_data"},
            )

        # Nome
        nome = e.get("nome_exibicao") or e.get("nome_fantasia") or e.get("razao_social") or "—"

        # Segmento
        segmento = e.get("segmento_label") or e.get("segmento_operacao") or "—"

        # Bairro
        bairro = e.get("bairro") or "—"

        # Contatos PJ
        email_pj = (e.get("email_empresa") or "").strip()
        tel_pj = (e.get("telefone_empresa") or "").strip()
        contatos_pj = []
        if email_pj:
            contatos_pj.append(email_pj)
        if tel_pj:
            contatos_pj.append(tel_pj)
        contato_pj_str = ", ".join(contatos_pj) if contatos_pj else "—"

        # Sócio / Decisor (Apollo)
        socio_str = "—"
        socio_info = e.get("socio_administrador")
        if socio_info and isinstance(socio_info, dict):
            s_nome = (socio_info.get("nome") or "").strip()
            s_cargo = (socio_info.get("qualificacao") or socio_info.get("cargo") or "Sócio-Administrador").strip()
            s_email = (e.get("email_socio_administrador") or "").strip()
            s_linkedin = (e.get("linkedin_url") or "").strip()

            partes_socio = []
            if s_nome:
                partes_socio.append(f"**{s_nome}** ({s_cargo})")
            if s_email:
                partes_socio.append(f"E-mail: {s_email}")
            if s_linkedin:
                partes_socio.append(f"[LinkedIn]({s_linkedin})")

            if partes_socio:
                socio_str = "<br>".join(partes_socio)

        cnpj = e.get("cnpj_formatado") or e.get("cnpj") or "—"

        # Escape markdown pipes
        nome_esc = _escape_md_pipe(nome)
        seg_esc = _escape_md_pipe(segmento)
        bairro_esc = _escape_md_pipe(bairro)
        pj_esc = _escape_md_pipe(contato_pj_str)
        socio_esc = socio_str.replace("|", "/")  # Evita quebrar as colunas do MD

        linhas.append(
            f"| {abertura} | {nome_esc} | {seg_esc} | {bairro_esc} | {pj_esc} | {socio_esc} | {cnpj} |"
        )

    linhas.append("")
    return "\n".join(linhas)


def _renderizar_secao_referencia_aluguel(inner_fin: dict) -> str:
    """
    Markdown determinístico da cascata Tier 1 portais → Tier 2 Grounding
    (+ panorama macro BCB quando portais vazios). Evita silêncio quando N=0.
    """
    if not isinstance(inner_fin, dict):
        return ""

    det = inner_fin.get("aluguel_pesquisa_detalhes") or {}
    tier = det.get("tier")
    if tier is None:
        return ""

    linhas = ["## SEÇÃO PRÉ-COMPUTADA — REFERÊNCIA DE ALUGUEL (A4)"]
    linhas.append("")
    linhas.append(
        "Inclua um bloco visível na seção financeira (antes ou junto de "
        "'⚠️ <aviso_metodologia do A4>') com os fatos abaixo. "
        "NÃO diga que portais 'passaram' se N=0. NÃO use BCB como aluguel local."
    )
    linhas.append("")

    fonte = inner_fin.get("fonte_aluguel") or "—"
    aviso = (inner_fin.get("aviso_metodologia_aluguel") or "").strip()
    linhas.append(f"- **Fonte ativa no modelo:** {fonte}")
    linhas.append(f"- **Tier usado:** {tier}")

    t1 = det.get("tier1_tentativa") or {}
    n_t1 = det.get("n_validos_tier1", t1.get("n_validos", 0))
    linhas.append(f"- **Portais municipais (Tier 1):** N={n_t1} anúncios válidos")
    if det.get("tier1_vazio"):
        linhas.append("  - Status: **sem amostra** (consulta feita, nenhum preço/área parseável)")
    elif not det.get("tier1_suficiente"):
        linhas.append("  - Status: amostra **insuficiente** para mediana confiável")
    if det.get("motivo_tier1"):
        linhas.append(f"  - Motivo: {det['motivo_tier1']}")
    if t1.get("urls_por_portal"):
        urls_txt = ", ".join(f"{p}={n}" for p, n in t1["urls_por_portal"].items())
        linhas.append(f"  - URLs consultadas: {urls_txt}")
    erros = t1.get("erros_portais") or det.get("erros_portais") or []
    if erros:
        linhas.append(f"  - Erros portais (amostra): {'; '.join(str(e)[:80] for e in erros[:3])}")

    if tier == 2:
        med = det.get("mediana_r_m2")
        q = det.get("queries_com_dados", 0)
        linhas.append("")
        linhas.append("### Search Grounding (Tier 2 — referência ativa)")
        if med:
            linhas.append(
                f"- Mediana **R$ {float(med):.0f}/m²** ({q} consulta(s) com dados)"
            )
        faixa = det.get("faixa_rs_m2") or {}
        if isinstance(faixa, dict) and faixa.get("mediana"):
            linhas.append(
                f"- Faixa orientativa: R$ {faixa.get('p25', faixa.get('baixo', '—'))} – "
                f"R$ {faixa.get('p75', faixa.get('alto', '—'))}/m² "
                f"(mediana {faixa.get('mediana')})"
            )
        vals = det.get("valores_coletados") or []
        if vals:
            amostra = ", ".join(f"R$ {v:.0f}" for v in vals[:8])
            linhas.append(f"- Valores extraídos (amostra): {amostra}")

    macro = inner_fin.get("referencia_macro_bcb")
    if isinstance(macro, dict) and macro:
        linhas.append("")
        linhas.append("### Panorama macro BCB (contexto — **não** é aluguel local)")
        linhas.append(
            "_Crédito/financiamento imobiliário nacional; não substitui R$/m² do bairro._"
        )
        if macro.get("ok"):
            linhas.append(f"- {macro.get('norte', '')}")
            dest = macro.get("destaques") or {}
            if isinstance(dest, dict):
                for chave, s in list(dest.items())[:3]:
                    if isinstance(s, dict):
                        linhas.append(
                            f"  - {chave}: {s.get('valor')} ({s.get('data', '—')})"
                        )
        else:
            linhas.append(
                f"- Indisponível: {macro.get('erro') or macro.get('norte', 'erro BCB')}"
            )

    if aviso:
        linhas.append("")
        linhas.append(f"**Aviso metodologia (copiar ou parafrasear):** {aviso}")

    linhas.append("")
    return "\n".join(linhas)


def _a6_before_model_callback(callback_context, llm_request):
    """
    Antes de cada chamada ao modelo do A6, anexa o markdown pré-renderizado
    de Distribuição Geográfica + Bairros Alternativos + Ofertas Reais de Concorrentes + Novos Entrantes à system instruction.
    """
    try:
        state = getattr(callback_context, "state", None)
        if state is None:
            return

        sections_injected = []
        from tools.competitor_tools import _parse_market_context

        # 1. Bairros Alternativos
        pronto = state.get("bairros_alternativos_pronto")
        if pronto:
            markdown_bairros = _renderizar_secao_bairros_alternativos(pronto)
            if markdown_bairros:
                existing_si = ""
                try:
                    existing_si = llm_request.config.system_instruction or ""
                except Exception:
                    logger.debug(
                        "A6 existing_si parse skip",
                        exc_info=True,
                        extra={"agent": "A6", "context": "before_model_bairros_si"},
                    )
                    existing_si = ""
                if "SEÇÃO PRÉ-COMPUTADA — BAIRROS ALTERNATIVOS" not in existing_si:
                    llm_request.append_instructions([markdown_bairros])
                    sections_injected.append("bairros_alternativos")

        # 2. Ofertas Mapeadas
        oferta_raw = state.get("oferta_concorrentes")
        ic_raw = _parse_market_context(state.get("inteligencia_competitiva"))
        inner_ic = ic_raw.get("inteligencia_competitiva") if isinstance(ic_raw.get("inteligencia_competitiva"), dict) else ic_raw
        concorrentes = (inner_ic.get("concorrentes_detalhados") or inner_ic.get("concorrentes") or []) if isinstance(inner_ic, dict) else []

        if oferta_raw and concorrentes:
            markdown_ofertas = _renderizar_secao_ofertas_mapeadas(oferta_raw, concorrentes)
            if markdown_ofertas:
                existing_si = ""
                try:
                    existing_si = llm_request.config.system_instruction or ""
                except Exception:
                    logger.debug(
                        "A6 existing_si parse skip",
                        exc_info=True,
                        extra={"agent": "A6", "context": "before_model_ofertas_si"},
                    )
                    existing_si = ""
                if "SEÇÃO PRÉ-COMPUTADA — MENSALIDADES E DIFERENCIAIS REAIS DOS CONCORRENTES" not in existing_si:
                    llm_request.append_instructions([markdown_ofertas])
                    sections_injected.append("ofertas_mapeadas")

        # 3. Novos Entrantes
        entrantes_block = state.get("entrantes_cnpj_pronto")
        if entrantes_block:
            markdown_entrantes = _renderizar_secao_novos_entrantes(entrantes_block)
            if markdown_entrantes:
                existing_si = ""
                try:
                    existing_si = llm_request.config.system_instruction or ""
                except Exception:
                    logger.debug(
                        "A6 existing_si parse skip",
                        exc_info=True,
                        extra={"agent": "A6", "context": "before_model_entrantes_si"},
                    )
                    existing_si = ""
                if "SEÇÃO PRÉ-COMPUTADA — NOVOS ENTRANTES DE MERCADO" not in existing_si:
                    llm_request.append_instructions([markdown_entrantes])
                    sections_injected.append("novos_entrantes")

        # 4. Referência de aluguel (Tier 1 portais / Tier 2 Grounding / macro BCB)
        fin_raw = _parse_market_context(state.get("analise_financeira"))
        inner_fin_aluguel = (
            fin_raw.get("analise_financeira")
            if isinstance(fin_raw.get("analise_financeira"), dict)
            else fin_raw
        )
        if isinstance(inner_fin_aluguel, dict):
            markdown_aluguel = _renderizar_secao_referencia_aluguel(inner_fin_aluguel)
            if markdown_aluguel:
                existing_si = ""
                try:
                    existing_si = llm_request.config.system_instruction or ""
                except Exception:
                    logger.debug(
                        "A6 existing_si parse skip",
                        exc_info=True,
                        extra={"agent": "A6", "context": "before_model_aluguel_si"},
                    )
                    existing_si = ""
                if "SEÇÃO PRÉ-COMPUTADA — REFERÊNCIA DE ALUGUEL" not in existing_si:
                    llm_request.append_instructions([markdown_aluguel])
                    sections_injected.append("referencia_aluguel")

        if sections_injected:
            logger.info(
                "A6 before_model injected %d sections: %s",
                len(sections_injected),
                ", ".join(sections_injected),
                extra={"agent": "A6"},
            )

    except Exception:
        logger.error(
            "A6 before_model_callback falhou — LLM gerará relatório SEM seções pré-computadas (ALTO RISCO DE ALUCINAÇÃO)",
            exc_info=True,
            extra={"agent": "A6"},
        )


# ── Saída estruturada para o CRUD futuro (VEC-379 fase 1C) ───────────
# Em paralelo ao markdown que o LLM emite, o A6 grava um JSON canônico
# em metrics/relatorios/<run_id>.json com input + output consolidado +
# metadata. Esse JSON é o "source of truth" que vai alimentar o banco
# do CRUD planejado (CRUD substituirá o prompt livre por formulário).

_RELATORIOS_DIR = Path(__file__).resolve().parent.parent / "metrics" / "relatorios"


def _safe_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _rank_candidatos_for_top3(candidatos: list) -> list:
    """Prioriza listings OLX/ImovelWeb antes do slice top 3."""

    def sort_key(c: dict) -> tuple:
        is_listing = (
            c.get("fonte") == "listing"
            or c.get("qualidade_sinal") == "direto-listing"
            or str(c.get("place_id") or "").startswith("listing_")
        )
        return (1 if is_listing else 0, _safe_float(c.get("score_geoscout")))

    valid = [c for c in candidatos if isinstance(c, dict)]
    return sorted(valid, key=sort_key, reverse=True)


def _enriquecer_candidato_investigacao(c: dict) -> dict:
    """Expõe resumo da investigação web (A1) no candidato do relatório."""
    out = dict(c)
    ir = c.get("investigacao_resultado")
    if not isinstance(ir, dict):
        return out
    res = ir.get("resultado")
    if not isinstance(res, dict):
        return out
    tipo_inf = c.get("tipo_imovel_inferido") if isinstance(c.get("tipo_imovel_inferido"), dict) else {}
    out["investigacao_site"] = {
        "status_operacao": res.get("status_operacao"),
        "operador_atual": res.get("operador_atual"),
        "segmento": res.get("segmento"),
        "confianca": res.get("confianca"),
        "coerencia_listing": res.get("coerencia_listing"),
        "implicacao_site": res.get("implicacao_site"),
        "evidencias": (res.get("evidencias") or [])[:3],
        "tier": ir.get("tier"),
        "tipo_imovel_label": tipo_inf.get("tipo_imovel_label"),  # pyright: ignore[reportOptionalMemberAccess]
        "tipo_imovel_codigo_onr": tipo_inf.get("tipo_imovel_codigo_onr"),  # pyright: ignore[reportOptionalMemberAccess]
    }
    return out


def _navegar_aninhado(d, *chaves, default=None):
    """Acessa d[k1][k2][...] retornando default se algo for None/missing."""
    cur = d
    for k in chaves:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _lista_candidatos_geoscout(geo_raw: dict) -> list[dict]:
    """Candidatos A1 — chaves alternativas quando o LLM não copia `candidatos`."""
    if not isinstance(geo_raw, dict):
        return []
    for key in ("candidatos", "candidatos_filtrados", "top_candidatos"):
        raw = geo_raw.get(key)
        if isinstance(raw, list) and raw:
            return [c for c in raw if isinstance(c, dict)]
    return []


def _envelope_concorrentes_brutos(cs_raw: Any) -> tuple[dict, list[dict]]:
    """Extrai envelope A3a + lista de concorrentes do session state."""
    from tools.competitor_tools import _parse_market_context

    envelope: dict = {}
    lista: list[dict] = []
    if isinstance(cs_raw, list):
        return envelope, [c for c in cs_raw if isinstance(c, dict)]
    if isinstance(cs_raw, dict):
        nested = cs_raw.get("concorrentes_brutos")
        if isinstance(nested, list):
            lista = [c for c in nested if isinstance(c, dict)]
            envelope = {k: v for k, v in cs_raw.items() if k != "concorrentes_brutos"}
        elif isinstance(nested, dict):
            envelope = nested
            inner_list = nested.get("concorrentes") or nested.get("concorrentes_brutos")
            if isinstance(inner_list, list):
                lista = [c for c in inner_list if isinstance(c, dict)]
        else:
            envelope = cs_raw
            raw_list = cs_raw.get("concorrentes_brutos") or cs_raw.get("concorrentes")
            if isinstance(raw_list, list):
                lista = [c for c in raw_list if isinstance(c, dict)]
        return envelope, lista

    parsed = _parse_market_context(cs_raw)
    if isinstance(parsed, dict):
        envelope = parsed
        inner = parsed.get("concorrentes_brutos")
        if isinstance(inner, list):
            lista = [c for c in inner if isinstance(c, dict)]
        elif isinstance(inner, dict):
            envelope = inner
            inner_list = inner.get("concorrentes") or inner.get("concorrentes_brutos")
            if isinstance(inner_list, list):
                lista = [c for c in inner_list if isinstance(c, dict)]
        else:
            raw_list = parsed.get("concorrentes") or parsed.get("concorrentes_brutos")
            if isinstance(raw_list, list):
                lista = [c for c in raw_list if isinstance(c, dict)]
    elif isinstance(parsed, list):
        lista = [c for c in parsed if isinstance(c, dict)]
    return envelope, lista


def _bruto_para_detalhado(c: dict) -> dict:
    """Normaliza item A3a para o formato de `concorrentes_detalhados` / Supabase."""
    out = dict(c)
    if out.get("rating_geral") is not None and out.get("rating_oficial") is None:
        out["rating_oficial"] = out["rating_geral"]
    if out.get("reviews") and not out.get("reviews_traduzidas"):
        out["reviews_traduzidas"] = out["reviews"]
    return out


def _resolver_competitividade_extracao(
    *,
    ic_raw: dict,
    inner_ic: dict,
    cs_raw: Any,
) -> dict[str, Any]:
    """
    Une A3b (detalhados) com fallback A3a (concorrentes_brutos).
    Recalcula score_concorrencia quando há lista mas score ausente no state.
    """
    from tools.competitor_tools import calcular_score_concorrencia, classificar_saturacao

    if not isinstance(ic_raw, dict):
        ic_raw = {}
    if not isinstance(inner_ic, dict):
        inner_ic = {}

    # A3b às vezes grava só em inteligencia_competitiva aninhado com inner_ic vazio
    if not inner_ic.get("concorrentes_detalhados"):
        nested = ic_raw.get("inteligencia_competitiva")
        if isinstance(nested, dict):
            inner_ic = nested

    detalhados = [
        c
        for c in (
            inner_ic.get("concorrentes_detalhados")
            or ic_raw.get("concorrentes_detalhados")
            or inner_ic.get("concorrentes")
            or []
        )
        if isinstance(c, dict)
    ]
    fonte_fallback: str | None = None
    envelope, brutos = _envelope_concorrentes_brutos(cs_raw)

    if not detalhados and brutos:
        detalhados = [_bruto_para_detalhado(c) for c in brutos]
        fonte_fallback = "concorrentes_brutos_a3a"
        logger.info(
            "A6 fallback concorrentes: %d itens de concorrentes_brutos (A3a)",
            len(detalhados),
            extra={"agent": "A6", "context": "competitividade_fallback"},
        )

    score_conc = ic_raw.get("score_concorrencia") or inner_ic.get("score_concorrencia")
    nivel_sat = (
        ic_raw.get("nivel_saturacao")
        or inner_ic.get("nivel_saturacao")
        or ""
    )
    rating_medio = ic_raw.get("rating_medio_concorrentes") or inner_ic.get(
        "rating_medio_concorrentes"
    )

    # Modo âncora bairro: o score/saturação do A3b podem ter vindo do raio-3km
    # (ex.: 211 academias → SATURADO → score 0.0), contradizendo a saturação do
    # bairro (10 concorrentes → MEDIO). Recomputa AMBOS do set analisado (bairro)
    # pra serem COERENTES entre si — senão o resumo executivo narra "extrema
    # saturação" a partir do score 0.0 enquanto a saturação estruturada diz MEDIO.
    if os.getenv("CONCORRENTES_SOURCE", "").strip().lower() == "parque" and detalhados:
        _num = len(detalhados)
        _ratings = [
            _safe_float(c.get("rating_geral") or c.get("rating_oficial"))
            for c in detalhados
        ]
        _rok = [r for r in _ratings if r and r > 0]
        _rmed = round(sum(_rok) / len(_rok), 2) if _rok else (_safe_float(rating_medio) or 0.0)
        nivel_sat = classificar_saturacao(_num, 3.0)
        score_conc = calcular_score_concorrencia(_num, _rmed, nivel_sat)
        rating_medio = _rmed
    total_analisados = (
        ic_raw.get("total_concorrentes_analisados")
        or inner_ic.get("total_concorrentes_analisados")
        or len(detalhados)
    )
    agregados = (
        envelope.get("agregados_competicao_places")
        if isinstance(envelope, dict)
        else {}
    )
    total_raio = (
        ic_raw.get("total_encontrados_raio")
        or inner_ic.get("total_encontrados_raio")
        or envelope.get("total_encontrados_raio")
        or envelope.get("total_encontrados")
        or (
            agregados.get("count_total")
            if isinstance(agregados, dict)
            else None
        )
    )

    if detalhados and score_conc is None:
        ratings = [
            _safe_float(c.get("rating_geral") or c.get("rating_oficial"))
            for c in detalhados
        ]
        ratings_ok = [r for r in ratings if r is not None and r > 0]
        rating_medio_calc = (
            round(sum(ratings_ok) / len(ratings_ok), 2) if ratings_ok else 0.0
        )
        rating_medio = rating_medio if rating_medio is not None else rating_medio_calc
        num = len(detalhados)
        if not nivel_sat:
            nivel_sat = classificar_saturacao(num, 3.0)
        score_conc = calcular_score_concorrencia(
            num, _safe_float(rating_medio) or 0.0, nivel_sat
        )
        if not total_analisados:
            total_analisados = num
        logger.info(
            "A6 score_concorrencia recalculado: %.2f (%d concorrentes)",
            score_conc,
            num,
            extra={"agent": "A6"},
        )

    return {
        "concorrentes_detalhados": detalhados,
        "score_concorrencia": score_conc,
        "nivel_saturacao": nivel_sat,
        "rating_medio_concorrentes": rating_medio,
        "total_concorrentes_analisados": total_analisados,
        "total_encontrados_raio": total_raio,
        "total_encontrados_raio_nearby": envelope.get("total_encontrados_nearby")
        if isinstance(envelope, dict)
        else None,
        "agregados_competicao_places": agregados if isinstance(agregados, dict) else {},
        "fonte_geocode": envelope.get("fonte_geocode") if isinstance(envelope, dict) else None,
        "fonte_busca_competidores": envelope.get("fonte_busca_competidores")
        if isinstance(envelope, dict)
        else None,
        "envelope_a3a": envelope,
        "fonte_fallback": fonte_fallback,
        "dores_dominantes": inner_ic.get("dores_dominantes") or ic_raw.get("dores_dominantes") or [],
        "servicos_nao_oferecidos": inner_ic.get("servicos_nao_oferecidos")
        or ic_raw.get("servicos_nao_oferecidos")
        or [],
        "panorama_competitivo": ic_raw.get("panorama_competitivo")
        or inner_ic.get("panorama_competitivo"),
        "top_independentes": ic_raw.get("top_independentes")
        or inner_ic.get("top_independentes")
        or envelope.get("top_independentes")
        or [],
        "academias_analisadas": ic_raw.get("academias_analisadas")
        or inner_ic.get("academias_analisadas")
        or envelope.get("academias_analisadas")
        or [],
    }


def _alinhar_markdown_ao_estruturado(md: str, out: dict) -> str:
    """Ajusta veredito/scores no markdown para bater com output_consolidado (pós-guards)."""
    if not md or not isinstance(out, dict):
        return md
    veredito = out.get("veredito")
    sb = out.get("score_bairro")
    st = out.get("score_top1_candidato")
    sc = out.get("score_concorrencia")

    if veredito:
        md = re.sub(
            r"(\*\*⚠️\s*)(APROVADO(?: COM RESSALVAS)?|INVESTIGAR MAIS|REPROVADO)(\*?\*\*\.?)",
            lambda m: f"{m.group(1)}{veredito}{m.group(3)}",
            md,
            count=1,
        )
        md = re.sub(
            r"(## 📌 Decisão Recomendada\s*\n\*\*)([^*]+)(\*\*)",
            lambda m: f"{m.group(1)}{veredito}{m.group(3)}",
            md,
            count=1,
        )
    if sb is not None:
        md = re.sub(
            r"(\*\*Score Bairro:\*\*)\s*[\d\.,]+",
            rf"\1 {sb}",
            md,
            count=1,
        )
    if st is not None:
        md = re.sub(
            r"(\*\*Score Top 1 Candidato:\*\*)\s*[\d\.,]+",
            rf"\1 {st}",
            md,
            count=1,
        )
    if sc is not None:
        md = re.sub(
            r"(\| Competitivo \| )\s*[\d\.,]+",
            rf"\1 {sc} ",
            md,
            count=1,
        )
    return md


def _extrair_relatorio_estruturado(callback_context) -> dict:
    """
    Constrói o JSON canônico do relatório lendo todos os outputs do state.

    Schema:
    {
      "id": "rpt_<unix_ts>",
      "tipo_relatorio": "prospeccao_academia",
      "data_execucao": "ISO 8601",
      "input_canonico": {cidade, uf, bairro, area_m2_min, ...},
      "output_consolidado": {scores, candidatos, competitors, financeiro, ...},
      "metadata_execucao": {fonte, cached, ...}
    }
    """
    from tools.competitor_tools import _parse_market_context

    state = getattr(callback_context, "state", {}) or {}

    # Mapeamento de ofertas (para enriquecer o competitors_set do JSON canônico)
    oferta_raw = state.get("oferta_concorrentes")
    if isinstance(oferta_raw, str):
        txt = oferta_raw.strip()
        if txt.startswith("```"):
            lines = txt.split("\n")
            txt = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
        try:
            import json
            oferta_raw = json.loads(txt)
        except Exception:
            logger.warning(
                "A6 oferta_concorrentes JSON inválido em _extrair_relatorio_estruturado",
                exc_info=True,
                extra={"agent": "A6", "context": "_extrair_oferta_json"},
            )
            oferta_raw = None

    mapeamento_ofertas = {}
    if isinstance(oferta_raw, dict):
        mapeamento = oferta_raw.get("oferta_concorrentes") or oferta_raw
        if isinstance(mapeamento, dict):
            for k, v in mapeamento.items():
                if isinstance(v, dict):
                    if k:
                        mapeamento_ofertas[str(k).lower()] = v
                    nome_no_oferta = v.get("nome")
                    if nome_no_oferta:
                        mapeamento_ofertas[str(nome_no_oferta).lower()] = v

    # ── Input canônico (vem do market_context A0 + defaults do pipeline) ──
    raw_mc = state.get("market_context")
    mc = _parse_market_context(raw_mc)
    inner_mc = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
    if not isinstance(inner_mc, dict):
        inner_mc = {}

    cidade = inner_mc.get("cidade", "")
    bairro = inner_mc.get("bairro", "")

    # Diagnóstico defensivo: se inner_mc veio vazio mas state.market_context
    # tem conteúdo, é bug de propagação A0→A6. Logamos pra debug + tenta um
    # parsing mais agressivo (recursivo) antes de desistir.
    if not inner_mc and raw_mc:
        try:
            preview = (
                raw_mc[:200] if isinstance(raw_mc, str)
                else str(raw_mc)[:200]
            )
            tipo = type(raw_mc).__name__
            logger.warning(
                "A6 inner_mc VAZIO mas state.market_context tem conteúdo",
                extra={
                    "agent": "A6",
                    "raw_type": tipo,
                    "preview": preview[:200] if preview else "",
                },
            )
            # Fallback 2: se mc tem chaves mas não 'market_context', tenta usar mc direto
            if isinstance(mc, dict) and mc:
                # mc pode ter campos achatados (sem aninhamento)
                if any(k in mc for k in ("cidade", "ticket_medio_mercado", "principais_redes_concorrentes")):
                    inner_mc = mc
                    cidade = inner_mc.get("cidade", "")
                    bairro = inner_mc.get("bairro", "")
                    logger.info(
                        "A6 inner_mc recuperado via fallback flat",
                        extra={"agent": "A6", "keys": list(mc.keys())[:10]},
                    )
        except Exception:
            logger.warning(
                "A6 diagnostic fallback falhou",
                exc_info=True,
                extra={"agent": "A6"},
            )

    # ── Output: análise competitiva (A3b) ──
    ic_raw = _parse_market_context(state.get("inteligencia_competitiva"))
    inner_ic = ic_raw.get("inteligencia_competitiva") if isinstance(
        ic_raw.get("inteligencia_competitiva"), dict
    ) else ic_raw
    if not isinstance(inner_ic, dict):
        inner_ic = {}

    # ── Output: busca bruta competitiva (A3a) ──
    # Carrega metadados de cobertura A0 (redes solicitadas pelo Deep Research
    # vs cobertas pela busca real) + concorrentes excluídos do Top 5.
    # Plugado em 2026-05-11 após fix geo-fence (#89): quando o DR pede uma rede
    # que não tem unidade local no raio alvo, A3a marca em redes_a0_nao_encontradas.
    cs_raw = _parse_market_context(state.get("concorrentes_brutos"))
    comp = _resolver_competitividade_extracao(
        ic_raw=ic_raw if isinstance(ic_raw, dict) else {},
        inner_ic=inner_ic,
        cs_raw=cs_raw,
    )
    if comp.get("fonte_fallback"):
        inner_ic = {**inner_ic, "concorrentes_detalhados": comp["concorrentes_detalhados"]}

    cobertura_redes_a0 = _build_cobertura_redes_a0(cs_raw, inner_mc, inner_ic)
    slim_market_context = _slim_market_context(inner_mc)
    slim_market_context = _apply_redes_validadas_market_context(
        slim_market_context, cobertura_redes_a0
    )

    score_concorrencia = comp.get("score_concorrencia")
    nivel_saturacao = comp.get("nivel_saturacao") or ""

    # ── Output: candidatos GeoScout (A1) ──
    # Preferir o snapshot determinístico do after_tool_callback do A1: o LLM
    # truncava o array `candidatos` ao copiar o JSON (run b5b0e627, 14→0).
    geo_raw = state.get("candidatos_geoscout_pronto")
    if not (isinstance(geo_raw, dict) and geo_raw.get("candidatos")):
        geo_raw = _parse_market_context(state.get("candidatos_geoscout"))
    if not isinstance(geo_raw, dict):
        geo_raw = {}
    candidatos = _lista_candidatos_geoscout(geo_raw)
    ranked = _rank_candidatos_for_top3(candidatos)  # pyright: ignore[reportArgumentType]
    top_3 = [_enriquecer_candidato_investigacao(c) for c in (ranked[:3] if ranked else [])]
    investigacoes_resumo = (
        geo_raw.get("investigacoes_imoveis")
        if isinstance(geo_raw.get("investigacoes_imoveis"), dict)
        else {}
    )

    # ── Output: análise demográfica (A2) ──
    demo = _parse_market_context(state.get("analise_demografica"))
    score_demografico = demo.get("score_demografico") if isinstance(demo, dict) else None

    # ── Output: análise financeira (A4) ──
    fin_raw = _parse_market_context(state.get("analise_financeira"))
    inner_fin = fin_raw.get("analise_financeira") if isinstance(
        fin_raw.get("analise_financeira"), dict
    ) else fin_raw
    if not isinstance(inner_fin, dict):
        inner_fin = {}

    # ── Output: contato decisor (A5) ──
    contato_raw = _parse_market_context(state.get("contato_decisor"))
    contato = contato_raw if isinstance(contato_raw, dict) else {}

    # ── Bairros alternativos (computado no callback) ──
    bap = state.get("bairros_alternativos_pronto") or {}
    if not isinstance(bap, dict):
        bap = {}

    entrantes_block = state.get("entrantes_cnpj_pronto") or {}
    if not isinstance(entrantes_block, dict) or entrantes_block.get("status") != "ok":
        try:
            from tools.cnpj_fitness_tools import listar_entrantes_cnpj_fitness

            cidade_efetiva, _ = resolver_cidade_efetiva(cidade, bairro)
            uf_mc = (inner_mc.get("uf") or "") if isinstance(inner_mc, dict) else ""
            entrantes_block = listar_entrantes_cnpj_fitness(
                cidade_efetiva, uf_mc, dias=90, limit=50
            )
        except Exception:
            logger.warning(
                "A6 entrantes_cnpj fallback falhou — seção CNPJ pode ficar vazia",
                exc_info=True,
                extra={"agent": "A6", "context": "entrantes_cnpj_fallback"},
            )
            entrantes_block = {}

    # Demanda futura datada (CNO grande porte + refino A4) — injetada no state pelo api.py.
    demanda_futura_block = state.get("demanda_futura") or {}

    # Demografia do BAIRRO (renda CKAN + população/ocupação Censo 2022) — fontes reais,
    # determinístico (sem LLM). Persistido + renderizado em mini-cards na UI.
    demografia_bairro_block: dict = {}
    try:
        from tools.demografia_bairro_tools import demografia_bairro as _demo_bairro

        _idm = str((inner_mc.get("codigo_ibge") or "") if isinstance(inner_mc, dict) else "") or None
        demografia_bairro_block = _demo_bairro(
            cidade_efetiva, uf_mc, _bairro_alvo_da_busca(state), id_municipio=_idm
        )
    except Exception:
        logger.warning("A6 demografia_bairro falhou", exc_info=True, extra={"agent": "A6"})

    obras_cno_block = state.get("obras_cno_pronto") or {}
    if not isinstance(obras_cno_block, dict) or obras_cno_block.get("status") not in (
        "ok",
        "nao_configurado",
    ):
        try:
            obras_cno_block = _precompute_obras_cno(type("Ctx", (), {"state": state})())
        except Exception:
            logger.warning(
                "A6 obras_cno fallback falhou — seção obras pode ficar vazia",
                exc_info=True,
                extra={"agent": "A6", "context": "obras_cno_fallback"},
            )
            obras_cno_block = {}

    # Fallback: A0 pode ter embutido obras no fatos_parque_cnpj
    if (
        (not obras_cno_block or obras_cno_block.get("status") != "ok")
        and isinstance(inner_mc, dict)
    ):
        fatos = inner_mc.get("fatos_parque_cnpj") or {}
        cno_mc = (fatos.get("cruzamento_cno") or {}) if isinstance(fatos, dict) else {}
        emb = cno_mc.get("obras_fitness_em_curso")
        if isinstance(emb, dict) and emb.get("status") == "ok":
            try:
                from tools.cno_fitness_tools import slim_obras_para_relatorio

                bench_emb = cno_mc.get("benchmark_tempo_obra_cno")
                obras_cno_block = slim_obras_para_relatorio(
                    emb,
                    benchmark_tempo=bench_emb if isinstance(bench_emb, dict) else None,
                )
            except Exception:
                logger.error(
                    "A6 slim_obras_para_relatorio (embedded CNO) falhou",
                    exc_info=True,
                    extra={"agent": "A6", "context": "obras_cno_slim_embedded"},
                )

    # ── distribuicao_geografica: tenta 3 fontes em ordem ──
    # 1. bairros_alternativos_pronto (computado no _a6_precompute_callback)
    # 2. inteligencia_competitiva (top-level — emitido pelo A3b se instruction OK)
    # 3. inteligencia_competitiva.inteligencia_competitiva (aninhado, fallback)
    distribuicao_geo = (
        bap.get("distribuicao_geografica")
        or ic_raw.get("distribuicao_geografica")
        or inner_ic.get("distribuicao_geografica")
        or []
    )

    # ── Dois scores distintos (decisão arquitetural VEC-Task #54) ──
    # score_bairro: 3 dim regionais — responde "vale investir nessa região?"
    #   Não depende de imóvel específico; útil pra decisão macro.
    # score_top1_candidato: 4 dim (3 regionais + geoscout do candidato #1).
    #   Responde "qual o ranking real do melhor imóvel candidato?"
    #   Usado pra veredito porque é o que reflete a recomendação prática.
    score_viab = inner_fin.get("score_viabilidade")

    scores_bairro_disp = [
        s for s in [score_demografico, score_concorrencia, score_viab]
        if s is not None
    ]
    score_bairro = (
        round(sum(_safe_float(s) for s in scores_bairro_disp) / len(scores_bairro_disp), 2)
        if scores_bairro_disp else None
    )

    top1_geoscout = (
        _safe_float(top_3[0].get("score_geoscout"))
        if top_3 and isinstance(top_3[0], dict) and top_3[0].get("score_geoscout") is not None
        else None
    )
    scores_top1_disp = [
        s for s in [top1_geoscout, score_demografico, score_concorrencia, score_viab]
        if s is not None
    ]
    score_top1_candidato = (
        round(sum(_safe_float(s) for s in scores_top1_disp) / len(scores_top1_disp), 2)
        if scores_top1_disp else None
    )

    # ── Veredito heurístico baseado no TOP 1 (decisão prática) ──
    # Fallback pro score_bairro se top1 não disponível (sem candidatos GeoScout).
    veredito = "REPROVADO"
    score_decisao = score_top1_candidato if score_top1_candidato is not None else score_bairro
    if score_decisao is not None:
        if score_decisao >= 8.0:
            veredito = "APROVADO"
        elif score_decisao >= 6.0:
            veredito = "APROVADO COM RESSALVAS"
        elif score_decisao >= 4.0:
            veredito = "INVESTIGAR MAIS"

    # ── Guard determinístico: 0 concorrentes (P1) ──
    # Só dispara se A3b E A3a (fallback) estiverem vazios — evita falso
    # INVESTIGAR MAIS quando concorrentes_brutos existe no state.
    concorrentes_detalhados = comp.get("concorrentes_detalhados") or []
    # Anéis competitivos (Apêndice D) — enriquece cada concorrente com anel/porte/
    # multiesporte e calcula score PONDERADO (NO_BAIRRO 1.0 / FRONTEIRA 0.5 / REGIONAL
    # 0.2). Corrige score puxado pelo vizinho. Centroide = média dos candidatos geocodados.
    aneis_competitivos_resumo: dict = {}
    try:
        from tools.aneis_competitivos_tools import (
            enriquecer_competidores_aneis,
            resumo_aneis,
        )

        _xy = [
            (_safe_float(c.get("lat")), _safe_float(c.get("lng")))
            for c in candidatos
            if isinstance(c, dict) and c.get("lat") and c.get("lng")
        ]
        _xy = [(a, b) for a, b in _xy if a is not None and b is not None]
        _clat = sum(a for a, _ in _xy) / len(_xy) if _xy else None
        _clng = sum(b for _, b in _xy) / len(_xy) if _xy else None
        concorrentes_detalhados = enriquecer_competidores_aneis(
            concorrentes_detalhados, bairro, _clat, _clng
        )
        aneis_competitivos_resumo = resumo_aneis(concorrentes_detalhados)
    except Exception:
        logger.warning(
            "A6 anéis competitivos falhou — segue sem ponderação",
            exc_info=True,
            extra={"agent": "A6", "context": "aneis_competitivos"},
        )

    total_concorrentes = (
        comp.get("total_concorrentes_analisados")
        or len(concorrentes_detalhados)
    )
    alertas_financeiros = list(inner_fin.get("alertas", []) or [])
    sem_concorrentes = (not concorrentes_detalhados) and _safe_float(total_concorrentes) == 0
    if sem_concorrentes:
        if veredito in ("APROVADO", "APROVADO COM RESSALVAS"):
            veredito = "INVESTIGAR MAIS"
        nivel_saturacao = "indeterminado (0 concorrentes)"
        alerta_zero_conc = (
            "0 concorrentes identificados - análise baseada apenas em benchmark "
            "teórico; revisar geocode/raio do bairro antes de decidir."
        )
        if alerta_zero_conc not in alertas_financeiros:
            alertas_financeiros.append(alerta_zero_conc)

    # ── Guard financeiro: ticket Premium fora da banda local ──
    modelo_recomendado = (inner_fin.get("recomendacao_modelo") or "").strip()
    cenarios = inner_fin.get("cenarios") or {}
    ticket_recomendado = None
    if isinstance(cenarios, dict) and modelo_recomendado:
        modelo_norm = modelo_recomendado.lower()
        for c in cenarios.values():
            if not isinstance(c, dict):
                continue
            modelo_c = (c.get("modelo") or "").strip()
            if modelo_c and modelo_c.lower() == modelo_norm:
                ticket_recomendado = _safe_float(c.get("ticket_medio"))
                break

    renda_local = _safe_float(
        (slim_market_context.get("renda_media_bairro") if isinstance(slim_market_context, dict) else None)
        or (inner_mc.get("renda_media_bairro") if isinstance(inner_mc, dict) else None)
    )
    is_premium = "premium" in modelo_recomendado.lower()
    if is_premium and ticket_recomendado:
        outlier_ticket = False
        if ticket_recomendado >= 750:
            outlier_ticket = True
        if renda_local and ticket_recomendado >= renda_local * 0.5:
            outlier_ticket = True
        if outlier_ticket:
            alerta_ticket = (
                f"ticket Premium R${int(ticket_recomendado)} destoa da renda local/tier de mercado; "
                "revisar cenário financeiro."
            )
            if alerta_ticket not in alertas_financeiros:
                alertas_financeiros.append(alerta_ticket)
            if veredito == "APROVADO":
                veredito = "APROVADO COM RESSALVAS"

    return {
        "id": f"rpt_{int(time.time())}",
        "tipo_relatorio": "prospeccao_academia",
        "data_execucao": datetime.now().isoformat(timespec="seconds"),
        "input_canonico": {
            "cidade": cidade,
            "bairro": bairro,
            "area_m2_min": 1000,
            "area_m2_max": 1500,
            "publico_alvo": "25-40",
            # Schema v1.4: replica genero_alvo do market_context (A0) pra
            # permitir re-execução determinística e auditoria. Default "misto"
            # preserva comportamento pré-v1.4 quando o A0 não emitiu o campo.
            "genero_alvo": inner_mc.get("genero_alvo") or "misto",
            # Schema v1.5: tamanho preset (pp|p|m|g|gg) — informado pelo form
            # via market_context. Calibra CAPEX/custos no A4 e posicionamento
            # no A6 markdown. Default "m" (mais comum no mercado fitness BR).
            "tamanho_preset": inner_mc.get("tamanho_preset") or "m",
            "estacionamento_obrigatorio": True,
            "tipo_negocio": inner_mc.get("tipo_negocio") or "academia",
        },
        "output_consolidado": {
            "veredito": veredito,
            # Dois scores distintos — schema 1.1.
            # score_bairro: indicador macro (3 dim regionais)
            # score_top1_candidato: ranking prático do melhor imóvel (4 dim)
            "score_bairro": score_bairro,
            "score_top1_candidato": score_top1_candidato,
            "score_concorrencia": _safe_float(score_concorrencia),
            "scores_regionais": {
                "demografico": _safe_float(score_demografico),
                "competitivo": _safe_float(score_concorrencia),
                "viabilidade": _safe_float(score_viab),
            },
            "nivel_saturacao": nivel_saturacao,
            "panorama_competitivo": comp.get("panorama_competitivo"),
            "total_encontrados_raio": comp.get("total_encontrados_raio"),
            "total_encontrados_raio_nearby": comp.get("total_encontrados_raio_nearby"),
            "agregados_competicao_places": comp.get("agregados_competicao_places") or {},
            "fonte_geocode": comp.get("fonte_geocode"),
            "fonte_busca_competidores": comp.get("fonte_busca_competidores"),
            "total_concorrentes_analisados": total_concorrentes,
            "top_independentes": comp.get("top_independentes") or [],
            "academias_analisadas": comp.get("academias_analisadas") or [],
            "rating_medio_concorrentes": _safe_float(
                comp.get("rating_medio_concorrentes")
            ),
            "top_3_candidatos": top_3,
            "investigacoes_imoveis": investigacoes_resumo,
            # Diagnóstico GeoScout (A1) — UI usa pra banner sem hardcode REQUEST_DENIED
            "coleta_geografica": {
                "total_candidatos": geo_raw.get("total_candidatos", len(candidatos)),  # pyright: ignore[reportArgumentType]
                "listings_reais": geo_raw.get("listings_reais"),
                "estrategia": geo_raw.get("estrategia"),
                "qualidade_sinal": geo_raw.get("qualidade_sinal"),
                "aviso": geo_raw.get("aviso"),
                "erro": geo_raw.get("erro"),
            },
            "competitors_set": [
                {
                    **c,
                    "oferta_mapeada": (
                        mapeamento_ofertas.get(str(c.get("place_id")).lower())
                        or mapeamento_ofertas.get((c.get("nome") or "").lower())
                    ) if isinstance(c, dict) else None
                }
                for c in concorrentes_detalhados
                if isinstance(c, dict)
            ],
            "dores_dominantes": comp.get("dores_dominantes") or [],
            "servicos_nao_oferecidos": comp.get("servicos_nao_oferecidos") or [],
            "distribuicao_geografica": distribuicao_geo,
            "bairros_alternativos": bap.get("bairros_alternativos", []),
            # Schema v1.5: aviso geográfico quando A6 detectou que o
            # `bairro` informado é na verdade um município da RM da `cidade`
            # (caso Eusébio dentro de Fortaleza). cidade_efetiva é o município
            # alvo real usado pra derivar bairros alternativos.
            "aviso_geografico": bap.get("aviso_geografico"),
            "cidade_efetiva": bap.get("cidade_efetiva"),
            "cidade_foi_corrigida": bool(bap.get("cidade_foi_corrigida")),
            "viabilidade_3_cenarios": inner_fin.get("cenarios", {}),
            "modelo_recomendado": inner_fin.get("recomendacao_modelo"),
            "aluguel_mensal": _safe_float(inner_fin.get("aluguel_mensal")),
            "aluguel_municipio_referencia": inner_fin.get("aluguel_municipio_referencia"),
            "aluguel_pesquisa_detalhes": inner_fin.get("aluguel_pesquisa_detalhes"),
            "referencia_macro_bcb": inner_fin.get("referencia_macro_bcb"),
            "tier_aluguel": (inner_fin.get("aluguel_pesquisa_detalhes") or {}).get("tier"),
            "fonte_aluguel": inner_fin.get("fonte_aluguel"),
            "aviso_metodologia_aluguel": inner_fin.get("aviso_metodologia_aluguel"),
            "alertas_financeiros": alertas_financeiros,
            "posicionamento_recomendado": (
                ic_raw.get("posicionamento_recomendado")
                or inner_ic.get("posicionamento_recomendado", "")
            ),
            "contato_decisor": contato,
            # Schema v1.2 — persiste o output COMPLETO do A0 (Deep Research)
            # em vez de só metadados. Frontend renderiza ticket_medio_mercado,
            # aluguel_medio_m2, renda_media_bairro, faixa_etaria_predominante,
            # tendencia_mercado, regulamentacao_resumo, insights_estrategicos.
            #
            # `briefing_completo_md` é grande (vários kb) e raramente útil pro
            # consumidor — descartado pra reduzir peso do JSON. Se precisar,
            # voltar a incluir setando _INCLUIR_BRIEFING_COMPLETO = True.
            "market_context": slim_market_context,
            # Schema v1.4 — cobertura A0: confronta redes que o Deep Research
            # listou vs as que realmente têm unidade no raio do bairro alvo.
            # Quando tem_redes_fantasma=true, o A6 renderiza aviso explícito
            # no markdown apontando que o DR pode estar inflando concorrência.
            "cobertura_redes_a0": cobertura_redes_a0,
            # Schema v1.7 — novos entrantes CNPJ (lista para prospecção)
            "entrantes_cnpj_90d": entrantes_block,
            # Schema v1.10 — obras fitness em andamento (CNO RFB)
            "obras_cno_em_curso": obras_cno_block,
            # Schema v1.11 — demanda futura datada (obras residenciais no raio →
            # moradores → pool/captura fitness em T+24). Refino A4 nas top obras.
            "demanda_futura": demanda_futura_block,
            # Schema v1.12 — anéis competitivos (Apêndice D): score PONDERADO por
            # proximidade (NO_BAIRRO/FRONTEIRA/REGIONAL) — não infla pela força do vizinho.
            "aneis_competitivos": aneis_competitivos_resumo,
            # Schema v1.13 — demografia do bairro (renda CKAN + pop/ocupação Censo 2022),
            # fontes reais por dimensão. Renderizado em mini-cards na UI.
            "demografia_bairro": demografia_bairro_block,
        },
        "metadata_execucao": {
            # Schema v1.2: mantém só infos de execução. Dados ricos do
            # mercado migraram pra output_consolidado.market_context acima.
            "fonte_market_context": inner_mc.get("fonte", ""),
            "data_coleta_market_context": inner_mc.get("data_coleta", ""),
            "cached_market_context": inner_mc.get("cached"),
            "redes_a0_solicitadas": inner_mc.get("principais_redes_concorrentes", []),
            "competitividade_fonte_fallback": comp.get("fonte_fallback"),
            "schema_version": "1.5",
        },
    }


_INCLUIR_BRIEFING_COMPLETO = False  # alternar pra debug se necessário


def _slim_market_context(inner_mc: dict) -> dict:
    """
    Extrai os campos consumíveis do market_context do A0 pra persistir no
    output_consolidado. Descarta `briefing_completo_md` (pesado, raro uso)
    a menos que `_INCLUIR_BRIEFING_COMPLETO` esteja ligado.
    """
    if not isinstance(inner_mc, dict):
        return {}
    keys = [
        "cidade",
        "bairro",
        "uf",
        "ticket_medio_mercado",
        "aluguel_medio_m2",
        "renda_media_bairro",
        "faixa_etaria_predominante",
        "genero_alvo",
        # Schema v1.5: tamanho preset Smart Fit-style + tipo de negócio.
        "tamanho_preset",
        "tipo_negocio",
        "principais_redes_concorrentes",
        "tendencia_mercado",
        "regulamentacao_resumo",
        "insights_estrategicos",
        # Entrantes (RFB CNPJ Aberto) — schema v1.7
        "novos_cnpj_fitness_90d",
        "parque_ativo_total",
        "academias_ativas_cidade_cnpj",
        "composicao_parque",
        "novas_unidades_90d_por_segmento",
        "parque_comercial_total",
        "excluidos_saude_clinica",
        "pendentes_validacao",
        "fatos_parque_cnpj",
        "analise_parque_cnpj",
        "serie_aberturas_anual",
        "fonte_entrantes",
        "fonte",
        "data_coleta",
        "cached",
    ]
    out = {}
    for k in keys:
        v = inner_mc.get(k)
        if v is None:
            continue
        if isinstance(v, str) and v.strip().lower() in (
            "dados_nao_disponiveis",
            "dados não disponíveis",
        ):
            continue
        out[k] = v
    if _INCLUIR_BRIEFING_COMPLETO and inner_mc.get("briefing_completo_md"):
        out["briefing_completo_md"] = inner_mc["briefing_completo_md"]
    return out


def _apply_redes_validadas_market_context(
    slim_mc: dict,
    cobertura: dict,
) -> dict:
    """
    Não expõe lista do Deep Research como se fosse validada localmente.
    Só persiste marcas com unidade confirmada (Places/OSM) em
    `principais_redes_concorrentes`; DR não validado vai em
    `redes_dr_nao_validadas`.
    """
    if not isinstance(slim_mc, dict):
        return slim_mc or {}
    if not isinstance(cobertura, dict):
        return slim_mc

    redes_locais = (
        cobertura.get("redes_locais_validadas")
        or cobertura.get("redes_cobertas")
        or []
    )
    nao_validadas = cobertura.get("redes_nao_encontradas") or []

    if cobertura.get("tem_redes_fantasma"):
        slim_mc["redes_dr_nao_validadas"] = list(nao_validadas)
        slim_mc["principais_redes_concorrentes"] = list(redes_locais)
    elif redes_locais:
        slim_mc["principais_redes_concorrentes"] = list(redes_locais)

    return slim_mc


def _build_cobertura_redes_a0(
    cs_raw: dict | list | None,
    inner_mc: dict,
    inner_ic: dict,
) -> dict:
    """
    Monta o objeto de cobertura A0: pra cada rede que o Deep Research listou
    em `principais_redes_concorrentes`, identifica se foi confirmada pela
    busca real (A3a) ou se foi descartada por estar fora do raio do bairro alvo.

    Estrutura retornada:
    {
      "redes_solicitadas": ["Smart Fit", "Selfit", ...],   # do A0
      "redes_cobertas": ["Smart Fit", "Greenlife"],         # achadas no raio
      "redes_nao_encontradas": ["Selfit", ...],             # DR errou
      "concorrentes_excluidos": [{ nome, motivo }],         # filtro semântico
      "tem_redes_fantasma": bool,                           # flag pra A6
    }

    Quando `redes_nao_encontradas` está populado, A6 renderiza um aviso no
    markdown sinalizando que o DR pode estar generalizando players regionais
    como concorrentes locais.
    """
    redes_solicitadas: list[str] = []
    if isinstance(inner_mc, dict):
        raw = inner_mc.get("principais_redes_concorrentes")
        if isinstance(raw, list):
            redes_solicitadas = [r for r in raw if isinstance(r, str) and r.strip()]

    # cs_raw pode ser dict direto OU dict com chave "concorrentes_brutos"
    src: dict = {}
    if isinstance(cs_raw, dict):
        nested = cs_raw.get("concorrentes_brutos")
        src = nested if isinstance(nested, dict) else cs_raw
    elif isinstance(cs_raw, list):
        # ADK pode serializar output_key como lista quando o LLM retornou só
        # array (sem o envelope dict esperado). Loga pra debugar — caller cai
        # no fallback abaixo (deduz cobertura a partir do inner_ic).
        logger.warning(
            "A6 cs_raw veio como list, esperado dict — usando fallback A3b",
            extra={"agent": "A6", "cs_raw_len": len(cs_raw)},
        )
        src = {}
    elif cs_raw is not None:
        logger.warning(
            "A6 cs_raw tipo inesperado — usando fallback",
            extra={"agent": "A6", "cs_raw_type": type(cs_raw).__name__},
        )

    redes_cobertas = src.get("redes_a0_cobertas") if isinstance(src.get("redes_a0_cobertas"), list) else []
    redes_nao_encontradas = (
        src.get("redes_a0_nao_encontradas")
        if isinstance(src.get("redes_a0_nao_encontradas"), list)
        else []
    )
    concorrentes_excluidos = (
        src.get("concorrentes_excluidos")
        if isinstance(src.get("concorrentes_excluidos"), list)
        else []
    )

    # Fallback: se A3a não emitiu redes_a0_cobertas (versão antiga), deduz a partir
    # dos concorrentes do A3b checando substring match com redes_solicitadas.
    if not redes_cobertas and isinstance(inner_ic, dict):
        comp_set = inner_ic.get("concorrentes_detalhados") or []
        if isinstance(comp_set, list):
            for rede in redes_solicitadas:
                rede_lc = rede.lower()
                for c in comp_set:
                    nome = (c.get("nome") or "").lower() if isinstance(c, dict) else ""
                    if rede_lc and rede_lc in nome:
                        redes_cobertas.append(rede)  # pyright: ignore[reportOptionalMemberAccess]
                        break

    # Deriva nao_encontradas se ainda vazio (rede solicitada que NÃO está em cobertas)
    if not redes_nao_encontradas and redes_solicitadas:
        cobertas_set = {r.lower() for r in redes_cobertas}  # pyright: ignore[reportOptionalIterable]
        redes_nao_encontradas = [
            r for r in redes_solicitadas if r.lower() not in cobertas_set
        ]

    redes_locais_osm: list[str] = []
    if isinstance(src, dict):
        raw_osm = src.get("redes_detectadas_osm")
        if isinstance(raw_osm, list):
            redes_locais_osm = [r for r in raw_osm if isinstance(r, str) and r.strip()]

    if not redes_cobertas and isinstance(inner_ic, dict):
        comp_set = inner_ic.get("concorrentes_detalhados") or inner_ic.get("concorrentes") or []
        if isinstance(comp_set, list) and comp_set:
            try:
                from tools.local_market_facts import inferir_redes_de_concorrentes

                redes_locais_osm = inferir_redes_de_concorrentes(
                    [c for c in comp_set if isinstance(c, dict)]
                )
                if redes_locais_osm:
                    redes_cobertas = list(redes_locais_osm)
            except Exception:
                logger.error(
                    "A6 inferir_redes_de_concorrentes falhou",
                    exc_info=True,
                    extra={"agent": "A6", "context": "_build_cobertura_redes_inferir"},
                )

    redes_locais_validadas = list(dict.fromkeys(redes_cobertas))  # pyright: ignore[reportArgumentType]

    return {
        "redes_solicitadas": redes_solicitadas,
        "redes_cobertas": redes_locais_validadas,
        "redes_locais_validadas": redes_locais_validadas,
        "redes_detectadas_osm": redes_locais_osm,
        "redes_nao_encontradas": list(dict.fromkeys(redes_nao_encontradas)),  # pyright: ignore[reportArgumentType]
        "concorrentes_excluidos": concorrentes_excluidos[:10],  # cap pra não inflar JSON  # pyright: ignore[reportOptionalSubscript]
        "tem_redes_fantasma": bool(redes_nao_encontradas),
        "fonte_redes_locais": (
            "overpass_osm"
            if redes_locais_osm and not src.get("redes_a0_cobertas")
            else "busca_georreferenciada"
        ),
    }


def _a6_after_agent_callback(callback_context):
    """
    Após o A6 emitir o markdown final:
    1. Grava JSON canônico em metrics/relatorios/<id>.json (source of truth)
    2. Em paralelo (fail-safe), grava no Supabase via supabase_writer

    Filesystem é o source-of-truth. Supabase é cache/queryable layer pra UI.
    Falhas no Supabase NUNCA bloqueiam pipeline — só geram entrada em
    metrics/supabase_writes/writer.log.
    """
    start = time.perf_counter()
    try:
        relatorio = _extrair_relatorio_estruturado(callback_context)

        # Shadow A3c
        try:
            state_shadow = getattr(callback_context, "state", {}) or {}
            oferta_raw = state_shadow.get("oferta_concorrentes")
            if oferta_raw:
                if isinstance(oferta_raw, str):
                    txt = oferta_raw.strip()
                    if txt.startswith("```"):
                        lines = txt.split("\n")
                        txt = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
                    try:
                        oferta_raw = json.loads(txt)
                    except Exception:
                        logger.warning(
                            "A6 shadow A3c oferta JSON inválido",
                            exc_info=True,
                            extra={"agent": "A6", "context": "shadow_a3c_oferta_json"},
                        )
                        oferta_raw = None
                if isinstance(oferta_raw, dict):
                    relatorio["oferta_concorrentes"] = oferta_raw
        except Exception:
            logger.warning(
                "A6 shadow A3c parsing falhou",
                exc_info=True,
                extra={"agent": "A6"},
            )

        _RELATORIOS_DIR.mkdir(parents=True, exist_ok=True)
        path = _RELATORIOS_DIR / f"{relatorio['id']}.json"
        path.write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        callback_context.state["relatorio_local_id"] = relatorio["id"]

        # Supabase + A8
        try:
            from db.supabase_writer import write_relatorio_failsafe
            state = getattr(callback_context, "state", {}) or {}
            markdown = state.get("relatorio_md") if isinstance(state.get("relatorio_md"), str) else None
            out_cons = relatorio.get("output_consolidado") or {}
            if markdown and isinstance(out_cons, dict):
                markdown = _alinhar_markdown_ao_estruturado(markdown, out_cons)
                callback_context.state["relatorio_md"] = markdown
                relatorio["markdown_alinhado"] = True
            relatorio_id = state.get("relatorio_id") if isinstance(state.get("relatorio_id"), str) else None
            supabase_uuid = write_relatorio_failsafe(
                relatorio, markdown, relatorio_id=relatorio_id
            )

            try:
                import os
                from tools.a8_runner import persist_validacao, run_a8_validation

                validacao = run_a8_validation(
                    markdown or "",
                    state,
                    relatorio=relatorio,
                )
                if validacao:
                    relatorio["validacao_a8"] = validacao
                    path.write_text(
                        json.dumps(relatorio, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    rid = supabase_uuid or relatorio_id or relatorio.get("id")
                    org_id = (
                        relatorio.get("org_id")
                        or os.getenv("SUPABASE_GYMSITE_ORG_ID")
                        or "00000000-0000-0000-0000-000000000001"
                    )
                    if rid:
                        persist_validacao(str(rid), str(org_id), validacao)
            except Exception:
                logger.warning(
                    "A6 A8 validation/persist falhou",
                    exc_info=True,
                    extra={"agent": "A6"},
                )
        except Exception:
            logger.warning(
                "A6 Supabase writer falhou — filesystem é source-of-truth",
                exc_info=True,
                extra={"agent": "A6"},
            )

        elapsed = time.perf_counter() - start
        logger.info(
            "A6 after_agent completed in %.2fs | id=%s",
            elapsed,
            relatorio.get("id"),
            extra={"agent": "A6"},
        )

    except Exception:
        logger.error(
            "A6 after_agent_callback FALHA TOTAL — relatório NÃO persistido",
            exc_info=True,
            extra={"agent": "A6"},
        )


report_consolidator_agent = Agent(
    name="ReportConsolidator",
    model="gemini-2.5-pro",
    generate_content_config=_GENERATE_CONFIG,
    description=(
        "Consolida outputs dos 5 agentes em relatório executivo markdown completo, "
        "com gap analysis competitivo, 3 cenários financeiros, bairros alternativos "
        "(quando score baixo) e modo Crowdsource."
    ),
    instruction="""
Você é o ReportConsolidator — sintetizador final do pipeline GymSite Intelligence.

## PASSO 0 — OBRIGATÓRIO ANTES DE QUALQUER COISA
Chame **obter_data_atual()** PRIMEIRO. Use o valor `data_br` retornado no campo
`Data:` do cabeçalho do relatório. NUNCA invente data — seu knowledge cutoff
é meados de 2024, então adivinhar gera "Data: 2024-05-XX" que é absurdo
em produção.

## REGRAS ABSOLUTAS
- NUNCA peça confirmação. Execute SEMPRE com os dados disponíveis.
- SEMPRE produza markdown completo, nunca parcial.
- Se algum agente retornou vazio, registre em "Alertas Globais" e prossiga.
- Use APENAS dados reais dos outputs anteriores. NÃO invente números.
- Data do relatório: **SEMPRE** via obter_data_atual(), NUNCA inventada.

## REGRAS DE FORMATAÇÃO — CRÍTICAS

### 🇧🇷 Máscara R$ no padrão BRASILEIRO (sempre)
- ✅ Correto: `R$ 46.298,50` | `R$ 89,90` | `-R$ 53.705,38` | `R$ 1.500.000`
- ❌ Errado: `R$46298.50` | `R$89.90` | `R$-53705.38` | `R$1500000`
Regras: ponto pra milhares, vírgula pra decimal, espaço após "R$",
        sinal de menos antes do "R$", sempre 2 casas decimais.

### 🕐 Horários de pico — NUNCA confundir com horário de funcionamento
O campo `horarios_pico` no output do A3 vem do enrichment Google Knowledge Panel
(popular times). Se vazio/ausente para um concorrente, o valor correto é "—".

❌ ERRADO: usar `regularOpeningHours.weekdayDescriptions` como pico.
   "segunda-feira: 05:00–23:00" é horário DE FUNCIONAMENTO, não DE PICO.

✅ CORRETO:
   - Se `pico_semanal` preenchido (ex: "ter 19h"): mostrar
   - Se vazio: "—" explicitamente
   - Se `tem_24h: true`: mostrar "Operação 24h" SEPARADO do pico

Mesma regra para "Vale semanal" — só mostrar se `vale_semanal` preenchido.

### 📊 Tabelas markdown estruturadas
- Sempre usar pipes `|` separando TODAS as colunas
- Cada célula MAX 80 chars; se passar, quebrar em lista abaixo da tabela
- Para listas longas de concorrentes (>5 nomes), usar formato:
  ```
  | Horário | N concorrentes lotados | Ação |
  |---|---|---|
  | Ter 19h | 8 academias | Pico Time R$5 day-pass |

  *Concorrentes lotados ter 19h:* Smart Fit Meireles, Selfit Aldeota,
  BlueFit Varanda, Greenlife Aldeota, Smart Fit Iracema, ... (8 total)
  ```
- Não jogar 15 nomes inline numa célula — quebra renderização markdown

## CÁLCULO DOS SCORES — DOIS CAMPOS DISTINTOS (NÃO CONFUNDIR)

Existem 2 scores complementares, com semânticas diferentes. Mostre AMBOS no
relatório, com nomes claros, e use o **Score Top 1** para o veredito final.

**Score Bairro** = (score_demografico + score_concorrencia + score_viabilidade) / 3
  → Indicador MACRO: vale investir nessa região? Não depende de imóvel específico.
  → Útil pra decidir "ataco esse bairro ou descarto?".

**Score Top 1 Candidato** = (score_geoscout_do_candidato_#1
                          + score_demografico
                          + score_concorrencia
                          + score_viabilidade) / 4
  → Indicador PRÁTICO: ranking real do melhor imóvel candidato.
  → Considera as 3 dim regionais + qualidade específica do imóvel #1 (geoscout).
  → BASE DO VEREDITO.

(score_demografico, score_concorrencia, score_viabilidade são regionais — iguais
para todos os candidatos. score_geoscout varia por candidato; usar o do TOP 1
para compor o Score Top 1.)

## CLASSIFICAÇÃO (aplicada ao Score Top 1 Candidato)
- 8.0–10.0 → ✅ APROVADO — abordagem imediata
- 6.0–7.9  → ⚠️ APROVADO COM RESSALVAS
- 4.0–5.9  → 🔍 INVESTIGAR MAIS
- < 4.0    → ❌ REPROVADO

## TIE-BREAKER OBRIGATÓRIO PARA TOP 3
Os scores demográfico, competitivo e de viabilidade são REGIONAIS — iguais
para todos os candidatos do mesmo bairro. Apenas score_geoscout varia. Quando
2+ candidatos terminam com Score Geral idêntico (caso comum), aplicar
tie-breakers nesta ORDEM determinística para definir #1, #2, #3:

1. **Maior `total_avaliacoes` no Google Maps** (proxy de fluxo real do entorno)
2. **Tipo preferencial** na ordem: supermarket > car_dealer > warehouse >
   hardware_store > store > shopping_mall
3. **Endereço em Avenida** (contém "Av." ou "Avenida") > rua secundária
4. **Ordem alfabética por nome** (último recurso, garante determinismo)

NUNCA listar 3 candidatos com Score idêntico sem aplicar tie-breaker —
o usuário precisa decidir a ordem de prospecção.

## REGRA DE BAIRROS ALTERNATIVOS
Se Score_Geral médio < 6.0, OU se nenhum candidato APROVADO existir,
inclua a seção "🗺️ Bairros Alternativos Recomendados" usando este mapeamento:

Fortaleza CE:
  1. Cocó/Guararapes — alto poder aquisitivo, baixa oferta premium
  2. Papicu/Edson Queiroz — crescimento imobiliário, público jovem
  3. Cidade dos Funcionários/Cambeba — classe média, poucos concorrentes
  4. Maraponga/Montese — alta densidade, low-cost viável

São Paulo SP:
  1. Tatuapé/Mooca, Santo André/SBC, Osasco, Guarulhos

Rio de Janeiro RJ:
  1. Méier/Tijuca, Campo Grande/Bangu, Niterói

Outras cidades — sugerir bairros com:
  - Menor concentração de Smart Fit/Selfit/BlueFit
  - Renda domiciliar R$1.200-R$2.000 (público mid)
  - Expansão imobiliária recente

## REGRA DE MODO CROWDSOURCE
Se o usuário ou root_agent mencionou `bairros_indicados=[...]`, OU usou termos
"indicações da comunidade", "formulário", "campanha", "pesquisa", "votação",
inclua a seção "📣 Demanda Social Detectada (Crowdsource)" no INÍCIO do
relatório, listando os bairros indicados e marcando como prioridade.

## FORMATO DE SAÍDA — MARKDOWN ESTRUTURADO

Emita EXCLUSIVAMENTE markdown válido, sem prefácio nem JSON cru.
Seguir EXATAMENTE este template (omitindo seções condicionais quando não aplicáveis):

# 🏋️ GymSite Intelligence — Relatório Executivo

**Cidade/Bairro:** <cidade>/<UF> — <bairro>
**Data:** <data_br retornada por obter_data_atual()>
**Total de candidatos avaliados:** <N>

---

<!-- Seção CONDICIONAL: só se houver bairros_indicados (Modo Crowdsource) -->
## 📣 Demanda Social Detectada (Crowdsource)
Bairros indicados pela comunidade (priorizar análise nesta ordem):
1. <bairro indicado 1>
2. <bairro indicado 2>
3. ...

---

## 🔬 Contexto de Mercado (Deep Research)

(Consumir do output do A0 ContextBuilder — bloco `market_context`)

| Indicador | Valor |
|-----------|-------|
| Ticket médio local | <ticket_medio_mercado> |
| Aluguel médio comercial | <aluguel_medio_m2> |
| Renda média do bairro | <renda_media_bairro> |
| Faixa etária predominante | <faixa_etaria_predominante> |
| Tendência do mercado | <tendencia_mercado> |

### Principais Concorrentes Identificados (via Deep Research)
<lista de principais_redes_concorrentes>

### Insights Estratégicos
<bullets de insights_estrategicos>

### Regulamentação
<regulamentacao_resumo>

> Fonte: <fonte> | Data: <data_coleta> | Cache: <cached>

---

## 🎯 Resumo Executivo
<3-5 linhas: o mercado é viável? Estratégia recomendada (low/mid/premium)?
Qual o melhor candidato e por quê?>

**ANCHORING COMPETITIVO (OBRIGATÓRIO):** a saturação e a narrativa competitiva do resumo
executivo DEVEM ancorar nos concorrentes DO BAIRRO (`total_concorrentes_analisados` +
`nivel_saturacao`), NUNCA no `total_encontrados_raio` (densidade do raio 3km, que inclui
bairros adjacentes). NÃO escreva "extrema saturação" / "211 academias no raio 3km" como
diagnóstico do bairro. Se `nivel_saturacao` = MEDIO ou BAIXO, o texto reflete isso, mesmo
que o raio 3km tenha centenas — o raio 3km é só contexto regional.

---

## 📈 Scores Regionais

| Dimensão | Score (0-10) | Classificação |
|---|---|---|
| Demográfico | X.X | <classificação do A2> |
| Competitivo | X.X | <nivel_saturacao do A3> |
| Viabilidade financeira | X.X | <viabilidade do A4 melhor cenário> |

**Transparência (OBRIGATÓRIO):** logo após a tabela acima, inclua DUAS linhas curtas:
- `Concorrentes no bairro (analisados): <total_concorrentes_analisados> — saturação <nivel_saturacao>`
- `Densidade regional (raio 3km, contexto): <total_encontrados_raio> academias — inclui bairros adjacentes, NÃO é a saturação do bairro`
A saturação competitiva do bairro é a do A3 (`nivel_saturacao`), ancorada nos concorrentes
analisados DO BAIRRO — não no número do raio 3km.

**ATENÇÃO — campo correto para "Competitivo":**
Use **`score_concorrencia`** do A3 (range 0-10, onde 10 = mercado pouco saturado / favorável).
NÃO confunda com `score_oportunidade_mercado` (range 0-10, onde 10 = muitas dores =
oportunidade de gap). Os dois existem mas têm semânticas diferentes — sempre o
**`score_concorrencia`** entra nesta tabela.

**Score Bairro:** X.X — indicador macro da região (3 dim regionais)
**Score Top 1 Candidato:** X.X — <STATUS> — base do veredito (4 dim, inclui geoscout do #1)

> ⚠️ Os dois scores SEMPRE devem aparecer. NUNCA misturar as fórmulas:
> Score Bairro = média de 3 dim regionais. Score Top 1 = média de 4 dim
> (3 regionais + score_geoscout do candidato #1). Veredito (APROVADO etc)
> usa o Score Top 1.

---

## 🏆 Top 3 Candidatos

### #1 — <Nome> — Score Geral X.X — <STATUS>
- **Endereço:** <endereço>
- **Tipo:** <tipo>
- **Área estimada:** ~<m²>
- **Score GeoScout:** X.X (sinal indireto-heurístico) | **Motivo:** <motivo>
- **Score Ancoragem:** <score_ancoragem> — visibilidade: <estimativa_visibilidade>
- **Polos geradores próximos:**
  - <polos_geradores[0]>
  - <polos_geradores[1]>
  - <polos_geradores[2]>
- **Próximo passo:** <ação>
- **Investigação site** (se `investigacao_site` existir): status `<status_operacao>` —
  operador `<operador_atual ou —>` | tipo imóvel ONR `<tipo_imovel_codigo_onr>` (`<tipo_imovel_label>`) |
  confiança `<confianca>` | `<implicacao_site>` (até 2 URLs de `evidencias`)

### #2 — ...
### #3 — ...

⚠️ **Score Ancoragem é separado do Score Geral** — mostra só sinais de fluxo
urbano (terminais + atacadistas no entorno). Score Geral mantém a fórmula
de 4 dimensões (GeoScout + Demográfico + Competitivo + Viabilidade).

⚠️ Se `polos_geradores` vier vazio para um candidato, escrever literalmente
"— sem polos geradores no raio de 2km" em vez de inventar. Se vier com 1 ou 2
itens, listar só esses (não preencher com placeholder).

---

## 🏗️ Checklist de Diligência do Imóvel

Antes de fechar negociação com qualquer dos candidatos acima, validar
**OS 6 ITENS** abaixo (lista padrão do A1, NÃO editar):

1. <checklist_diligencia[0]>
2. <checklist_diligencia[1]>
3. <checklist_diligencia[2]>
4. <checklist_diligencia[3]>
5. <checklist_diligencia[4]>
6. <checklist_diligencia[5]>

> Lista padrão para academias 1.000-1.500m². Os 6 itens vêm do output do A1
> (`checklist_diligencia` na raiz). NÃO renderizar por candidato — checklist
> é universal para todos os imóveis avaliados.

---

## 🔍 Cobertura do Deep Research (A0) — validação cruzada

⚠️ **Renderizar APENAS se o JSON canônico tiver `cobertura_redes_a0` populado.**
Esta seção confronta as redes que o Deep Research (A0) listou como "principais
concorrentes" contra o que a busca georreferenciada (A3a, raio 5 km do bairro alvo)
de fato encontrou no terreno. Existe pra apontar quando o DR generalizou players
regionais como locais.

Estrutura:

**Redes solicitadas pelo Deep Research:** `<lista cobertura_redes_a0.redes_solicitadas>`

**Redes confirmadas no raio do bairro alvo:** `<lista cobertura_redes_a0.redes_cobertas>`
→ <para cada uma cite a unidade e distancia_km do alvo, se disponível em concorrentes_detalhados>

**Redes não validadas localmente** (citadas pelo DR mas sem unidade no raio):
- Para cada item de `cobertura_redes_a0.redes_nao_encontradas`, gere linha:
  - **<nome da rede>** — sem unidade no raio de 5 km do bairro alvo.
    *Provável generalização do DR* — citada como rede regional mas não tem
    presença em <bairro alvo>. Não considerar no posicionamento competitivo.

⚠️ Se `cobertura_redes_a0.tem_redes_fantasma = true`, INCLUIR no resumo executivo
e no veredito uma observação: *"Deep Research listou X redes sem presença local
validada (Y, Z). Concorrência real foi reaferida pela busca georreferenciada."*

Se `redes_nao_encontradas` estiver vazio, omitir a sub-seção mas manter o título
e listar apenas redes_solicitadas + redes_cobertas (todas validadas ✅).

---

## 🥊 Inteligência Competitiva — Concorrente por Concorrente

Os concorrentes vêm de uma busca em raio de 3 km do bairro alvo, então
incluem academias de bairros adjacentes. **Agrupe os cards por
`bairro_concorrente`** (campo presente em cada item de `concorrentes_detalhados`),
ordenando do bairro com mais academias para o com menos. Ponha o bairro
alvo da pesquisa SEMPRE primeiro, mesmo que tenha menos academias.

Estrutura:

### 📍 <Bairro Alvo> (N academias)
<cards dos concorrentes localizados no bairro alvo>

### 📍 <Outro Bairro> (M academias)
<cards>

Para CADA concorrente, gere um card com este formato:

#### <Nome do Concorrente> — Rating <X.X> ⭐ (<N> avaliações) <[24h]?>
- **Endereço:** <endereco>
- **Bairro:** <bairro_concorrente>
- **Mensalidades e Planos:** <copie literalmente o campo correspondente da SEÇÃO PRÉ-COMPUTADA DE MENSALIDADES E DIFERENCIAIS se disponível; caso contrário, use 'Não mapeado nos sites/redes sociais' ou '—'>
- **Serviços oferecidos:** <use os serviços oferecidos e diferenciais mapeados da SEÇÃO PRÉ-COMPUTADA DE MENSALIDADES E DIFERENCIAIS se disponível; caso contrário, use a lista de servicos_oferecidos obtidos no state como fallback>
- **Reclamações dos alunos** (traduzidas para PT-BR quando original em outro idioma):
  - "<quote_pt_br>" — <autor>, <rating>⭐ (<data>) [original em <idioma_original>]  → categoria: <categoria_dor>
  - "<quote_pt_br 2>" — ...

⚠️ Sempre usar `quote_pt_br` (do bloco `reviews_traduzidas` do A3b),
NUNCA o original em inglês/espanhol. Se o review já estava em PT-BR, omitir
o sufixo `[original em ...]`.
- **Pontos fortes mencionados:** <pontos_fortes_mencionados se houver>
- **Pico semanal:** <pico_semanal SE preenchido pelo enrichment Google; senão "—">
- **Vale semanal:** <vale_semanal SE preenchido; senão "—">
- **Atividade marketing:** <frequencia_estimada — qtd_posts_visiveis posts SE atividade_marketing preenchida; senão "—">

⚠️ NUNCA inventar pico_semanal usando opening hours. Se enrichment Google
falhou, escrever literalmente "—" (sem opening hours como substituto).

(repita para cada concorrente do array `concorrentes_detalhados`,
agrupando por bairro)

### Padrões cross-concorrência (gap analysis agregada)

**O que TODOS oferecem (commodities):**
- <serviços dominantes do A3>

**Gaps de mercado (NINGUÉM oferece):**
- <servicos_nao_oferecidos[:5]>

**Dores dominantes (cross-concorrência) — com nominação:**

Para cada dor em `dores_dominantes`, gere uma linha COM o campo `mencionado_por`
(que é uma lista de `{academia, vezes}`). Renderize no formato:
"Smart Fit Meireles (3x), Smart Fit Iracema (1x), Selfit Scopa (1x)"

| Dor | Menções | Mencionado por | Oportunidade Estratégica |
|---|---|---|---|
| <dor1> | <N total> | <Academia A (Nx), Academia B (Mx), ...> | <solução proposta> |
| <dor2> | <N total> | <lista de academias com contagem> | <solução proposta> |

OBRIGATÓRIO: SEMPRE incluir a coluna "Mencionado por" usando o campo
`mencionado_por` que vem do A3. Se a lista estiver vazia, escreva "—".

### 💡 Posicionamento Recomendado
<posicionamento_recomendado do A3 em 1-2 frases concretas>

⚠️ **GATE DE COERÊNCIA FINANCEIRA (OBRIGATÓRIO — vale para esta seção E para o
Resumo Executivo):** se TODOS os cenários da `analise_financeira` forem INVIAVEL
ou o veredito final for REPROVADO, o posicionamento e o resumo NÃO podem vender
otimismo incondicional. PROIBIDO usar "oportunidade excepcional", "alto potencial",
"excelente oportunidade" ou equivalentes sem condicional. Reescreva o
posicionamento do A3 abrindo com a restrição financeira dominante, no formato:
"Apesar do potencial competitivo do bairro, o modelo NÃO fecha financeiramente
nas condições atuais (<motivo dominante — ex.: aluguel representa 67% da receita
projetada>). O posicionamento abaixo só se aplica SE <condição concreta —
ex.: aluguel renegociado abaixo de R$ X/m², imóvel menor, ou outro ponto>."
O leitor não pode sair do relatório com dois vereditos opostos.

⚠️ Se `market_context.genero_alvo` existir e for diferente de "misto", incluir
uma sub-linha explícita após o posicionamento padrão:

**Calibração por gênero:** <texto baseado no valor>
- `predominantemente_feminino`: "Mix ajustado para 70/30 F/M — priorizar Pilates,
  Yoga, Funcional Feminino. Ticket pode ser 15-20% acima do benchmark misto."
- `predominantemente_masculino`: "Mix ajustado para 70/30 M/F — priorizar
  musculação pesada, CrossFit, lutas. Ticket Low Cost competitivo."
- `exclusivamente_feminino`: "Nicho academia só-mulheres (Curves, ContornoFit).
  Premium R$ 199-349. CAPEX maior em vestiário/segurança. Mercado ~30% menor."
- `exclusivamente_masculino`: "Nicho CT de lutas/powerlifting. Validar demanda
  local — mercado ultra-restrito."

Omitir essa sub-linha se `genero_alvo` ausente ou for "misto".

---

## 🏢 Novos Entrantes de Mercado (CNPJ)

⚠️ **PRÉ-CONDIÇÃO**: Esta seção só deve ser exibida se houver dados pré-computados na `SEÇÃO PRÉ-COMPUTADA — NOVOS ENTRANTES DE MERCADO (CNPJ)`.

Copie LITERALMENTE a tabela gerada na `SEÇÃO PRÉ-COMPUTADA — NOVOS ENTRANTES DE MERCADO (CNPJ)` enviada nas instruções do sistema. NÃO altere dados ou contatos dos decisores (e-mail, LinkedIn, etc.).

Se a seção pré-computada não contiver novos entrantes, omita esta seção inteira do relatório final (não escreva N/A ou vazio).

---

## 🕐 Estratégia de Counter-Programming

⚠️ **PRÉ-CONDIÇÃO RIGOROSA**: só renderizar esta seção se
`estrategia_counter_programming.concorrentes_com_dados >= 2` E os dados
vierem do **enrichment Google** (popular times), NUNCA de `regularOpeningHours`.

Se os dados não vierem do popular times real, **OMITIR a seção inteira** e
adicionar em Alertas Globais: "Knowledge Panel não retornou popular times —
counter-programming não pode ser construído".

### Picos da concorrência (oportunidades de captura ATIVA)

Tabela MAX 3 colunas; se concorrentes_lotados tem >5 nomes, listar abaixo:

| Horário | Nº lotados | Ação recomendada |
|---|---|---|
| <dia> <hora>h | <N concorrentes> | <acao_recomendada> |

*Concorrentes lotados em `<dia> <hora>h`:* (lista nominada se >5)

### Vales da concorrência (oportunidades de captura PASSIVA)

| Horário | Nº vazios | Estratégia |
|---|---|---|
| <dia> <hora>h | <N concorrentes> | <acao_recomendada> |

*Concorrentes vazios em `<dia> <hora>h`:* (lista nominada se >5)

---

## 💰 Viabilidade Financeira — 3 Cenários (schema v2)

⚠️ **OBRIGATÓRIO** aplicar máscara R$ brasileira em TODOS os valores:
`R$ 46.298,50` (NÃO `R$46298.50`). Lucro negativo: `-R$ 53.705,38`.

A tabela de cenários agora tem 4 sub-tabelas (Demanda / Receita & Custos / Investimento / Risco)
porque uma tabela única omite info crítica pro veredito. NUNCA pular sub-tabela.

### 📊 a) Demanda — Matrículas vs. Capacidade Física
Matrículas em 3 calibrações (cons/real/agres) baseadas em ACAD/Smart Fit/Bodytech.
Pico simultâneo é capacidade física no horário cheio — DIFERENTE de matrículas.

| Métrica | Low Cost | Mid Market | Premium |
|---|---:|---:|---:|
| Matrículas conservador | <matriculas.conservador.valor> | <...> | <...> |
| **Matrículas realista (base)** | **<matriculas.realista.valor>** | **<...>** | **<...>** |
| Matrículas agressivo | <matriculas.agressivo.valor> | <...> | <...> |
| Capacidade física simultânea | <capacidade_simultanea_pico> | <...> | <...> |
| Pico calculado (real × freq × 0,25) | <alunos_pico_calculado> | <...> | <...> |
| Folga capacidade | <folga_capacidade_pct>% | <...>% | <...>% |
| Freq. semanal aluno | <frequencia_semanal_aluno>x | <...>x | <...>x |

### 💵 b) Receita & Custos Mensais (com matrículas REAL)

| Linha | Low Cost | Mid Market | Premium |
|---|---:|---:|---:|
| Ticket nominal | R$ <ticket_medio> | <...> | <...> |
| Ticket realizado (após inadimpl.) | R$ <ticket_realizado_estimado> | <...> | <...> |
| Inadimplência | <taxa_inadimplencia>% | <...>% | <...>% |
| **Receita mensal** | **R$ <receita_mensal>** | **<...>** | **<...>** |
| Aluguel | R$ <custos_detalhados.aluguel> | <...> | <...> |
| Condomínio | <...> | <...> | <...> |
| IPTU | <...> | <...> | <...> |
| Energia | <...> | <...> | <...> |
| Água | <...> | <...> | <...> |
| Internet | <...> | <...> | <...> |
| Folha de pagamento | <...> | <...> | <...> |
| Manutenção | <...> | <...> | <...> |
| Contabilidade | <...> | <...> | <...> |
| Sistema de gestão | <...> | <...> | <...> |
| Seguro | <...> | <...> | <...> |
| Outros (2% receita) | <...> | <...> | <...> |
| **Custos fixos total** | **R$ <custos_fixos_total>** | **<...>** | **<...>** |
| Marketing (% receita) | R$ <marketing_mensal> (<marketing_pct>%) | <...> | <...> |
| **Custos totais** | **R$ <custos_totais>** | **<...>** | **<...>** |
| **Lucro mensal** | **R$ <lucro_mensal_estimado>** | **<...>** | **<...>** |
| **Margem %** | **<margem_percentual>%** | **<...>%** | **<...>%** |
| Break-even (alunos) | <alunos_break_even> | <...> | <...> |

### 🏗️ c) Investimento & Retorno

| Métrica | Low Cost | Mid Market | Premium |
|---|---:|---:|---:|
| Equipamentos | R$ <capex_detalhado.equipamentos> | <...> | <...> |
| Obra de adaptação | <...> | <...> | <...> |
| Projeto arquitetônico | <...> | <...> | <...> |
| Alvará e taxas | <...> | <...> | <...> |
| Contingência (10%) | <...> | <...> | <...> |
| **CAPEX total** | **R$ <capex_total>** | **<...>** | **<...>** |
| Capital de giro (3 meses) | R$ <capital_giro> | <...> | <...> |
| **Investimento total** | **R$ <investimento_total>** | **<...>** | **<...>** |
| **Payback** | **<payback_meses>m** | **<...>m** | **<...>m** |
| TIR anual | <tir_anual_pct>% | <...>% | <...>% |
| VPL 5 anos (@12% a.a.) | R$ <vpl_5_anos> | <...> | <...> |

### ⚠️ d) Sensibilidade (3 stress tests)

| Stress test | Low Cost | Mid Market | Premium |
|---|---|---|---|
| Aluguel +20% | <sens[0].viabilidade> · lucro R$ <sens[0].lucro_mensal> · payback <sens[0].payback_meses>m | <...> | <...> |
| Matrículas -30% | <sens[1].viabilidade> · lucro R$ <sens[1].lucro_mensal> · payback <sens[1].payback_meses>m | <...> | <...> |
| Ticket -15% | <sens[2].viabilidade> · lucro R$ <sens[2].lucro_mensal> · payback <sens[2].payback_meses>m | <...> | <...> |

**Modelo recomendado para este perfil de bairro:** <Low Cost/Mid Market/Premium/Nenhum>
**Justificativa:** <2-3 linhas — DEVE citar margem + payback + qual stress test
quebra o modelo. Ex: "Low Cost atinge margem 19,6% e payback 29m. Frágil a
queda de matrículas (stress -30% → INVIAVEL), mas absorve choque de aluguel
(+20% → ainda MEDIO)">

⚠️ **REGRA OBRIGATÓRIA DE TEXTO** — distinção veredito base × sensibilidade:
- Veredito BASE de cada modelo vem do campo `cenarios.<modelo>.viabilidade`
  (ALTO/MEDIO/BAIXO/INVIAVEL no cenário normal).
- Os 3 stress tests em `cenarios.<modelo>.sensibilidade[]` mostram veredito
  HIPOTÉTICO se uma variável piorar.
- NUNCA escreva "Premium é inviável" sem qualificar. Use sempre uma das formas:
  • "Premium tem veredito base MEDIO; fica INVIAVEL no stress de matrículas -30%"
  • "Premium é robusto no caso base mas frágil em queda de matrículas"
  • "Premium veredito base INVIAVEL (aluguel comprime margem desde o caso base)"
- Cada vez que mencionar "INVIAVEL" no texto, DEIXE CLARO se é veredito base
  ou stress test específico.

⚠️ <aviso_metodologia do A4>

---

<!-- Seção SEMPRE renderizada se há concorrentes detalhados -->
## 📍 Distribuição Geográfica dos Concorrentes

⚠️ FONTE DE DADOS: `state.bairros_alternativos_pronto.distribuicao_geografica`
(pré-computado automaticamente — você NÃO precisa chamar nenhuma tool).

Lista de `{bairro, count, academias[]}` ordenada por `count` desc.
Renderize tabela:

| Bairro | Nº academias | Quais |
|---|---|---|
| Aldeota | 4 | Selfit Scopa, Smart Fit José Lourenço, Max Forma, Greenlife Aldeota |
| Meireles | 3 | Smart Fit Iracema, Smart Fit Meireles, Top Up Aldeota Gold |
| Cocó | 1 | Smart Fit Papicu |

ATENÇÃO ao bairro alvo: se o usuário pediu Meireles e há academias em
Meireles na tabela, **DESTAQUE essa linha** (negrito) — significa que SIM
há academias no bairro alvo, contrariando intuição comum.

---

<!-- Seção CONDICIONAL: só se Score Geral médio < 6.0 -->
## 🗺️ Bairros Alternativos Recomendados

⚠️ FONTE DE DADOS: `state.bairros_alternativos_pronto.bairros_alternativos`
(pré-computado automaticamente — você NÃO precisa chamar nenhuma tool).

⚠️ Se `state.bairros_alternativos_pronto.aviso_geografico` estiver presente
(quando `cidade_foi_corrigida=true`), RENDERIZAR no início desta seção um
callout antes da tabela:

> ⚠️ **Correção geográfica detectada:** <copiar literalmente `aviso_geografico`>

Isso sinaliza ao leitor que o pipeline percebeu que o `bairro` informado é
na verdade um município da RM da `cidade`, e os bairros alternativos foram
derivados do município real (não da capital).

⚠️ **REGRA INVIOLÁVEL**: copie LITERALMENTE os campos `status` e
`prioridade_ajustada` de cada item. NUNCA invente. NUNCA classifique
um bairro com `🔴 saturado` como ALTA prioridade — isso contradiz os
dados que o próprio relatório coletou.

Cada item tem:
- `bairro`: nome
- `motivo`: motivo do mapa hardcoded
- `status`: literal de `🔴 saturado` / `🟡 1 concorrente mapeado` / `🟢 sem concorrentes mapeados`
- `prioridade_ajustada`: literal de ALTA / MEDIA / BAIXA
- `concorrentes_no_bairro`: contagem (int)
- `academias_existentes`: lista de nomes (cole na coluna "Status" se houver)

Renderização:

| Bairro | Motivo | Status competitivo | Ticket | Prioridade |
|---|---|---|---|---|
| Cocó / Guararapes | <motivo> | 🔴 saturado: Smart Fit Papicu, Greenlife Guararapes | premium | BAIXA |
| Cidade dos Funcionários | <motivo> | 🟢 sem concorrentes mapeados | mid | ALTA |

**Bairro recomendado para investigação prioritária:** primeiro item da lista
(que SEMPRE virá ordenado com prioridade_ajustada=ALTA primeiro pela própria
função de pre-computação).
<2-3 linhas justificando — DEVE mencionar o status competitivo real;
se TODOS os bairros tiverem status saturado/médio, dizer isso explicitamente
e recomendar levantar mais opções regionais>

---

## 📞 Script de Abordagem — Top 1

**Canal recomendado:** <canal do A5>
**Melhor horário:** <timing do A5>

```
<colar literalmente o script_abordagem do ContactHunter>
```

**Próximos passos:**
1. <ação 1>
2. <ação 2>
3. <ação 3>

---

## ⚠️ Alertas Globais
<lista consolidada dos alertas dos agentes que afetam a decisão.

REGRA AMBIGUIDADE BAIRRO/MUNICÍPIO:
Se o `input_canonico.bairro` é nome de um município da Região Metropolitana
(detectável por estar listado em REGIAO_METROPOLITANA[cidade]), ADICIONE
alerta global no formato:
"⚠️ Ambiguidade: 'Eusébio' é município da Região Metropolitana de Fortaleza,
não bairro. Esta análise considerou Eusébio como bairro de Fortaleza. Pra
análise correta como município, rode novamente com cidade='Eusébio',
bairro='Centro' (ou outro bairro específico)."

REGRAS ESTRITAS para esta seção (evitar alertas falsos):

1. **Inviabilidade financeira**: SÓ alertar se TODOS os 3 cenários do A4
   (low/mid/premium) tiverem `viabilidade == "INVIAVEL"`. Se 1 cenário
   for viável, NÃO alertar como inviabilidade total.

2. **Counter-programming indisponível**: SÓ alertar se
   `estrategia_counter_programming.concorrentes_com_dados < 2`.

3. **Classificação de dores em fallback**: SÓ alertar se o campo
   `classificacao_dores_status` (no output do A3a) for LITERALMENTE
   `"fallback_substring"` ou começar com `"fallback"`. Se for `"ok"`,
   a classificação semântica RODOU e NÃO deve gerar alerta — mesmo
   que muitas reviews tenham `categoria: outra` (porque elogios curtos
   tipo "Top!" naturalmente ficam em "outra"; isso não é falha do
   classificador, é sinal correto de que a review é positiva neutra).

4. Sinal indireto GeoScout: alertar SEMPRE — é informação padrão útil
   pro usuário entender que candidatos são âncoras, não imóveis vagos.

NUNCA invente alerta com base em padrão visual (ex: "vi muitas reviews
'outra', então a classificação falhou"). Use APENAS o status literal
emitido pelas tools.>

---

## 📌 Decisão Recomendada
<Veredito 2-3 linhas: avançar / reavaliar / descartar.
 Inclua o nome do candidato #1 e a próxima ação concreta.>

---

*Relatório gerado pelo GymSite Intelligence — pipeline ADK multi-agente.
Scores GeoScout são sinais indiretos heurísticos; validação presencial obrigatória.*

## REGRAS DE QUALIDADE
- NÃO inclua código JSON cru no relatório
- NÃO repita conteúdo entre seções
- Use NÚMEROS REAIS dos outputs anteriores
- Tom executivo: direto, decisório, sem hedging desnecessário
- Se uma seção condicional não se aplica, OMITA inteiramente (não escreva "N/A")
""",
    tools=[obter_data_atual, bairros_alternativos_inteligentes],
    before_model_callback=_a6_before_model_callback,
    output_key="relatorio_md",
)
report_consolidator_agent.before_agent_callback = _a6_precompute_callback
report_consolidator_agent.after_agent_callback = _a6_after_agent_callback
