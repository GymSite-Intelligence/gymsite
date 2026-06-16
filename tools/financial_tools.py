from typing import Any, Optional
# tools/financial_tools.py
"""
Modelagem financeira pra viabilidade de academia (schema v2).

Todos os benchmarks vêm de fontes auditáveis do setor fitness brasileiro:

📚 FONTES PRIMÁRIAS:
  - ACAD Brasil (Associação Brasileira de Academias) — relatórios anuais 2023/2024
  - SEBRAE — "Como abrir uma academia" + "Painel do setor fitness 2024"
  - Smart Fit Holdings (BVMF: SMFT3) — releases trimestrais 2023-2024
  - Bodytech Group — apresentação ao investidor 2024
  - IHRSA Latin America Report 2024

📊 INDICADORES-CHAVE ACAD 2024:
  - Brasil: 32.000+ academias, +8%/ano (crescimento setor)
  - Aluno médio: 2-3 visitas/semana
  - Inadimplência média: 4-7% (low-cost na faixa alta)
  - Ticket médio: low R$89-119 / mid R$149-249 / premium R$299-599
  - Folha % faturamento: 18-28% (saudável)
  - Margem líquida saudável: 15-25%
  - Payback ideal: 24-36 meses

⚠️ ESTES VALORES SÃO BENCHMARKS — não substituem due diligence local.
   Recalibráveis via tabela Supabase `parametros_metodologia` (param()).
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

# Constantes sourceadas via param() (Supabase override > _DEFAULTS rotulado).
TICKET_MEDIO = param("ticket_medio_nacional")
ALUNOS_POR_M2 = param("alunos_por_m2_legado")

# ── 3 cenários de ticket (ACAD/Sebrae benchmarks via param) ─────────
TICKET_FAIXAS = {
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

# Matrículas por m² (PAGANTES, não simultâneos no pico).
# Calibrações cons/real/agres pra cada modelo, baseadas em:
# - Smart Fit Brasil: ~2.500 alunos / 800m² = ~3.0 matr/m² (top performers)
# - Bluefit/Selfit: ~1.800-2.000 alunos / 750m² = ~2.4-2.7 matr/m²
# - Bodytech entry: ~1.000 alunos / 1.500m² = ~0.7 matr/m²
# - Bio Ritmo (premium): ~600 alunos / 2.000m² = ~0.3 matr/m²
MATRICULADOS_POR_M2 = {
    m: {cal: param(f"matr_m2_{m}_{cal}")
        for cal in ("conservador", "realista", "agressivo")}
    for m in ("low", "mid", "premium")
}

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

    faixa_key = faixa if faixa in MATRICULADOS_POR_M2 else "mid"
    faixa_info = TICKET_FAIXAS[faixa_key]
    ticket = ticket_override if ticket_override is not None else faixa_info["ticket_medio"]
    inad = TAXA_INADIMPLENCIA_POR_MODELO[faixa_key]
    ticket_realizado = round(ticket * (1.0 - inad), 2)

    calibracoes = MATRICULADOS_POR_M2[faixa_key]
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

# Capacidade FÍSICA simultânea (no pico horário) — check de conforto/segurança.
# Diferente de matrículas: quantas pessoas cabem ao mesmo tempo na academia.
CAPACIDADE_SIMULTANEA_POR_M2 = param_por_modelo("capacidade_simultanea")

# Frequência semanal média do aluno por modelo (ACAD/Sebrae 2024).
# Low-cost: alunos mais regulares (preço baixo → uso intenso pra valer).
# Premium: alunos mais ocupados, frequência menor mas churn menor.
FREQUENCIA_SEMANAL = param_por_modelo("frequencia_semanal")

# Pico share: % dos que vieram num dia que estão simultaneamente no pico (18h-21h).
# Padrão ACAD: 25%.
PICO_SHARE = param("pico_share")

# Taxas operacionais — calibradas por modelo (ACAD/Sebrae 2024).
# Low-cost tem maior inadimplência (cliente mais sensível a preço) e maior churn.
# Premium tem menor inadimplência (alunos mais comprometidos) e menor churn.
TAXA_INADIMPLENCIA_POR_MODELO = param_por_modelo("inadimplencia")

# Backward-compat — código v1 que ainda lê o campo único
TAXA_INADIMPLENCIA = param("inadimplencia_mid")

TAXA_CANCELAMENTO_MENSAL_POR_MODELO = param_por_modelo("churn_mensal")
TAXA_CANCELAMENTO_MENSAL = param("churn_mensal_mid")   # backward-compat

# Custos detalhados — 12 linhas. Valores são "base" e são modulados por:
# - aluguel: vem do Tier 1 Search Grounding (mediana) ou benchmark
# - área: muitos custos escalam com m²
# - modelo: premium tem folha maior, low-cost tem manutenção menor
CUSTOS_DETALHADOS_BASE = {
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

CUSTOS_MARKETING_PCT = param_por_modelo("marketing_pct")

# CAPEX detalhado
CAPEX_DETALHADO_BASE = {
    "equipamentos_por_m2": param_por_modelo("capex_equip_m2"),
    "obra_adaptacao_por_m2": param_por_modelo("capex_obra_m2"),
    "projeto_arquitetonico": param("capex_projeto_arquitetonico"),
    "alvara_e_taxas": param("capex_alvara_taxas"),
    "contingencia_pct": param("capex_contingencia_pct"),
    "capital_giro_meses": param_int("capex_capital_giro_meses"),
}

# Sensibilidade — 3 stress tests aplicados em cima do cenário "realista"
STRESS_TESTS = [
    {"id": "aluguel_mais_20pct",     "label": "Aluguel +20%",     "delta_aluguel": 0.20},
    {"id": "matriculas_menos_30pct", "label": "Matrículas -30%",  "delta_matriculas": -0.30},
    {"id": "ticket_menos_15pct",     "label": "Ticket -15%",      "delta_ticket": -0.15},
]

# Ticket mensal sustentável ≈ % da renda domiciliar (ACAD / A2).
TICKET_RENDA_PCT: dict[str, float] = param_por_modelo("ticket_renda_pct")

# Custo de capital pra cálculo de VPL/TIR (12% a.a. ≈ Selic + premium fitness)
CUSTO_CAPITAL_ANUAL = param("custo_capital_anual")


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
                          area_m2: float, ticket: float = TICKET_MEDIO) -> dict:
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
    capacidade = int(area_m2 * ALUNOS_POR_M2)

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
) -> dict:
    _capex_ctx = _resolve_capex_indices(uf, capex_indices)
    # Benchmarks setoriais atualizados (Panorama Fitness Brasil mais recente).
    # Sobrescreve constantes ACAD 2024 hardcoded quando Search Grounding
    # consegue extrair dados. Fallback é o próprio default — pipeline nunca
    # falha por benchmark ausente.
    from tools.benchmarks_tool import obter_benchmarks_setoriais
    _bench = obter_benchmarks_setoriais()
    _ticket_dinamico = _bench.get("ticket_por_modelo") or {}
    _inadimp_dinamica = _bench.get("inadimplencia_por_modelo") or {}
    _churn_dinamico = _bench.get("churn_mensal_por_modelo") or {}
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

    # CAPEX e custos comuns que não dependem do modelo
    iptu_mensal = CUSTOS_DETALHADOS_BASE["iptu_mensal_base"]
    internet = CUSTOS_DETALHADOS_BASE["internet_mensal"]
    contabilidade = CUSTOS_DETALHADOS_BASE["contabilidade_mensal"]
    sistema = CUSTOS_DETALHADOS_BASE["sistema_gestao_mensal"]

    # Schema v1.5: equipamentos por modelo financeiro vêm do kit detalhado.
    # Low usa kit 1 tamanho abaixo (econômico), Mid usa tamanho selecionado,
    # Premium usa 1 acima (robusto). Fallback gracioso se kit não existe.
    try:
        from tools.kits_equipamentos import kit_totais_por_cenario
        equipamentos_por_cenario = kit_totais_por_cenario(tipo_negocio, tamanho_preset)
    except Exception:
        equipamentos_por_cenario = {"low": None, "mid": None, "premium": None}

    for faixa_key, faixa in TICKET_FAIXAS.items():
        raw_ticket = float(_ticket_dinamico.get(faixa_key) or faixa["ticket_medio"])
        ticket, ticket_notes = _resolver_ticket_faixa(
            faixa_key, raw_ticket, renda_media_bairro
        )
        alertas_ticket.extend(ticket_notes)

        # ── DEMANDA: 3 calibrações de matrículas + pico simultâneo ──
        calibracoes = MATRICULADOS_POR_M2[faixa_key]
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
            area_m2 * CAPACIDADE_SIMULTANEA_POR_M2[faixa_key]
        )
        freq_semanal = FREQUENCIA_SEMANAL[faixa_key]
        # Alunos esperados simultaneamente no pico:
        # matr × (freq/7 dias) × pico_share
        alunos_pico_calc = int(matr_real * (freq_semanal / 7.0) * PICO_SHARE)
        folga_pct = round(
            (1.0 - alunos_pico_calc / capacidade_simultanea_pico) * 100, 1
        ) if capacidade_simultanea_pico > 0 else 0.0

        # ── RECEITA ──
        # Inadimplência por modelo: usa benchmark atualizado se disponível,
        # senão ACAD 2024 (low 6%, mid 4%, premium 2.5%). Panorama 2025
        # mostra que esses valores assumem débito recorrente — sem
        # recorrência, inadimplência real é 15-25%.
        inadimplencia = _inadimp_dinamica.get(faixa_key) or TAXA_INADIMPLENCIA_POR_MODELO[faixa_key]
        churn_mensal = _churn_dinamico.get(faixa_key) or TAXA_CANCELAMENTO_MENSAL_POR_MODELO[faixa_key]
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
        )["total"]
        folha = CUSTOS_DETALHADOS_BASE["folha_por_modelo"][faixa_key]
        custos = {
            "aluguel": round(aluguel_mensal, 2),
            "condominio": round(
                aluguel_mensal * CUSTOS_DETALHADOS_BASE["condominio_pct_aluguel"], 2
            ),
            "iptu": round(iptu_mensal, 2),
            "energia": round(
                area_m2 * CUSTOS_DETALHADOS_BASE["energia_por_m2"]
                * (1.5 if faixa_key == "premium" else 1.0),  # premium gasta 50% mais
                2,
            ),
            "agua": round(area_m2 * CUSTOS_DETALHADOS_BASE["agua_por_m2"], 2),
            "internet": round(internet, 2),
            "folha": round(folha, 2),
            "manutencao": round(
                capex_total * CUSTOS_DETALHADOS_BASE["manutencao_pct_capex"], 2
            ),
            "contabilidade": round(contabilidade, 2),
            "sistema_gestao": round(sistema, 2),
            "seguro": round(
                capex_total * CUSTOS_DETALHADOS_BASE["seguro_pct_capex"], 2
            ),
            "outros": round(
                receita_mensal * CUSTOS_DETALHADOS_BASE["outros_pct_receita"], 2
            ),
        }
        custos_fixos_total = sum(custos.values())

        # Marketing (pct da receita)
        mkt_pct = CUSTOS_MARKETING_PCT[faixa_key]
        marketing_mensal = round(receita_mensal * mkt_pct, 2)

        custos_totais = custos_fixos_total + marketing_mensal

        # ── RESULTADO ──
        lucro_mensal = receita_mensal - custos_totais
        margem_pct = (lucro_mensal / receita_mensal * 100) if receita_mensal > 0 else 0
        alunos_break_even = (
            int(custos_totais / ticket_realizado) + 1
            if ticket_realizado > 0 else 0
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
        )
        capital_giro = round(
            custos_totais * CAPEX_DETALHADO_BASE["capital_giro_meses"], 2
        )
        investimento_total = capex_detalhado["total"] + capital_giro
        payback_meses = (
            int(investimento_total / lucro_mensal) if lucro_mensal > 0 else 999
        )
        tir_anual = _calcular_tir_anual(investimento_total, lucro_mensal, anos=5)
        vpl_5_anos = _calcular_vpl(
            investimento_total, lucro_mensal, anos=5,
            taxa_anual=CUSTO_CAPITAL_ANUAL,
        )

        # ── VEREDITO ──
        viabilidade = _classificar_viabilidade(lucro_mensal, payback_meses, margem_pct)

        # ── SENSIBILIDADE (3 stress tests) ──
        sensibilidade = _calcular_sensibilidade(
            base_aluguel=aluguel_mensal,
            base_matriculas=matr_real,
            base_ticket=ticket,
            custos_fixos_sem_aluguel=custos_fixos_total - custos["aluguel"],
            marketing_pct=mkt_pct,
            inadimplencia=TAXA_INADIMPLENCIA,
            investimento_total=investimento_total,
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
            "pico_share": PICO_SHARE,
            "alunos_pico_calculado": alunos_pico_calc,
            "folga_capacidade_pct": folga_pct,

            # Receita
            "ticket_realizado_estimado": round(ticket_realizado, 2),
            "taxa_inadimplencia": inadimplencia,
            "taxa_cancelamento_mensal": churn_mensal,
            "receita_mensal": round(receita_mensal, 2),

            # Custos (12 linhas + agregado)
            "custos_detalhados": custos,
            "custos_fixos_total": round(custos_fixos_total, 2),
            "marketing_pct_faturamento": mkt_pct,
            "marketing_mensal": marketing_mensal,
            "custos_totais": round(custos_totais, 2),

            # Resultado
            "lucro_mensal_estimado": round(lucro_mensal, 2),
            "margem_percentual": round(margem_pct, 1),
            "alunos_break_even": alunos_break_even,

            # Investimento
            "capex_detalhado": capex_detalhado,
            "capex_total": capex_detalhado["total"],
            "capital_giro_meses": CAPEX_DETALHADO_BASE["capital_giro_meses"],
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

    melhor = _escolher_cenario_recomendado(cenarios, renda_media_bairro)
    alertas_benchmark = _alertas_vs_sector_listed(cenarios)
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
        "melhor_lucro_mensal": melhor["lucro_mensal_estimado"],
        "melhor_payback_meses": melhor["payback_meses"],
        "schema_cenarios": "v2",
        "alertas_benchmark": alertas_benchmark,
        "alertas_ticket": alertas_ticket,
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
        pct = TICKET_RENDA_PCT.get(faixa_key, param("ticket_renda_pct_mid"))
        cap = round(renda_media_bairro * pct, 2)
        if ticket > cap:
            avisos.append(
                f"ticket {faixa_key} capado em R${cap:.0f} "
                f"({int(pct * 100)}% da renda bairro R${renda_media_bairro:.0f})"
            )
            ticket = cap
    return round(ticket, 2), avisos


def _renda_media_bairro(cidade: str, bairro: str, uf: str) -> float | None:
    """Renda per capita do bairro p/ escolher o tier do modelo (low/mid/premium).

    PRIMÁRIO: `renda_bairro` IBGE Censo 2022 (renda_pc) — MESMA fonte do A9/headroom.
    Antes lia o CKAN 2010 (`bairro_renda_loader.renda_media`) como primário, o que
    fazia o A4 recomendar Low Cost em bairro top-1% (ex.: Cocó: CKAN 2010 = R$2.095
    -> tier low, enquanto IBGE 2022 = R$4.952 -> premium). Isso contradizia o
    posicionamento OCEANO_AZUL/Premium do A9 — duas fontes de renda divergentes.
    CKAN 2010 (per capita) fica só como FALLBACK quando o IBGE 2022 não cobre o bairro.
    """
    if not (bairro or "").strip():
        return None
    # Fonte 2022 (coerente com o A9)
    try:
        from tools.posicionamento_renda import renda_bairro_ipece

        r = renda_bairro_ipece(cidade, uf or "", bairro)
        if r and r.get("renda_pc"):
            return float(r["renda_pc"])
    except Exception:
        pass
    # Fallback CKAN 2010 — usa renda_media_per_capita (mesma ESCALA dos thresholds)
    try:
        from tools.bairro_renda_loader import enrich_demografia_bairro

        b = enrich_demografia_bairro({"bairro": {}}, cidade, bairro, uf or "").get("bairro") or {}
        val = b.get("renda_media_per_capita") or b.get("renda_media")
        return float(val) if val is not None else None
    except Exception:
        return None


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
) -> dict[str, Any]:
    """
    Escolhe cenário alinhado ao tier de renda local — não só max(lucro) com ticket irreal.
    """
    preferido = _tier_mercado_por_renda(renda_media_bairro)
    ordem = {"low": 0, "mid": 1, "premium": 2}
    viaveis = [
        c for c in cenarios.values()
        if c.get("viabilidade") not in ("INVIAVEL", None)
    ]
    pool = viaveis or list(cenarios.values())

    def _rank(c: dict[str, Any]) -> tuple[float, float, float]:
        faixa = _faixa_key_de_modelo(c.get("modelo", ""))
        tier_gap = abs(ordem.get(faixa, 1) - ordem.get(preferido, 1))
        lucro = float(c.get("lucro_mensal_estimado") or 0)
        payback = float(c.get("payback_meses") or 999)
        # Prioriza tier de mercado, depois lucro, depois payback menor.
        return (-tier_gap, lucro, -payback)

    return max(pool, key=_rank)


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
    if capex_indices:
        return capex_indices
    if not (uf or "").strip():
        return None
    try:
        from tools.sinapi_indices import capex_indices_for_uf

        block = capex_indices_for_uf(uf)
        if (block.get("fonte_obra") or "").startswith("benchmark_fixo"):
            return None
        return block
    except Exception:
        return None


def _obra_por_m2_modelo(
    modelo: str,
    *,
    capex_indices: dict | None = None,
) -> float:
    """R$/m² obra adaptação: bundle SINAPI > fallback CAPEX_DETALHADO_BASE."""
    modelo = (modelo or "mid").lower()
    if capex_indices:
        por_mod = capex_indices.get("obra_adaptacao_por_m2_por_modelo")
        if isinstance(por_mod, dict) and por_mod.get(modelo) is not None:
            return float(por_mod[modelo])
        mid = capex_indices.get("obra_adaptacao_por_m2")
        if mid is not None and modelo == "mid":
            return float(mid)
        if mid is not None:
            ratios = {"low": _RATIO_LOW_MID, "premium": _RATIO_PREMIUM_MID}
            if modelo in ratios:
                return round(float(mid) * ratios[modelo], 2)
    return float(CAPEX_DETALHADO_BASE["obra_adaptacao_por_m2"][modelo])


def _calcular_capex_detalhado(
    area_m2: float,
    modelo: str,
    equipamentos_override: float | None = None,
    uf_destino: str | None = None,
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
    capex_indices: dict | None = None,
) -> dict:
    """Breakdown CAPEX com contingência + frete ANTT.

    Schema v1.5: `equipamentos_override` aceita valor do kit detalhado real.
    Schema v1.6: `uf_destino` ativa cálculo de frete via ANTT (R$/km).
    Quando UF fornecida, adiciona linha `frete_equipamentos` ao subtotal.
    """
    if equipamentos_override is not None and equipamentos_override > 0:
        equip = equipamentos_override
    else:
        equip = area_m2 * CAPEX_DETALHADO_BASE["equipamentos_por_m2"][modelo]
    obra = area_m2 * _obra_por_m2_modelo(modelo, capex_indices=capex_indices)
    projeto = CAPEX_DETALHADO_BASE["projeto_arquitetonico"]
    alvara = CAPEX_DETALHADO_BASE["alvara_e_taxas"]

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

    subtotal = equip + obra + projeto + alvara + frete
    contingencia = subtotal * CAPEX_DETALHADO_BASE["contingencia_pct"]
    return {
        "equipamentos": round(equip, 2),
        "obra_adaptacao": round(obra, 2),
        "projeto_arquitetonico": round(projeto, 2),
        "alvara_e_taxas": round(alvara, 2),
        "frete_equipamentos": round(frete, 2),
        "frete_detalhes": frete_detalhes,
        "contingencia_pct": CAPEX_DETALHADO_BASE["contingencia_pct"],
        "contingencia_valor": round(contingencia, 2),
        "total": round(subtotal + contingencia, 2),
        "fonte_equipamentos": (
            "kit detalhado v1.5" if equipamentos_override else "R$/m² benchmark"
        ),
        "fonte_frete": (
            "ANTT 6.034/2024 + margem broker" if frete > 0 else "não calculado"
        ),
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


def _classificar_viabilidade(lucro: float, payback: int, margem: float) -> dict:
    """Retorna {status, justificativa} baseado em 3 critérios."""
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
) -> list[dict]:
    """
    3 stress tests com lucro/payback/viabilidade resultantes.

    Cada stress aplica um delta sobre o cenário "realista":
    - aluguel +20%: simula contrato com reajuste alto
    - matrículas -30%: simula execução abaixo do benchmark Smart Fit
    - ticket -15%: simula pressão de preço (concorrência low-cost agressiva)
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
        lucro = receita - custos_total
        margem = (lucro / receita * 100) if receita > 0 else 0
        payback = int(investimento_total / lucro) if lucro > 0 else 999
        viab = _classificar_viabilidade(lucro, payback, margem)

        resultados.append({
            "id": stress["id"],
            "label": stress["label"],
            "lucro_mensal": round(lucro, 2),
            "margem_percentual": round(margem, 1),
            "payback_meses": payback,
            "viabilidade": viab["status"],
        })
    return resultados


