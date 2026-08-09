"""Testes determinísticos — A3b CompetitorAnalysis (BaseAgent).

A3b foi determinizado (era LlmAgent-eco). O filtro autoritativo bairro/tipo/CLOSED
saiu do after_agent_callback e roda INLINE no BaseAgent via `_filtrar_envelope`
(RN-A3b-06). Sem LLM / sem rede.
"""
from __future__ import annotations

import pytest

import agents.a3b_competitor_analysis as m


def _envelope(lista: list[dict]) -> dict:
    """Envelope no formato que a macro retorna (inteligencia_competitiva aninhado)."""
    return {"inteligencia_competitiva": {"concorrentes_detalhados": lista}}


def _detalhados(env: dict) -> list[dict]:
    return env["inteligencia_competitiva"]["concorrentes_detalhados"]


# ---------------------------------------------------------------------------
# Módulo importável + função exportada
# ---------------------------------------------------------------------------

def test_modulo_importavel():
    import agents.a3b_competitor_analysis  # noqa: F401


def test_funcao_filtro_exportada():
    assert callable(m._filtrar_envelope)
    assert callable(m._sintetizar_textos)


# ---------------------------------------------------------------------------
# Filtro determinístico inline (_filtrar_envelope)
# ---------------------------------------------------------------------------

class TestFiltrarEnvelope:
    def _run(self, lista, state_extra=None):
        env = _envelope(lista)
        state = {"inteligencia_competitiva": env, **(state_extra or {})}
        m._filtrar_envelope(env, state)
        return env

    def test_nao_filtra_por_string_de_bairro(self):
        # Canônico §9 (conferencia-fontes): inclusão geográfica = R=1000m do centróide
        # em buscar_academias, NUNCA gate de string de bairro no caminho crítico. O
        # filtro do envelope só aplica tipo/status — bairro nunca dropa concorrente.
        env = self._run(
            [
                {"nome": "Academia Cocó Fit", "endereco": "Rua X, Cocó, Fortaleza", "tipos": ["gym"]},
                {"nome": "Smart Fit Aldeota", "endereco": "Av Y, Aldeota, Fortaleza", "tipos": ["gym"]},
            ],
            {"bairro": "Cocó"},
        )
        nomes = [c["nome"] for c in _detalhados(env)]
        assert "Academia Cocó Fit" in nomes and "Smart Fit Aldeota" in nomes

    def test_mantem_todos_quando_nenhum_no_bairro(self):
        env = self._run(
            [
                {"nome": "Academia Aldeota Fit", "endereco": "Av Y, Aldeota, Fortaleza"},
                {"nome": "Body Tech Meireles", "endereco": "Rua Z, Meireles, Fortaleza"},
            ],
            {"bairro": "Bairro Inexistente"},
        )
        assert len(_detalhados(env)) == 2  # salvaguarda: não zera

    def test_remove_crossfit_quando_tipo_academia(self):
        env = self._run(
            [
                {"nome": "Smart Fit Cocó", "endereco": "Rua X, Cocó, Fortaleza", "tipos": ["gym"]},
                {"nome": "Body Tech Cocó", "endereco": "Rua Y, Cocó, Fortaleza", "tipos": ["gym"]},
                {"nome": "CrossFit Cocó Box", "endereco": "Av Z, Cocó, Fortaleza", "tipos": ["gym"]},
            ],
            {"bairro": "Cocó", "input_params": {"tipo_negocio": "academia"}},
        )
        nomes = [c["nome"] for c in _detalhados(env)]
        assert "CrossFit Cocó Box" not in nomes
        assert "Smart Fit Cocó" in nomes and "Body Tech Cocó" in nomes

    def test_remove_permanently_closed(self):
        env = self._run(
            [
                {"nome": "Academia Fechada", "endereco": "Rua X, Cocó, Fortaleza",
                 "business_status": "PERMANENTLY_CLOSED"},
                {"nome": "Smart Fit Cocó", "endereco": "Rua Y, Cocó, Fortaleza"},
            ],
            {"bairro": "Cocó"},
        )
        nomes = [c["nome"] for c in _detalhados(env)]
        assert "Academia Fechada" not in nomes and "Smart Fit Cocó" in nomes

    def test_tipo_lido_de_input_params_governa_o_gate(self):
        # O que governa o envelope é tipo/status (tipo lido de input_params), não bairro.
        # bairro divergente NÃO dropa; especialidade fora-de-escopo (crossfit) sim.
        env = self._run(
            [
                {"nome": "Smart Fit Cocó", "endereco": "Rua X, Cocó, Fortaleza", "tipos": ["gym"]},
                {"nome": "Body Tech Meireles", "endereco": "Av Y, Meireles, Fortaleza", "tipos": ["gym"]},
                {"nome": "CrossFit Box", "endereco": "Av Z, Cocó, Fortaleza", "tipos": ["gym"]},
            ],
            {"input_params": {"bairro": "Meireles", "tipo_negocio": "academia"}},
        )
        nomes = [c["nome"] for c in _detalhados(env)]
        assert "Smart Fit Cocó" in nomes and "Body Tech Meireles" in nomes
        assert "CrossFit Box" not in nomes

    # tolerância (best-effort, nunca derruba)

    def test_envelope_sem_ic_nao_levanta(self):
        m._filtrar_envelope({"bairro": "x"}, {})

    def test_envelope_nao_dict_ic_nao_levanta(self):
        m._filtrar_envelope({"inteligencia_competitiva": "texto"}, {})

    def test_lista_vazia_nao_levanta(self):
        m._filtrar_envelope(_envelope([]), {"bairro": "Cocó"})


