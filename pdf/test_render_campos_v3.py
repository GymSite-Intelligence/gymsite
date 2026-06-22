"""FASE 3 — renderização dos campos V3 (A4 tributos/ocupação + A9 zona/alertas) no PDF HTML.

Constrói um RelatorioPdfModel COM os campos novos preenchidos (cenário com
ocupacao_estoura=True, zona 1, 1 alerta FATOR_R) e confirma que o HTML:
  (a) renderiza sem exceção;
  (b) contém a linha de tributos (sub-tabela Tributos & Ocupação);
  (c) contém o box de ocupação estourada (INVIÁVEL por ocupação);
  (d) contém a Zona de Percepção (Z1) + o alerta financeiro/fiscal.
E que relatórios SEM os campos novos não quebram (degradação graciosa).
"""

from __future__ import annotations

from pdf.html_builder import gerar_html
from pdf.models import CenarioPdf, RelatorioPdfModel


def _modelo_com_v3() -> RelatorioPdfModel:
    cen = CenarioPdf(
        modelo="premium",
        label="Premium",
        ticket_medio=200.0,
        receita_mensal=80000.0,
        lucro_mensal=-5000.0,
        margem_pct=-6.0,
        payback_meses=None,
        investimento_total=900000.0,
        capex_total=700000.0,
        capex_obra=300000.0,
        capex_equipamentos=350000.0,
        capex_contingencia=50000.0,
        viabilidade="INVIAVEL",
        matriculas_realista=400,
        # V3 (A4)
        tributos_mensal=12400.0,
        aliquota_tributos=0.155,
        anexo_simples="V",
        fator_r=0.21,
        folha_pct_efetivo=0.21,
        ocupacao_pct=0.4035,
        teto_ocupacao=0.15,
        ticket_piso_ocupacao=537.0,
        ocupacao_estoura=True,
    )
    pos = {
        "veredito_posicionamento": "OCEANO_VERMELHO",
        "zona_percepcao": 1,
        "zona_nome": "Comodidade",
        "zona_descricao": "Cliente paga pelo acesso e conveniência; valor percebido baixo.",
        "alertas_financeiros_fiscais": [
            {
                "tipo": "FATOR_R",
                "severidade": "ALTA",
                "titulo": "Fator R: folha+pró-labore >=28% migra o Simples do Anexo V (15,5%) p/ III (6%)",
                "diagnostico": (
                    "Academia (CNAE 9313-1/00) NASCE no Anexo V (15,5%). Fator R atual 21% < corte 28%."
                ),
                "fonte": "deterministico (LC 123/2006 — Fator R) + A4",
            },
        ],
    }
    return RelatorioPdfModel(
        relatorio_id="abc12345",
        data_execucao="2026-06-21",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        tipo_negocio="academia",
        area_m2_min=400,
        area_m2_max=600,
        publico_alvo=None,
        veredito="OCEANO_VERMELHO",
        score_bairro=4.2,
        score_top1=5.1,
        modelo_recomendado="premium",
        cenarios=[cen],
        posicionamento_estrategico=pos,
    )


def test_render_v3_campos_presentes():
    html = gerar_html(_modelo_com_v3())  # (a) sem exceção
    # (b) sub-tabela de tributos & ocupação
    assert "Tributos &amp; Ocupação por cenário" in html
    assert "Fator R" in html
    assert "Anexo" in html
    # alíquota 15,5% e ocupação 0.4035 → "40,4%" (1 casa, como no exemplo do spec)
    assert "15,5%" in html
    assert "40,4%" in html
    # (c) box de ocupação estourada
    assert "Inviável por ocupação imobiliária" in html
    assert "INVIÁVEL por ocupação" in html
    # (d) Zona de Percepção + alerta financeiro/fiscal
    assert "Zona de Percepção" in html
    assert "Z1 — Comodidade" in html
    assert "Fator R: folha" in html


def test_render_v3_ausente_nao_quebra():
    """Relatório antigo (sem campos V3) renderiza sem os blocos novos e sem erro."""
    m = RelatorioPdfModel(
        relatorio_id="old00001",
        data_execucao="2025-01-01",
        cidade="Fortaleza",
        bairro="Aldeota",
        uf="CE",
        tipo_negocio="academia",
        area_m2_min=200,
        area_m2_max=400,
        publico_alvo=None,
        veredito="APROVADO",
        score_bairro=7.0,
        score_top1=8.0,
        cenarios=[
            CenarioPdf(
                modelo="mid", label="Mid", ticket_medio=120.0, receita_mensal=40000.0,
                lucro_mensal=8000.0, margem_pct=20.0, payback_meses=24,
                investimento_total=400000.0, capex_total=300000.0, capex_obra=150000.0,
                capex_equipamentos=120000.0, capex_contingencia=30000.0,
                viabilidade="ALTO", matriculas_realista=300,
            ),
        ],
        posicionamento_estrategico=None,
    )
    html = gerar_html(m)
    assert "Tributos &amp; Ocupação por cenário" not in html
    assert "Inviável por ocupação imobiliária" not in html
    assert "Zona de Percepção" not in html
