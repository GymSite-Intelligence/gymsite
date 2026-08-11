"""
Parâmetros de metodologia — REGRA DE OURO: zero hardcode.

Todo fator de cálculo do enriquecimento (ocupação, penetração, market share,
ticket, janelas) é um registro {valor, fonte, data_coleta, metodo, unidade},
recalibrável via tabela Supabase `parametros_metodologia` (override), com default
SÓ como fallback rotulado. Toda métrica carrega a fonte → exibida no relatório.

Ver feedback memory regra-ouro-zero-hardcode-metodologia + PLANO_ENRIQUECIMENTO §1.0.
"""
from __future__ import annotations

import os
from typing import Any

# Defaults documentados (fallback rotulado — NUNCA verdade silenciosa).
# Cada registro: valor, fonte, data_coleta, metodo, unidade, categoria.
#   categoria ∈ {benchmark, calibracao, aberto}
#     benchmark  = vem de fonte setorial externa (ACAD, Sebrae, Smart Fit/CVM)
#     calibracao = limiar/peso de metodologia GymSite (corte de score/veredito)
#     aberto     = derivável de dado aberto (IBGE/Censo/CKAN); default é fallback
# REGRA: estes valores são IDÊNTICOS ao código que substituíram (relocate, não
# recalibragem). Recalibrar = editar a tabela Supabase, sem deploy.
_HOJE = "2026-06-15"


def _p(valor, fonte, metodo, unidade, categoria="benchmark", data=_HOJE):
    return {"valor": valor, "fonte": fonte, "data_coleta": data,
            "metodo": metodo, "unidade": unidade, "categoria": categoria}