# ---------------------------------------------------------------------------
# Síntese determinística de textos (_sintetizar_textos)
# ---------------------------------------------------------------------------

class TestMesclarServicos:
    """FUSÃO A3c: modalidades mapeadas entram em servicos_oferecidos (o campo do gap A9)."""

    def test_merge_por_place_id(self):
        env = {"inteligencia_competitiva": {"concorrentes_detalhados": [
            {"place_id": "P1", "nome": "VS Club", "servicos_oferecidos": ["musculacao"]},
            {"place_id": "P2", "nome": "Parque Esportes", "servicos_oferecidos": []},
        ]}}
        oferta = {"oferta_concorrentes": {
            "P1": {"nome": "VS Club", "modalidades": ["piscina", "natacao"]},
            "P2": {"nome": "Parque Esportes", "modalidades": ["funcional", "danca"]},
        }}
        m._mesclar_servicos_na_oferta(env, oferta)
        det = env["inteligencia_competitiva"]["concorrentes_detalhados"]
        assert set(det[0]["servicos_oferecidos"]) == {"musculacao", "piscina", "natacao"}
        assert set(det[1]["servicos_oferecidos"]) == {"funcional", "danca"}

    def test_match_por_nome(self):
        env = {"inteligencia_competitiva": {"concorrentes_detalhados": [
            {"nome": "Academia X", "servicos_oferecidos": []}]}}
        oferta = {"oferta_concorrentes": {"idx_0": {"nome": "Academia X", "modalidades": ["pilates"]}}}
        m._mesclar_servicos_na_oferta(env, oferta)
        assert env["inteligencia_competitiva"]["concorrentes_detalhados"][0]["servicos_oferecidos"] == ["pilates"]

    def test_oferta_vazia_nao_altera(self):
        env = {"inteligencia_competitiva": {"concorrentes_detalhados": [
            {"nome": "A", "servicos_oferecidos": ["x"]}]}}
        m._mesclar_servicos_na_oferta(env, {})
        assert env["inteligencia_competitiva"]["concorrentes_detalhados"][0]["servicos_oferecidos"] == ["x"]


class TestSintetizarTextos:
    def test_textos_usam_so_fatos_do_envelope(self):
        env = {
            "inteligencia_competitiva": {
                "concorrentes_detalhados": [{"nome": "A"}, {"nome": "B"}],
                "dores_dominantes": [{"dor": "lotação no pico"}],
                "servicos_nao_oferecidos": ["natação"],
                "oportunidades_rankeadas": [{"titulo": "24h premium"}],
                "melhor_avaliada": {"nome": "REK", "rating": 4.9},
            },
            "nivel_saturacao": "ALTO",
            "score_concorrencia": 6.0,
        }
        pos, resumo = m._sintetizar_textos(env)
        assert "ALTO" in resumo and "6.0" in resumo and "lotação no pico" in resumo
        assert "natação" in pos and "lotação no pico" in pos

    def test_envelope_vazio_nao_levanta(self):
        pos, resumo = m._sintetizar_textos({"inteligencia_competitiva": {}})
        assert isinstance(pos, str) and isinstance(resumo, str)


# ---------------------------------------------------------------------------
# Contrato estático do agente A3b (agora BaseAgent, sem LLM)
# ---------------------------------------------------------------------------

class TestContratoEstaticoA3b:
    def setup_method(self):
        self.agent = m.competitor_analysis_agent

    def test_eh_base_agent_sem_llm(self):
        from google.adk.agents import BaseAgent
        assert isinstance(self.agent, BaseAgent)
        assert type(self.agent).__name__ == "CompetitorAnalysisAgent"

    def test_nome_agente_correto(self):
        assert self.agent.name == "CompetitorAnalysis"

    def test_sem_after_agent_callback(self):
        # filtro virou inline; não há mais callback pós-LLM
        assert getattr(self.agent, "after_agent_callback", None) is None

    def test_description_nao_vazia(self):
        assert self.agent.description and len(self.agent.description.strip()) > 0
