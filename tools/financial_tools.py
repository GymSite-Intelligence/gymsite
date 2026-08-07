from typing import Any, Optional
# tools/financial_tools.py
"""
Motor de modelagem financeira para viabilidade de academias (schema v2).

Este módulo implementa um modelo financeiro determinístico que projeta a
viabilidade de uma academia em 3 cenários (low-cost, mid-market, premium).
Os cálculos NÃO são baseados em benchmarks diretos, mas sim em uma metodologia
de projeção de receita, custos e investimento, cujas premissas são parametrizadas
e auditáveis via `tools.parametros_metodologia`.

📚 FONTES PRIMÁRIAS:
  - ACAD Brasil (Associação Brasileira de Academias) — relatórios anuais 2023/2024
  - SEBRAE — "Como abrir uma academia" + "Painel do setor fitness 2024"
  - Smart Fit Holdings (BVMF: SMFT3) — releases trimestrais 2023-2024

📊 METODOLOGIA DE CÁLCULO:
  - **Receita:** Projeção de matrículas por m² (calibração por modelo) × ticket médio (ajustado pela renda local) × (1 - inadimplência).
  - **Custos:** Detalhamento de 12 linhas de OPEX, incluindo folha (piso + % da receita), marketing e custos variáveis como água (por visita) e sistema (por aluno).
  - **Impostos:** Cálculo dinâmico do Simples Nacional (Anexo III vs V) baseado no Fator R (folha/faturamento).
  - **Investimento (CAPEX):** Custo de equipamentos (via kits), obra (índices SINAPI), frete (ANTT), projeto e capital de giro.
  - **Viabilidade:** Payback, VPL, TIR e score de viabilidade (0-10) baseado em payback e ocupação no break-even.
  - **Risco:** Análise de sensibilidade (stress tests) e guardrails de ocupação imobiliária.

⚠️ As premissas (ex: matrículas/m², % de custos) são benchmarks do setor, mas o CÁLCULO é uma modelagem completa. Todas as premissas são recalibráveis via `parametros_metodologia`.
"""

from tools.parametros_metodologia import param, param_int, param_por_modelo

BENCHMARKS_ALUGUEL = {
    "São Paulo": {"min": 45, "med": 85, "max": 150},
    "Rio de Janeiro": {"min": 40, "med": 75, "max": 130},
    "Brasília": {"min": 35, "med": 65, "max": 110},
    "Belo Horizonte": {"min": 25, "med": 50, "max": 90},
    "Curitiba": {"min": 28, "med": 55, "max": 95},
    "Porto Alegre": {"min": 30, "med": 58, "max": 100},
    "Salvador": {"min": 20, "med": 38, "max": 65},
    "Fortaleza": {"min": 18, "med": 35, "max": 60},
    "Recife": {"min": 18, "med": 35, "max": 62},
    "Goiânia": {"min": 22, "med": 42, "max": 72},
    "default": {"min": 20, "med": 40, "max": 70},
}

# Constantes sourceadas via param() — LAZY (PEP 562 __getattr__).
# Não congelar no import: override Supabase + clear_param_cache() passam a valer
# no próximo acesso. Ver docs/metodologia/data_lineage.md.


def _ticket_faixas() -> dict:
    return {
        "low": {
            "label": "Low Cost",
            "ticket_medio": param("ticket_low"),
            "descricao": "Modelo econômico 24h, sem personal, autoatendimento",
            "exemplos": "Smart Fit, Bluefit, Selfit",
        },
        "mid": {
            "label": "Mid Market",
            "ticket_medio": param("ticket_mid"),
            "descricao": "Modelo intermediário com aulas em grupo e suporte",
            "exemplos": "Bodytech entry, academias regionais premium",
        },
        "premium": {
            "label": "Premium",
            "ticket_medio": param("ticket_premium"),
            "descricao": "Modelo completo com personal, nutrição e experiência",
            "exemplos": "Bodytech, Bio Ritmo, academias boutique",
        },
    }


def _matriculados_por_m2() -> dict:
    return {
        m: {cal: param(f"matr_m2_{m}_{cal}")
            for cal in ("conservador", "realista", "agressivo")}
        for m in ("low", "mid", "premium")
    }


def _custos_detalhados_base() -> dict:
    return {
        "condominio_pct_aluguel": param("custo_condominio_pct_aluguel"),
        "iptu_mensal_base": param("custo_iptu_mensal_base"),
        "energia_por_m2": param("custo_energia_por_m2"),
        "agua_por_m2": param("custo_agua_por_m2"),
        "internet_mensal": param("custo_internet_mensal"),
        "folha_por_modelo": {
            "low": param("folha_min_low"),
            "mid": param("folha_min_mid"),
            "premium": param("folha_min_premium"),
        },
        "manutencao_pct_capex": param("custo_manutencao_pct_capex"),
        "contabilidade_mensal": param("custo_contabilidade_mensal"),
        "sistema_gestao_mensal": param("custo_sistema_gestao_mensal"),
        "seguro_pct_capex": param("custo_seguro_pct_capex"),
        "outros_pct_receita": param("custo_outros_pct_receita"),
    }


def _capex_detalhado_base() -> dict:
    return {
        "equipamentos_por_m2": param_por_modelo("capex_equip_m2"),
        "obra_adaptacao_por_m2": param_por_modelo("capex_obra_m2"),
        "projeto_arquitetonico": param("capex_projeto_arquitetonico"),
        "alvara_e_taxas": param("capex_alvara_taxas"),
        "contingencia_pct": param("capex_contingencia_pct"),
        "capital_giro_meses": param_int("capex_capital_giro_meses"),
    }


_LAZY_PARAM_ATTRS = frozenset({
    "TICKET_MEDIO", "ALUNOS_POR_M2", "TICKET_FAIXAS", "MATRICULADOS_POR_M2",
    "CAPACIDADE_SIMULTANEA_POR_M2", "FREQUENCIA_SEMANAL", "PICO_SHARE_POR_MODELO",
    "TAXA_INADIMPLENCIA_POR_MODELO", "TAXA_INADIMPLENCIA",
    "TAXA_CANCELAMENTO_MENSAL_POR_MODELO", "TAXA_CANCELAMENTO_MENSAL",
    "CUSTOS_DETALHADOS_BASE", "CUSTOS_MARKETING_PCT", "FOLHA_PCT_FATURAMENTO",
    "OCUPACAO_TETO", "CAPEX_DETALHADO_BASE", "TICKET_RENDA_PCT", "CUSTO_CAPITAL_ANUAL",
})


def __getattr__(name: str) -> Any:
    """Resolve constantes param()-backed sob demanda (não no import)."""
    if name == "TICKET_MEDIO":
        return param("ticket_medio_nacional")
    if name == "ALUNOS_POR_M2":
        return param("alunos_por_m2_legado")
    if name == "TICKET_FAIXAS":
        return _ticket_faixas()
    if name == "MATRICULADOS_POR_M2":
        return _matriculados_por_m2()
    if name == "CAPACIDADE_SIMULTANEA_POR_M2":
        return param_por_modelo("capacidade_simultanea")
    if name == "FREQUENCIA_SEMANAL":
        return param_por_modelo("frequencia_semanal")
    if name == "PICO_SHARE_POR_MODELO":
        return param_por_modelo("pico_share")
    if name == "TAXA_INADIMPLENCIA_POR_MODELO":
        return param_por_modelo("inadimplencia")
    if name == "TAXA_INADIMPLENCIA":
        return param("inadimplencia_mid")
    if name == "TAXA_CANCELAMENTO_MENSAL_POR_MODELO":
        return param_por_modelo("churn_mensal")
    if name == "TAXA_CANCELAMENTO_MENSAL":
        return param("churn_mensal_mid")
    if name == "CUSTOS_DETALHADOS_BASE":
        return _custos_detalhados_base()
    if name == "CUSTOS_MARKETING_PCT":
        return param_por_modelo("marketing_pct")
    if name == "FOLHA_PCT_FATURAMENTO":
        return param_por_modelo("folha_pct_fat")
    if name == "OCUPACAO_TETO":
        return param_por_modelo("ocupacao_teto")
    if name == "CAPEX_DETALHADO_BASE":
        return _capex_detalhado_base()
    if name == "TICKET_RENDA_PCT":
        return param_por_modelo("ticket_renda_pct")
    if name == "CUSTO_CAPITAL_ANUAL":
        return param("custo_capital_anual")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _lp(name: str) -> Any:
    """Lazy const neste módulo — bare name NÃO passa por __getattr__."""
    return __getattr__(name)


CUSTOS_FIXOS_BASE = {
    "aluguel_por_m2": 35.0,
    "condominio_pct": 0.15,
    "energia_por_m2": 12.0,
    "folha_minima": 18000.0,
    "manutencao_pct": 0.03,
    "marketing_pct": 0.08,
    "sistema_gestao": 800.0,
}

CAPEX_BASE = {
    "equipamentos_por_m2": 450.0,
    "obra_adaptacao_por_m2": 280.0,
    "projeto_arquitetonico": 15000.0,
    "alvara_e_taxas": 8000.0,
    "capital_giro_meses": 3,
}


# ─────────────────────────────────────────────────────────────────────────
# SCHEMA v2 — Constantes do novo modelo financeiro
# ─────────────────────────────────────────────────────────────────────────

# CNO / prospecção: códigos de situação da obra (RFB — campo Situação no CSV)
CNO_SITUACAO_EM_CURSO = frozenset({"01", "02", "03", "04"})
CNO_SITUACAO_ENCERRADA = frozenset({"15"})


def projecao_demanda_receita_obra(
    area_m2: float,
    faixa: str = "mid",
    *,
    ticket_override: float | None = None,
) -> dict:
    """
    Projeção operacional a partir de m² (CNO ou input manual).

    Mesma lógica de `calcular_viabilidade_3_cenarios`: matrículas pagantes em
    3 calibrações; receita = matrículas × ticket × (1 − inadimplência).

    Retorno é **estimativa** (benchmark A4), não dado CNPJ/CNO.
    """
    if area_m2 <= 0:
        return {"status": "erro", "motivo": "area_m2 inválida"}

    matr_m2 = _lp("MATRICULADOS_POR_M2")
    faixa_key = faixa if faixa in matr_m2 else "mid"
    faixa_info = _lp("TICKET_FAIXAS")[faixa_key]
    ticket = ticket_override if ticket_override is not None else faixa_info["ticket_medio"]
    inad = _lp("TAXA_INADIMPLENCIA_POR_MODELO")[faixa_key]
    ticket_realizado = round(ticket * (1.0 - inad), 2)

    calibracoes = matr_m2[faixa_key]
    matriculas: dict[str, dict] = {}
    receita_mensal_estimada: dict[str, float] = {}
    for cal_id, mpm in calibracoes.items():
        n = int(area_m2 * mpm)
        matriculas[cal_id] = {
            "valor": n,
            "matr_por_m2": mpm,
            "densidade_maxima_m2": mpm,  # alias legível em relatórios CNO
        }
        receita_mensal_estimada[cal_id] = round(n * ticket_realizado, 2)

    return {
        "status": "ok",
        "tipo": "projecao_estimativa",
        "fonte_premissas": "financial_tools — mesmo benchmark do A4",
        "area_m2": round(area_m2, 2),
        "faixa_ticket": faixa_key,
        "faixa_label": faixa_info["label"],
        "ticket_nominal": round(ticket, 2),
        "taxa_inadimplencia": inad,
        "ticket_realizado": ticket_realizado,
        "matriculas": matriculas,
        "receita_mensal_estimada": receita_mensal_estimada,
        "receita_base_calibracao": "realista",
        "nota": (
            "Projeção para prospecção/parâmetros. Não é faturamento declarado "
            "nem garantia de ocupação na abertura."
        ),
    }

