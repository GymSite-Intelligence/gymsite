"""Testes determinísticos — A3b CompetitorAnalysis: callback _a3b_filtrar_concorrentes.

Foco: filtro autoritativo pós-agente (RN-A3b-06).
Sem LLM / sem rede. Usa dados reais do filtrar_concorrentes_bairro_tipo.
"""
from __future__ import annotations

import types

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_callback_context(state: dict):
    """Mínimo fake de CallbackContext com .state."""
    ctx = types.SimpleNamespace()
    ctx.state = state
    return ctx


def _ic_com_concorrentes(lista: list[dict], bairro_alvo: str | None = None) -> dict:
    """Monta estrutura inteligencia_competitiva no formato esperado pelo callback."""
    ic = {
        "inteligencia_competitiva": {
            "concorrentes_detalhados": lista,
        }
    }
    return ic


# ---------------------------------------------------------------------------
# Importação do módulo
# ---------------------------------------------------------------------------

def test_modulo_importavel():
    import agents.a3b_competitor_analysis  # noqa: F401


def test_funcao_filtro_exportada():
    import agents.a3b_competitor_analysis as m
    assert callable(m._a3b_filtrar_concorrentes)


# ---------------------------------------------------------------------------
# Testes do callback _a3b_filtrar_concorrentes
# ---------------------------------------------------------------------------

