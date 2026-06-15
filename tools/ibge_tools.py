# tools/ibge_tools.py
import httpx
import unicodedata
from typing import Optional

from tools.parametros_metodologia import param

IBGE_LOCAL = "https://servicodados.ibge.gov.br/api/v1/localidades"
IBGE_AGREGA = "https://servicodados.ibge.gov.br/api/v3/agregados"


def _strip_acentos(s: str) -> str:
    """Remove diacríticos pra comparação tolerante (Eusébio == Eusebio)."""
    nfkd = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))

CODIGOS_ESTADO = {
    "35": "SP", "33": "RJ", "31": "MG", "43": "RS", "41": "PR",
    "42": "SC", "29": "BA", "23": "CE", "26": "PE", "52": "GO",
    "53": "DF", "13": "AM", "15": "PA", "21": "MA", "22": "PI",
    "24": "RN", "25": "PB", "27": "AL", "28": "SE", "32": "ES",
    "50": "MS", "51": "MT", "11": "RO", "12": "AC", "14": "RR",
    "16": "AP", "17": "TO",
}
RENDA_MEDIA_UF = {
    "SP": 2150, "RJ": 1980, "MG": 1450, "RS": 1820, "PR": 1750,
    "SC": 1900, "BA": 980,  "CE": 870,  "PE": 960,  "GO": 1350,
    "DF": 3200, "AM": 1100, "PA": 950,  "ES": 1400, "MS": 1300,
    "MT": 1350, "default": 1200,
}

# Renda média per capita POR MUNICÍPIO (Censo IBGE 2022, dados oficiais).
# Substitui a média UF pra cidades onde a renda local diverge MUITO da média
# estadual — caso clássico de municípios de classe média alta em estados
# com sertão pobre (Eusébio/CE = R$ 1.835 vs CE estadual R$ 870).
#
# ⚠️ Censo IBGE é a cada 10 anos (próximo só em 2032). Pra dados intermediários,
# usar Search Grounding (PNAD Contínua trimestral) — TODO #89.
RENDA_PER_CAPITA_MUNICIPIO = {
    # RMF — Eusébio é um exemplo clássico do problema da média UF
    "2304400": 1572,  # Fortaleza
    "2304285": 1835,  # Eusébio (classe média alta RMF)
    "2303709": 730,   # Caucaia
    "2307650": 803,   # Maracanaú
    "2301109": 763,   # Aquiraz
    "2309706": 661,   # Pacatuba
    "2307700": 707,   # Maranguape
    "2305233": 712,   # Horizonte
    "2306256": 612,   # Itaitinga

    # Capitais
    "3550308": 2700,  # São Paulo
    "3304557": 2543,  # Rio de Janeiro
    "3106200": 2252,  # Belo Horizonte
    "4106902": 2589,  # Curitiba
    "4314902": 2521,  # Porto Alegre
    "2927408": 1389,  # Salvador
    "5208707": 2024,  # Goiânia
    "1302603": 1487,  # Manaus
    "2611606": 1655,  # Recife
    "5300108": 3823,  # Brasília
    "3205309": 2147,  # Vitória
    "4205407": 2812,  # Florianópolis
    "2507507": 1556,  # João Pessoa
    "2408102": 1391,  # Natal
    "1501402": 1289,  # Belém

    # RMSP
    "3518800": 1510,  # Guarulhos
    "3509502": 2380,  # Campinas
    "3547809": 2105,  # Santo André
    "3534401": 2052,  # Osasco
    "3548708": 2186,  # São Bernardo do Campo

    # RMRJ
    "3303302": 3108,  # Niterói (renda mais alta RJ)
    "3304904": 1187,  # São Gonçalo
    "3301702": 1267,  # Duque de Caxias
    "3303500": 1147,  # Nova Iguaçu
}