_DEFAULTS: dict[str, dict[str, Any]] = {
    # ── Ocupação por tipologia (moradores/unidade) — IBGE média domiciliar ───
    "ocupacao_studio":      _p(1.5, "IBGE PNAD + ajuste tipologia studio", "media_domiciliar_ajustada", "moradores/unidade", "aberto", "2026-06-14"),
    "ocupacao_1_2_dorm":    _p(2.2, "IBGE PNAD + ajuste 1-2 dorm", "media_domiciliar_ajustada", "moradores/unidade", "aberto", "2026-06-14"),
    "ocupacao_3_mais_dorm": _p(3.0, "IBGE PNAD + ajuste 3+ dorm", "media_domiciliar_ajustada", "moradores/unidade", "aberto", "2026-06-14"),
    "ocupacao_default":     _p(2.8, "fallback_IBGE_media_domiciliar_BR", "media_nacional", "moradores/unidade", "aberto", "2026-06-14"),
    "m2_por_unidade":       _p(75.0, "fallback_proxy_unidade_media+area_comum", "proxy_area_construida", "m2/unidade", "benchmark", "2026-06-14"),
    "m2_por_morador":       _p(25.0, "IBGE área privativa média por morador (2 dorm ~25 m²/pessoa)", "densidade_ocupacao", "m2/morador", "benchmark", "2026-06-18"),
    "max_moradores_por_unidade": _p(4.5, "teto IBGE moradores/domicílio urbano (apto grande não escala linear)", "limite_ocupacao", "moradores/unidade", "calibracao", "2026-06-18"),
    # Gatilho 'janela quente' (demanda futura): obra na reta final → entrega iminente →
    # avisar p/ ação de MKT com construtora/corretor antes da concorrência.
    "obra_acabamento_threshold_pct": _p(50, "obra em fase de acabamento ≥50% = entrega <12m (recalibrar c/ CNO)", "limiar_timing_obra", "%", "calibracao", "2026-06-18"),
    "obra_total_threshold_pct":      _p(85, "obra ≥85% concluída = reta final/entrega iminente", "limiar_timing_obra", "%", "calibracao", "2026-06-18"),
    "saturacao_bairro_medio_min":    _p(3, "≥3 academias no bairro = saturação MEDIO", "limiar_saturacao_bairro", "concorrentes", "calibracao", "2026-06-18"),
    "saturacao_bairro_alto_min":     _p(6, "≥6 academias no bairro = saturação ALTO", "limiar_saturacao_bairro", "concorrentes", "calibracao", "2026-06-18"),
    "saturacao_bairro_saturado_min": _p(10, "≥10 academias no bairro = SATURADO", "limiar_saturacao_bairro", "concorrentes", "calibracao", "2026-06-18"),
    # Matriz demografia × saturação → modelo (spec 2026-08-07)
    "matriz_n_per_10k_baixo":        _p(2.0, "N/10k < limiar = densidade competitiva baixa", "matriz_demo_saturacao", "acad/10k_hab", "calibracao", "2026-08-07"),
    "matriz_n_per_10k_alto":         _p(4.0, "N/10k ≥ limiar = saturação geral / guerra", "matriz_demo_saturacao", "acad/10k_hab", "calibracao", "2026-08-07"),
    "genero_diff_limiar_pp":         _p(8.0, "diff % mulheres−homens < limiar → misto; ≥ limiar → lado majoritário (faixa-alvo)", "genero_estrategia", "pp", "calibracao", "2026-08-10"),
    # B1+B2 — cobertura competitiva / gaps universais (A6→A9)
    "limiar_cobertura_gap": _p(
        0.60,
        "GymSite B2: n_com_oferta/gated_n < limiar → gap universal = artefato_cobertura (não ERRC)",
        "limiar_cobertura_oferta",
        "fração",
        "calibracao",
        "2026-08-11",
    ),
    "servicos_universais": _p(
        [
            "Musculação",
            "Spinning",
            "Treino funcional/HIIT",
            "Personal (PT)",
            "Yoga/Pilates",
        ],
        "GymSite B2: serviços quase-universais — gap só é real se amostra de oferta ≥ limiar",
        "catalogo_servicos_universais",
        "lista",
        "calibracao",
        "2026-08-11",
    ),
    "servicos_nicho_gap": _p(
        ["Natação/Hidro", "Crossfit", "Aulas/espaço kids"],
        "GymSite B2: nichos — gap sempre candidato a CRIAR (confiança média)",
        "catalogo_servicos_nicho",
        "lista",
        "calibracao",
        "2026-08-11",
    ),
    "matriz_premium_min_armadilha":  _p(2, "≥2 Premium no polígono + alta renda = Armadilha", "matriz_demo_saturacao", "concorrentes", "calibracao", "2026-08-07"),
    "matriz_rating_fraco_max":       _p(4.0, "rating médio < limiar = oferta fraca (Oceano com N>0)", "matriz_demo_saturacao", "estrelas", "calibracao", "2026-08-07"),
    "matriz_ticket_low_max":         _p(150.0, "ticket ≤ limiar → tier low", "matriz_demo_saturacao", "BRL/mês", "calibracao", "2026-08-07"),
    "matriz_ticket_premium_min":     _p(250.0, "ticket ≥ limiar → tier premium (se não rede known)", "matriz_demo_saturacao", "BRL/mês", "calibracao", "2026-08-07"),
    "matriz_renda_alta_percentil":   _p(0.75, "percentil renda ≥ limiar = alta renda (matriz)", "matriz_demo_saturacao", "fração", "calibracao", "2026-08-07"),
    "matriz_renda_pc_alta_min":      _p(3500.0, "renda_pc ≥ limiar = alta renda (fallback sem percentil)", "matriz_demo_saturacao", "BRL/pessoa", "calibracao", "2026-08-07"),
    "nominatim_intervalo_seg":       _p(1.1, "intervalo mínimo entre chamadas Nominatim (ToS 1 req/s)", "rate_limit", "segundos", "calibracao", "2026-06-18"),
    "cascata_raio_bairro_km":        _p(2.0, "raio máx (km) do centroide do bairro p/ aceitar listing da cascata — fora disso = vazamento de bairro vizinho", "filtro_bairro_listing", "km", "calibracao", "2026-06-18"),
    "janela_demanda_min_concorrentes": _p(2, "mín de concorrentes COM popular_times p/ a janela de demanda agregada ser confiável — abaixo disso, amostra insuficiente (não inventa pico)", "janela_demanda", "concorrentes", "calibracao", "2026-06-18"),
    "zoneamento_penal_restrito":     _p(2.0, "penalidade no score do top candidato em zona RESTRITO (LUOS)", "penalidade_zoneamento", "pontos", "calibracao", "2026-06-18"),
    "zoneamento_penal_condicionado": _p(1.0, "penalidade no score em zona CONDICIONADO (LUOS)", "penalidade_zoneamento", "pontos", "calibracao", "2026-06-18"),
    "zeus_osm_raio_m":               _p(150, "raio Overpass landuse/zoning (ZEUS Fase 1)", "zeus_osm", "metros", "calibracao", "2026-08-11"),
    "zeus_osm_completude_min_features": _p(3, "mín. features OSM no raio p/ completude alta", "zeus_osm", "features", "calibracao", "2026-08-11"),
    "zeus_osm_confianca_alta":       _p(85, "score confiança proxy OSM com amostra suficiente (nunca = legal)", "zeus_osm", "pontos", "calibracao", "2026-08-11"),
    "zeus_osm_confianca_baixa":      _p(40, "score confiança proxy OSM com amostra esparsa", "zeus_osm", "pontos", "calibracao", "2026-08-11"),
    # ── Penetração fitness (% da pop. que É MEMBRO de academia) — ACAD ───────
    "penetracao_geral":     _p(0.045, "ACAD/Panorama Fitness Brasil", "penetracao_mercado", "fração", "benchmark", "2026-06-14"),
    "penetracao_bairro_ab": _p(0.10, "ACAD (bairro alta renda A/B)", "penetracao_mercado_segmentada", "fração", "benchmark", "2026-06-14"),
    # Corte de perfil A/B (define se o bairro usa penetração segmentada). Derivado da
    # renda REAL do bairro (CKAN IDH-Renda Atlas + renda per capita), não default.
    "perfil_ab_idh_renda_min": _p(0.800, "Atlas Brasil/PNUD (IDH-Renda 'muito alto' ≥ 0,800)", "corte_perfil_renda", "índice", "calibracao"),
    "perfil_ab_renda_pc_min":  _p(2000.0, "IBGE classes A/B (corte renda per capita, ~2× mediana nacional)", "corte_perfil_renda", "BRL/pessoa", "calibracao"),
    # Posicionamento por headroom de renda (spec docs/metodologia/posicionamento_headroom_premium.md)
    "renda_percentil_premium":      _p(0.75, "calibração GymSite v2 (quartil superior da cidade → Premium)", "corte_posicionamento", "fração", "calibracao"),
    "renda_percentil_mid":          _p(0.40, "calibração GymSite v2 (acima da mediana → Mid)", "corte_posicionamento", "fração", "calibracao"),
    "headroom_ratio_oceano_azul":   _p(2.0, "calibração GymSite v2 (ticket sustentável ≥ 2× ticket de mercado)", "corte_posicionamento", "fator", "calibracao"),
    "headroom_ratio_transicao":     _p(1.2, "calibração GymSite v2 (folga moderada de ticket)", "corte_posicionamento", "fator", "calibracao"),
    # ── A9 KPI / Valuation readiness (PLANO_MOTOR_FINANCEIRO_V3 §2.5, adendo M&A) ──
    # LTV por aluno mínimo por tier (Boutique/Premium exige histórico longo de retenção).
    "ltv_aluno_min_mid":     _p(1500.0, "Benchmark Financeiro Academias 2024 (LTV/aluno Mid mínimo p/ Valuation)", "kpi_valuation", "BRL/aluno", "benchmark"),
    "ltv_aluno_min_premium": _p(2800.0, "Benchmark Financeiro Academias 2024 (LTV/aluno Boutique/Premium mínimo)", "kpi_valuation", "BRL/aluno", "benchmark"),
    # Faixa de múltiplo EBITDA por tier (M&A) — param() só aceita escalar → _min/_max.
    "multiplo_ebitda_low_min":     _p(4.0, "Benchmark M&A Academias 2024 (Low 4,0-6,0× EBITDA)", "multiplo_ebitda", "x_ebitda", "benchmark"),
    "multiplo_ebitda_low_max":     _p(6.0, "Benchmark M&A Academias 2024 (Low 4,0-6,0× EBITDA)", "multiplo_ebitda", "x_ebitda", "benchmark"),
    "multiplo_ebitda_mid_min":     _p(2.4, "Benchmark M&A Academias 2024 (Mid 2,4-3,6× EBITDA)", "multiplo_ebitda", "x_ebitda", "benchmark"),
    "multiplo_ebitda_mid_max":     _p(3.6, "Benchmark M&A Academias 2024 (Mid 2,4-3,6× EBITDA)", "multiplo_ebitda", "x_ebitda", "benchmark"),
    "multiplo_ebitda_premium_min": _p(3.8, "Benchmark M&A Academias 2024 (Premium/Boutique 3,8-6,5× EBITDA)", "multiplo_ebitda", "x_ebitda", "benchmark"),
    "multiplo_ebitda_premium_max": _p(6.5, "Benchmark M&A Academias 2024 (Premium/Boutique 3,8-6,5× EBITDA)", "multiplo_ebitda", "x_ebitda", "benchmark"),
    # Retenção anual / churn (premium retém >85%/ano = churn <~5%/mês).
    "retencao_ano_min_premium": _p(0.85, "Benchmark Financeiro Academias 2024 (retenção anual Premium >85%)", "kpi_valuation", "fração", "benchmark"),
    # Metas de Valuation readiness (genéricas — atreladas a due-diligence M&A).
    "cac_max_valuation":         _p(180.0, "Benchmark M&A Academias 2024 (CAC máx por aluno p/ múltiplo-alvo)", "kpi_valuation", "BRL/aluno", "benchmark"),
    "retencao_ano_min_valuation": _p(0.85, "Benchmark M&A Academias 2024 (retenção anual mínima p/ Valuation)", "kpi_valuation", "fração", "benchmark"),
    "market_share_default": _p(0.15, "fallback_conservador (A4/anéis recalibra)", "quota_raio_estimada", "fração", "calibracao", "2026-06-14"),
    "inadimplencia_default": _p(0.06, "fallback_ACAD_com_recorrencia", "benchmark_setorial", "fração", "benchmark", "2026-06-14"),
    "meses_entrega":        _p(30, "fallback_mediana_obra_24_36m (recalibrar CNO encerradas)", "mediana_tempo_obra", "meses", "benchmark", "2026-06-14"),
    "janela_compra_equipamento_meses": _p(4, "fallback_3_6m_antes_entrega", "lead_time_compra", "meses", "benchmark", "2026-06-14"),
    # ── Anéis competitivos (Apêndice D) ─────────────────────────────────────
    "anel_peso_no_bairro":  _p(1.0, "Motor v2 Apêndice D", "peso_anel", "fator", "calibracao", "2026-06-14"),
    "anel_peso_fronteira":  _p(0.5, "Motor v2 Apêndice D", "peso_anel", "fator", "calibracao", "2026-06-14"),
    "anel_peso_regional":   _p(0.2, "Motor v2 Apêndice D", "peso_anel", "fator", "calibracao", "2026-06-14"),
    "raio_fronteira_km":    _p(2.0, "Motor v2 Apêndice D (≤2km da borda)", "raio_anel", "km", "calibracao", "2026-06-14"),
    "porte_pequena_max_avaliacoes": _p(150, "fallback_heuristica_places", "limiar_porte", "avaliacoes", "calibracao", "2026-06-14"),
    "porte_media_max_avaliacoes":   _p(600, "fallback_heuristica_places", "limiar_porte", "avaliacoes", "calibracao", "2026-06-14"),

    # ══ DEMOGRÁFICO (A2 / ibge_tools) ════════════════════════════════════════
    # Faixa etária — % da população na faixa (pirâmide etária). DADO ABERTO:
    # default é fallback nacional; recalibrar com Censo 2022 por município/setor.
    "faixa_pct_15_29":      _p(0.23, "IBGE Censo 2022 pirâmide etária BR (fallback nacional)", "piramide_etaria", "fração", "aberto"),
    "faixa_pct_18_35":      _p(0.26, "IBGE Censo 2022 pirâmide etária BR (fallback nacional)", "piramide_etaria", "fração", "aberto"),
    "faixa_pct_18_45":      _p(0.36, "IBGE Censo 2022 pirâmide etária BR (fallback nacional)", "piramide_etaria", "fração", "aberto"),
    "faixa_pct_20_40":      _p(0.30, "IBGE Censo 2022 pirâmide etária BR (fallback nacional)", "piramide_etaria", "fração", "aberto"),
    "faixa_pct_25_50":      _p(0.35, "IBGE Censo 2022 pirâmide etária BR (fallback nacional)", "piramide_etaria", "fração", "aberto"),
    "faixa_pct_default":    _p(0.30, "IBGE Censo 2022 pirâmide etária BR (fallback nacional)", "piramide_etaria", "fração", "aberto"),
    # Público POTENCIAL fitness (% da faixa etária com interesse/aptidão — NÃO membro)
    "penetracao_potencial_fitness": _p(0.40, "ACAD/Panorama Fitness Brasil (interesse fitness na faixa)", "publico_potencial", "fração", "benchmark"),
    # Score demográfico — cortes de população na faixa
    "score_demo_pop_alta":   _p(50000, "calibração metodológica GymSite v2", "limiar_score", "pessoas", "calibracao"),
    "score_demo_pop_media":  _p(30000, "calibração metodológica GymSite v2", "limiar_score", "pessoas", "calibracao"),
    "score_demo_pop_baixa":  _p(15000, "calibração metodológica GymSite v2", "limiar_score", "pessoas", "calibracao"),
    "score_demo_pop_minima": _p(5000,  "calibração metodológica GymSite v2", "limiar_score", "pessoas", "calibracao"),
    # Score demográfico — cortes de renda média (R$)
    "score_demo_renda_alta":   _p(2500, "calibração metodológica GymSite v2", "limiar_score", "BRL", "calibracao"),
    "score_demo_renda_media":  _p(1800, "calibração metodológica GymSite v2", "limiar_score", "BRL", "calibracao"),
    "score_demo_renda_baixa":  _p(1200, "calibração metodológica GymSite v2", "limiar_score", "BRL", "calibracao"),
    "publico_fitness_idade_min": _p(25, "Definição de produto GymSite (público-alvo fitness)", "faixa_gancho_sexo_idade", "anos", "calibracao"),
    "publico_fitness_idade_max": _p(40, "Definição de produto GymSite (público-alvo fitness)", "faixa_gancho_sexo_idade", "anos", "calibracao"),
    "score_demo_renda_minima": _p(800,  "calibração metodológica GymSite v2", "limiar_score", "BRL", "calibracao"),
    "score_demo_base":         _p(2.0,  "calibração metodológica GymSite v2 (base aditiva)", "score_base", "pontos", "calibracao"),
    # Limiares de classificação demográfica (EXCELENTE/BOM/REGULAR)
    "demo_limiar_excelente": _p(8.0, "calibração metodológica GymSite v2", "limiar_classificacao", "pontos", "calibracao"),
    "demo_limiar_bom":       _p(6.0, "calibração metodológica GymSite v2", "limiar_classificacao", "pontos", "calibracao"),
    "demo_limiar_regular":   _p(4.0, "calibração metodológica GymSite v2", "limiar_classificacao", "pontos", "calibracao"),

    # ══ VEREDITO FINAL (A6) ══════════════════════════════════════════════════
    "veredito_limiar_aprovado":   _p(8.0, "calibração metodológica GymSite v2", "limiar_veredito", "pontos", "calibracao"),
    "veredito_limiar_ressalvas":  _p(6.0, "calibração metodológica GymSite v2", "limiar_veredito", "pontos", "calibracao"),
    "veredito_limiar_investigar": _p(4.0, "calibração metodológica GymSite v2", "limiar_veredito", "pontos", "calibracao"),
    # Teto de payback pra RECOMENDAR modelo (A4 gate) — alerta produto ≈48m; recálculo sem KeyError.
    "payback_limiar_recomendavel": _p(48, "calibração GymSite v2 (acima = risco elevado; não recomendar tier)", "limiar_recomendacao", "meses", "calibracao"),

    # ══ VIABILIDADE FINANCEIRA (financial_tools) ═════════════════════════════
    # Score de viabilidade — cortes de payback (meses)
    "payback_limiar_excelente": _p(18, "calibração metodológica GymSite v2", "limiar_score", "meses", "calibracao"),
    "payback_limiar_bom":       _p(30, "calibração metodológica GymSite v2", "limiar_score", "meses", "calibracao"),
    "payback_limiar_regular":   _p(48, "calibração metodológica GymSite v2", "limiar_score", "meses", "calibracao"),
    "payback_limiar_fraco":     _p(60, "calibração metodológica GymSite v2", "limiar_score", "meses", "calibracao"),
    # Score de viabilidade — cortes de ocupação no break-even
    "ocupacao_break_otima":  _p(0.30, "calibração metodológica GymSite v2", "limiar_score", "fração", "calibracao"),
    "ocupacao_break_boa":    _p(0.50, "calibração metodológica GymSite v2", "limiar_score", "fração", "calibracao"),
    "ocupacao_break_limite": _p(0.70, "calibração metodológica GymSite v2", "limiar_score", "fração", "calibracao"),
    "score_viab_base": _p(3.0, "calibração metodológica GymSite v2 (base aditiva viabilidade)", "score_base", "pontos", "calibracao"),
    "aluguel_sustentavel_pct_faturamento": _p(0.15, "ACAD/Sebrae (aluguel sustentável < 15% do faturamento)", "limiar_risco", "fração", "benchmark"),
    "margem_operacional_ticket_pct": _p(0.15, "benchmark setorial (margem sobre ticket bruto)", "margem_operacional", "fração", "benchmark"),
    "fator_projecao_6m": _p(1.3, "benchmark setorial (rampa 6m sobre break-even)", "fator_rampa", "fator", "benchmark"),
    # Classificação de viabilidade (status ALTO/MEDIO/BAIXO) — payback (meses) + margem (%)
    "viab_payback_alto":  _p(36, "calibração metodológica GymSite v2", "limiar_classificacao", "meses", "calibracao"),
    "viab_payback_medio": _p(60, "calibração metodológica GymSite v2", "limiar_classificacao", "meses", "calibracao"),
    "viab_payback_baixo": _p(84, "calibração metodológica GymSite v2", "limiar_classificacao", "meses", "calibracao"),
    "viab_margem_alto":   _p(15, "calibração metodológica GymSite v2", "limiar_classificacao", "%", "calibracao"),
    "viab_margem_medio":  _p(10, "calibração metodológica GymSite v2", "limiar_classificacao", "%", "calibracao"),
    "custo_capital_anual": _p(0.12, "BCB Selic + prêmio risco fitness", "custo_capital", "fração_a.a.", "benchmark"),
    # Ticket médio por modelo (R$)
    "ticket_low":     _p(89.90,  "ACAD/Sebrae 2024 (Smart Fit/Bluefit/Selfit)", "ticket_benchmark", "BRL/mês", "benchmark"),
    "ticket_mid":     _p(149.90, "ACAD/Sebrae 2024 (Bodytech entry/regional)", "ticket_benchmark", "BRL/mês", "benchmark"),
    "ticket_premium": _p(299.90, "ACAD/Sebrae 2024 (Bio Ritmo/boutique)", "ticket_benchmark", "BRL/mês", "benchmark"),
    "ticket_medio_nacional": _p(149.90, "ACAD/Panorama Fitness 2024", "ticket_benchmark", "BRL/mês", "benchmark"),
    "alunos_por_m2_legado":  _p(3.5, "benchmark setorial (compat v1)", "densidade_alunos", "alunos/m2", "benchmark"),
    # Matrículas pagantes por m² — 3 calibrações × 3 modelos
    "matr_m2_low_conservador":     _p(1.5, "ACAD 2024 + Smart Fit/Bluefit amostras", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_low_realista":        _p(2.2, "ACAD 2024 + Smart Fit/Bluefit amostras", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_low_agressivo":       _p(3.0, "ACAD 2024 + Smart Fit top performers", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_mid_conservador":     _p(1.0, "ACAD 2024 + Bodytech entry amostras", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_mid_realista":        _p(1.4, "ACAD 2024 + Bodytech entry amostras", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_mid_agressivo":       _p(1.8, "ACAD 2024 + Bodytech entry amostras", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_premium_conservador": _p(0.4, "ACAD 2024 + Bio Ritmo amostras", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_premium_realista":    _p(0.6, "ACAD 2024 + Bio Ritmo amostras", "matriculas_m2", "matr/m2", "benchmark"),
    "matr_m2_premium_agressivo":   _p(0.9, "ACAD 2024 + Bio Ritmo amostras", "matriculas_m2", "matr/m2", "benchmark"),
    # Absorção / margem fresca — área proxy por tier (franquia; não m² Maps)
    "area_proxy_low_m2": _p(1000.0, "Smart Fit mín franquia ≥950 + Panobianco Padrão 900-1000", "absorcao_area_proxy", "m2", "benchmark", "2026-08-07"),
    "area_proxy_mid_m2": _p(1500.0, "Ultra média ~1500 + Bluefit tip.", "absorcao_area_proxy", "m2", "benchmark", "2026-08-07"),
    "area_proxy_premium_m2": _p(2000.0, "placeholder Bodytech/Cia — calibrável W2c", "absorcao_area_proxy", "m2", "calibracao", "2026-08-07"),
    "area_proxy_nicho_desconhecido_m2": _p(1250.0, "meio-termo low↔mid", "absorcao_area_proxy", "m2", "calibracao", "2026-08-07"),
    # Capacidade física simultânea no pico (pessoas/m²)
    "capacidade_simultanea_low":     _p(0.55, "ACAD/Sebrae 2024", "capacidade_pico", "pessoas/m2", "benchmark"),
    "capacidade_simultanea_mid":     _p(0.40, "ACAD/Sebrae 2024", "capacidade_pico", "pessoas/m2", "benchmark"),
    "capacidade_simultanea_premium": _p(0.25, "ACAD/Sebrae 2024", "capacidade_pico", "pessoas/m2", "benchmark"),
    # Frequência semanal média do aluno
    "frequencia_semanal_low":     _p(2.5, "ACAD/Panorama 2024", "frequencia_semanal", "visitas/sem", "benchmark"),
    "frequencia_semanal_mid":     _p(2.0, "ACAD/Panorama 2024", "frequencia_semanal", "visitas/sem", "benchmark"),
    "frequencia_semanal_premium": _p(1.8, "ACAD/Panorama 2024", "frequencia_semanal", "visitas/sem", "benchmark"),
    # pico_share POR MODELO — A4 independente por tipologia; nunca um acumulado global.
    # Low: dormência varejo escala → ~0,25. Boutique/CF (quando entrarem): 0,35–0,50 + freq≥3,5.
    "pico_share_low":     _p(0.25, "ACAD 2024 (% no pico 18h-21h) low-cost", "pico_share", "fração", "benchmark"),
    "pico_share_mid":     _p(0.25, "ACAD 2024 (% no pico 18h-21h) mid", "pico_share", "fração", "benchmark"),
    "pico_share_premium": _p(0.25, "ACAD 2024 (% no pico 18h-21h) premium/bairro", "pico_share", "fração", "benchmark"),
    "pico_share": _p(0.25, "DEPRECATED alias→mid; usar pico_share_{modelo}", "pico_share", "fração", "benchmark"),
    # Inadimplência mensal por modelo
    "inadimplencia_low":     _p(0.06,  "Smart Fit Holdings 2023-2024 (releases investidor)", "inadimplencia", "fração", "benchmark"),
    "inadimplencia_mid":     _p(0.04,  "Bodytech entry / média setor 2024", "inadimplencia", "fração", "benchmark"),
    "inadimplencia_premium": _p(0.025, "boutique/premium 2024 (cliente fiel)", "inadimplencia", "fração", "benchmark"),
    # Churn mensal por modelo
    "churn_mensal_low":     _p(0.10, "ACAD/Smart Fit 2024", "churn_mensal", "fração", "benchmark"),
    "churn_mensal_mid":     _p(0.07, "ACAD 2024", "churn_mensal", "fração", "benchmark"),
    "churn_mensal_premium": _p(0.04, "ACAD 2024 (premium retém mais)", "churn_mensal", "fração", "benchmark"),
    # Marketing % do faturamento
    "marketing_pct_low":     _p(0.06, "ACAD/Sebrae 2024", "marketing_pct", "fração", "benchmark"),
    "marketing_pct_mid":     _p(0.08, "ACAD/Sebrae 2024", "marketing_pct", "fração", "benchmark"),
    "marketing_pct_premium": _p(0.12, "ACAD/Sebrae 2024", "marketing_pct", "fração", "benchmark"),
    # Ticket sustentável como % da renda domiciliar
    "ticket_renda_pct_low":     _p(0.08, "ACAD comportamento consumidor 2024", "ticket_renda", "fração", "benchmark"),
    "ticket_renda_pct_mid":     _p(0.12, "ACAD comportamento consumidor 2024", "ticket_renda", "fração", "benchmark"),
    "ticket_renda_pct_premium": _p(0.15, "ACAD comportamento consumidor 2024", "ticket_renda", "fração", "benchmark"),
    # CAPEX por m² e fixos
    "capex_equip_m2_low":     _p(350.0, "Sebrae/fornecedores 2024", "capex_m2", "BRL/m2", "benchmark"),
    "capex_equip_m2_mid":     _p(500.0, "Sebrae/fornecedores 2024", "capex_m2", "BRL/m2", "benchmark"),
    "capex_equip_m2_premium": _p(850.0, "Sebrae/fornecedores 2024", "capex_m2", "BRL/m2", "benchmark"),
    "capex_obra_m2_low":      _p(200.0, "SINAPI/Sebrae 2024", "capex_m2", "BRL/m2", "benchmark"),
    "capex_obra_m2_mid":      _p(350.0, "SINAPI/Sebrae 2024", "capex_m2", "BRL/m2", "benchmark"),
    "capex_obra_m2_premium":  _p(600.0, "SINAPI/Sebrae 2024", "capex_m2", "BRL/m2", "benchmark"),
    "capex_projeto_arquitetonico": _p(15000.0, "Sebrae 2024", "capex_fixo", "BRL", "benchmark"),
    "capex_alvara_taxas":          _p(8000.0,  "Sebrae 2024", "capex_fixo", "BRL", "benchmark"),
    "capex_contingencia_pct":      _p(0.10, "calibração metodológica GymSite v2", "contingencia", "fração", "calibracao"),
    "capex_capital_giro_meses":    _p(3, "Sebrae 2024 (meses de custo fixo)", "capital_giro", "meses", "benchmark"),
    # Custos fixos detalhados
    "custo_condominio_pct_aluguel": _p(0.15, "benchmark setorial 2024", "custo_fixo", "fração", "benchmark"),
    "custo_iptu_mensal_base":       _p(2000.0, "benchmark setorial (varia por município)", "custo_fixo", "BRL/mês", "benchmark"),
    "custo_energia_por_m2":         _p(12.0, "benchmark setorial 2024", "custo_fixo", "BRL/m2", "benchmark"),
    "custo_agua_por_m2":            _p(2.0,  "benchmark setorial 2024", "custo_fixo", "BRL/m2", "benchmark"),
    "custo_internet_mensal":        _p(800.0, "benchmark setorial 2024", "custo_fixo", "BRL/mês", "benchmark"),
    "folha_min_low":     _p(18000.0, "Sebrae 2024 (~6 func, autoatendimento)", "folha", "BRL/mês", "benchmark"),
    "folha_min_mid":     _p(32000.0, "Sebrae 2024 (~10 func)", "folha", "BRL/mês", "benchmark"),
    "folha_min_premium": _p(55000.0, "Sebrae 2024 (~16 func)", "folha", "BRL/mês", "benchmark"),
    "custo_manutencao_pct_capex":  _p(0.005, "benchmark setorial (mensal sobre CAPEX)", "custo_fixo", "fração", "benchmark"),
    "custo_contabilidade_mensal":  _p(1300.0, "benchmark setorial 2024", "custo_fixo", "BRL/mês", "benchmark"),
    "custo_sistema_gestao_mensal": _p(800.0, "benchmark setorial 2024", "custo_fixo", "BRL/mês", "benchmark"),
    "custo_seguro_pct_capex":      _p(0.002, "benchmark setorial (mensal sobre CAPEX)", "custo_fixo", "fração", "benchmark"),
    "custo_outros_pct_receita":    _p(0.02, "calibração metodológica GymSite v2 (imprevistos)", "custo_fixo", "fração", "calibracao"),
    # ── Folha como % do faturamento (benchmark maduro). Aplicado como max(piso R$, % da receita). ──
    "folha_pct_fat_low":     _p(0.18, "Benchmark Financeiro Academias 2024 (Low-Cost 18%)", "folha_pct", "fração", "benchmark"),
    "folha_pct_fat_mid":     _p(0.35, "Benchmark Financeiro Academias 2024 (Mid-Market 35%)", "folha_pct", "fração", "benchmark"),
    "folha_pct_fat_premium": _p(0.33, "Benchmark Financeiro Academias 2024 (Premium 28-38%, alvo Fator R)", "folha_pct", "fração", "benchmark"),
    # ── Fator R / Simples Nacional CNAE 9313-1/00 ──
    "fator_r_corte_folha":        _p(0.28,  "LC 123/2006 — corte Fator R folha/faturamento", "fator_r", "fração", "regulatorio"),
    "aliquota_simples_anexo_iii": _p(0.06,  "LC 123/2006 Anexo III faixa inicial", "tributo", "fração", "regulatorio"),
    "aliquota_simples_anexo_v":   _p(0.155, "LC 123/2006 Anexo V faixa inicial", "tributo", "fração", "regulatorio"),
    # ── Teto de ocupação imobiliária (aluguel+condomínio+IPTU / faturamento) por modelo ──
    "ocupacao_teto_low":     _p(0.125, "Benchmark Financeiro Academias 2024 (Low-Cost 12,5%)", "ocupacao_teto", "fração", "benchmark"),
    "ocupacao_teto_mid":     _p(0.15,  "Benchmark Financeiro Academias 2024 (Mid-Market 15%)", "ocupacao_teto", "fração", "benchmark"),
    "ocupacao_teto_premium": _p(0.15,  "Benchmark Financeiro Academias 2024 (Premium 15-16%)", "ocupacao_teto", "fração", "benchmark"),

    # ══ SATURAÇÃO / CONCORRÊNCIA (competitor_tools) ══════════════════════════
    "saturacao_densidade_baixo": _p(0.3, "benchmark densidade acad/km² (mercado)", "limiar_saturacao", "acad/km2", "benchmark"),
    "saturacao_densidade_medio": _p(0.8, "benchmark densidade acad/km² (mercado)", "limiar_saturacao", "acad/km2", "benchmark"),
    "saturacao_densidade_alto":  _p(1.5, "benchmark densidade acad/km² (mercado)", "limiar_saturacao", "acad/km2", "benchmark"),
    "score_conc_bonus_baixo":    _p(5.0, "calibração metodológica GymSite v2", "peso_score", "pontos", "calibracao"),
    "score_conc_bonus_medio":    _p(3.5, "calibração metodológica GymSite v2", "peso_score", "pontos", "calibracao"),
    "score_conc_bonus_alto":     _p(1.5, "calibração metodológica GymSite v2", "peso_score", "pontos", "calibracao"),
    "score_conc_bonus_saturado": _p(0.0, "calibração metodológica GymSite v2", "peso_score", "pontos", "calibracao"),
    "score_conc_penalidade_por_conc": _p(0.4, "calibração metodológica GymSite v2", "peso_score", "pontos/conc", "calibracao"),
    "score_conc_penalidade_teto":     _p(4.0, "calibração metodológica GymSite v2", "teto_score", "pontos", "calibracao"),
    "score_conc_rating_mult":    _p(2.0, "calibração metodológica GymSite v2", "peso_score", "fator", "calibracao"),
    "score_conc_rating_default": _p(1.0, "calibração metodológica GymSite v2 (sem rating)", "peso_score", "fator", "calibracao"),
    "score_oport_peso_dores": _p(0.8, "calibração metodológica GymSite v2", "peso_score", "pontos/dor", "calibracao"),
    "score_oport_peso_gaps":  _p(0.3, "calibração metodológica GymSite v2", "peso_score", "pontos/gap", "calibracao"),
    "benchmark_rating_bem_avaliada": _p(4.2, "Google Places (corte rede premium)", "limiar_rating", "estrelas", "benchmark"),

    # ══ ANCORAGEM (anchoring_tools) ══════════════════════════════════════════
    "ancoragem_dist_forte_m":  _p(500,  "calibração metodológica GeoScout v2", "limiar_distancia", "metros", "calibracao"),
    "ancoragem_dist_media_m":  _p(1000, "calibração metodológica GeoScout v2", "limiar_distancia", "metros", "calibracao"),
    "ancoragem_dist_fraca_m":  _p(2000, "calibração metodológica GeoScout v2", "limiar_distancia", "metros", "calibracao"),
    "ancoragem_pts_forte":     _p(3, "calibração metodológica GeoScout v2", "peso_score", "pontos", "calibracao"),
    "ancoragem_pts_media":     _p(2, "calibração metodológica GeoScout v2", "peso_score", "pontos", "calibracao"),
    "ancoragem_pts_fraca":     _p(1, "calibração metodológica GeoScout v2", "peso_score", "pontos", "calibracao"),
    "geoscout_rating_baixo":   _p(3.5, "Google Places (corte rating baixo)", "limiar_rating", "estrelas", "benchmark"),
    "geoscout_min_avaliacoes": _p(30, "calibração metodológica GeoScout v2 (amostra mínima)", "limiar_amostra", "avaliacoes", "calibracao"),

    # ══ VALIDAÇÃO (a8_validator) ═════════════════════════════════════════════
    "validacao_score_minimo_aprovado":     _p(6.0, "calibração metodológica GymSite v2", "limiar_validacao", "pontos", "calibracao"),
    "validacao_score_concorrencia_minimo": _p(4.0, "calibração metodológica GymSite v2", "limiar_validacao", "pontos", "calibracao"),
    "validacao_peso_critico": _p(0.40, "calibração metodológica GymSite v2", "peso_penalidade", "fração", "calibracao"),
    "validacao_peso_alta":    _p(0.25, "calibração metodológica GymSite v2", "peso_penalidade", "fração", "calibracao"),
    "validacao_peso_media":   _p(0.15, "calibração metodológica GymSite v2", "peso_penalidade", "fração", "calibracao"),
    "validacao_peso_baixa":   _p(0.05, "calibração metodológica GymSite v2", "peso_penalidade", "fração", "calibracao"),

    # ══ POPULAR TIMES (popular_times_tool) — perfil horário + oportunidade ════
    "pop_spread_24h_equilibrado": _p(25, "calibração metodológica GymSite v2 (variabilidade)", "limiar_perfil", "pontos_pct", "calibracao"),
    "pop_picos_min_multi":        _p(5, "calibração metodológica GymSite v2", "limiar_perfil", "horas", "calibracao"),
    "pop_pct_pico_alto":          _p(70, "calibração metodológica GymSite v2 (hora cheia)", "limiar_ocupacao", "pct", "calibracao"),
    "pop_pct_superlotado":        _p(80, "calibração metodológica GymSite v2 (hora crítica)", "limiar_ocupacao", "pct", "calibracao"),
    "pop_pct_livre":              _p(20, "calibração metodológica GymSite v2 (hora vazia)", "limiar_ocupacao", "pct", "calibracao"),
    "pop_pct_muito_livre":        _p(15, "calibração metodológica GymSite v2 (hora muito vazia)", "limiar_ocupacao", "pct", "calibracao"),
    "pop_vale_midweek_max":       _p(20, "calibração metodológica GymSite v2", "limiar_ocupacao", "pct", "calibracao"),
    "pop_dias_min_perfil":        _p(4, "calibração metodológica GymSite v2 (consenso semana)", "limiar_recomendacao", "dias", "calibracao"),
    "pop_dias_min_vale_midweek":  _p(2, "calibração metodológica GymSite v2", "limiar_recomendacao", "dias", "calibracao"),
    "pop_hora_manha_ini":   _p(6,  "padrão fitness Brasil (café 6-10h)", "faixa_horaria", "hora", "calibracao"),
    "pop_hora_manha_fim":   _p(10, "padrão fitness Brasil (café 6-10h)", "faixa_horaria", "hora", "calibracao"),
    "pop_hora_almoco_ini":  _p(11, "padrão fitness Brasil (almoço 11-15h)", "faixa_horaria", "hora", "calibracao"),
    "pop_hora_almoco_fim":  _p(15, "padrão fitness Brasil (almoço 11-15h)", "faixa_horaria", "hora", "calibracao"),
    "pop_hora_tarde_ini":   _p(16, "padrão fitness Brasil (saída trabalho 16-20h)", "faixa_horaria", "hora", "calibracao"),
    "pop_hora_tarde_fim":   _p(20, "padrão fitness Brasil (saída trabalho 16-20h)", "faixa_horaria", "hora", "calibracao"),

    # ══ CNO obra (cno_fitness_tools) — filtros de plausibilidade ══════════════
    "cno_area_min_m2":         _p(80.0,    "benchmark mercado (estúdio mínimo)", "filtro_plausibilidade", "m2", "benchmark"),
    "cno_area_max_m2":         _p(8000.0,  "benchmark mercado (academia grande)", "filtro_plausibilidade", "m2", "benchmark"),
    "cno_area_gp_min_m2":      _p(2000,    "gate grande porte (cno_bigquery_loader)", "filtro_plausibilidade", "m2", "benchmark", "2026-06-16"),
    "cno_area_gp_max_m2":      _p(100000,  "gate grande porte (corta mega-infra)", "filtro_plausibilidade", "m2", "benchmark", "2026-06-16"),
    "cutoff_obras_meses":      _p(36,      "janela retroativa busca CNO (demanda_futura)", "janela_busca", "meses", "calibracao", "2026-06-16"),
    "ig_cache_ttl_dias":       _p(14,      "frescor do cache de IG do concorrente (marketing muda devagar)", "freshness_cache", "dias", "calibracao", "2026-06-16"),
    "cno_duracao_min_dias":    _p(60,      "análise CNO encerradas (obra mínima)", "filtro_plausibilidade", "dias", "benchmark"),
    "cno_duracao_max_dias":    _p(1200,    "análise CNO encerradas (obra máxima)", "filtro_plausibilidade", "dias", "benchmark"),
    "cno_dias_por_m2_min":     _p(0.04,    "análise CNO encerradas (ritmo obra)", "filtro_plausibilidade", "dias/m2", "benchmark"),
    "cno_dias_por_m2_max":     _p(4.0,     "análise CNO encerradas (ritmo obra)", "filtro_plausibilidade", "dias/m2", "benchmark"),
    "cno_area_edificacao_min": _p(80.0,    "benchmark mercado (edificação mínima)", "filtro_plausibilidade", "m2", "benchmark"),
    "cno_area_edificacao_max": _p(50000.0, "benchmark mercado (prédio multi-uso)", "filtro_plausibilidade", "m2", "benchmark"),
}

_OVERRIDE_CACHE: dict[str, dict[str, Any]] | None = None
_OVERRIDE_CACHE_AT: float | None = None  # monotonic time of last load


def clear_param_cache() -> None:
    """Invalida override Supabase — próximo param() recarrega. Use após seed/recalibração."""
    global _OVERRIDE_CACHE, _OVERRIDE_CACHE_AT
    _OVERRIDE_CACHE = None
    _OVERRIDE_CACHE_AT = None


def _cache_ttl_seg() -> float:
    raw = (os.environ.get("PARAMETROS_CACHE_TTL_SEG") or "").strip()
    if not raw:
        return 0.0  # 0 = sem TTL (só clear_param_cache / processo novo)
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0


def _carregar_overrides() -> dict[str, dict[str, Any]]:
    """Override recalibrável da tabela Supabase parametros_metodologia (best-effort)."""
    global _OVERRIDE_CACHE, _OVERRIDE_CACHE_AT
    import time as _time

    ttl = _cache_ttl_seg()
    if _OVERRIDE_CACHE is not None:
        if ttl <= 0 or _OVERRIDE_CACHE_AT is None:
            return _OVERRIDE_CACHE
        if (_time.monotonic() - _OVERRIDE_CACHE_AT) < ttl:
            return _OVERRIDE_CACHE
        _OVERRIDE_CACHE = None
        _OVERRIDE_CACHE_AT = None

    _OVERRIDE_CACHE = {}
    _OVERRIDE_CACHE_AT = _time.monotonic()
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not (os.environ.get("SUPABASE_URL") and key):
        return _OVERRIDE_CACHE
    try:
        from tools.supabase_client import load_create_client

        cli = load_create_client()(os.environ["SUPABASE_URL"], key)
        res = cli.table("parametros_metodologia").select("*").execute()
        for row in getattr(res, "data", None) or []:
            nome = row.get("nome")
            if nome and row.get("valor") is not None:
                _OVERRIDE_CACHE[nome] = row
    except Exception as e:
        print(f"[parametros] override Supabase indisponível: {type(e).__name__}: {e}")
    return _OVERRIDE_CACHE


def param_meta(nome: str) -> dict[str, Any]:
    """Registro completo do parâmetro (valor + fonte + metodo) — para exibir no relatório."""
    override = _carregar_overrides().get(nome)
    base = _DEFAULTS.get(nome)
    if override:
        rec = {**(base or {}), **override}
        rec.setdefault("fonte", "supabase_override")
        return rec
    if base is None:
        raise KeyError(f"parâmetro de metodologia desconhecido: {nome!r}")
    return dict(base)


def param(nome: str) -> float:
    """Valor numérico do parâmetro (override Supabase > default rotulado)."""
    return float(param_meta(nome)["valor"])


def param_int(nome: str) -> int:
    """Valor inteiro do parâmetro (limiares discretos: meses, pessoas, avaliações)."""
    return int(round(param(nome)))


def param_list(nome: str) -> list:
    """Valor lista do parâmetro (override Supabase > default). Aceita list ou 'a|b|c'."""
    v = param_meta(nome)["valor"]
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        return [x.strip() for x in v.split("|") if x.strip()]
    raise TypeError(f"parâmetro {nome!r} não é lista (got {type(v).__name__})")


def param_por_modelo(prefixo: str) -> dict[str, float]:
    """Mapa {low, mid, premium} a partir de chaves `{prefixo}_{modelo}`.

    Ex.: param_por_modelo("ticket") → {"low": .., "mid": .., "premium": ..}
    """
    return {m: param(f"{prefixo}_{m}") for m in ("low", "mid", "premium")}


def ocupacao_por_tipologia(tipologia: str | None) -> str:
    """Mapeia tipologia (do lançamento) → chave de parâmetro de ocupação."""
    t = (tipologia or "").lower()
    if "studio" in t or "stúdio" in t or "kit" in t:
        return "ocupacao_studio"
    if "3" in t or "4" in t or "alto padr" in t:
        return "ocupacao_3_mais_dorm"
    if "1 " in t or "2 " in t or "1-2" in t or "dorm" in t:
        return "ocupacao_1_2_dorm"
    return "ocupacao_default"