# ── Macro-tool consolidadora A4 (Task #56 — mesmo padrão A3a/A3b) ──
def calcular_score_viabilidade(payback_meses: float, ocupacao_break: float) -> float:
    """Score 0-10 de viabilidade (CANÔNICO) — payback + ocupação no break-even.

    Cortes e base via param() (calibração GymSite v2). Mesma fórmula usada pela
    granularização (metodologia_explain). É a FOLHA `score_viabilidade` do score_bairro
    → veredito; determinístico para o LLM do A4 não inventar.
    """
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
    score = calcular_score_viabilidade(payback, ocup_break)

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
) -> dict:
    """
    Macro-tool A4 FinancialEstimator — consolida 2 tools em 1 call.

    Por que existe (Run 20 deu MALFORMED_FUNCTION_CALL no A4):
    A4 com 2 tools (pesquisar_aluguel_mediana + analise_financeira_completa,
    a segunda com 7 parâmetros) confundiu o Pro na primeira function_call,
    resultando em ERROR:MALFORMED_FUNCTION_CALL e A4 OUT=0.

    Esta macro encapsula tudo em código Python:
      1. await pesquisar_aluguel_mediana — 3 queries paralelas Search Grounding
      2. analise_financeira_completa — viabilidade 3 cenários com mediana real

    A4 vira redator com 1 tool, 1 call. Mesmo pattern que eliminou
    MALFORMED em A1 (anchoring) e A3b (competitor_tools).

    Returns:
        Dict mesclando viabilidade financeira + detalhes da pesquisa de aluguel,
        pronto pra A4 emitir como JSON via output_key="analise_financeira".
    """
    from tools.aluguel_municipio_portais import (
        MIN_SAMPLES_ALTA,
        pesquisar_aluguel_municipio,
    )
    from tools.enrichment_cache import cached_aluguel_portais, cached_bcb_imobiliario
    from tools.gemini_search_grounding import pesquisar_aluguel_mediana

    municipio_cached = cached_aluguel_portais()
    if municipio_cached is not None:
        municipio = municipio_cached
    else:
        municipio = await pesquisar_aluguel_municipio(
            cidade, uf, area_m2_min, area_m2_max
        )
    ref_municipio = municipio.get("aluguel_municipio_referencia") or {}
    n_validos_t1 = int(municipio.get("n_validos") or 0)
    tier1_vazio = n_validos_t1 == 0
    tier1_suficiente = bool(municipio.get("tier1_suficiente"))
    motivo_tier1: str | None = None
    tier_usado = 1

    if tier1_suficiente:
        mediana = municipio.get("mediana_r_m2", 0.0)
        min_r = municipio.get("min_r_m2", 0.0)
        max_r = municipio.get("max_r_m2", 0.0)
        queries_ok = n_validos_t1
        aluguel = municipio
    else:
        if tier1_vazio:
            motivo_tier1 = (
                f"Portais municipais (ZAP/Viva/OLX): nenhum anúncio válido em "
                f"{cidade}{f'/{uf}' if uf else ''} na faixa {area_m2_min}–{area_m2_max} m²."
            )
        else:
            motivo_tier1 = (
                f"Portais municipais: amostra insuficiente (N={n_validos_t1}, "
                f"mínimo recomendado {MIN_SAMPLES_ALTA})."
            )
        aluguel = await pesquisar_aluguel_mediana(
            bairro, cidade, uf, area_m2_min, area_m2_max
        )
        mediana = aluguel.get("mediana_r_m2", 0.0)
        min_r = aluguel.get("min_r_m2", 0.0)
        max_r = aluguel.get("max_r_m2", 0.0)
        queries_ok = aluguel.get("queries_com_dados", 0)
        tier_usado = 2 if mediana and mediana > 0 else 3

    # 2. Calcula viabilidade 3 cenários (síncrono — só matemática)
    # Schema v1.5: propaga tipo_negocio + tamanho_preset pra cascata
    # de equipamentos detalhada (kit por modelo financeiro).
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
    )

    fin.setdefault("alertas", [])
    for av in fin.pop("alertas_ticket", []) or []:
        if av not in fin["alertas"]:
            fin["alertas"].append(av)
    for av in fin.pop("alertas_benchmark", []) or []:
        if av not in fin["alertas"]:
            fin["alertas"].append(av)

    if tier_usado == 1:
        fin["fonte_aluguel"] = (
            f"Portais municipais (ZAP/Viva/OLX) | N={queries_ok}"
        )
        fin["aviso_metodologia_aluguel"] = municipio.get("norte") or municipio.get("aviso", "")
    elif tier_usado == 2 and mediana and mediana > 0:
        fin["fonte_aluguel"] = (
            f"Search Grounding (mediana de {queries_ok} queries)"
            if queries_ok
            else "Search Grounding (Tier 2 — portais sem amostra)"
        )
        fin["aviso_metodologia_aluguel"] = (
            f"⚠️ {motivo_tier1} "
            f"Fonte ativa: Search Grounding — mediana R$ {float(mediana):.0f}/m² "
            f"({queries_ok} consulta(s) com dados). "
            "Panorama web municipal; não substitui cotação de locador."
        )
        alerta_t2 = (
            "Aluguel no modelo: portais municipais "
            + ("sem amostra (N=0)" if tier1_vazio else f"com amostra baixa (N={n_validos_t1})")
            + "; Search Grounding é a referência ativa — validar com imobiliária local."
        )
        if alerta_t2 not in fin["alertas"]:
            fin["alertas"].append(alerta_t2)
    elif tier_usado >= 3:
        fin["fonte_aluguel"] = fin.get("fonte_aluguel") or "Benchmark ACAD / FipeZap"
        fin["aviso_metodologia_aluguel"] = (
            f"⚠️ {motivo_tier1} Search Grounding sem valores parseáveis. "
            "Aluguel no modelo usa benchmark setorial — validar cotação local."
        )
        alerta_t3 = (
            "Aluguel: portais e Search Grounding sem mediana utilizável; "
            "modelo financeiro em benchmark ACAD/FipeZap."
        )
        if alerta_t3 not in fin["alertas"]:
            fin["alertas"].append(alerta_t3)
        if n_validos_t1 < MIN_SAMPLES_ALTA:
            legado = (
                "Aluguel: amostra municipal nos portais insuficiente; "
                "usando benchmark ACAD/Sebrae — validar cotação local."
            )
            if legado not in fin["alertas"]:
                fin["alertas"].append(legado)

    referencia_macro_bcb = None
    if tier1_vazio:
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
        "tier1_vazio": tier1_vazio,
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
                {"p25": min_r, "mediana": mediana, "p75": max_r}
                if tier_usado == 2 and mediana
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
            {"query": (f.get("query") or "")[:60], "n_valores": f.get("n_valores", 0)}
            for f in (aluguel.get("fontes") or [])
        ]
        if tier_usado == 2
        else [
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
) -> dict:
    """
    Macro-tool: resolve aluguel + viabilidade em 3 cenários em UMA chamada.

    Tiers de aluguel:
    1. Se `aluguel_m2_mediana > 0` (mediana de N queries Search Grounding —
       Task #47), usa esse valor: aluguel_mensal = aluguel_m2_mediana × area_m2.
       Marca `fonte_aluguel = "Search Grounding (mediana de N queries)"`.
       Usa `aluguel_min_m2_real`/`max_m2_real` se vieram do mesmo batch.
    2. Caso contrário (Tier 1 indisponível ou todas queries falharam),
       fallback pro benchmark `estimar_aluguel(cidade, area_m2)` (ACAD/Sebrae).
       Marca `fonte_aluguel = "Benchmark ACAD"` + alertas de incerteza.

    Em ambos calcula `calcular_viabilidade_3_cenarios` e devolve dict
    consolidado, eliminando uma rodada LLM no FinancialEstimator.
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
            f"Search Grounding (mediana de {queries_com_dados} queries)"
            if queries_com_dados else "Search Grounding"
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
        renda_media_bairro=_renda_media_bairro(cidade, bairro, uf),
    )

    viabilidade["fonte_aluguel"] = fonte_aluguel
    viabilidade["aluguel_min_m2_observado"] = aluguel_min_m2
    viabilidade["aluguel_mediana_m2_observado"] = (
        float(aluguel_m2_mediana) if aluguel_m2_mediana else None
    )
    viabilidade["aluguel_max_m2_observado"] = aluguel_max_m2

    return viabilidade
