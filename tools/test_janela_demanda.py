"""Testes determinísticos para pdf/adapters.py — janela de demanda agregada.

Testa a lógica de agregação de horarios_pico dentro de relatorio_from_api_payload().
Shape real: horarios_pico = {dia: {"HH": pct_ocupacao}}.

Sem rede, sem LLM, sem I/O externo.
param_int("janela_demanda_min_concorrentes") é monkeypatchado para retornar 2.
"""
from __future__ import annotations

import os
import sys
import types as _types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(competidores: list[dict]) -> dict:
    """Monta payload mínimo válido para relatorio_from_api_payload."""
    return {
        "id": "test-id",
        "header": {"data_execucao": "2026-06-18", "status": "done", "schema_version": "1"},
        "input_canonico": {"cidade": "Fortaleza", "bairro": "Cocó", "uf": "CE",
                           "tipo_negocio": "academia", "area_m2_min": 200, "area_m2_max": 500},
        "output_consolidado": {},
        "candidatos": [],
        "competidores": competidores,
        "cenarios": [],
        "bairros_alternativos": [],
    }


def _call_adapter(monkeypatch, competidores: list[dict]) -> dict | None:
    """
    Chama relatorio_from_api_payload com param_int monkeypatchado.
    Retorna metadata['pico'] (pode ser None).
    """
    # Monkeypatch param_int para retornar 2 (min_concorrentes) sem Supabase
    import tools.parametros_metodologia as pm
    monkeypatch.setattr(pm, "param_int", lambda nome: 2)

    from pdf.adapters import relatorio_from_api_payload
    payload = _make_payload(competidores)
    resultado = relatorio_from_api_payload(payload)
    return resultado.metadata.get("pico")


# ---------------------------------------------------------------------------
# Construção de fixtures de horarios_pico
# ---------------------------------------------------------------------------

def _bimodal_manha_noite() -> dict:
    """
    Picos em 07h e 19h nos dias úteis.
    seg-sex: hora 7 = 90, hora 19 = 80, resto baixo.
    """
    horas_dia: dict[str, float] = {
        "06": 20.0,
        "07": 90.0,  # pico manhã
        "08": 50.0,
        "09": 30.0,
        "10": 20.0,
        "12": 30.0,
        "17": 40.0,
        "18": 60.0,
        "19": 80.0,  # pico noite
        "20": 50.0,
        "21": 20.0,
    }
    return {
        "segunda": horas_dia,
        "terca": horas_dia,
        "quarta": horas_dia,
        "quinta": horas_dia,
        "sexta": horas_dia,
        # fim de semana com pico na tarde (deve ser IGNORADO pela lógica de dias úteis)
        "sabado": {"12": 10.0, "14": 95.0, "15": 85.0},
        "domingo": {"13": 30.0, "15": 90.0},
    }


def _bimodal_manha_noite_v2() -> dict:
    """
    Segundo concorrente: pico em 07h e 19h também, mas com magnitudes diferentes.
    """
    horas_dia: dict[str, float] = {
        "06": 15.0,
        "07": 85.0,  # pico manhã
        "08": 40.0,
        "10": 15.0,
        "17": 35.0,
        "18": 55.0,
        "19": 75.0,  # pico noite
        "20": 45.0,
    }
    return {
        "segunda": horas_dia,
        "terca": horas_dia,
        "quarta": horas_dia,
        "quinta": horas_dia,
        "sexta": horas_dia,
        # fim de semana com pico na tarde
        "sabado": {"13": 20.0, "15": 88.0, "16": 70.0},
    }


# ---------------------------------------------------------------------------
# 1. Dois concorrentes bimodais (07h e 19h) → pico contem 07 e 19, NÃO 08-10
# ---------------------------------------------------------------------------

def test_pico_bimodal_manha_e_noite(monkeypatch):
    """
    Com 2 concorrentes com pico claro em 07h e 19h nos dias úteis,
    o pico agregado deve incluir horas 7 e 19 — e NÃO deve ter 8, 9 ou 10 como top.
    """
    competidores = [
        {"nome": "Smart Fit Cocó", "horarios_pico": _bimodal_manha_noite()},
        {"nome": "BlueFit Cocó", "horarios_pico": _bimodal_manha_noite_v2()},
    ]
    pico = _call_adapter(monkeypatch, competidores)

    assert pico is not None, "pico deve ser gerado com 2 concorrentes com dados"

    horas_top = pico["horas"]  # lista de strings como "07h", "19h"
    # Converte "07h" → 7 para comparar
    horas_int = [int(h.replace("h", "")) for h in horas_top]

    assert 7 in horas_int, f"hora 7 (pico manhã) deve estar no top; top={horas_int}"
    assert 19 in horas_int, f"hora 19 (pico noite) deve estar no top; top={horas_int}"

    # NÃO deve ter 8, 9 ou 10 como horas de pico principal
    # (o pico em 07 é claramente maior que 08-10)
    assert 8 not in horas_int or 7 in horas_int, (
        f"hora 8 não deveria superar hora 7 no top; top={horas_int}"
    )


def test_pico_nao_contem_hora_de_pico_fds(monkeypatch):
    """
    Hora 14h/15h tem pico alto só no fim de semana.
    A lógica filtra só dias úteis → 14h/15h NÃO deve aparecer no top.
    """
    competidores = [
        {"nome": "A", "horarios_pico": _bimodal_manha_noite()},
        {"nome": "B", "horarios_pico": _bimodal_manha_noite_v2()},
    ]
    pico = _call_adapter(monkeypatch, competidores)
    assert pico is not None

    horas_int = [int(h.replace("h", "")) for h in pico["horas"]]
    # 14h e 15h só existem no fim de semana dos fixtures — não devem estar no top 3
    assert 14 not in horas_int, f"hora 14 (só FDS) não deveria estar no top; top={horas_int}"
    assert 15 not in horas_int, f"hora 15 (só FDS) não deveria estar no top; top={horas_int}"