class TestFiltrarConcorrentes:
    """Testa o filtro determinístico via callback (usa state dict como agente faz)."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import agents.a3b_competitor_analysis as m
        self.fn = m._a3b_filtrar_concorrentes

    def _run(self, state: dict):
        ctx = _fake_callback_context(state)
        result = self.fn(ctx)
        return ctx.state, result

    # ------------------------------------------------------------------
    # Filtragem por bairro
    # ------------------------------------------------------------------

    def test_remove_concorrente_fora_do_bairro(self):
        """Concorrente de outro bairro é dropado quando existe ao menos 1 no bairro alvo."""
        lista = [
            {"nome": "Academia Cocó Fit", "endereco": "Rua X, Cocó, Fortaleza"},
            {"nome": "Smart Fit Aldeota", "endereco": "Av Y, Aldeota, Fortaleza"},
        ]
        state = {
            "bairro": "Cocó",
            "inteligencia_competitiva": _ic_com_concorrentes(lista),
        }
        st, ret = self._run(state)

        sobrou = st["inteligencia_competitiva"]["inteligencia_competitiva"]["concorrentes_detalhados"]
        nomes = [c["nome"] for c in sobrou]
        assert "Academia Cocó Fit" in nomes
        assert "Smart Fit Aldeota" not in nomes

    def test_mantem_todos_quando_nenhum_no_bairro(self):
        """Salvaguarda: se ZERO casam o bairro, mantém todos (não zera a lista)."""
        lista = [
            {"nome": "Academia Aldeota Fit", "endereco": "Av Y, Aldeota, Fortaleza"},
            {"nome": "Body Tech Meireles", "endereco": "Rua Z, Meireles, Fortaleza"},
        ]
        state = {
            "bairro": "Bairro Inexistente",
            "inteligencia_competitiva": _ic_com_concorrentes(lista),
        }
        st, _ = self._run(state)

        sobrou = st["inteligencia_competitiva"]["inteligencia_competitiva"]["concorrentes_detalhados"]
        assert len(sobrou) == 2  # todos preservados

    # ------------------------------------------------------------------
    # Filtragem por tipo
    # ------------------------------------------------------------------

    def test_remove_crossfit_quando_tipo_academia_com_2_on_type(self):
        """CrossFit é off-type para 'academia' quando sobram >=2 academias comuns."""
        lista = [
            {"nome": "Smart Fit Cocó", "endereco": "Rua X, Cocó, Fortaleza", "tipos": ["gym"]},
            {"nome": "Body Tech Cocó", "endereco": "Rua Y, Cocó, Fortaleza", "tipos": ["gym"]},
            {"nome": "CrossFit Cocó Box", "endereco": "Av Z, Cocó, Fortaleza", "tipos": ["gym"]},
        ]
        state = {
            "bairro": "Cocó",
            "input_params": {"tipo_negocio": "academia"},
            "inteligencia_competitiva": _ic_com_concorrentes(lista),
        }
        st, _ = self._run(state)

        sobrou = st["inteligencia_competitiva"]["inteligencia_competitiva"]["concorrentes_detalhados"]
        nomes = [c["nome"] for c in sobrou]
        assert "CrossFit Cocó Box" not in nomes
        assert "Smart Fit Cocó" in nomes
        assert "Body Tech Cocó" in nomes

    # ------------------------------------------------------------------
    # Filtragem por status CLOSED
    # ------------------------------------------------------------------

    def test_remove_permanently_closed(self):
        """Academias PERMANENTLY_CLOSED são removidas quando existe ao menos 1 operacional."""
        lista = [
            {
                "nome": "Academia Fechada",
                "endereco": "Rua X, Cocó, Fortaleza",
                "business_status": "PERMANENTLY_CLOSED",
            },
            {
                "nome": "Smart Fit Cocó",
                "endereco": "Rua Y, Cocó, Fortaleza",
            },
        ]
        state = {
            "bairro": "Cocó",
            "inteligencia_competitiva": _ic_com_concorrentes(lista),
        }
        st, _ = self._run(state)

        sobrou = st["inteligencia_competitiva"]["inteligencia_competitiva"]["concorrentes_detalhados"]
        nomes = [c["nome"] for c in sobrou]
        assert "Academia Fechada" not in nomes
        assert "Smart Fit Cocó" in nomes

    def test_remove_closed_temporarily(self):
        """Academias CLOSED_TEMPORARILY também são removidas."""
        lista = [
            {
                "nome": "Gym Temp Closed",
                "endereco": "Rua X, Cocó, Fortaleza",
                "business_status": "CLOSED_TEMPORARILY",
            },
            {
                "nome": "Ativa Fit Cocó",
                "endereco": "Rua Y, Cocó, Fortaleza",
            },
        ]
        state = {
            "bairro": "Cocó",
            "inteligencia_competitiva": _ic_com_concorrentes(lista),
        }
        st, _ = self._run(state)

        sobrou = st["inteligencia_competitiva"]["inteligencia_competitiva"]["concorrentes_detalhados"]
        nomes = [c["nome"] for c in sobrou]
        assert "Gym Temp Closed" not in nomes

    # ------------------------------------------------------------------
    # Tolerância a state malformado (RN-A3b-06: best-effort, nunca derruba)
    # ------------------------------------------------------------------

    def test_state_sem_inteligencia_competitiva_nao_levanta(self):
        """State sem a chave inteligencia_competitiva → retorna None silenciosamente."""
        state = {"bairro": "Cocó"}
        ctx = _fake_callback_context(state)
        result = self.fn(ctx)
        assert result is None

    def test_inteligencia_competitiva_nao_dict_nao_levanta(self):
        """Valor string (não-dict) em inteligencia_competitiva → não derruba."""
        state = {
            "bairro": "Cocó",
            "inteligencia_competitiva": "texto não-dict",
        }
        ctx = _fake_callback_context(state)
        # Não deve levantar exceção
        result = self.fn(ctx)
        assert result is None

    def test_concorrentes_detalhados_vazio_nao_levanta(self):
        """Lista vazia em concorrentes_detalhados → retorna None sem erro."""
        state = {
            "bairro": "Cocó",
            "inteligencia_competitiva": _ic_com_concorrentes([]),
        }
        ctx = _fake_callback_context(state)
        result = self.fn(ctx)
        assert result is None

    def test_state_completamente_vazio_nao_levanta(self):
        """State {} → retorna None sem exceção."""
        ctx = _fake_callback_context({})
        result = self.fn(ctx)
        assert result is None

    def test_callback_sempre_retorna_none(self):
        """O contrato ADK: after_agent_callback deve retornar None (sem interceptar resposta)."""
        lista = [
            {"nome": "Smart Fit Cocó", "endereco": "Rua X, Cocó, Fortaleza"},
        ]
        state = {
            "bairro": "Cocó",
            "inteligencia_competitiva": _ic_com_concorrentes(lista),
        }
        ctx = _fake_callback_context(state)
        result = self.fn(ctx)
        assert result is None

    # ------------------------------------------------------------------
    # Bairro lido de fontes alternativas (input_params, market_context)
    # ------------------------------------------------------------------

    def test_bairro_lido_de_input_params(self):
        """Se state['bairro'] ausente, lê de input_params.bairro."""
        lista = [
            {"nome": "Gym no Bairro Alvo", "endereco": "Rua X, Meireles, Fortaleza"},
            {"nome": "Gym Fora", "endereco": "Av Y, Aldeota, Fortaleza"},
        ]
        state = {
            "input_params": {"bairro": "Meireles", "tipo_negocio": "academia"},
            "inteligencia_competitiva": _ic_com_concorrentes(lista),
        }
        st, _ = self._run(state)
        sobrou = st["inteligencia_competitiva"]["inteligencia_competitiva"]["concorrentes_detalhados"]
        nomes = [c["nome"] for c in sobrou]
        assert "Gym no Bairro Alvo" in nomes
        assert "Gym Fora" not in nomes


# ---------------------------------------------------------------------------
# Testes de contrato estático do agente A3b
# ---------------------------------------------------------------------------

class TestContratoEstaticoA3b:
    @pytest.fixture(autouse=True)
    def _load(self):
        import agents.a3b_competitor_analysis as m
        self.agent = m.competitor_analysis_agent
        self.fn = m._a3b_filtrar_concorrentes

    def test_output_key_correto(self):
        assert self.agent.output_key == "inteligencia_competitiva"

    def test_nome_agente_correto(self):
        assert self.agent.name == "CompetitorAnalysis"

    def test_after_agent_callback_eh_filtrar_concorrentes(self):
        """RN-A3b-06: after_agent_callback deve ser _a3b_filtrar_concorrentes."""
        assert self.agent.after_agent_callback is self.fn

    def test_description_nao_vazia(self):
        assert self.agent.description and len(self.agent.description.strip()) > 0

    def test_instruction_nao_vazia(self):
        assert self.agent.instruction and len(str(self.agent.instruction).strip()) > 0