# Capacidade simultânea / freq / pico / inad / churn / custos / CAPEX / ticket_renda /
# CUSTO_CAPITAL — via __getattr__ (externo) ou builders/param() (interno neste arquivo).
# Não reatribuir no import: senão freeze + clear_param_cache() não pega.

# Sensibilidade — stress tests aplicados em cima do cenário "realista".
# 1.7: o stress de ocupação (aluguel +20%) reprova quando a razão de ocupação
# (aluguel+condomínio+IPTU)/faturamento ultrapassa o teto do modelo.
STRESS_TESTS = [
    {"id": "aluguel_mais_20pct",     "label": "Aluguel +20%",     "delta_aluguel": 0.20},
    {"id": "matriculas_menos_30pct", "label": "Matrículas -30%",  "delta_matriculas": -0.30},
    {"id": "ticket_menos_15pct",     "label": "Ticket -15%",      "delta_ticket": -0.15},
    {"id": "ocupacao_aluguel_mais_20pct", "label": "Ocupação (aluguel +20%)",
     "delta_aluguel": 0.20, "check_ocupacao": True},
    # Task #19: disciplina de folha escorrega (PJ/MEI) → Fator R < 28% → Anexo V
    # (+9,5pp sobre TODO o faturamento). O estresse fiscal mais comum do setor:
    # 40-48% dos centros contratam PJ (Panorama Fitness Brasil 2025).
    {"id": "fiscal_anexo_v", "label": "Fiscal: Fator R < 28% (Anexo V)",
     "forca_anexo_v": True},
]


def estimar_aluguel(cidade: str, area_m2: float) -> dict:
    bench = BENCHMARKS_ALUGUEL.get(cidade, BENCHMARKS_ALUGUEL["default"])
    return {
        "aluguel_min": round(bench["min"] * area_m2, 2),
        "aluguel_estimado": round(bench["med"] * area_m2, 2),
        "aluguel_max": round(bench["max"] * area_m2, 2),
        "preco_m2_estimado": bench["med"],
    }


def calcular_investimento(area_m2: float) -> dict:
    reforma_med = ((800 + 2000) / 2) * area_m2
    equip_med = ((300 + 600) / 2) * area_m2
    capital_giro = 50000
    return {
        "custo_reforma": round(reforma_med, 2),
        "custo_equipamentos": round(equip_med, 2),
        "capital_giro": capital_giro,
        "investimento_total": round(reforma_med + equip_med + capital_giro, 2),
    }


def calcular_viabilidade(aluguel_mensal: float, investimento_total: float,
                          area_m2: float, ticket: float | None = None) -> dict:
    if ticket is None:
        ticket = float(_lp("TICKET_MEDIO"))
    custos_fixos = (
        aluguel_mensal
        + max(8000, area_m2 * 8)   # folha
        + area_m2 * 12             # energia
        + area_m2 * 2              # água
        + 800                      # internet
        + area_m2 * 3              # manutenção
        + max(2000, aluguel_mensal * 0.10)  # marketing
        + 1300                     # contabilidade + seguro + outros
    )

    margem = ticket - ticket * param("margem_operacional_ticket_pct")
    break_even = int(custos_fixos / margem) + 1
    capacidade = int(area_m2 * _lp("ALUNOS_POR_M2"))

    # Projeção 6 meses
    alunos_proj = int(break_even * param("fator_projecao_6m"))
    lucro_proj = (alunos_proj * margem) - custos_fixos
    payback = int(investimento_total / max(lucro_proj, 1)) if lucro_proj > 0 else 999

    # Score 0-10 (cortes via param — calibração metodológica)
    score = 0.0
    if payback <= param("payback_limiar_excelente"): score += 4.0
    elif payback <= param("payback_limiar_bom"): score += 3.0
    elif payback <= param("payback_limiar_regular"): score += 2.0
    elif payback <= param("payback_limiar_fraco"): score += 1.0

    ocupacao_break = break_even / capacidade if capacidade > 0 else 1
    if ocupacao_break < param("ocupacao_break_otima"): score += 3.0
    elif ocupacao_break < param("ocupacao_break_boa"): score += 2.0
    elif ocupacao_break < param("ocupacao_break_limite"): score += 1.0

    alertas = []
    if aluguel_mensal > investimento_total * 0.05:
        alertas.append("⚠️ Aluguel representa mais de 5% do investimento total")
    if break_even > capacidade * 0.70:
        alertas.append("⚠️ Break-even exige mais de 70% da capacidade máxima")
    if payback > 48:
        alertas.append("⚠️ Payback acima de 48 meses — risco elevado")

    return {
        "custos_fixos_mensais": round(custos_fixos, 2),
        "break_even_alunos": break_even,
        "capacidade_maxima_alunos": capacidade,
        "payback_meses": payback,
        "score_viabilidade": round(min(score + 3.0, 10.0), 2),
        "alertas": alertas,
    }


def cac_teto_reposicao(marketing_mensal: float, matriculas: int, churn_mensal: float) -> dict:
    """Churn deixa de ser decorativo (task #34): quanto custa MANTER a base.

    reposicoes = matrículas × churn (quem sai todo mês e precisa ser reposto
    só pra receita ficar de pé). cac_teto = verba de marketing ÷ reposições —
    se o CAC real da praça passar disso, a base encolhe com a verba atual.
    """
    reposicoes = int(round(matriculas * churn_mensal))
    return {
        "reposicoes_mes_churn": reposicoes,
        "cac_teto_reposicao": (
            round(marketing_mensal / reposicoes, 2) if reposicoes > 0 else None
        ),
    }


def custo_agua_mensal(area_m2: float, agua_por_m2: float, visitas_mes: float) -> float:
    """Água escala com VISITAS, não só com m² (task #33, confronto Gemini).

    Antes era area × R$/m² → idêntico nos 3 modelos, otimista pro low-cost
    (~4× mais gente = mais chuveiro/bebedouro). Premissas rotuladas:
    13 L/visita (5 L base sanitário/bebedouro + 20% das visitas tomam banho
    de 40 L) × tarifa comercial R$ 15/m³. O m² vira PISO (banheiros/limpeza
    existem mesmo com academia vazia).
    """
    piso = area_m2 * agua_por_m2
    consumo_m3 = visitas_mes * 0.013          # 13 L/visita
    variavel = consumo_m3 * 15.0              # R$/m³ comercial (banda conservadora)
    return round(max(piso, variavel), 2)


def custo_sistema_gestao(base_mensal: float, matriculas: int) -> float:
    """ERP fitness escala com a base de alunos (task #32, confronto Gemini).

    Contratos Pacto/Evo/Next são escalonados por tamanho do banco de alunos;
    acima de ~1.500 vidas a franquia comum rompe e o contrato sobe pra faixa
    de R$ 1.200+ (1,5× a base de R$ 800). Antes era constante — subdimensionava
    exatamente o modelo low-cost, que tem a maior base.
    """
    return round(base_mensal * (1.5 if matriculas > 1500 else 1.0), 2)


def calcular_break_even_alunos(
    custos_fixos_puros: float,
    ticket_realizado: float,
    mkt_pct: float = 0.0,
    outros_pct: float = 0.0,
    aliquota_tributos: float = 0.0,
) -> int:
    """Break-even em alunos por margem de contribuição (task #31).

    Margem unitária = ticket_realizado × (1 − mkt% − outros% − alíquota Simples):
    marketing, "outros" e tributos são % da RECEITA — no BE a receita é menor,
    então esses custos encolhem junto. Tratá-los como fixos (fórmula antiga
    custos_totais ÷ ticket) superestimava o BE em ~8%.
    """
    margem_unit = ticket_realizado * (1.0 - mkt_pct - outros_pct - aliquota_tributos)
    if margem_unit <= 0:
        return 0
    return int(custos_fixos_puros / margem_unit) + 1