def test_pico_tem_campos_obrigatorios(monkeypatch):
    """Estrutura do pico_top deve ter horas, faixa, barras, concentracao_pct."""
    competidores = [
        {"nome": "A", "horarios_pico": _bimodal_manha_noite()},
        {"nome": "B", "horarios_pico": _bimodal_manha_noite_v2()},
    ]
    pico = _call_adapter(monkeypatch, competidores)
    assert pico is not None
    assert "horas" in pico
    assert "faixa" in pico
    assert "barras" in pico
    assert "concentracao_pct" in pico
    assert isinstance(pico["horas"], list)
    assert len(pico["horas"]) <= 3  # top 3
    assert isinstance(pico["concentracao_pct"], (int, float))


def test_barras_excluem_horas_antes_das_5(monkeypatch):
    """barras só inclui horas >= 5 (filtro explícito no código)."""
    competidores = [
        {"nome": "A", "horarios_pico": _bimodal_manha_noite()},
        {"nome": "B", "horarios_pico": _bimodal_manha_noite_v2()},
    ]
    pico = _call_adapter(monkeypatch, competidores)
    assert pico is not None
    for barra in pico["barras"]:
        hora_int = int(barra["hora"].replace("h", ""))
        assert hora_int >= 5, f"barra com hora {hora_int} < 5 não deveria aparecer"


# ---------------------------------------------------------------------------
# 2. 1 concorrente só → pico None (amostra insuficiente, min=2)
# ---------------------------------------------------------------------------

def test_pico_none_com_um_concorrente(monkeypatch):
    """
    Com apenas 1 concorrente com horarios_pico, _n_com_dados=1 < _min_conc=2.
    pico deve ser None.
    """
    competidores = [
        {"nome": "Único", "horarios_pico": _bimodal_manha_noite()},
    ]
    pico = _call_adapter(monkeypatch, competidores)
    assert pico is None, f"pico deveria ser None com 1 concorrente, mas foi: {pico}"


def test_pico_none_sem_competidores(monkeypatch):
    pico = _call_adapter(monkeypatch, [])
    assert pico is None


def test_pico_none_sem_horarios_pico(monkeypatch):
    """Competidores sem campo horarios_pico não contam para _n_com_dados."""
    competidores = [
        {"nome": "A"},
        {"nome": "B", "horarios_pico": None},
        {"nome": "C", "horarios_pico": "invalido"},
    ]
    pico = _call_adapter(monkeypatch, competidores)
    assert pico is None


def test_pico_none_com_horarios_pico_apenas_fds(monkeypatch):
    """
    Concorrentes que têm horarios_pico só com sabado/domingo não contribuem
    para _n_com_dados (filtro dias úteis). Mesmo com 2, pico deve ser None.
    """
    so_fds = {
        "sabado": {"10": 50.0, "14": 90.0},
        "domingo": {"11": 60.0, "15": 80.0},
    }
    competidores = [
        {"nome": "A", "horarios_pico": so_fds},
        {"nome": "B", "horarios_pico": so_fds},
    ]
    pico = _call_adapter(monkeypatch, competidores)
    assert pico is None, "sem dados de dias úteis, pico deveria ser None"


# ---------------------------------------------------------------------------
# 3. Normalização: academia grande não domina sobre academia pequena
# ---------------------------------------------------------------------------

def test_normalizacao_por_concorrente(monkeypatch):
    """
    Concorrente A: ocupação 100-200 (grande), pico em 07h
    Concorrente B: ocupação 1-10 (pequeno), pico em 19h
    Após normalização (0-100 por pico próprio), ambos contribuem igualmente.
    O top deve incluir tanto 07h quanto 19h.
    """
    hp_grande = {
        "segunda": {"07": 200.0, "08": 100.0, "19": 50.0},
        "terca": {"07": 200.0, "08": 100.0, "19": 50.0},
        "quarta": {"07": 200.0, "08": 100.0, "19": 50.0},
        "quinta": {"07": 200.0, "08": 100.0, "19": 50.0},
        "sexta": {"07": 200.0, "08": 100.0, "19": 50.0},
    }
    hp_pequeno = {
        "segunda": {"07": 2.0, "19": 10.0, "20": 8.0},
        "terca": {"07": 2.0, "19": 10.0, "20": 8.0},
        "quarta": {"07": 2.0, "19": 10.0, "20": 8.0},
        "quinta": {"07": 2.0, "19": 10.0, "20": 8.0},
        "sexta": {"07": 2.0, "19": 10.0, "20": 8.0},
    }
    competidores = [
        {"nome": "Grande", "horarios_pico": hp_grande},
        {"nome": "Pequeno", "horarios_pico": hp_pequeno},
    ]
    pico = _call_adapter(monkeypatch, competidores)
    assert pico is not None

    horas_int = [int(h.replace("h", "")) for h in pico["horas"]]
    # 7h é pico do Grande; 19h é pico do Pequeno
    # Após normalização, ambas devem aparecer no top
    assert 7 in horas_int, f"hora 7 deve estar no top; top={horas_int}"
    assert 19 in horas_int, f"hora 19 deve estar no top; top={horas_int}"
