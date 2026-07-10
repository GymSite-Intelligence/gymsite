"""Regressão da 'fonte do problema' do Arquiteto: calcular_sanitarios_por_lotacao
apresentava sua estimativa 50/50 genérica como se fosse a exigência legal do
município (docstring 'use SEMPRE / não estime'), e o agente cuspiu '5 bacias
femininas' onde João Pessoa (Lei 1.347/1971, assimétrica) exige mais.

O conserto na FONTE: a tool tem que se declarar ESTIMATIVA NÃO-OFICIAL — na
saída (campo que o agente não pode dropar) e no docstring (que o LLM lê pra
decidir uso). Não corrige o número (o número certo vem do COE municipal via
store/busca) — corrige a AUTORIDADE FALSA.
"""
from __future__ import annotations

import inspect

from agents_site.tools import calcular_sanitarios_por_lotacao


def test_saida_carimba_estimativa_nao_oficial():
    r = calcular_sanitarios_por_lotacao(200)
    # o carimbo tem que ser DADO na saída, não texto solto que o agente ignora
    assert r.get("tipo") == "estimativa_nao_oficial", (
        "saída precisa se declarar estimativa não-oficial num campo estruturado"
    )
    aviso = (r.get("aviso") or "").lower()
    assert "coe" in aviso or "código de obras" in aviso or "codigo de obras" in aviso
    assert "assim" in aviso or "município" in aviso or "municipio" in aviso, (
        "aviso precisa alertar que o COE municipal pode diferir/ser assimétrico"
    )


def test_docstring_nao_reivindica_autoridade_legal():
    doc = (calcular_sanitarios_por_lotacao.__doc__ or "").lower()
    # a raiz do bug: o contrato mandava usar SEMPRE e proibia estimar
    assert "não estime" not in doc and "nao estime" not in doc, (
        "docstring não pode proibir o agente de tratar isto como estimativa"
    )
    assert "estimativa" in doc, "docstring tem que rotular explicitamente como estimativa"