# Fallback IBGE — capitais + principais municípios de RMs.
# Chave é nome normalizado (lowercase, sem acentos) pra lookup robusto.
_MUNICIPIOS_IBGE = {
    # Capitais
    "fortaleza":     ("2304400", "Fortaleza", "CE"),
    "sao paulo":     ("3550308", "São Paulo", "SP"),
    "rio de janeiro": ("3304557", "Rio de Janeiro", "RJ"),
    "belo horizonte": ("3106200", "Belo Horizonte", "MG"),
    "curitiba":      ("4106902", "Curitiba", "PR"),
    "porto alegre":  ("4314902", "Porto Alegre", "RS"),
    "salvador":      ("2927408", "Salvador", "BA"),
    "goiania":       ("5208707", "Goiânia", "GO"),
    "manaus":        ("1302603", "Manaus", "AM"),
    "recife":        ("2611606", "Recife", "PE"),
    "brasilia":      ("5300108", "Brasília", "DF"),
    "vitoria":       ("3205309", "Vitória", "ES"),
    "florianopolis": ("4205407", "Florianópolis", "SC"),
    "joao pessoa":   ("2507507", "João Pessoa", "PB"),
    "natal":         ("2408102", "Natal", "RN"),
    "aracaju":       ("2800308", "Aracaju", "SE"),
    "maceio":        ("2704302", "Maceió", "AL"),
    "teresina":      ("2211001", "Teresina", "PI"),
    "sao luis":      ("2111300", "São Luís", "MA"),
    "campo grande":  ("5002704", "Campo Grande", "MS"),
    "cuiaba":        ("5103403", "Cuiabá", "MT"),
    "macapa":        ("1600303", "Macapá", "AP"),
    "boa vista":     ("1400100", "Boa Vista", "RR"),
    "porto velho":   ("1100205", "Porto Velho", "RO"),
    "rio branco":    ("1200401", "Rio Branco", "AC"),
    "palmas":        ("1721000", "Palmas", "TO"),
    "belem":         ("1501402", "Belém", "PA"),

    # RMF (Região Metropolitana de Fortaleza) — fix Eusébio bug 11/05
    "eusebio":       ("2304285", "Eusébio", "CE"),
    "caucaia":       ("2303709", "Caucaia", "CE"),
    "maracanau":     ("2307650", "Maracanaú", "CE"),
    "aquiraz":       ("2301109", "Aquiraz", "CE"),
    "pacatuba":      ("2309706", "Pacatuba", "CE"),
    "maranguape":    ("2307700", "Maranguape", "CE"),
    "horizonte":     ("2305233", "Horizonte", "CE"),
    "itaitinga":     ("2306256", "Itaitinga", "CE"),

    # RMSP — top municípios
    "guarulhos":     ("3518800", "Guarulhos", "SP"),
    "campinas":      ("3509502", "Campinas", "SP"),
    "santo andre":   ("3547809", "Santo André", "SP"),
    "osasco":        ("3534401", "Osasco", "SP"),
    "sao bernardo do campo": ("3548708", "São Bernardo do Campo", "SP"),

    # RMRJ
    "niteroi":       ("3303302", "Niterói", "RJ"),
    "sao goncalo":   ("3304904", "São Gonçalo", "RJ"),
    "duque de caxias": ("3301702", "Duque de Caxias", "RJ"),
    "nova iguacu":   ("3303500", "Nova Iguaçu", "RJ"),
}


def buscar_municipio(nome: str, uf: str) -> Optional[dict]:
    """
    Busca código IBGE do município. Dict fallback rápido; rede só pra outros.

    Tolerante a acentos (Eusébio == Eusebio) — fix de bug 11/05 onde
    o A0 mandava "Eusebio" mas IBGE tinha "Eusébio".
    """
    # 1) Dict fallback (sem rede) — chave normalizada sem acentos
    chave_norm = _strip_acentos(nome.strip().lower())
    if chave_norm in _MUNICIPIOS_IBGE:
        codigo, nome_oficial, uf_oficial = _MUNICIPIOS_IBGE[chave_norm]
        return {"codigo": codigo, "nome": nome_oficial, "uf": uf_oficial}

    # 2) API do IBGE — comparação tolerante a acentos
    if not uf:
        return None  # sem UF não consegue listar municípios

    try:
        with httpx.Client(timeout=20) as c:
            r = c.get(f"{IBGE_LOCAL}/estados/{uf}/municipios")
        if r.status_code != 200:
            return None
        municipios = r.json()
        nome_norm = _strip_acentos(nome.lower().strip())
        for m in municipios:
            m_norm = _strip_acentos(m["nome"].lower())
            # Match exato ou substring (ambos os lados normalizados)
            if nome_norm == m_norm or nome_norm in m_norm or m_norm in nome_norm:
                return {"codigo": str(m["id"]), "nome": m["nome"], "uf": uf.upper()}
        return None
    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPError, Exception):
        return None


