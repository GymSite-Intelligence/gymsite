"""Testes do runner ADK da degustação (Fase 3a) — parte testável sem ADK real.

Cobre a lógica pura (derivação do contador de amostras, extração de resposta) e o
import do módulo (pega quebra de símbolo do google-adk). A integração ADK
(re-hidratação, run_async, latência) é validada por smoke contra `adk web` antes do
canário — ver o cabeçalho de agents_site/runner.py.
"""
from __future__ import annotations

from types import SimpleNamespace


def test_import_runner():
    """O módulo importa — pega quebra de símbolo do google-adk / dos agentes."""
    from agents_site.runner import run_site_agent_adk  # noqa: F401


def test_derivar_amostras_conta_tool_calls_de_amostra():
    from agents_site.runner import _derivar_amostras

    historico = [
        {"role": "user", "content": "quero abrir no Butantã"},
        {"role": "assistant", "content": "...", "tool_calls": [{"name": "buscar_concorrentes"}]},
        {"role": "user", "content": "e a demografia?"},
        {"role": "assistant", "content": "...", "tool_calls": [{"name": "analisar_demografia"}]},
        # tool fora da lista de amostra não conta
        {"role": "assistant", "content": "...", "tool_calls": [{"name": "consultar_base_regulatoria"}]},
    ]
    assert _derivar_amostras(historico) == 2


def test_derivar_amostras_sem_tool_calls():
    from agents_site.runner import _derivar_amostras

    assert _derivar_amostras([{"role": "user", "content": "oi"}]) == 0
    assert _derivar_amostras([]) == 0


def _ev(*, partial=False, role="model", textos=("resposta",)):
    parts = [SimpleNamespace(text=t) for t in textos]
    return SimpleNamespace(partial=partial, content=SimpleNamespace(role=role, parts=parts))


def test_extrair_resposta_coleta_modelo_final():
    from agents_site.runner import _extrair_resposta

    assert _extrair_resposta(_ev(textos=("olá",))) == "olá"


def test_extrair_resposta_ignora_partial():
    from agents_site.runner import _extrair_resposta

    assert _extrair_resposta(_ev(partial=True, textos=("parcial",))) == ""


def test_extrair_resposta_ignora_eco_do_user():
    from agents_site.runner import _extrair_resposta

    assert _extrair_resposta(_ev(role="user", textos=("minha pergunta",))) == ""


def test_coletar_acoes_extrai_function_call():
    from agents_site.runner import _coletar_acoes

    ev = SimpleNamespace(
        content=SimpleNamespace(
            parts=[SimpleNamespace(function_call=SimpleNamespace(name="buscar_concorrentes"))]
        )
    )
    acoes = _coletar_acoes(ev)
    assert len(acoes) == 1
    assert acoes[0]["ferramenta"] == "buscar_concorrentes"


def test_coletar_acoes_preserva_resultado_function_response():
    from agents_site.runner import _coletar_acoes, _normalizar_tool_calls

    payload = {"total_concorrentes": 2, "concorrentes": [{"nome": "Aquazul"}]}
    ev = SimpleNamespace(
        content=SimpleNamespace(
            parts=[
                SimpleNamespace(
                    function_call=None,
                    function_response=SimpleNamespace(
                        name="buscar_concorrentes",
                        response=payload,
                    ),
                )
            ]
        )
    )
    acoes = _coletar_acoes(ev)
    assert acoes[0]["resultado"]["total_concorrentes"] == 2
    norm = _normalizar_tool_calls(
        [{"ferramenta": "buscar_concorrentes", "status": "sucesso", "resumo": "buscar_concorrentes"}, *acoes]
    )
    assert norm[0]["resultado"]["concorrentes"][0]["nome"] == "Aquazul"


def test_extrair_resposta_evento_sem_content():
    from agents_site.runner import _extrair_resposta

    assert _extrair_resposta(SimpleNamespace(partial=False, content=None)) == ""

