# agents/a6_report_consolidator.py
"""A6: Consolidador final — relatório executivo markdown com gap + bairros alternativos + crowdsource."""
import json
import time
from datetime import datetime
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
    thinking_config=types.ThinkingConfig(thinking_budget=8192),
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
}


def _norm_cidade(cidade: str) -> str:
    """
    Lowercase + strip + remove acentos pra lookup robusto.
    'São Paulo' → 'sao paulo', 'Eusébio' → 'eusebio'.
    """
    import unicodedata
    s = (cidade or "").lower().strip()
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


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

    # 3. Fallback genérico
    return [
        {"bairro": "Centro Expandido",
         "motivo": "Alta densidade comercial e fluxo garantido"},
        {"bairro": "Bairros em expansão imobiliária recente",
         "motivo": "Novos empreendimentos = público novo, sem concorrência consolidada"},
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
            return (inner.get("bairro") or "").strip()
    except Exception:
        pass
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
    de 2km especificamente. Custo extra: ~4 chamadas Places API por relatório
    (~$0.13 USD ≈ R$ 0,72). Tradeoff aceito para evitar falsa segurança.

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
    distribuicao: list = []

    if state is not None:
        ctx = _parse_market_context(state.get("market_context"))
        if isinstance(ctx, dict):
            inner_candidate = ctx.get("market_context")
            inner = inner_candidate if isinstance(inner_candidate, dict) else ctx
            cidade = (inner.get("cidade") or "").strip()

        ic = _parse_market_context(state.get("inteligencia_competitiva"))
        if isinstance(ic, dict):
            distribuicao = ic.get("distribuicao_geografica") or []
            if not distribuicao:
                inner_ic = ic.get("inteligencia_competitiva")
                if isinstance(inner_ic, dict):
                    distribuicao = inner_ic.get("distribuicao_geografica") or []

    bairro_alvo = _bairro_alvo_da_busca(state)
    bairro_alvo_low = bairro_alvo.lower().strip()

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
        partes_low = {p.lower().strip() for p in partes}
        count_total = 0
        academias_existentes: list[str] = []
        place_ids_vistos: set = set()
        metodologia = "busca real (raio 2km, filtros: academia tradicional + match de bairro)"

        try:
            for parte in partes:
                resultado = buscar_academias(parte, cidade_para_busca, raio_metros=2000)
                if "erro" in resultado:
                    raise RuntimeError(resultado.get("erro"))
                concorrentes = resultado.get("concorrentes") or []
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
                        bairro_concorrente = (
                            extrair_bairro_endereco(c.get("endereco", "")) or ""
                        ).lower().strip()
                    except Exception:
                        pass
                    if bairro_alvo_low and bairro_concorrente == bairro_alvo_low:
                        continue

                    # Match de bairro com tolerância: se bairro_concorrente
                    # não bate com nenhuma parte da entrada, ainda mantém SE
                    # o nome da academia menciona alguma das partes
                    # (ex: "TP FITNESS ACADEMIAS | MARAPONGA" sem bairro
                    # extraído deve contar como Maraponga).
                    if bairro_concorrente and bairro_concorrente not in partes_low:
                        nome_low = (c.get("nome") or "").lower()
                        nome_bate_bairro = any(p in nome_low for p in partes_low)
                        if not nome_bate_bairro:
                            continue
                    place_ids_vistos.add(pid)
                    count_total += 1
                    nome_academia = c.get("nome", "?")
                    if nome_academia not in academias_existentes:
                        academias_existentes.append(nome_academia)
        except Exception as e:
            # Fallback: usa distribuicao_geografica do A3b
            metodologia = f"fallback distribuicao_geografica (busca falhou: {type(e).__name__})"
            count_total = 0
            academias_existentes = []
            for parte in partes:
                p_low = parte.lower()
                count_total += saturados_fallback.get(p_low, 0)
                academias_existentes.extend(academias_fallback.get(p_low, []))

        # Cap acadêmico: se busca real retornou >20, é provavelmente região
        # comercial densa — cap em 20 pra não estourar a tabela
        if len(academias_existentes) > 10:
            academias_existentes = academias_existentes[:10] + [f"... (+{len(academias_existentes) - 10})"]

        status, prioridade = _classificar_status_competitivo(count_total)

        enriquecidos.append({
            **entry,
            "bairro_principal_busca": bairro_principal,
            "concorrentes_no_bairro": count_total,
            "academias_existentes": academias_existentes,
            "status": status,
            "prioridade_ajustada": prioridade,
            "metodologia": metodologia,
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
    try:
        result = bairros_alternativos_inteligentes(callback_context)
        callback_context.state["bairros_alternativos_pronto"] = result
    except Exception:
        pass  # falha silenciosa — não bloqueia o pipeline
    try:
        _telemetry_before(callback_context)
    except Exception:
        pass


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
            "Status competitivo vem de **busca real no Google Places** (raio 2km "
            "em cada bairro alternativo) — não de extrapolação do raio do bairro alvo."
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


def _a6_before_model_callback(callback_context, llm_request):
    """
    Antes de cada chamada ao modelo do A6, anexa o markdown pré-renderizado
    de Distribuição Geográfica + Bairros Alternativos à system instruction.

    Por que aqui (e não no `before_agent_callback`):
    o `before_agent_callback` popula state, mas ADK não injeta state no
    prompt automaticamente. Já o `before_model_callback` recebe o
    `llm_request` que vai pro modelo — `append_instructions` adiciona ao
    system_instruction de forma garantida.

    Idempotente: se o markdown já foi anexado em uma call anterior do
    mesmo turno, não duplica (verifica via marker no system instruction).
    """
    try:
        state = getattr(callback_context, "state", None)
        if state is None:
            return
        pronto = state.get("bairros_alternativos_pronto")
        if not pronto:
            return

        markdown = _renderizar_secao_bairros_alternativos(pronto)
        if not markdown:
            return

        # Idempotência: só anexa se ainda não foi anexado neste request
        existing_si = ""
        try:
            existing_si = llm_request.config.system_instruction or ""
        except Exception:
            existing_si = ""
        if "SEÇÃO PRÉ-COMPUTADA — BAIRROS ALTERNATIVOS" in existing_si:
            return

        llm_request.append_instructions([markdown])
    except Exception:
        pass  # falha silenciosa — nunca bloqueia o pipeline


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
            print(
                f"[A6 _extrair] inner_mc VAZIO mas state.market_context tem "
                f"type={tipo} len={len(raw_mc) if hasattr(raw_mc,'__len__') else '?'} "
                f"preview={preview!r}"
            )
            # Fallback 2: se mc tem chaves mas não 'market_context', tenta usar mc direto
            if isinstance(mc, dict) and mc:
                # mc pode ter campos achatados (sem aninhamento)
                if any(k in mc for k in ("cidade", "ticket_medio_mercado", "principais_redes_concorrentes")):
                    inner_mc = mc
                    cidade = inner_mc.get("cidade", "")
                    bairro = inner_mc.get("bairro", "")
                    print(f"[A6 _extrair] Recuperado via fallback flat: chaves={list(mc.keys())[:10]}")
        except Exception as e:
            print(f"[A6 _extrair] diagnostic falhou: {type(e).__name__}: {e}")

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
    cobertura_redes_a0 = _build_cobertura_redes_a0(cs_raw, inner_mc, inner_ic)

    # Scores podem estar no top-level OU dentro de inteligencia_competitiva
    score_concorrencia = (
        ic_raw.get("score_concorrencia")
        or inner_ic.get("score_concorrencia")
    )
    nivel_saturacao = (
        ic_raw.get("nivel_saturacao")
        or inner_ic.get("nivel_saturacao", "")
    )

    # ── Output: candidatos GeoScout (A1) ──
    geo_raw = _parse_market_context(state.get("candidatos_geoscout"))
    candidatos = (
        geo_raw.get("candidatos")
        if isinstance(geo_raw.get("candidatos"), list)
        else []
    )
    top_3 = candidatos[:3] if candidatos else []

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
            "scores_regionais": {
                "demografico": _safe_float(score_demografico),
                "competitivo": _safe_float(score_concorrencia),
                "viabilidade": _safe_float(score_viab),
            },
            "nivel_saturacao": nivel_saturacao,
            "rating_medio_concorrentes": _safe_float(
                ic_raw.get("rating_medio_concorrentes")
                or inner_ic.get("rating_medio_concorrentes")
            ),
            "top_3_candidatos": top_3,
            "competitors_set": inner_ic.get("concorrentes_detalhados", []),
            "dores_dominantes": inner_ic.get("dores_dominantes", []),
            "servicos_nao_oferecidos": inner_ic.get("servicos_nao_oferecidos", []),
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
            "alertas_financeiros": inner_fin.get("alertas", []),
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
            "market_context": _slim_market_context(inner_mc),
            # Schema v1.4 — cobertura A0: confronta redes que o Deep Research
            # listou vs as que realmente têm unidade no raio do bairro alvo.
            # Quando tem_redes_fantasma=true, o A6 renderiza aviso explícito
            # no markdown apontando que o DR pode estar inflando concorrência.
            "cobertura_redes_a0": cobertura_redes_a0,
        },
        "metadata_execucao": {
            # Schema v1.2: mantém só infos de execução. Dados ricos do
            # mercado migraram pra output_consolidado.market_context acima.
            "fonte_market_context": inner_mc.get("fonte", ""),
            "data_coleta_market_context": inner_mc.get("data_coleta", ""),
            "cached_market_context": inner_mc.get("cached"),
            "redes_a0_solicitadas": inner_mc.get("principais_redes_concorrentes", []),
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
        "fonte",
        "data_coleta",
        "cached",
    ]
    out = {k: inner_mc.get(k) for k in keys if inner_mc.get(k) is not None}
    if _INCLUIR_BRIEFING_COMPLETO and inner_mc.get("briefing_completo_md"):
        out["briefing_completo_md"] = inner_mc["briefing_completo_md"]
    return out


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
        print(
            "[a6:_build_cobertura_redes_a0] WARN: cs_raw veio como list, "
            f"esperado dict — usando fallback A3b. (len={len(cs_raw)})"
        )
        src = {}
    elif cs_raw is not None:
        print(
            f"[a6:_build_cobertura_redes_a0] WARN: cs_raw tipo inesperado "
            f"{type(cs_raw).__name__} — usando fallback."
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
                        redes_cobertas.append(rede)
                        break

    # Deriva nao_encontradas se ainda vazio (rede solicitada que NÃO está em cobertas)
    if not redes_nao_encontradas and redes_solicitadas:
        cobertas_set = {r.lower() for r in redes_cobertas}
        redes_nao_encontradas = [
            r for r in redes_solicitadas if r.lower() not in cobertas_set
        ]

    return {
        "redes_solicitadas": redes_solicitadas,
        "redes_cobertas": list(dict.fromkeys(redes_cobertas)),  # dedup preservando ordem
        "redes_nao_encontradas": list(dict.fromkeys(redes_nao_encontradas)),
        "concorrentes_excluidos": concorrentes_excluidos[:10],  # cap pra não inflar JSON
        "tem_redes_fantasma": bool(redes_nao_encontradas),
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
    try:
        relatorio = _extrair_relatorio_estruturado(callback_context)

        # ── A3c CompetitorMapper (modo SHADOW — GymSite #127) ──
        # A3c grava `oferta_concorrentes` no state. A6 NÃO consome no JSON
        # principal (shadow), mas anexamos aqui pro writer persistir em
        # competidores.oferta_mapeada e nós inspecionarmos via SQL.
        try:
            state_shadow = getattr(callback_context, "state", {}) or {}
            oferta_raw = state_shadow.get("oferta_concorrentes")
            if oferta_raw:
                # pode vir como string JSON do LLM com fence ```json
                if isinstance(oferta_raw, str):
                    txt = oferta_raw.strip()
                    if txt.startswith("```"):
                        lines = txt.split("\n")
                        txt = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
                    try:
                        oferta_raw = json.loads(txt)
                    except Exception:
                        oferta_raw = None
                if isinstance(oferta_raw, dict):
                    relatorio["oferta_concorrentes"] = oferta_raw
        except Exception:
            pass  # shadow nunca bloqueia

        _RELATORIOS_DIR.mkdir(parents=True, exist_ok=True)
        path = _RELATORIOS_DIR / f"{relatorio['id']}.json"
        path.write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Gravação paralela no Supabase (fail-safe — não bloqueia em erro)
        try:
            from db.supabase_writer import write_relatorio_failsafe
            state = getattr(callback_context, "state", {}) or {}
            markdown = state.get("relatorio_md") if isinstance(state.get("relatorio_md"), str) else None
            # Modo API HTTP: state["relatorio_id"] aponta pro stub pré-criado
            # pelo endpoint POST /api/relatorios. Quando ausente (CLI/adk web),
            # o writer insere um novo header com UUID gerado pelo Postgres.
            relatorio_id = state.get("relatorio_id") if isinstance(state.get("relatorio_id"), str) else None
            write_relatorio_failsafe(relatorio, markdown, relatorio_id=relatorio_id)
        except Exception:
            pass  # falha total do import/writer não bloqueia o pipeline
    except Exception:
        pass


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

---

## 📈 Scores Regionais

| Dimensão | Score (0-10) | Classificação |
|---|---|---|
| Demográfico | X.X | <classificação do A2> |
| Competitivo | X.X | <nivel_saturacao do A3> |
| Viabilidade financeira | X.X | <viabilidade do A4 melhor cenário> |

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
- **Serviços oferecidos:** <lista do servicos_oferecidos>
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
    before_agent_callback=_a6_precompute_callback,
    before_model_callback=_a6_before_model_callback,
    after_agent_callback=_a6_after_agent_callback,
    output_key="relatorio_md",
)