def buscar_populacao(codigo_municipio: str) -> dict:
    """Busca população total pelo Censo 2022, com fallback para estimativas."""
    # Fallback com populações reais (Censo IBGE 2022)
    populacoes_conhecidas = {
        # Capitais
        "2304400": 2428678,  # Fortaleza
        "3550308": 11451245, # São Paulo
        "3304557": 6211223,  # Rio de Janeiro
        "3106200": 2315560,  # Belo Horizonte
        "4106902": 1773733,  # Curitiba
        "4314902": 1332570,  # Porto Alegre
        "2927408": 2418005,  # Salvador
        "5208707": 1437237,  # Goiânia
        "1302603": 2063547,  # Manaus
        "2611606": 1488920,  # Recife
        "5300108": 2817381,  # Brasília
        "3205309": 322869,   # Vitória
        "4205407": 537211,   # Florianópolis
        "2507507": 833932,   # João Pessoa
        "2408102": 751300,   # Natal
        "1501402": 1303403,  # Belém
        # RMF (Censo 2022)
        "2304285": 57345,    # Eusébio
        "2303709": 365212,   # Caucaia
        "2307650": 224804,   # Maracanaú
        "2301109": 81252,    # Aquiraz
        "2309706": 79945,    # Pacatuba
        "2307700": 117832,   # Maranguape
        "2305233": 84169,    # Horizonte
        "2306256": 41687,    # Itaitinga
        # RMSP
        "3518800": 1291784,  # Guarulhos
        "3509502": 1139047,  # Campinas
        "3547809": 748919,   # Santo André
        "3534401": 728615,   # Osasco
        "3548708": 810979,   # São Bernardo do Campo
        # RMRJ
        "3303302": 481480,   # Niterói
        "3304904": 896744,   # São Gonçalo
        "3301702": 808870,   # Duque de Caxias
        "3303500": 758231,   # Nova Iguaçu
    }

    if codigo_municipio in populacoes_conhecidas:
        return {"populacao_total": populacoes_conhecidas[codigo_municipio]}

    # Tenta a API do IBGE
    url = (f"https://servicodados.ibge.gov.br/api/v3/agregados/9514"
           f"/periodos/2022/variaveis/93/localidades/N6[{codigo_municipio}]")
    try:
        with httpx.Client(timeout=15) as c:
            data = c.get(url).json()
        val = data[0]["resultados"][0]["series"][0]["serie"].get("2022", "0")
        return {"populacao_total": int(val.replace(".", "").replace(",", ""))}
    except Exception as e:
        return {"populacao_total": 500000, "erro": str(e),
                "aviso": "Usando estimativa padrão — verifique código IBGE"}


def estimar_faixa_etaria(populacao_total: int, faixa: str = "18-45") -> dict:
    """Estima população na faixa etária alvo.

    % da faixa = dado aberto (pirâmide etária Censo 2022); default é fallback
    nacional via param(). Público potencial = % da faixa com interesse fitness
    (benchmark ACAD), também via param().
    """
    pcts = {
        "15-29": param("faixa_pct_15_29"), "18-35": param("faixa_pct_18_35"),
        "18-45": param("faixa_pct_18_45"), "20-40": param("faixa_pct_20_40"),
        "25-50": param("faixa_pct_25_50"),
    }
    pct = pcts.get(faixa, param("faixa_pct_default"))
    pop_faixa = int(populacao_total * pct)
    return {
        "faixa_etaria": faixa,
        "percentual": pct,
        "populacao_na_faixa": pop_faixa,
        "publico_potencial": int(pop_faixa * param("penetracao_potencial_fitness")),
    }


