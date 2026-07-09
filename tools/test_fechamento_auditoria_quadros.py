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
