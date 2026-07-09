"""Fechamento das tasks #16/#17/#29 da auditoria de quadros (run b7199c7c).

#16 — portal de listagem passava no gate de logradouro e virava empreendimento
      fantasma ("Apartamentos à Venda na Rua", 138m²).
#17 — selo INVIAVEL exibia a justificativa da RECOMENDAÇÃO (teto de captação),
      não o motivo realista do selo.
#29 — linha de aluguel do panorama carimbava a pesquisa (Deep Research) em vez
      da fonte USADA na viabilidade (metodologia MRLR).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.lancamento_fetcher import _candidato_valido
from db.supabase_writer import _rows_cenarios
from pdf.adapters import _map_cenario_row
from pdf.html_builder import gerar_html
from pdf.models import MarketContextPdf
from pdf.test_render_campos_v3 import _modelo_com_v3


def _market_minimo():
    return MarketContextPdf(ticket_mercado="R$ 150", aluguel_m2="35.71",
                            renda="R$ 4.200", tendencia="estável")


# ---------- #16: blocklist de portais ----------

def test_portal_de_listagem_rejeitado():
    assert not _candidato_valido(
        "https://www.vivareal.com.br/venda/ceara/fortaleza/bairros/coco/",
        "Apartamentos à Venda na Rua Coronel Manuel Jesuíno")
    assert not _candidato_valido(
        "https://www.zapimoveis.com.br/lancamentos/fortaleza/",
        "Mood Cocó")  # domínio de portal derruba mesmo com nome próprio


def test_titulo_generico_rejeitado_mesmo_fora_de_portal():
    assert not _candidato_valido(
        "https://imobiliariax.com.br/pagina", "Apartamentos à venda em Fortaleza")
    assert not _candidato_valido(
        "https://imobiliariax.com.br/pagina", "Casas a venda no Cocó")


def test_pagina_de_lancamento_com_nome_proprio_passa():
    assert _candidato_valido("https://apto.vc/like-residencial", "Like Residencial — Cocó")
    assert _candidato_valido("https://construtorabs.com.br/rubi", "BS Rubi Design Residence")


# ---------- #17: selo INVIAVEL com motivo realista ----------

def _rel_com_premium_inviavel():
    return {"output_consolidado": {"viabilidade_3_cenarios": {"premium": {
        "viabilidade": "INVIAVEL",
        "justificativa": "Recomendado operando no TETO DE CAPTAÇÃO (312 matrículas…)",
        "justificativa_realista": "Prejuízo mensal de R$ 14.200",
    }}}}


def test_writer_inviavel_persiste_motivo_realista():
    rows = _rows_cenarios(_rel_com_premium_inviavel(), "rel-1")
    premium = [r for r in rows if r.get("modelo") == "premium"][0]
    assert premium["justificativa"] == "Prejuízo mensal de R$ 14.200"


def test_writer_viavel_mantem_justificativa_da_recomendacao():
    rel = {"output_consolidado": {"viabilidade_3_cenarios": {"mid": {
        "viabilidade": "VIAVEL",
        "justificativa": "Payback 28m, margem 22%",
        "justificativa_realista": "Payback 28m",
    }}}}
    mid = [r for r in _rows_cenarios(rel, "rel-1") if r.get("modelo") == "mid"][0]
    assert mid["justificativa"] == "Payback 28m, margem 22%"


def test_adapter_inviavel_prefere_realista():
    c = _map_cenario_row({"viabilidade": "INVIAVEL",
                          "justificativa": "Recomendado operando no TETO DE CAPTAÇÃO…",
                          "justificativa_realista": "Prejuízo mensal de R$ 14.200"})
    assert c.justificativa == "Prejuízo mensal de R$ 14.200"


# ---------- #31: break-even por margem de contribuição ----------

from tools.financial_tools import calcular_break_even_alunos


def test_break_even_exemplo_do_confronto_gemini():
    # Caso do confronto (sem tributos): fixos puros 83.312, ticket 95,
    # mkt 6%, outros 2% → margem 87,40 → 83.312/87,40 = 953,2 → 954 pra cobrir.
    # Fórmula antiga (custos_totais 98.360 ÷ 95) dava 1.036+ — ~8% a mais.
    be = calcular_break_even_alunos(83_312, 95.0, mkt_pct=0.06, outros_pct=0.02)
    assert be == 954
    be_formula_antiga = int(98_360 / 95.0) + 1
    assert be < be_formula_antiga


def test_break_even_com_tributos_simples():
    # Simples também é % da receita — entra na margem, não nos fixos.
    # margem = 95 × (1 − 0,06 − 0,02 − 0,155) = 72,675 → 83.312/72,675 = 1.146,3 → 1.147
    be = calcular_break_even_alunos(
        83_312, 95.0, mkt_pct=0.06, outros_pct=0.02, aliquota_tributos=0.155)
    assert be == 1147


def test_break_even_margem_nao_positiva():
    assert calcular_break_even_alunos(50_000, 100.0, mkt_pct=0.6, outros_pct=0.5) == 0


# ---------- #34: churn operacionalizado (CAC-teto de reposição) ----------

from tools.financial_tools import cac_teto_reposicao


def test_cac_teto_caso_do_confronto():
    # Low do confronto: 1.980 alunos × 6% churn = 119 reposições/mês;
    # R$ 11.286 de marketing ÷ 119 = R$ 94,84 de CAC máximo.
    r = cac_teto_reposicao(11_286, 1_980, 0.06)
    assert r["reposicoes_mes_churn"] == 119
    assert r["cac_teto_reposicao"] == 94.84


def test_cac_teto_sem_churn_nao_divide_por_zero():
    r = cac_teto_reposicao(10_000, 500, 0.0)
    assert r["reposicoes_mes_churn"] == 0
    assert r["cac_teto_reposicao"] is None


# ---------- #33: água escala com visitas ----------

from tools.financial_tools import custo_agua_mensal


def test_agua_low_cost_paga_pelo_volume_de_visitas():
    # ~30k visitas/mês (2k alunos × 3,5×/sem): 30.000 × 0,013 m³ × R$15 = 5.850
    assert custo_agua_mensal(900, 2.0, visitas_mes=30_000) == 5_850.0


def test_agua_premium_fica_no_piso_por_m2():
    # 5k visitas → variável 975 < piso 1.800 (900 m² × R$2) → piso segura
    assert custo_agua_mensal(900, 2.0, visitas_mes=5_000) == 1_800.0


def test_agua_academia_vazia_paga_o_piso():
    assert custo_agua_mensal(900, 2.0, visitas_mes=0) == 1_800.0


# ---------- #32: ERP escala com a base de alunos ----------

from tools.financial_tools import custo_sistema_gestao


def test_sistema_gestao_degrau_por_base_de_alunos():
    assert custo_sistema_gestao(800.0, 540) == 800.0     # premium: franquia comum
    assert custo_sistema_gestao(800.0, 1500) == 800.0    # borda: ainda na franquia
    assert custo_sistema_gestao(800.0, 1980) == 1200.0   # low ~2k vidas: rompe → 1,5×


# ---------- #30: colunas fiscais persistidas (quadro fecha na conferência) ----------

def test_writer_persiste_campos_fiscais():
    rel = {"output_consolidado": {"viabilidade_3_cenarios": {"low": {
        "viabilidade": "VIAVEL", "justificativa": "ok",
        "fator_r": 0.18, "anexo_simples": "V",
        "aliquota_tributos": 0.155, "tributos_mensal": 33156.28,
    }}}}
    low = [r for r in _rows_cenarios(rel, "rel-1") if r.get("modelo") == "low"][0]
    assert low["fator_r"] == 0.18
    assert low["anexo_simples"] == "V"
    assert low["aliquota_tributos"] == 0.155
    assert low["tributos_mensal"] == 33156.28


def test_writer_fiscal_ausente_vira_none():
    rel = {"output_consolidado": {"viabilidade_3_cenarios": {"mid": {
        "viabilidade": "VIAVEL", "justificativa": "ok"}}}}
    mid = [r for r in _rows_cenarios(rel, "rel-1") if r.get("modelo") == "mid"][0]
    assert mid["tributos_mensal"] is None  # run antigo: viewer mostra "—", não 0


# ---------- #29: carimbo do aluguel = fonte usada ----------

def test_panorama_carimba_metodologia_mrlr():
    model = _modelo_com_v3()
    model.market = _market_minimo()
    model.aluguel_mensal = 27876.0
    model.aluguel_fonte = "MRLR IBAPE-GO (R²=0,8633) — espelhos municipio_pib + renda_bairro"
    html = gerar_html(model)
    assert "metodologia MRLR" in html


def test_panorama_sem_a4_cai_na_pesquisa():
    model = _modelo_com_v3()
    model.market = _market_minimo()
    model.aluguel_mensal = None
    model.aluguel_fonte = None
    html = gerar_html(model)
    assert "metodologia MRLR" not in html