def buscar_renda(codigo_municipio: str) -> dict:
    """
    Retorna renda média per capita. Tenta em cascata:
    1. Dict municipal (Censo IBGE 2022 oficial) — preciso, instantâneo
    2. Fallback UF — média estadual quando município não está no dict

    Pra cidades pequenas fora do dict, considere chamar
    buscar_renda_search_grounding_async() pra dados PNAD mais recentes.
    """
    # 1. Dict municipal — fonte primária
    if codigo_municipio in RENDA_PER_CAPITA_MUNICIPIO:
        renda = RENDA_PER_CAPITA_MUNICIPIO[codigo_municipio]
        uf = CODIGOS_ESTADO.get(codigo_municipio[:2], "??")
        return {
            "renda_media": renda,
            "uf": uf,
            "fonte": "Censo IBGE 2022 (per capita municipal)",
            "granularidade": "municipal",
        }

    # 2. Fallback: média da UF
    uf = CODIGOS_ESTADO.get(codigo_municipio[:2], "SP")
    return {
        "renda_media": RENDA_MEDIA_UF.get(uf, RENDA_MEDIA_UF["default"]),
        "uf": uf,
        "fonte": f"Média UF {uf} (município sem dado específico no Censo 2022)",
        "granularidade": "uf",
        "aviso": (
            "Renda baseada na média estadual — município pode divergir muito "
            "(ex: Eusébio/CE renda R$ 1.835 vs CE estadual R$ 870). "
            "Considerar consulta PNAD Contínua via Search Grounding."
        ),
    }