def calcular_viabilidade_3_cenarios(
    area_m2: float,
    aluguel_mensal: float,
    bairro: str,
    cidade: str,
    tipo_negocio: str = "academia",
    tamanho_preset: str = "m",
    uf: str = "",
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
    capex_indices: dict | None = None,
    renda_media_bairro: float | None = None,
    renda_percentil: float | None = None,
    tipo_obra: str = "adaptacao",
    necessita_reforco_estrutural: bool = False,
    matriz_demo_saturacao: dict | None = None,
) -> dict:
    _capex_ctx = _resolve_capex_indices(uf, capex_indices)
    from tools.obra_capex import normalize_tipo_obra

    _tipo_obra = normalize_tipo_obra(tipo_obra)
    alertas_obra: list[str] = []
    if necessita_reforco_estrutural:
        alertas_obra.append(
            "Obra: reforço estrutural indicado — CAPEX civil pode subir além do modelo "
            f"({_tipo_obra}); validar laudo técnico."
        )
    # Task #26 — DETERMINIZAÇÃO: ticket/inadimplência/churn saem do CATÁLOGO
    # (parametros_metodologia, versionado com fonte/data), NUNCA mais do
    # benchmark via Search Grounding/LLM. Era a última variância do score:
    # cache de 7 dias expirava/rodava em container novo → ticket novo →
    # payback/viabilidade/modelo recomendado mudavam com o MESMO input
    # (provado nos runs bf7a8d5a/e88e0b32/b7199c7c: premium 299,90→500).
    # O _bench continua APENAS pra avisos informativos (nunca número de conta).
    from tools.benchmarks_tool import obter_benchmarks_setoriais
    _bench = obter_benchmarks_setoriais()
    """
    Calcula viabilidade em 3 cenários (low/mid/premium) com SCHEMA v2:

    Novo modelo (vs v1 que confundia capacidade simultânea com matrículas):
    - Matrículas pagantes em 3 calibrações (conservador/realista/agressivo)
    - Capacidade simultânea separada (check de conforto físico)
    - Frequência semanal por modelo (ACAD 2024)
    - Custos detalhados em 12 linhas
    - CAPEX detalhado com contingência
    - 3 stress tests de sensibilidade (aluguel +20%, matrículas -30%, ticket -15%)
    - TIR + VPL pra decisão de investimento

    Receita usa SEMPRE a calibração "realista" como base. Calibrações cons/agres
    ficam no campo `matriculas` pra compor a tabela de demanda + servir de
    stress test "matriculas_menos_30pct" implícito.
    """
    cenarios = {}
    alertas_ticket: list[str] = []
    alertas_legal: list[str] = []

    from tools.legal_fees_loader import resolver_taxas_capex

    _legal_ctx = None
    if (cidade or "").strip() and (uf or "").strip():
        _legal_ctx = resolver_taxas_capex(cidade, uf, area_m2, policy="mid")
        if not _legal_ctx:
            alertas_legal.append(
                f"Taxas municipais: {cidade}/{uf} sem curadoria legal_fees_pilot — "
                "alvará/projeto usam benchmark Sebrae."
            )

    # CAPEX e custos comuns que não dependem do modelo (lazy — fresh param each call)
    _custos_base = _lp("CUSTOS_DETALHADOS_BASE")
    _capex_base = _lp("CAPEX_DETALHADO_BASE")
    _ticket_faixas_map = _lp("TICKET_FAIXAS")
    _matr_m2 = _lp("MATRICULADOS_POR_M2")
    _cap_sim = _lp("CAPACIDADE_SIMULTANEA_POR_M2")
    _freq = _lp("FREQUENCIA_SEMANAL")
    _pico = _lp("PICO_SHARE_POR_MODELO")
    _inad_mod = _lp("TAXA_INADIMPLENCIA_POR_MODELO")
    _churn_mod = _lp("TAXA_CANCELAMENTO_MENSAL_POR_MODELO")
    _folha_pct = _lp("FOLHA_PCT_FATURAMENTO")
    _mkt_pct = _lp("CUSTOS_MARKETING_PCT")
    _ocup_teto = _lp("OCUPACAO_TETO")
    _inad_legacy = _lp("TAXA_INADIMPLENCIA")
    _custo_cap = _lp("CUSTO_CAPITAL_ANUAL")

    iptu_mensal = _custos_base["iptu_mensal_base"]
    internet = _custos_base["internet_mensal"]
    contabilidade = _custos_base["contabilidade_mensal"]
    sistema = _custos_base["sistema_gestao_mensal"]

    # Schema v1.5: equipamentos por modelo financeiro vêm do kit detalhado.
    # Low usa kit 1 tamanho abaixo (econômico), Mid usa tamanho selecionado,
    # Premium usa 1 acima (robusto). Fallback gracioso se kit não existe.
    try:
        from tools.kits_equipamentos import kit_totais_por_cenario
        equipamentos_por_cenario = kit_totais_por_cenario(tipo_negocio, tamanho_preset)
    except Exception:
        equipamentos_por_cenario = {"low": None, "mid": None, "premium": None}

    for faixa_key, faixa in _ticket_faixas_map.items():
        raw_ticket = float(faixa["ticket_medio"])  # catálogo (#26) — nunca LLM
        ticket, ticket_notes = _resolver_ticket_faixa(
            faixa_key, raw_ticket, renda_media_bairro
        )
        alertas_ticket.extend(ticket_notes)

        # ── DEMANDA: 3 calibrações de matrículas + pico simultâneo ──
        calibracoes = _matr_m2[faixa_key]
        matriculas_dict = {}
        for cal_id, mpm in calibracoes.items():
            matriculas_dict[cal_id] = {
                "valor": int(area_m2 * mpm),
                "matr_por_m2": mpm,
                "premissa": _premissa_calibracao(faixa_key, cal_id),
            }

        # Matrículas "realista" é a base do cálculo financeiro
        matr_real = matriculas_dict["realista"]["valor"]

        # Capacidade física simultânea (no pico)
        capacidade_simultanea_pico = int(
            area_m2 * _cap_sim[faixa_key]
        )
        freq_semanal = _freq[faixa_key]
        pico_share = _pico[faixa_key]
        # Alunos esperados simultaneamente no pico (params do próprio modelo):
        # matr × (freq/7 dias) × pico_share_{modelo}
        alunos_pico_calc = int(matr_real * (freq_semanal / 7.0) * pico_share)
        folga_pct = round(
            (1.0 - alunos_pico_calc / capacidade_simultanea_pico) * 100, 1
        ) if capacidade_simultanea_pico > 0 else 0.0

        # ── RECEITA ──
        # Inadimplência por modelo: usa benchmark atualizado se disponível,
        # senão ACAD 2024 (low 6%, mid 4%, premium 2.5%). Panorama 2025
        # mostra que esses valores assumem débito recorrente — sem
        # recorrência, inadimplência real é 15-25%.
        inadimplencia = _inad_mod[faixa_key]  # catálogo (#26)
        churn_mensal = _churn_mod[faixa_key]  # catálogo (#26)
        ticket_realizado = ticket * (1.0 - inadimplencia)
        receita_mensal = matr_real * ticket_realizado

        # ── CUSTOS DETALHADOS (12 linhas) ──
        # Schema v1.5: equipamentos vem do kit (mediana real) quando disponível.
        # Mapeia faixa_key (low|mid|premium) ↔ kit_totais_por_cenario.
        equip_override = equipamentos_por_cenario.get(faixa_key)
        capex_total = _calcular_capex_detalhado(
            area_m2,
            faixa_key,
            equipamentos_override=equip_override,
            uf_destino=uf or None,
            destino_lat=destino_lat,
            destino_lng=destino_lng,
            fornecedor_principal=fornecedor_principal,
            capex_indices=_capex_ctx,
            legal_fees_ctx=_legal_ctx,
            tipo_obra=_tipo_obra,
        )["total"]
        # 1.2 Folha = max(piso R$, % do faturamento). Piso preserva realismo na
        # rampa/operação pequena; % do faturamento captura a escala (Benchmark
        # Financeiro Academias 2024: low 18% / mid 35% / premium 33%). Também é o
        # insumo do Fator R (folha/faturamento define Anexo III vs V).
        folha_min = _custos_base["folha_por_modelo"][faixa_key]
        folha = max(folha_min, receita_mensal * _folha_pct[faixa_key])
        custos = {
            "aluguel": round(aluguel_mensal, 2),
            "condominio": round(
                aluguel_mensal * _custos_base["condominio_pct_aluguel"], 2
            ),
            "iptu": round(iptu_mensal, 2),
            "energia": round(
                area_m2 * _custos_base["energia_por_m2"]
                * (1.5 if faixa_key == "premium" else 1.0),  # premium gasta 50% mais
                2,
            ),
            "agua": custo_agua_mensal(
                area_m2, _custos_base["agua_por_m2"],
                visitas_mes=matr_real * freq_semanal * 4.345,  # semanas/mês
            ),
            "internet": round(internet, 2),
            "folha": round(folha, 2),
            "manutencao": round(
                capex_total * _custos_base["manutencao_pct_capex"], 2
            ),
            "contabilidade": round(contabilidade, 2),
            "sistema_gestao": custo_sistema_gestao(sistema, matr_real),
            "seguro": round(
                capex_total * _custos_base["seguro_pct_capex"], 2
            ),
            "outros": round(
                receita_mensal * _custos_base["outros_pct_receita"], 2
            ),
        }
        custos_fixos_total = sum(custos.values())

        # Marketing (pct da receita)
        mkt_pct = _mkt_pct[faixa_key]
        marketing_mensal = round(receita_mensal * mkt_pct, 2)

        custos_totais = custos_fixos_total + marketing_mensal

        # ── 1.3 MOTOR FISCAL (Fator R — Simples Nacional CNAE 9313-1/00) ──
        # LC 123/2006: folha/faturamento ≥ 28% → Anexo III (6% faixa inicial),
        # senão Anexo V (15,5% faixa inicial). Antes o motor era cego a tributos
        # (lucro = receita − custos era pré-imposto disfarçado de líquido).
        fator_r = (folha / receita_mensal) if receita_mensal > 0 else 0.0
        anexo_simples = "III" if fator_r >= param("fator_r_corte_folha") else "V"
        aliquota_tributos = (
            param("aliquota_simples_anexo_iii") if anexo_simples == "III"
            else param("aliquota_simples_anexo_v")
        )
        tributos_mensal = round(receita_mensal * aliquota_tributos, 2)

        # ── 1.4 GUARDRAIL DE OCUPAÇÃO IMOBILIÁRIA ──
        # Ocupação = (aluguel+condomínio+IPTU)/faturamento. Teto por modelo
        # (Benchmark Financeiro Academias 2024: low 12,5% / mid 15% / premium 15-16%).
        # Acima do teto, o aluguel estrangula o caixa estruturalmente (raiz do
        # 34,3% do caso Cocó).
        ocupacao_abs = custos["aluguel"] + custos["condominio"] + custos["iptu"]
        ocupacao_pct = (ocupacao_abs / receita_mensal) if receita_mensal > 0 else 1.0
        teto_ocup = _ocup_teto[faixa_key]
        # Ticket mínimo p/ a ocupação caber no teto, à mesma matrícula realista.
        ticket_piso_ocupacao = (
            ocupacao_abs / (teto_ocup * matr_real * (1.0 - inadimplencia))
        ) if (matr_real > 0 and (1.0 - inadimplencia) > 0) else None
        ocupacao_estoura = ocupacao_pct > teto_ocup

        # ── RESULTADO ──
        # 1.3: lucro agora é LÍQUIDO de imposto (receita − custos − tributos).
        lucro_mensal = receita_mensal - custos_totais - tributos_mensal
        margem_pct = (lucro_mensal / receita_mensal * 100) if receita_mensal > 0 else 0
        # 1.7 (task #31): BE por MARGEM DE CONTRIBUIÇÃO. A fórmula antiga
        # (custos_totais ÷ ticket) tratava marketing/outros/tributos — todos %
        # da receita — como fixos, superestimando o BE em ~8% (confronto Gemini,
        # auditoria b7199c7c). Fixos puros = custos_fixos_total − outros.
        alunos_break_even = calcular_break_even_alunos(
            custos_fixos_puros=custos_fixos_total - custos["outros"],
            ticket_realizado=ticket_realizado,
            mkt_pct=mkt_pct,
            outros_pct=_custos_base["outros_pct_receita"],
            aliquota_tributos=aliquota_tributos,
        )

        # ── INVESTIMENTO ──
        # Schema v1.5: passa override consistente com o usado pra custos
        # Schema v1.6: uf_destino + destino_lat/lng ativa Distance Matrix
        capex_detalhado = _calcular_capex_detalhado(
            area_m2,
            faixa_key,
            equipamentos_override=equip_override,
            uf_destino=uf or None,
            destino_lat=destino_lat,
            destino_lng=destino_lng,
            fornecedor_principal=fornecedor_principal,
            capex_indices=_capex_ctx,
            legal_fees_ctx=_legal_ctx,
            tipo_obra=_tipo_obra,
        )
        capital_giro = round(
            custos_totais * _capex_base["capital_giro_meses"], 2
        )
        investimento_total = capex_detalhado["total"] + capital_giro
        payback_meses = (
            int(investimento_total / lucro_mensal) if lucro_mensal > 0 else 999
        )
        tir_anual = _calcular_tir_anual(investimento_total, lucro_mensal, anos=5)
        vpl_5_anos = _calcular_vpl(
            investimento_total, lucro_mensal, anos=5,
            taxa_anual=_custo_cap,
        )

        # ── VEREDITO ──
        # 1.5: ocupação acima do teto rebaixa o veredito para INVIAVEL
        # (estrangulamento estrutural de caixa, independente do payback).
        viabilidade = _classificar_viabilidade(
            lucro_mensal, payback_meses, margem_pct,
            ocupacao_estoura=ocupacao_estoura,
        )

        # ── SENSIBILIDADE (3 stress tests + stress de ocupação) ──
        # 1.7: passa ocupacao_abs/teto p/ medir a razão de ocupação (base e +20%
        # aluguel) e reprovar quando estoura o teto.
        sensibilidade = _calcular_sensibilidade(
            base_aluguel=aluguel_mensal,
            base_matriculas=matr_real,
            base_ticket=ticket,
            custos_fixos_sem_aluguel=custos_fixos_total - custos["aluguel"],
            marketing_pct=mkt_pct,
            inadimplencia=_inad_legacy,
            investimento_total=investimento_total,
            ocupacao_nao_aluguel=ocupacao_abs - custos["aluguel"],
            teto_ocupacao=teto_ocup,
            folha_mensal=custos["folha"],
        )

        cenarios[faixa_key] = {
            "modelo": faixa["label"],
            "modelo_key": faixa_key,
            "ticket_medio": ticket,
            "descricao": faixa["descricao"],
            "exemplos_redes": faixa["exemplos"],

            # Demanda
            "matriculas": matriculas_dict,
            "matriculas_recomendada": "realista",
            "capacidade_simultanea_pico": capacidade_simultanea_pico,
            "frequencia_semanal_aluno": freq_semanal,
            "pico_share": pico_share,
            "alunos_pico_calculado": alunos_pico_calc,
            "folga_capacidade_pct": folga_pct,

            # Receita
            "ticket_realizado_estimado": round(ticket_realizado, 2),
            "taxa_inadimplencia": inadimplencia,
            "taxa_cancelamento_mensal": churn_mensal,
            # Task #34: churn operacionalizado — custo de manter a base de pé.
            **cac_teto_reposicao(marketing_mensal, matr_real, churn_mensal),
            "receita_mensal": round(receita_mensal, 2),

            # Custos (12 linhas + agregado)
            "custos_detalhados": custos,
            "custos_fixos_total": round(custos_fixos_total, 2),
            "marketing_pct_faturamento": mkt_pct,
            "marketing_mensal": marketing_mensal,
            "custos_totais": round(custos_totais, 2),

            # Fiscal (1.3 — Fator R CNAE 9313-1/00, LC 123/2006)
            "tributos_mensal": tributos_mensal,
            "aliquota_tributos": round(aliquota_tributos, 4),
            "fator_r": round(fator_r, 4),
            "anexo_simples": anexo_simples,
            "folha_pct_efetivo": round((folha / receita_mensal), 4) if receita_mensal > 0 else 0.0,

            # Ocupação imobiliária (1.4 — guardrail de teto)
            "ocupacao_pct": round(ocupacao_pct, 4),
            "teto_ocupacao": round(teto_ocup, 4),
            "ocupacao_estoura": ocupacao_estoura,
            "ticket_piso_ocupacao": (
                round(ticket_piso_ocupacao, 2) if ticket_piso_ocupacao is not None else None
            ),

            # Resultado
            "lucro_mensal_estimado": round(lucro_mensal, 2),
            "margem_percentual": round(margem_pct, 1),
            "alunos_break_even": alunos_break_even,

            # Investimento
            "capex_detalhado": capex_detalhado,
            "capex_total": capex_detalhado["total"],
            "capital_giro_meses": _capex_base["capital_giro_meses"],
            "capital_giro": capital_giro,
            "investimento_total": round(investimento_total, 2),
            "payback_meses": payback_meses,
            "tir_anual_pct": round(tir_anual * 100, 1) if tir_anual else None,
            "vpl_5_anos": round(vpl_5_anos, 2),

            # Risco
            "sensibilidade": sensibilidade,

            # Veredito
            "viabilidade": viabilidade["status"],
            "justificativa": viabilidade["justificativa"],

            # Backward-compat — campos do schema v1 que A6/frontend antigos podem ler.
            # NÃO REMOVER — readers v1.1/v1.2 ainda existem em mocks.
            "capacidade_maxima_alunos": capacidade_simultanea_pico,
            "alunos_projetados": matr_real,
            "custos_fixos": round(custos_fixos_total, 2),
            "capex_estimado": capex_detalhado["total"],
        }

    melhor = _escolher_cenario_recomendado(
        cenarios, renda_media_bairro, renda_percentil,
        matriz_demo_saturacao=matriz_demo_saturacao,
    )
    alertas_benchmark = _alertas_vs_sector_listed(cenarios)
    # 1.6 Reconciliação OPEX (alerta bidirecional): além do alerta de margem BAIXA
    # (já em _alertas_vs_sector_listed), sinaliza margem OTIMISTA — acima do
    # benchmark de margem líquida do modelo + 8pp (Benchmark Financeiro Academias
    # 2024: low 30% / mid 17% / premium 22,5%). Indica premissas frouxas.
    alertas_benchmark.extend(_alertas_margem_otimista(cenarios))
    alertas_ticket.extend(_bench.get("ticket_sanity_avisos") or [])

    return {
        "bairro": bairro,
        "cidade": cidade,
        "area_m2": area_m2,
        "aluguel_mensal": aluguel_mensal,
        "renda_media_bairro": renda_media_bairro,
        "aviso": "Schema v2 — matrículas reais (não pico). Benchmarks: ACAD/Sebrae + Smart Fit/Bluefit/Bodytech.",
        "cenarios": cenarios,
        "recomendacao": melhor["modelo"],
        "recomendacao_justificativa": melhor.get("justificativa_recomendacao"),
        "recomendacao_no_teto_captacao": melhor.get("recomendado_no_teto_captacao"),
        "melhor_lucro_mensal": melhor["lucro_mensal_estimado"],
        "melhor_payback_meses": melhor["payback_meses"],
        "schema_cenarios": "v2",
        "alertas_benchmark": alertas_benchmark,
        "alertas_ticket": alertas_ticket,
        "alertas_legal": alertas_legal,
        "alertas_obra": alertas_obra,
        "tipo_obra": _tipo_obra,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers do schema v2
# ─────────────────────────────────────────────────────────────────────────

def _resolver_ticket_faixa(
    faixa_key: str,
    raw_ticket: float,
    renda_media_bairro: float | None,
) -> tuple[float, list[str]]:
    """Sanitiza ticket do benchmark + aplica teto por renda domiciliar local."""
    from tools.benchmarks_tool import sanitizar_ticket_por_modelo

    limpos, avisos = sanitizar_ticket_por_modelo({faixa_key: raw_ticket})
    ticket = limpos.get(faixa_key, raw_ticket)

    if renda_media_bairro and renda_media_bairro > 0:
        pct = _lp("TICKET_RENDA_PCT").get(faixa_key, param("ticket_renda_pct_mid"))
        cap = round(renda_media_bairro * pct, 2)
        if ticket > cap:
            avisos.append(
                f"ticket {faixa_key} capado em R${cap:.0f} "
                f"({int(pct * 100)}% da renda bairro R${renda_media_bairro:.0f})"
            )
            ticket = cap
    return round(ticket, 2), avisos


def _renda_media_bairro(cidade: str, bairro: str, uf: str) -> tuple[float | None, str]:
    """Renda per capita do bairro p/ escolher o tier do modelo. Retorna (valor, FONTE).

    PRIMÁRIO: `renda_bairro` IBGE Censo 2022 (renda_pc) — MESMA fonte do A9/headroom.
    FALLBACK: CKAN 2010 quando o IBGE 2022 não cobre o bairro (cobertura: 25/27 UFs —
    falta DF/TO; nomes populares fora da subdivisão IBGE, ex: Moema/SP). O CKAN é mais
    velho/grosso → a `fonte` retornada marca isso (item c, transparência).
    """
    if not (bairro or "").strip():
        return None, "sem_bairro"
    # Fonte 2022 (coerente com o A9) — pode vir por alias (marcado na fonte)
    try:
        from tools.posicionamento_renda import renda_bairro_ipece

        r = renda_bairro_ipece(cidade, uf or "", bairro)
        if r and r.get("renda_pc"):
            return float(r["renda_pc"]), (r.get("fonte") or "IBGE Censo 2022 (bairro)")
    except Exception:
        pass
    # Fallback CKAN 2010 — usa renda_media_per_capita (mesma ESCALA dos thresholds)
    try:
        from tools.bairro_renda_loader import enrich_demografia_bairro

        b = enrich_demografia_bairro({"bairro": {}}, cidade, bairro, uf or "").get("bairro") or {}
        val = b.get("renda_media_per_capita") or b.get("renda_media")
        if val is not None:
            return float(val), "CKAN 2010 (fallback — IBGE 2022 não cobre este bairro)"
    except Exception:
        pass
    return None, "indisponivel"


def _renda_percentil_bairro(cidade: str, bairro: str, uf: str) -> float | None:
    """Percentil de renda do bairro (IPECE/Censo 2022). Sinal MELHOR que renda absoluta
    p/ o teto de captação: Cocó renda_pc R$4.952 mal passa o floor premium (4.500), mas
    percentil 0,99 = top-1% → densidade captável sobe rumo ao agressivo."""
    if not (bairro or "").strip():
        return None
    try:
        from tools.posicionamento_renda import renda_bairro_ipece

        r = renda_bairro_ipece(cidade, uf or "", bairro)
        if r and r.get("percentil") is not None:
            return float(r["percentil"])
    except Exception:
        pass
    return None


def _fator_captacao(percentil: float | None) -> float:
    """Quanto empurrar a densidade do realista→agressivo, por percentil de renda.
    0 abaixo de renda_percentil_premium (bairro comum fica no realista); sobe linear
    até 1 no percentil 1,0 (bairro top-renda alcança o teto agressivo). Auto-regula:
    bairro pobre → fator 0 → premium NÃO é elevado → gate barra como deve."""
    if percentil is None:
        return 0.0
    p0 = param("renda_percentil_premium")  # 0.75
    if percentil <= p0:
        return 0.0
    return min(1.0, (percentil - p0) / max(1e-6, 1.0 - p0))


def _viab_no_teto_captacao(c: dict[str, Any], fator: float) -> dict[str, Any] | None:
    """Recomputa a viabilidade do cenário na densidade renda-ponderada (realista→agressivo
    por `fator`) e checa o GATE FÍSICO (pico simultâneo ≤ capacidade). Receita escala c/
    matrículas; só `outros` e marketing são revenue-linked — resto é fixo. None se não dá."""
    matr = c.get("matriculas") or {}

    def _valor(x):  # matriculas[cal] é {"valor": int, ...} no cenário real; int no teste
        return float(x.get("valor") or 0) if isinstance(x, dict) else float(x or 0)
    base = _valor(matr.get("realista"))
    teto = _valor(matr.get("agressivo"))
    receita0 = c.get("receita_mensal") or 0
    ticket = c.get("ticket_realizado_estimado") or 0
    if not base or not teto or fator <= 0 or receita0 <= 0 or ticket <= 0:
        return None
    alvo = base + (teto - base) * fator
    outros = (c.get("custos_detalhados") or {}).get("outros", 0)
    outros_pct = outros / receita0 if receita0 else 0
    mkt_pct = c.get("marketing_pct_faturamento") or 0
    fixos_puros = (c.get("custos_fixos_total") or 0) - outros  # tira o revenue-linked
    nova_receita = alvo * ticket
    novo_lucro = nova_receita * (1 - outros_pct - mkt_pct) - fixos_puros
    nova_margem = (novo_lucro / nova_receita * 100) if nova_receita > 0 else 0
    inv = c.get("investimento_total") or 0
    novo_payback = int(inv / novo_lucro) if novo_lucro > 0 else 999
    # GATE FÍSICO: o pico escala linear c/ matrículas (pico_share/freq do próprio cenário).
    pico_base = c.get("alunos_pico_calculado") or 0
    cap = c.get("capacidade_simultanea_pico") or 0
    pico_alvo = pico_base * (alvo / base) if base else 0
    pico_ok = (cap <= 0) or (pico_alvo <= cap)
    viab = _classificar_viabilidade(novo_lucro, novo_payback, nova_margem)
    return {
        "matriculas_alvo": int(round(alvo)),
        "densidade_fator": round(fator, 2),
        "lucro_mensal": round(novo_lucro, 2),
        "margem_percentual": round(nova_margem, 1),
        "payback_meses": novo_payback,
        "viabilidade": viab["status"],
        "pico_alvo": int(round(pico_alvo)),
        "capacidade_simultanea_pico": cap,
        "pico_comporta": pico_ok,
        "base": "teto de captação ACAD agressivo, ponderado por renda do bairro",
    }


def _tier_mercado_por_renda(renda_media_bairro: float | None) -> str:
    if not renda_media_bairro or renda_media_bairro <= 0:
        return "mid"
    if renda_media_bairro < 2500:
        return "low"
    if renda_media_bairro < 4500:
        return "mid"
    return "premium"


def _faixa_key_de_modelo(modelo: str) -> str:
    m = (modelo or "").lower()
    if "premium" in m:
        return "premium"
    if "mid" in m:
        return "mid"
    return "low"


def _escolher_cenario_recomendado(
    cenarios: dict[str, Any],
    renda_media_bairro: float | None,
    renda_percentil: float | None = None,
    matriz_demo_saturacao: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Escolhe cenário alinhado ao tier de renda local — não só max(lucro) com ticket irreal.

    DOIS GATES COMPLEMENTARES (auto-regulam):
    1) renda-ponderado: num bairro top-renda (percentil alto), a densidade captável do tier
       preferido sobe do realista rumo ao agressivo (teto ACAD). Bairro comum → fica no realista.
    2) gate físico: só eleva se o pico simultâneo no teto ≤ capacidade do espaço.
    Assim, premium INVIÁVEL no realista vira recomendável num bairro rico SE fecha no teto
    captável E o prédio comporta — e num bairro pobre o fator é 0, premium nunca é elevado.

    Matriz (Spec 2026-08-07): Armadilha de Renda veta Premium genérico.
    """
    preferido = _tier_mercado_por_renda(renda_media_bairro)
    ordem = {"low": 0, "mid": 1, "premium": 2}

    # Gate complementar: eleva o tier preferido se inviável no realista MAS viável no teto
    # de captação (renda-ponderado) E o gate físico comporta o pico.
    fator = _fator_captacao(renda_percentil)
    pref_c = cenarios.get(preferido)
    if (
        pref_c is not None
        and pref_c.get("viabilidade") in ("INVIAVEL", None)
        and fator > 0
    ):
        teto = _viab_no_teto_captacao(pref_c, fator)
        if teto and teto["viabilidade"] not in ("INVIAVEL", None) and teto["pico_comporta"]:
            pref_c["recomendado_no_teto_captacao"] = teto
            pref_c["_elegivel_teto"] = True
            # Preserva o motivo realista (auditoria) e troca a justificativa exibida pelo
            # racional REAL da recomendação (teto de captação) — renderers leem `justificativa`.
            pref_c["justificativa_realista"] = pref_c.get("justificativa")
            pref_c["viabilidade_realista"] = pref_c.get("viabilidade")
            pref_c["justificativa_recomendacao"] = (
                f"Recomendado operando no TETO DE CAPTAÇÃO ({teto['matriculas_alvo']} matrículas, "
                f"densidade ACAD agressiva), não no realista. O bairro é top-renda (percentil "
                f"{renda_percentil:.0%}) → sustenta a captação agressiva; o espaço comporta o pico "
                f"({teto['pico_alvo']} ≤ {teto['capacidade_simultanea_pico']} simultâneos). "
                f"Margem {teto['margem_percentual']:.0f}%, payback {teto['payback_meses']}m. "
                f"No realista o modelo não fecha — o upside é captável com marketing, sem CAPEX extra."
            )
            pref_c["justificativa"] = pref_c["justificativa_recomendacao"]

    # GATE DE VIABILIDADE (regra do produto): NUNCA recomendar modelo INVIÁVEL no
    # realista. O teto-de-captação (renda agressiva) vira UPSIDE anotado, não a
    # recomendação — recomendar Premium-inviável num relatório de viabilidade é
    # auto-contradição (VPL negativo, quebra em todo stress test).
    viaveis = [c for c in cenarios.values() if c.get("viabilidade") not in ("INVIAVEL", None)]

    # GATE DE PAYBACK (opção c, jun/2026): tier-por-renda NÃO recomenda payback longo.
    # Ceiling = 48 meses (mesmo limiar do alerta "Payback acima de 48 meses — risco elevado").
    # Premium num bairro rico só é recomendado se fecha em payback aceitável; senão cai pro
    # melhor modelo viável DENTRO do teto + nota. Evita recomendar premium de 7 anos calado.
    try:
        _CEIL_PB = float(param("payback_limiar_recomendavel"))
    except Exception:
        _CEIL_PB = 48.0
    recomendaveis = [c for c in viaveis if float(c.get("payback_meses") or 999) <= _CEIL_PB]
    pool = recomendaveis or viaveis or list(cenarios.values())
    so_inviaveis = not viaveis
    fora_do_teto = bool(viaveis) and not recomendaveis  # viável mas todos com payback > ceiling

    def _rank(c: dict[str, Any]) -> tuple[float, float, float]:
        faixa = _faixa_key_de_modelo(c.get("modelo", ""))
        tier_gap = abs(ordem.get(faixa, 1) - ordem.get(preferido, 1))
        lucro = float(c.get("lucro_mensal_estimado") or 0)
        payback = float(c.get("payback_meses") or 999)
        # Entre RECOMENDÁVEIS (payback ok): maior tier (alinha à renda), depois lucro, payback.
        # Se só sobrou inviável/fora-do-teto: payback manda (o menos-pior), tier é secundário.
        return (-tier_gap, lucro, -payback) if not (so_inviaveis or fora_do_teto) else (-payback, lucro, -tier_gap)

    escolhido = max(pool, key=_rank)

    # Matriz Armadilha: veta Premium genérico — reescolhe melhor non-premium do pool.
    _matriz = matriz_demo_saturacao if isinstance(matriz_demo_saturacao, dict) else {}
    if (
        _matriz.get("quadrante") == "Armadilha de Renda"
        and _faixa_key_de_modelo(escolhido.get("modelo", "")) == "premium"
    ):
        alt = [
            c for c in pool
            if _faixa_key_de_modelo(c.get("modelo", "")) != "premium"
        ]
        if alt:
            escolhido = max(alt, key=_rank)
            msg = (
                "Armadilha de Renda: ≥2 Premium no polígono — Premium genérico "
                "vetado pela matriz."
            )
            escolhido["justificativa_matriz"] = msg
            escolhido["justificativa_recomendacao"] = msg
            escolhido["justificativa"] = msg

    # Nota de transparência se o tier preferido pela renda ficou de FORA — por inviabilidade
    # OU por payback acima do teto.
    pref_c2 = cenarios.get(preferido)
    if (pref_c2 is not None and pref_c2 is not escolhido
            and _faixa_key_de_modelo(escolhido.get("modelo", "")) != preferido):
        pb = float(pref_c2.get("payback_meses") or 999)
        if pref_c2.get("viabilidade") in ("INVIAVEL", None):
            motivo = "é INVIÁVEL no cenário realista (não fecha conta)"
        elif pb > _CEIL_PB:
            motivo = f"tem payback de {int(pb)} meses (> {int(_CEIL_PB)}m — risco elevado)"
        else:
            motivo = None
        if motivo and not escolhido.get("justificativa_matriz"):
            escolhido.setdefault("nota_recomendacao",
                f"Renda do bairro suportaria o tier {preferido.upper()}, mas ele {motivo} — "
                f"recomendado o melhor modelo viável dentro do teto de payback.")

    # Garante justificativa SEMPRE (o ramo teto-captação já setou; aqui o caminho normal/fallback,
    # que antes deixava justificativa_recomendacao=None → relatório recomendava sem porquê).
    if not escolhido.get("justificativa_recomendacao"):
        escolhido["justificativa_recomendacao"] = (
            escolhido.get("nota_recomendacao")
            or f"Recomendado {escolhido.get('modelo', '')}: tier alinhado à renda do bairro, "
               f"viável no cenário realista com payback de {escolhido.get('payback_meses')} meses."
        )
        escolhido.setdefault("justificativa", escolhido["justificativa_recomendacao"])
    return escolhido


def _alertas_vs_sector_listed(cenarios: dict[str, Any]) -> list[str]:
    """Compara cenário realista (mid) com KPIs SMFT3 do snapshot CVM."""
    try:
        from tools.cvm_listed_metrics import kpis_smart_fit

        kpis = kpis_smart_fit()
    except Exception:
        return []
    margem_ref = kpis.get("margem_ebitda_pct")
    alav_ref = kpis.get("divida_liquida_ebitda")
    if margem_ref is None and alav_ref is None:
        return []

    alertas: list[str] = []
    base = cenarios.get("mid") or cenarios.get("low")
    if not base:
        return alertas

    margem = float(base.get("margem_percentual") or 0)
    payback = int(base.get("payback_meses") or 999)

    if margem_ref is not None and margem < float(margem_ref) * 0.7:
        alertas.append(
            f"⚠️ Margem operacional {margem:.1f}% abaixo de 70% da margem EBITDA "
            f"Smart Fit (SMFT3, CVM ~{margem_ref}%)"
        )
    if payback > 48:
        alertas.append(
            "⚠️ Payback > 48 meses — acima do horizonte típico de rede listada (validar premissas)"
        )
    if alav_ref is not None and payback > 60:
        alertas.append(
            f"⚠️ Payback estendido com alavancagem setorial SMFT3 ~{alav_ref}x DL/EBITDA (referência CVM)"
        )

    # Cobertura de KPIs operacionais (RI): expõe quando comparação operacional
    # (ARPU/churn/alunos) está indisponível — não silenciar a lacuna.
    try:
        from tools.cvm_listed_metrics import empresa_por_ticker, sector_kpi_coverage

        emp = empresa_por_ticker("SMFT3")
        if emp:
            cov = sector_kpi_coverage(emp)
            if cov["pct"] < 100.0:
                alertas.append(
                    f"ℹ️ Comparação operacional SMFT3 parcial ({cov['pct']:.0f}%) — "
                    f"sem {', '.join(cov['faltando'])} (CVM ITR não cobre; preencher RI overlay)"
                )
    except Exception:
        pass
    return alertas


# Benchmark de margem líquida por modelo (Benchmark Financeiro Academias 2024,
# operação madura): low 30% / mid 17% / premium 22,5%.
MARGEM_LIQUIDA_BENCHMARK = {"low": 30.0, "mid": 17.0, "premium": 22.5}
_MARGEM_OTIMISTA_PP = 8.0  # tolerância (pontos percentuais) antes de alertar


def _alertas_margem_otimista(cenarios: dict[str, Any]) -> list[str]:
    """1.6 — Alertas de plausibilidade: margem otimista e TIR/VPL fora da curva.

    Complementa o alerta de margem BAIXA (_alertas_vs_sector_listed). Margem muito
    acima do benchmark sugere premissas frouxas (folha/tributos/ocupação subestimados).
    TIR > 100% ou VPL negativo também recebem ressalva (por modelo, independente).
    """
    alertas: list[str] = []
    for faixa_key, c in cenarios.items():
        modelo = c.get("modelo", faixa_key)
        margem = float(c.get("margem_percentual") or 0)
        tir = float(c.get("tir_anual_pct") or 0)
        vpl = float(c.get("vpl_5_anos") or 0)

        bench = MARGEM_LIQUIDA_BENCHMARK.get(faixa_key)
        if bench is not None and margem > bench + _MARGEM_OTIMISTA_PP:
            alertas.append(
                f"⚠️ Margem {margem:.1f}% ({modelo}) otimista vs "
                f"benchmark {bench:.0f}% (+{_MARGEM_OTIMISTA_PP:.0f}pp) — revisar "
                f"premissas (folha/tributos/ocupação)."
            )
        if tir > 100.0:
            alertas.append(
                f"ℹ️ TIR de {tir:.0f}% ({modelo}) indica payback ultrarrápido. "
                "O resultado é sensível a pequenas variações de custo/receita; valide as premissas."
            )
        if vpl < 0:
            alertas.append(
                f"⚠️ VPL negativo (R$ {vpl:,.0f}) em {modelo} — o investimento "
                "não se paga no horizonte de 5 anos à taxa de desconto usada; "
                "revise ticket, matrículas ou CAPEX."
            )
    return alertas


def _premissa_calibracao(modelo: str, calibracao: str) -> str:
    """Texto-fonte da calibração — pra UI mostrar 'de onde veio o número'."""
    fontes = {
        ("low", "conservador"): "academia regional nova, 60% benchmark Smart Fit",
        ("low", "realista"):    "benchmark Smart Fit/Bluefit/Selfit (ACAD 2024)",
        ("low", "agressivo"):   "Smart Fit top performers (>3.000 alunos/unidade)",
        ("mid", "conservador"): "Bodytech entry sub-performante",
        ("mid", "realista"):    "Bodytech entry / regional premium consolidada",
        ("mid", "agressivo"):   "Bodytech entry top, mercado em expansão",
        ("premium", "conservador"): "boutique nicho, demanda local moderada",
        ("premium", "realista"):    "Bodytech / Bio Ritmo média (~600 alunos/unidade)",
        ("premium", "agressivo"):   "premium em bairro de alta renda, alto perfil",
    }
    return fontes.get((modelo, calibracao), "benchmark setorial")


_RATIO_LOW_MID = 200.0 / 350.0
_RATIO_PREMIUM_MID = 600.0 / 350.0


def _resolve_capex_indices(
    uf: str,
    capex_indices: dict | None = None,
) -> dict | None:
    try:
        from tools.obra_regua import resolve_capex_indices_for_uf

        return resolve_capex_indices_for_uf(uf, capex_indices=capex_indices)
    except Exception:
        return None


def _obra_por_m2_modelo(
    modelo: str,
    *,
    capex_indices: dict | None = None,
    tipo_obra: str = "adaptacao",
) -> float:
    """R$/m² obra civil: bundle CUB/SINAPI > fallback CAPEX_DETALHADO_BASE."""
    from tools.obra_capex import normalize_tipo_obra, obra_m2_por_modelo

    return obra_m2_por_modelo(
        modelo,
        tipo_obra=normalize_tipo_obra(tipo_obra),
        capex_indices=capex_indices,
    )


def _calcular_capex_detalhado(
    area_m2: float,
    modelo: str,
    equipamentos_override: float | None = None,
    uf_destino: str | None = None,
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
    capex_indices: dict | None = None,
    legal_fees_ctx: dict | None = None,
    tipo_obra: str = "adaptacao",
) -> dict:
    """Breakdown CAPEX com contingência + frete ANTT.

    Schema v1.5: `equipamentos_override` aceita valor do kit detalhado real.
    Schema v1.6: `uf_destino` ativa cálculo de frete via ANTT (R$/km).
    Schema v1.7: `legal_fees_ctx` (resolver_taxas_capex) sobrescreve alvará/projeto.
    Schema v1.8: `tipo_obra` adaptacao|bruta altera R$/m² obra (chave legada obra_adaptacao).
    Quando UF fornecida, adiciona linha `frete_equipamentos` ao subtotal.
    """
    from tools.obra_capex import carimbo_obra_civil, linha_obra, normalize_tipo_obra

    _tipo_obra = normalize_tipo_obra(tipo_obra)
    _capex_base = _lp("CAPEX_DETALHADO_BASE")
    if equipamentos_override is not None and equipamentos_override > 0:
        equip = equipamentos_override
    else:
        equip = area_m2 * _capex_base["equipamentos_por_m2"][modelo]
    obra_m2 = _obra_por_m2_modelo(
        modelo, capex_indices=capex_indices, tipo_obra=_tipo_obra
    )
    obra = area_m2 * obra_m2
    projeto = _capex_base["projeto_arquitetonico"]
    alvara = _capex_base["alvara_e_taxas"]
    fonte_projeto = "parametros_metodologia (Sebrae 2024)"
    fonte_alvara = "parametros_metodologia (Sebrae 2024)"
    legal_fees_meta = None
    if legal_fees_ctx and legal_fees_ctx.get("disponivel"):
        projeto = float(legal_fees_ctx.get("projeto_arquitetonico") or projeto)
        alvara = float(legal_fees_ctx.get("alvara_e_taxas") or alvara)
        fonte_projeto = legal_fees_ctx.get("carimbo_projeto_arquitetonico") or (
            legal_fees_ctx.get("fonte") or "legal_fees_pilot"
        )
        fonte_alvara = legal_fees_ctx.get("carimbo_alvara_e_taxas") or fonte_projeto
        legal_fees_meta = {
            "cidade": legal_fees_ctx.get("cidade"),
            "uf": legal_fees_ctx.get("uf"),
            "policy": legal_fees_ctx.get("policy"),
            "data_coleta": legal_fees_ctx.get("data_coleta"),
            "detalhe_taxas": legal_fees_ctx.get("detalhe_taxas"),
        }

    # Schema v1.6: frete via ANTT quando UF disponível
    frete = 0.0
    frete_detalhes = None
    if uf_destino:
        try:
            from tools.antt_tools import calcular_frete_kit_equipamentos
            frete_calc = calcular_frete_kit_equipamentos(
                valor_kit=equip,
                uf_destino=uf_destino,
                destino_lat=destino_lat,
                destino_lng=destino_lng,
                fornecedor_principal=fornecedor_principal,
            )
            frete = frete_calc["frete_estimado_real"]
            frete_detalhes = frete_calc
        except Exception:
            pass

    fonte_obra_adaptacao = carimbo_obra_civil(
        capex_indices, obra_m2, tipo_obra=_tipo_obra, modelo=modelo
    )
    _linha_obra = linha_obra(_tipo_obra)

    subtotal = equip + obra + projeto + alvara + frete
    contingencia = subtotal * _capex_base["contingencia_pct"]
    return {
        "equipamentos": round(equip, 2),
        "obra_adaptacao": round(obra, 2),
        "projeto_arquitetonico": round(projeto, 2),
        "alvara_e_taxas": round(alvara, 2),
        "frete_equipamentos": round(frete, 2),
        "frete_detalhes": frete_detalhes,
        "contingencia_pct": _capex_base["contingencia_pct"],
        "contingencia_valor": round(contingencia, 2),
        "total": round(subtotal + contingencia, 2),
        "fonte_equipamentos": (
            "kit detalhado v1.5" if equipamentos_override else "R$/m² benchmark"
        ),
        "fonte_frete": (
            "ANTT 6.034/2024 + margem broker" if frete > 0 else "não calculado"
        ),
        "fonte_projeto_arquitetonico": fonte_projeto,
        "fonte_alvara_e_taxas": fonte_alvara,
        "fonte_obra_adaptacao": fonte_obra_adaptacao,
        "obra_adaptacao_por_m2": round(obra_m2, 2),
        "obra_civil": round(obra, 2),
        "tipo_obra": _tipo_obra,
        "linha_obra": _linha_obra,
        "legal_fees": legal_fees_meta,
    }


def _calcular_tir_anual(investimento: float, lucro_mensal: float, anos: int = 5) -> float | None:
    """
    Newton-Raphson simples pra TIR.
    Fluxo: -investimento, +lucro_mensal × 12 (anuais), pelos `anos` anos.
    Retorna taxa anual decimal (0.20 = 20%) ou None se não convergir.
    """
    if lucro_mensal <= 0 or investimento <= 0:
        return None
    fluxo_anual = lucro_mensal * 12

    # Bisseção: TIR sempre entre 0 e 200% pra esses fluxos
    low, high = 0.0, 2.0
    for _ in range(50):
        mid = (low + high) / 2
        vpl = -investimento + sum(fluxo_anual / (1 + mid) ** ano for ano in range(1, anos + 1))
        if abs(vpl) < 1.0:
            return mid
        if vpl > 0:
            low = mid
        else:
            high = mid
    return mid


def _calcular_vpl(investimento: float, lucro_mensal: float, anos: int, taxa_anual: float) -> float:
    """VPL a `taxa_anual` decimal (0.12 = 12%)."""
    if lucro_mensal <= 0:
        return -investimento
    fluxo_anual = lucro_mensal * 12
    vpl = -investimento
    for ano in range(1, anos + 1):
        vpl += fluxo_anual / ((1 + taxa_anual) ** ano)
    return vpl


def _classificar_viabilidade(
    lucro: float, payback: int, margem: float, ocupacao_estoura: bool = False
) -> dict:
    """Retorna {status, justificativa} baseado em 3 critérios.

    1.5: `ocupacao_estoura=True` (ocupação imobiliária acima do teto do modelo)
    rebaixa para INVIAVEL — estrangulamento estrutural de caixa, independente do
    payback (Benchmark Financeiro Academias 2024).
    """
    if ocupacao_estoura:
        return {"status": "INVIAVEL",
                "justificativa": "Ocupação imobiliária acima do teto do modelo — aluguel estrangula o caixa estruturalmente"}
    if lucro <= 0:
        return {"status": "INVIAVEL", "justificativa": f"Prejuízo mensal de R$ {-lucro:,.0f}"}
    if payback <= param("viab_payback_alto") and margem >= param("viab_margem_alto"):
        return {"status": "ALTO", "justificativa": f"Margem {margem:.1f}% + payback {payback}m"}
    if payback <= param("viab_payback_medio") and margem >= param("viab_margem_medio"):
        return {"status": "MEDIO", "justificativa": f"Margem {margem:.1f}% + payback {payback}m (aceitável)"}
    if payback <= param("viab_payback_baixo"):
        return {"status": "BAIXO", "justificativa": f"Margem apertada {margem:.1f}%, payback longo {payback}m"}
    return {"status": "INVIAVEL", "justificativa": f"Payback {payback}m inviável"}


def _calcular_sensibilidade(
    base_aluguel: float,
    base_matriculas: int,
    base_ticket: float,
    custos_fixos_sem_aluguel: float,
    marketing_pct: float,
    inadimplencia: float,
    investimento_total: float,
    ocupacao_nao_aluguel: float = 0.0,
    teto_ocupacao: float | None = None,
    folha_mensal: float = 0.0,
) -> list[dict]:
    """
    Stress tests com lucro/payback/viabilidade resultantes.

    Task #19 — CASCATA FISCAL DINÂMICA: o Fator R é recalculado SOB CADA stress
    (folha ÷ receita estressada) e o Simples reenquadrado — queda de receita pode
    até MELHORAR o anexo (folha ganha peso relativo). O lucro de cada linha é
    LÍQUIDO do imposto do anexo resultante, coerente com o motor v1.3.
    CAPEX de equipamentos é PISO inviolável: nenhum stress corta equipamento.

    Cada stress aplica um delta sobre o cenário "realista":
    - aluguel +20%: simula contrato com reajuste alto
    - matrículas -30%: simula execução abaixo do benchmark Smart Fit
    - ticket -15%: simula pressão de preço (concorrência low-cost agressiva)
    - ocupação (aluguel +20%): mede a razão de ocupação (aluguel+condomínio+IPTU)/
      faturamento e reprova quando ultrapassa o teto do modelo (1.7).

    `ocupacao_nao_aluguel` = condomínio+IPTU (componentes de ocupação fora o aluguel),
    usado p/ recompor a ocupação absoluta sob o aluguel estressado.
    """
    resultados = []
    for stress in STRESS_TESTS:
        aluguel = base_aluguel * (1 + stress.get("delta_aluguel", 0))
        matriculas = int(base_matriculas * (1 + stress.get("delta_matriculas", 0)))
        ticket = base_ticket * (1 + stress.get("delta_ticket", 0))

        ticket_real = ticket * (1 - inadimplencia)
        receita = matriculas * ticket_real
        custos_fixos = custos_fixos_sem_aluguel + aluguel
        marketing = receita * marketing_pct
        custos_total = custos_fixos + marketing

        # Cascata fiscal (task #19): Fator R recalculado sob a receita estressada.
        fator_r_s = (folha_mensal / receita) if receita > 0 else 0.0
        anexo_s = (
            "V" if (stress.get("forca_anexo_v") or fator_r_s < param("fator_r_corte_folha"))
            else "III"
        )
        aliquota_s = (
            param("aliquota_simples_anexo_v") if anexo_s == "V"
            else param("aliquota_simples_anexo_iii")
        )
        tributos_s = receita * aliquota_s

        lucro = receita - custos_total - tributos_s
        margem = (lucro / receita * 100) if receita > 0 else 0
        payback = int(investimento_total / lucro) if lucro > 0 else 999

        # 1.7: razão de ocupação sob o aluguel estressado.
        ocupacao_abs = aluguel + ocupacao_nao_aluguel
        ocupacao_pct = (ocupacao_abs / receita) if receita > 0 else 1.0
        ocupacao_estoura = (
            teto_ocupacao is not None and ocupacao_pct > teto_ocupacao
        )
        viab = _classificar_viabilidade(
            lucro, payback, margem,
            ocupacao_estoura=ocupacao_estoura if stress.get("check_ocupacao") else False,
        )

        resultados.append({
            "id": stress["id"],
            "label": stress["label"],
            "lucro_mensal": round(lucro, 2),
            "margem_percentual": round(margem, 1),
            "payback_meses": payback,
            "viabilidade": viab["status"],
            "fator_r": round(fator_r_s, 4),
            "anexo_simples": anexo_s,
            "aliquota_tributos": round(aliquota_s, 4),
            "tributos_mensal": round(tributos_s, 2),
            "ocupacao_pct": round(ocupacao_pct, 4),
            "teto_ocupacao": round(teto_ocupacao, 4) if teto_ocupacao is not None else None,
            "ocupacao_estoura": bool(ocupacao_estoura),
        })
    return resultados


# ── Macro-tool consolidadora A4 (Task #56 — mesmo padrão A3a/A3b) ──
def calcular_score_viabilidade(
    payback_meses: float, ocupacao_break: float, ocupacao_estoura: bool = False
) -> float:
    """Score 0-10 de viabilidade (CANÔNICO) — payback + ocupação no break-even.

    Cortes e base via param() (calibração GymSite v2). Mesma fórmula usada pela
    granularização (metodologia_explain). É a FOLHA `score_viabilidade` do score_bairro
    → veredito; determinístico para o LLM do A4 não inventar.

    1.5: `ocupacao_estoura=True` (ocupação imobiliária acima do teto do modelo) zera
    o bônus e aplica penalidade — score abaixo do limiar de rejeição, coerente com o
    veredito INVIAVEL (Benchmark Financeiro Academias 2024).
    """
    if ocupacao_estoura:
        return 0.0
    score = 0.0
    if payback_meses <= param("payback_limiar_excelente"): score += 4.0
    elif payback_meses <= param("payback_limiar_bom"): score += 3.0
    elif payback_meses <= param("payback_limiar_regular"): score += 2.0
    elif payback_meses <= param("payback_limiar_fraco"): score += 1.0
    if ocupacao_break < param("ocupacao_break_otima"): score += 3.0
    elif ocupacao_break < param("ocupacao_break_boa"): score += 2.0
    elif ocupacao_break < param("ocupacao_break_limite"): score += 1.0
    return round(min(score + param("score_viab_base"), 10.0), 2)


def _resumo_decisao_a4(fin: dict) -> dict:
    """Campos de decisão DETERMINÍSTICOS do A4 (LLM não inventa): score_viabilidade
    (folha do veredito), recomendacao_modelo (do cenário escolhido) e os alertas de
    risco obrigatórios. LLM fica só com a justificativa narrativa.
    """
    cenarios = fin.get("cenarios") or {}
    rec_modelo = fin.get("recomendacao") or "Nenhum"
    c = cenarios.get(_faixa_key_de_modelo(rec_modelo)) or {}

    payback = float(c.get("payback_meses") or 999)
    cap = float(c.get("capacidade_maxima_alunos") or 0)
    be = float(c.get("alunos_break_even") or 0)
    ocup_break = (be / cap) if cap > 0 else 1.0
    # 1.5: ocupação imobiliária acima do teto penaliza o score (coerente c/ veredito).
    ocupacao_estoura = bool(c.get("ocupacao_estoura"))
    score = calcular_score_viabilidade(payback, ocup_break, ocupacao_estoura=ocupacao_estoura)

    alertas: list[str] = []
    margem = float(c.get("margem_percentual") or 0)
    receita = float(c.get("receita_mensal") or 0)
    aluguel = float((c.get("custos_detalhados") or {}).get("aluguel")
                    or fin.get("aluguel_mensal") or 0)
    pico = float(c.get("alunos_pico_calculado") or 0)
    cap_pico = float(c.get("capacidade_simultanea_pico") or 0)
    if payback > param("payback_limiar_fraco"):
        alertas.append("⚠️ Payback > 60 meses — modelo não fecha conta (inviável).")
    if margem < param("viab_margem_medio"):
        alertas.append("⚠️ Margem < 10% — sem espaço pra imprevistos.")
    if receita > 0 and aluguel / receita > param("aluguel_sustentavel_pct_faturamento"):
        alertas.append("⚠️ Aluguel > 15% do faturamento projetado — compromete viabilidade.")
    if cap_pico > 0 and pico > cap_pico:
        alertas.append("⚠️ Pico simultâneo > capacidade física nos horários cheios.")
    for s in c.get("sensibilidade") or []:
        if s.get("id") == "matriculas_menos_30pct" and s.get("viabilidade") == "INVIAVEL":
            alertas.append("⚠️ Matrículas −30% torna o modelo inviável — só fecha no benchmark Smart Fit.")
    return {"score_viabilidade": score, "recomendacao_modelo": rec_modelo,
            "ocupacao_break_recomendado": round(ocup_break, 3), "alertas_risco": alertas}


async def analise_financeira_a4_completo(
    bairro: str,
    cidade: str,
    uf: str = "",
    area_m2: float = 1250.0,
    area_m2_min: int = 1000,
    area_m2_max: int = 1500,
    tipo_negocio: str = "academia",
    tamanho_preset: str = "m",
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
    tipo_obra: str = "adaptacao",
    necessita_reforco_estrutural: bool = False,
    matriz_demo_saturacao: dict | None = None,
) -> dict:
    """Macro-tool A4 — viabilidade 3 cenários + aluguel (MRLR Tier 0 primeiro, P-000)."""
    import os

    from tools.aluguel_municipio_portais import MIN_SAMPLES_ALTA
    from tools.enrichment_cache import cached_bcb_imobiliario

    mediana = 0.0
    min_r = 0.0
    max_r = 0.0
    queries_ok = 0
    tier_usado = 3
    motivo_tier1: str | None = None
    municipio: dict = {}
    ref_municipio: dict = {}
    n_validos_t1 = 0
    tier1_suficiente = False
    tier1_vazio = True
    aluguel: dict = {}
    _tier0_mrlr = None

    # ── Tier 0: MRLR (primário) ───────────────────────────────────────────
    try:
        from tools.aluguel_mrlr import aluguel_deterministico

        _m = aluguel_deterministico(area_m2=float(area_m2), cidade=cidade, bairro=bairro)
        if _m.get("status") == "ok" and _m.get("valor_unitario_m2"):
            _tier0_mrlr = _m
            mediana = float(_m["valor_unitario_m2"])
            min_r = round(mediana * 0.85, 2)
            max_r = round(mediana * 1.15, 2)
            tier_usado = 0
    except Exception:
        pass

    # ── Fallback portais legado (opt-in; P-000 proíbe grounding em OPEX) ───
    if tier_usado != 0 and os.getenv("ALUGUEL_PORTAIS_TIER1", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        from tools.aluguel_municipio_portais import pesquisar_aluguel_municipio

        municipio = await pesquisar_aluguel_municipio(
            cidade, uf, area_m2_min, area_m2_max, bairro=bairro
        )
        ref_municipio = municipio.get("aluguel_municipio_referencia") or {}
        n_validos_t1 = int(municipio.get("n_validos") or 0)
        tier1_vazio = n_validos_t1 == 0
        tier1_suficiente = bool(municipio.get("tier1_suficiente"))
        if tier1_suficiente:
            mediana = float(municipio.get("mediana_r_m2", 0.0) or 0)
            min_r = float(municipio.get("min_r_m2", 0.0) or 0)
            max_r = float(municipio.get("max_r_m2", 0.0) or 0)
            queries_ok = n_validos_t1
            aluguel = municipio
            tier_usado = 1
        elif tier1_vazio:
            motivo_tier1 = (
                f"Portais municipais (ZAP/Viva/OLX): nenhum anúncio válido em "
                f"{cidade}{f'/{uf}' if uf else ''} na faixa {area_m2_min}–{area_m2_max} m²."
            )
        else:
            motivo_tier1 = (
                f"Portais municipais: amostra insuficiente (N={n_validos_t1}, "
                f"mínimo recomendado {MIN_SAMPLES_ALTA})."
            )
    elif tier_usado != 0:
        motivo_tier1 = "MRLR indisponível; portais Tier 1 desligados (P-000)."

    fin = analise_financeira_completa(
        area_m2=area_m2,
        bairro=bairro,
        cidade=cidade,
        aluguel_m2_mediana=mediana,
        aluguel_min_m2_real=min_r,
        aluguel_max_m2_real=max_r,
        queries_com_dados=queries_ok,
        tipo_negocio=tipo_negocio,
        tamanho_preset=tamanho_preset,
        uf=uf,
        destino_lat=destino_lat,
        destino_lng=destino_lng,
        fornecedor_principal=fornecedor_principal,
        tipo_obra=tipo_obra,
        necessita_reforco_estrutural=necessita_reforco_estrutural,
        matriz_demo_saturacao=matriz_demo_saturacao,
    )

    fin.setdefault("alertas", [])
    for av in fin.pop("alertas_ticket", []) or []:
        if av not in fin["alertas"]:
            fin["alertas"].append(av)
    for av in fin.pop("alertas_benchmark", []) or []:
        if av not in fin["alertas"]:
            fin["alertas"].append(av)
    for av in fin.pop("alertas_legal", []) or []:
        if av not in fin["alertas"]:
            fin["alertas"].append(av)
    for av in fin.pop("alertas_obra", []) or []:
        if av not in fin["alertas"]:
            fin["alertas"].append(av)

    if tier_usado == 0 and _tier0_mrlr:
        fin["fonte_aluguel"] = _tier0_mrlr.get("fonte") or "MRLR IBAPE-GO (determinístico)" # noqa: E501
        fin["aluguel_mrlr_inputs"] = _tier0_mrlr.get("inputs") # noqa: E501
        fin["aviso_metodologia_aluguel"] = "Aluguel determinístico (equação MRLR sobre espelhos: porte/PIB do município + padrão da renda do bairro + zona). Mesma praça = mesmo valor, recalibrável." # noqa: E501
    elif tier_usado == 1:
        fin["fonte_aluguel"] = (
            f"Portais municipais (ZAP/Viva/OLX) | N={queries_ok}"
        )
        fin["aviso_metodologia_aluguel"] = municipio.get("norte") or municipio.get("aviso", "")
    elif tier_usado >= 3:
        fin["fonte_aluguel"] = fin.get("fonte_aluguel") or "Benchmark ACAD / FipeZap"
        fin["aviso_metodologia_aluguel"] = f"⚠️ MRLR indisponível. {motivo_tier1 or ''} Aluguel no modelo usa benchmark setorial — validar cotação local." # noqa: E501
        alerta_t3 = (
            "Aluguel: MRLR indisponível e portais sem amostra; "
            "modelo financeiro em benchmark ACAD/FipeZap."
        )
        if alerta_t3 not in fin["alertas"]:
            fin["alertas"].append(alerta_t3)
        if n_validos_t1 < MIN_SAMPLES_ALTA and tier_usado >= 3:
            legado = (
                "Aluguel: amostra municipal nos portais insuficiente; "
                "usando benchmark ACAD/Sebrae — validar cotação local."
            )
            if legado not in fin["alertas"]:
                fin["alertas"].append(legado)

    # Ressalva de fonte NÃO-determinística (tier != 0 = MRLR indisponível).
    # Se o guardrail de ocupação reprovou algum cenário com aluguel de fallback
    # (Search Grounding tende a puxar varejo, não galpão → aluguel inflado), o
    # INVIAVEL por ocupação pode ser artefato da fonte. Não silencia a degradação:
    # marca o veredito como sensível à fonte e exige confirmação.
    fin["aluguel_deterministico"] = (tier_usado == 0)
    if tier_usado != 0:
        _cen = fin.get("cenarios") or {}
        _vals = _cen.values() if isinstance(_cen, dict) else (_cen if isinstance(_cen, list) else [])
        if any(isinstance(c, dict) and c.get("ocupacao_estoura") for c in _vals):
            ressalva = (
                "⚠️ Veredito de ocupação baseado em aluguel NÃO-determinístico "
                f"(fonte: {fin.get('fonte_aluguel', '?')}). MRLR indisponível — o "
                "INVIAVEL por ocupação pode ser artefato de aluguel superestimado; "
                "confirmar cotação real de galpão/academia antes de reprovar."
            )
            if ressalva not in fin["alertas"]:
                fin["alertas"].append(ressalva)

    referencia_macro_bcb = None
    if not _tier0_mrlr: # Tenta BCB se MRLR falhou
        bcb_cached = cached_bcb_imobiliario()
        if bcb_cached is not None:
            referencia_macro_bcb = bcb_cached
        else:
            try:
                from tools.bcb_imobiliario_olinda import extrair_resumo_imobiliario

                ctx = f"{cidade}/{uf}" if uf else cidade
                referencia_macro_bcb = extrair_resumo_imobiliario(cidade_contexto=ctx)
            except Exception as exc:
                referencia_macro_bcb = {
                    "ok": False,
                    "erro": str(exc)[:200],
                    "cidade_contexto": cidade,
                    "norte": (
                        "Panorama macro BCB indisponível nesta execução; "
                        "não é referência de aluguel local (R$/m²)."
                    ),
                }

    fin["aluguel_municipio_referencia"] = ref_municipio
    fin["referencia_macro_bcb"] = referencia_macro_bcb
    fin["aluguel_pesquisa_detalhes"] = {
        "tier": tier_usado,
        "tier1_vazio": n_validos_t1 == 0,
        "tier1_suficiente": tier1_suficiente,
        "n_validos_tier1": n_validos_t1,
        "motivo_tier1": motivo_tier1,
        "mediana_r_m2": mediana,
        "min_r_m2": min_r,
        "max_r_m2": max_r,
        "queries_com_dados": queries_ok,
        "valores_coletados": aluguel.get("valores_coletados", []),
        "faixa_rs_m2": (
            ref_municipio.get("faixa_rs_m2")
            or municipio.get("faixa_rs_m2")
            or (
                {"p25": min_r, "mediana": mediana, "p75": max_r} if mediana
                else None
            )
        ),
        "confianca_municipio": ref_municipio.get("confianca") or municipio.get("confianca"),
        "classificacao_municipio": municipio.get("classificacao"),
        "tier1_tentativa": {
            "n_validos": n_validos_t1,
            "confianca": municipio.get("confianca"),
            "classificacao": municipio.get("classificacao"),
            "aviso_portais": municipio.get("aviso"),
            "erros_portais": municipio.get("erros", [])[:10],
            "urls_por_portal": {
                p: len(u) for p, u in (municipio.get("urls_consultadas") or {}).items()
            },
        },
        "fontes_resumo": [
            {"portal": p, "n_urls": len(u)}
            for p, u in (municipio.get("urls_consultadas") or {}).items()
        ],
        "erros_portais": municipio.get("erros", [])[:10],
    }
    # Schema v1.5: contexto do tamanho/tipo pro A4 redator referenciar
    # benchmarks corretos e pro markdown final mostrar a faixa.
    fin["contexto_dimensionamento"] = {
        "tipo_negocio": tipo_negocio,
        "tamanho_preset": tamanho_preset,
        "area_m2_efetiva": area_m2,
        "area_m2_min": area_m2_min,
        "area_m2_max": area_m2_max,
    }
    # Decisão DETERMINÍSTICA (LLM não inventa): score_viabilidade (folha do veredito),
    # recomendacao_modelo e alertas de risco obrigatórios. LLM só redige a justificativa.
    _dec = _resumo_decisao_a4(fin)
    fin["score_viabilidade"] = _dec["score_viabilidade"]
    fin["recomendacao_modelo"] = _dec["recomendacao_modelo"]
    fin["ocupacao_break_recomendado"] = _dec["ocupacao_break_recomendado"]
    for av in _dec["alertas_risco"]:
        if av not in fin["alertas"]:
            fin["alertas"].append(av)
    return fin


def analise_financeira_completa(
    area_m2: float,
    bairro: str,
    cidade: str,
    aluguel_m2_mediana: float = 0.0,
    aluguel_min_m2_real: float = 0.0,
    aluguel_max_m2_real: float = 0.0,
    queries_com_dados: int = 0,
    tipo_negocio: str = "academia",
    tamanho_preset: str = "m",
    uf: str = "",
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
    tipo_obra: str = "adaptacao",
    necessita_reforco_estrutural: bool = False,
    matriz_demo_saturacao: dict | None = None,
) -> dict:
    """
    Macro-tool: resolve aluguel + viabilidade em 3 cenários em UMA chamada.
    Se `aluguel_m2_mediana` > 0 (MRLR ou portais), usa-o.
    Caso contrário, fallback FipeZap ou benchmark `estimar_aluguel` (ACAD/Sebrae).
    """
    if aluguel_m2_mediana and aluguel_m2_mediana > 0:
        aluguel_mensal = round(float(aluguel_m2_mediana) * float(area_m2), 2)
        # Se vieram min/max reais do batch, usa-os; senão deriva ±30% pra dar range
        aluguel_min_m2 = (
            float(aluguel_min_m2_real) if aluguel_min_m2_real and aluguel_min_m2_real > 0
            else round(float(aluguel_m2_mediana) * 0.7, 2)
        )
        aluguel_max_m2 = (
            float(aluguel_max_m2_real) if aluguel_max_m2_real and aluguel_max_m2_real > 0
            else round(float(aluguel_m2_mediana) * 1.4, 2)
        )
        fonte_aluguel = (
            f"Fonte externa (mediana de {queries_com_dados} pontos)" if queries_com_dados else "Fonte externa"
        )
    else:
        # Tier 1.5: FipeZap (dados mensais oficiais do mercado)
        try:
            from tools.fipezap_tools import get_aluguel_comercial_m2
            fipe = get_aluguel_comercial_m2(cidade)
        except Exception:
            fipe = {"disponivel": False}

        if fipe.get("disponivel") and fipe.get("preco_m2"):
            preco_m2 = float(fipe["preco_m2"])
            aluguel_mensal = round(preco_m2 * float(area_m2), 2)
            aluguel_min_m2 = round(preco_m2 * 0.7, 2)
            aluguel_max_m2 = round(preco_m2 * 1.4, 2)
            fonte_aluguel = fipe["fonte"]
        else:
            # Tier 2: Benchmarks ACAD hardcoded
            bench = estimar_aluguel(cidade, area_m2)
            aluguel_mensal = bench["aluguel_estimado"]
            bench_m2 = bench["preco_m2_estimado"]
            aluguel_min_m2 = round(bench_m2 * 0.6, 2)
            aluguel_max_m2 = round(bench_m2 * 1.5, 2)
            fonte_aluguel = "Benchmark ACAD"

    _rmb, _renda_fonte = _renda_media_bairro(cidade, bairro, uf)
    viabilidade = calcular_viabilidade_3_cenarios(
        area_m2=area_m2,
        aluguel_mensal=aluguel_mensal,
        bairro=bairro,
        cidade=cidade,
        tipo_negocio=tipo_negocio,
        tamanho_preset=tamanho_preset,
        uf=uf,
        destino_lat=destino_lat,
        destino_lng=destino_lng,
        fornecedor_principal=fornecedor_principal,
        renda_media_bairro=_rmb,
        renda_percentil=_renda_percentil_bairro(cidade, bairro, uf),
        tipo_obra=tipo_obra,
        necessita_reforco_estrutural=necessita_reforco_estrutural,
        matriz_demo_saturacao=matriz_demo_saturacao,
    )

    viabilidade["renda_fonte"] = _renda_fonte  # (c) transparência: qual fonte de renda foi usada
    viabilidade["fonte_aluguel"] = fonte_aluguel
    viabilidade["aluguel_min_m2_observado"] = aluguel_min_m2
    viabilidade["aluguel_mediana_m2_observado"] = (
        float(aluguel_m2_mediana) if aluguel_m2_mediana else None
    )
    viabilidade["aluguel_max_m2_observado"] = aluguel_max_m2

    return viabilidade
