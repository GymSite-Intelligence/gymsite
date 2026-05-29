from typing import Optional
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
"""

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

TICKET_MEDIO = 149.90
ALUNOS_POR_M2 = 3.5

# ── 3 cenários de ticket (ACAD/Sebrae benchmarks) ──────────────────
TICKET_FAIXAS = {
    "low": {
        "label": "Low Cost",
        "ticket_medio": 89.90,
        "descricao": "Modelo econômico 24h, sem personal, autoatendimento",
        "exemplos": "Smart Fit, Bluefit, Selfit",
    },
    "mid": {
        "label": "Mid Market",
        "ticket_medio": 149.90,
        "descricao": "Modelo intermediário com aulas em grupo e suporte",
        "exemplos": "Bodytech entry, academias regionais premium",
    },
    "premium": {
        "label": "Premium",
        "ticket_medio": 299.90,
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
    "low":     {"conservador": 1.5, "realista": 2.2, "agressivo": 3.0},
    "mid":     {"conservador": 1.0, "realista": 1.4, "agressivo": 1.8},
    "premium": {"conservador": 0.4, "realista": 0.6, "agressivo": 0.9},
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
CAPACIDADE_SIMULTANEA_POR_M2 = {"low": 0.55, "mid": 0.40, "premium": 0.25}

# Frequência semanal média do aluno por modelo (ACAD/Sebrae 2024).
# Low-cost: alunos mais regulares (preço baixo → uso intenso pra valer).
# Premium: alunos mais ocupados, frequência menor mas churn menor.
FREQUENCIA_SEMANAL = {"low": 2.5, "mid": 2.0, "premium": 1.8}

# Pico share: % dos que vieram num dia que estão simultaneamente no pico (18h-21h).
# Padrão ACAD: 25%.
PICO_SHARE = 0.25

# Taxas operacionais — calibradas por modelo (ACAD/Sebrae 2024).
# Low-cost tem maior inadimplência (cliente mais sensível a preço) e maior churn.
# Premium tem menor inadimplência (alunos mais comprometidos) e menor churn.
TAXA_INADIMPLENCIA_POR_MODELO = {
    "low":     0.06,   # 6% — Smart Fit reporta 5-7% em rounds investidor
    "mid":     0.04,   # 4% — Bodytech entry média setor
    "premium": 0.025,  # 2.5% — boutique/premium tem cliente mais fiel
}

# Backward-compat — código v1 que ainda lê o campo único
TAXA_INADIMPLENCIA = 0.04

TAXA_CANCELAMENTO_MENSAL_POR_MODELO = {
    "low":     0.10,   # 10% churn mensal (alto, mas reposição rápida)
    "mid":     0.07,
    "premium": 0.04,
}
TAXA_CANCELAMENTO_MENSAL = 0.08   # backward-compat

# Custos detalhados — 12 linhas. Valores são "base" e são modulados por:
# - aluguel: vem do Tier 1 Search Grounding (mediana) ou benchmark
# - área: muitos custos escalam com m²
# - modelo: premium tem folha maior, low-cost tem manutenção menor
CUSTOS_DETALHADOS_BASE = {
    "condominio_pct_aluguel": 0.15,     # 15% do aluguel
    "iptu_mensal_base": 2000.0,          # R$ 2k/mês (varia por município)
    "energia_por_m2": 12.0,              # R$/m² (low) — premium gasta mais com clima
    "agua_por_m2": 2.0,                  # R$/m²
    "internet_mensal": 800.0,            # R$ 800 fixo
    "folha_por_modelo": {                # folha mínima por modelo
        "low": 18000.0,                  # autoatendimento, ~6 funcionários
        "mid": 32000.0,                  # ~10 funcionários (incluí instrutores)
        "premium": 55000.0,              # ~16 funcionários (personal, nutri, recepção 24h)
    },
    "manutencao_pct_capex": 0.005,       # 0.5% do CAPEX por mês
    "contabilidade_mensal": 1300.0,
    "sistema_gestao_mensal": 800.0,
    "seguro_pct_capex": 0.002,           # 0.2% do CAPEX por mês
    "outros_pct_receita": 0.02,          # 2% da receita pra imprevistos
}

CUSTOS_MARKETING_PCT = {"low": 0.06, "mid": 0.08, "premium": 0.12}

# CAPEX detalhado
CAPEX_DETALHADO_BASE = {
    "equipamentos_por_m2": {"low": 350.0, "mid": 500.0, "premium": 850.0},
    "obra_adaptacao_por_m2": {"low": 200.0, "mid": 350.0, "premium": 600.0},
    "projeto_arquitetonico": 15000.0,
    "alvara_e_taxas": 8000.0,
    "contingencia_pct": 0.10,
    "capital_giro_meses": 3,
}

# Sensibilidade — 3 stress tests aplicados em cima do cenário "realista"
STRESS_TESTS = [
    {"id": "aluguel_mais_20pct",     "label": "Aluguel +20%",     "delta_aluguel": 0.20},
    {"id": "matriculas_menos_30pct", "label": "Matrículas -30%",  "delta_matriculas": -0.30},
    {"id": "ticket_menos_15pct",     "label": "Ticket -15%",      "delta_ticket": -0.15},
]

# Custo de capital pra cálculo de VPL/TIR (12% a.a. ≈ Selic + premium fitness)
CUSTO_CAPITAL_ANUAL = 0.12


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

    margem = ticket - ticket * 0.15
    break_even = int(custos_fixos / margem) + 1
    capacidade = int(area_m2 * ALUNOS_POR_M2)

    # Projeção 6 meses
    alunos_proj = int(break_even * 1.3)
    lucro_proj = (alunos_proj * margem) - custos_fixos
    payback = int(investimento_total / max(lucro_proj, 1)) if lucro_proj > 0 else 999

    # Score 0-10
    score = 0.0
    if payback <= 18: score += 4.0
    elif payback <= 30: score += 3.0
    elif payback <= 48: score += 2.0
    elif payback <= 60: score += 1.0

    ocupacao_break = break_even / capacidade if capacidade > 0 else 1
    if ocupacao_break < 0.30: score += 3.0
    elif ocupacao_break < 0.50: score += 2.0
    elif ocupacao_break < 0.70: score += 1.0

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
) -> dict:
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
        # Ticket: prefere valor atualizado do benchmark setorial, fallback no hardcode
        ticket = _ticket_dinamico.get(faixa_key) or faixa["ticket_medio"]

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

    melhor = max(cenarios.values(), key=lambda x: x["lucro_mensal_estimado"])

    return {
        "bairro": bairro,
        "cidade": cidade,
        "area_m2": area_m2,
        "aluguel_mensal": aluguel_mensal,
        "aviso": "Schema v2 — matrículas reais (não pico). Benchmarks: ACAD/Sebrae + Smart Fit/Bluefit/Bodytech.",
        "cenarios": cenarios,
        "recomendacao": melhor["modelo"],
        "melhor_lucro_mensal": melhor["lucro_mensal_estimado"],
        "melhor_payback_meses": melhor["payback_meses"],
        "schema_cenarios": "v2",
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers do schema v2
# ─────────────────────────────────────────────────────────────────────────

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


def _calcular_capex_detalhado(
    area_m2: float,
    modelo: str,
    equipamentos_override: float | None = None,
    uf_destino: str | None = None,
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
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
    obra = area_m2 * CAPEX_DETALHADO_BASE["obra_adaptacao_por_m2"][modelo]
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
    if payback <= 36 and margem >= 15:
        return {"status": "ALTO", "justificativa": f"Margem {margem:.1f}% + payback {payback}m"}
    if payback <= 60 and margem >= 10:
        return {"status": "MEDIO", "justificativa": f"Margem {margem:.1f}% + payback {payback}m (aceitável)"}
    if payback <= 84:
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
    from tools.gemini_search_grounding import pesquisar_aluguel_mediana

    # 1. Pesquisa aluguel via 3 queries paralelas
    aluguel = await pesquisar_aluguel_mediana(bairro, cidade, uf, area_m2_min, area_m2_max)
    mediana = aluguel.get("mediana_r_m2", 0.0)
    min_r = aluguel.get("min_r_m2", 0.0)
    max_r = aluguel.get("max_r_m2", 0.0)
    queries_ok = aluguel.get("queries_com_dados", 0)

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

    # Anexa transparência do tier 1 pra debug/auditoria
    fin["aluguel_pesquisa_detalhes"] = {
        "mediana_r_m2": mediana,
        "min_r_m2": min_r,
        "max_r_m2": max_r,
        "queries_com_dados": queries_ok,
        "valores_coletados": aluguel.get("valores_coletados", []),
        "fontes_resumo": [
            {"query": (f.get("query") or "")[:60], "n_valores": f.get("n_valores", 0)}
            for f in (aluguel.get("fontes") or [])
        ],
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
    )

    viabilidade["fonte_aluguel"] = fonte_aluguel
    viabilidade["aluguel_min_m2_observado"] = aluguel_min_m2
    viabilidade["aluguel_mediana_m2_observado"] = (
        float(aluguel_m2_mediana) if aluguel_m2_mediana else None
    )
    viabilidade["aluguel_max_m2_observado"] = aluguel_max_m2

    return viabilidade