async def buscar_renda_search_grounding_async(cidade: str, uf: str) -> dict:
    """
    Fallback dinâmico: usa Gemini Search Grounding pra buscar renda média
    do município em fontes recentes (PNAD Contínua, IBGE Cidades, Atlas Brasil).

    Útil quando:
    - Município não está no dict RENDA_PER_CAPITA_MUNICIPIO (cidade pequena)
    - Quer dado mais recente que Censo 2022
    - Cross-check com fonte secundária

    Pricing: 1 chamada Gemini Flash ~$0.001. NÃO chama por default em todo run
    pra não inflar custo; chame só quando A2 precisar (cidade pequena).

    Args:
        cidade, uf: localização do município.

    Returns:
        dict { "renda_media": float, "fonte": str, "ano": int }
        ou {} se Search Grounding falhar.
    """
    import re
    from tools.gemini_search_grounding import pesquisar_no_google_grounding

    query = (
        f"Qual é a renda média per capita ou domiciliar mensal em {cidade}/{uf} "
        f"em 2024? Cite valor numérico em reais e fonte (IBGE, PNAD, Atlas Brasil, "
        f"Wikipedia). Não me dê média estadual — quero do município específico."
    )
    cache_key = f"renda_municipio:{cidade}:{uf}".lower()

    try:
        resp = await pesquisar_no_google_grounding(query, cache_key=cache_key)
    except Exception:
        return {}

    if not isinstance(resp, str) or resp.startswith("[Search Grounding"):
        return {}

    # Extrai valor R$ XX.XXX,XX ou R$ X.XXX do texto retornado
    pattern_renda = re.compile(
        r"R\$\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{1,2})?)", re.IGNORECASE
    )
    valores = []
    for m in pattern_renda.finditer(resp):
        try:
            v = float(m.group(1).replace(".", "").replace(",", "."))
            if 200.0 <= v <= 50000.0:  # range plausível pra renda BR
                valores.append(v)
        except ValueError:
            continue

    if not valores:
        return {}

    # Mediana dos valores extraídos (algumas respostas trazem múltiplos)
    valores_ord = sorted(valores)
    mediana = valores_ord[len(valores_ord) // 2]

    return {
        "renda_media": mediana,
        "valores_coletados": valores_ord[:10],
        "fonte": "Search Grounding (PNAD/IBGE/Atlas, fontes mistas)",
        "granularidade": "municipal_estimada",
    }


def calcular_score_demografico(pop_faixa: int, renda_media: float) -> float:
    """Score demográfico de 0 a 10. Cortes via param() (calibração metodológica)."""
    score = 0.0
    if pop_faixa >= param("score_demo_pop_alta"): score += 4.0
    elif pop_faixa >= param("score_demo_pop_media"): score += 3.0
    elif pop_faixa >= param("score_demo_pop_baixa"): score += 2.0
    elif pop_faixa >= param("score_demo_pop_minima"):  score += 1.0

    if renda_media >= param("score_demo_renda_alta"): score += 4.0
    elif renda_media >= param("score_demo_renda_media"): score += 3.0
    elif renda_media >= param("score_demo_renda_baixa"): score += 2.0
    elif renda_media >= param("score_demo_renda_minima"):  score += 1.0

    return min(score + param("score_demo_base"), 10.0)


def analise_demografica_completa(cidade: str, uf: str, faixa: str = "18-45") -> dict:
    """
    Macro-tool: executa as 5 etapas demográficas em UMA chamada.

    Substitui buscar_municipio + buscar_populacao + estimar_faixa_etaria +
    buscar_renda + calcular_score_demografico, eliminando 5 round-trips LLM
    no DemoAnalyst (cada round-trip carrega ~33k tokens de histórico).

    Args:
        cidade: nome do município (ex: "Fortaleza")
        uf: sigla do estado (ex: "CE")
        faixa: faixa etária alvo (default "18-45")

    Returns:
        dict consolidado com todos os campos demográficos esperados pelo A2.
        Em caso de erro de busca, inclui chave "erro" com descrição.
    """
    mun = buscar_municipio(cidade, uf)
    if not mun:
        # Fallback gracioso: usa renda da UF + população default em vez
        # de bloquear o pipeline. A2 segue com dados aproximados em vez
        # de retornar "não disponível" pro relatório.
        uf_upper = (uf or "").upper()
        renda_estimada = RENDA_MEDIA_UF.get(uf_upper, RENDA_MEDIA_UF["default"])
        pop_default = 50000  # estimativa conservadora pra cidade pequena RM
        pct_default = param("faixa_pct_default")
        pop_faixa_default = int(pop_default * pct_default)
        score = calcular_score_demografico(pop_faixa_default, renda_estimada)
        return {
            "erro": f"Município não encontrado no IBGE: {cidade}/{uf}",
            "fallback_usado": True,
            "municipio": cidade,
            "codigo_ibge": None,
            "uf": uf_upper,
            "populacao_total": pop_default,
            "faixa_etaria_alvo": faixa,
            "percentual_faixa": pct_default,
            "populacao_faixa_18_45": pop_faixa_default,
            "publico_potencial_fitness": int(pop_faixa_default * param("penetracao_potencial_fitness")),
            "renda_media_domiciliar": renda_estimada,
            "renda_uf_fonte": uf_upper,
            "score_demografico": score,
            "classificacao": "ESTIMATIVA",
            "fonte_populacao": "fallback (município não encontrado IBGE)",
            "fonte_renda": f"Média UF {uf_upper}",
            "aviso": (
                f"Município '{cidade}' não encontrado no IBGE — usando "
                f"estimativa UF {uf_upper} (renda R$ {renda_estimada}, pop 50k). "
                f"Validar manualmente pelos dados reais do IBGE."
            ),
        }

    pop_data = buscar_populacao(mun["codigo"])
    pop_total = int(pop_data.get("populacao_total", 0))

    faixa_data = estimar_faixa_etaria(pop_total, faixa)
    pop_faixa = int(faixa_data["populacao_na_faixa"])
    publico = int(faixa_data["publico_potencial"])

    renda_data = buscar_renda(mun["codigo"])
    renda = float(renda_data["renda_media"])

    # pyrefly: ignore [unnecessary-type-conversion]
    score = float(calcular_score_demografico(pop_faixa, renda))

    if score >= param("demo_limiar_excelente"):
        classificacao = "EXCELENTE"
    elif score >= param("demo_limiar_bom"):
        classificacao = "BOM"
    elif score >= param("demo_limiar_regular"):
        classificacao = "REGULAR"
    else:
        classificacao = "FRACO"

    out = {
        "municipio": mun["nome"],
        "codigo_ibge": mun["codigo"],
        "uf": mun["uf"],
        "populacao_total": pop_total,
        "faixa_etaria_alvo": faixa,
        "percentual_faixa": faixa_data["percentual"],
        "populacao_faixa_18_45": pop_faixa,
        "publico_potencial_fitness": publico,
        "renda_media_domiciliar": renda,
        "renda_uf_fonte": renda_data["uf"],
        "score_demografico": score,
        "classificacao": classificacao,
        "fonte_populacao": pop_data.get("aviso", "IBGE Censo 2022"),
        "fonte_renda": renda_data["fonte"],
        # Granularidade da renda: "municipal" (Censo 2022) ou "uf" (fallback)
        # A6 usa pra avisar no relatório quando a renda é só média estadual.
        "renda_granularidade": renda_data.get("granularidade", "uf"),
    }
    # Se caiu no fallback UF, propaga o aviso pra A2/A6 sinalizarem no markdown
    if renda_data.get("aviso"):
        out["renda_aviso"] = renda_data["aviso"]
    return out
