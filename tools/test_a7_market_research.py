"""Testes determinísticos — A7 MarketResearch (sem LLM / sem rede).

Foco: contrato de configuração do agente (RN-A7-05, RN-A7-07).
A auditoria C4.3 apontou ausência de output_key como bug histórico (comentário
nas linhas 15-19 do código); este arquivo valida que o fix está em vigor.
Sem nenhuma chamada real ao Google Search ou LLM.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Importação do módulo
# ---------------------------------------------------------------------------

def test_modulo_importavel():
    """Módulo deve importar sem credenciais Google reais."""
    import agents.a7_market_research  # noqa: F401


def test_agente_exportado():
    """market_research_agent deve estar acessível no módulo."""
    import agents.a7_market_research as m
    assert hasattr(m, "market_research_agent")
    assert m.market_research_agent is not None


# ---------------------------------------------------------------------------
# Contrato de configuração (critérios de aceite do SPEC_A7)
# ---------------------------------------------------------------------------

class TestContratoA7:
    @pytest.fixture(autouse=True)
    def _load(self):
        import agents.a7_market_research as m
        self.agent = m.market_research_agent

    def test_output_key_market_research_result(self):
        """RN-A7-07 / fix histórico C6.2/C6.4: output_key deve ser 'market_research_result'.
        Antes desse fix o resultado se perdia no state e outros agentes não conseguiam ler."""
        assert self.agent.output_key == "market_research_result"

    def test_nome_agente_correto(self):
        assert self.agent.name == "MarketResearch"

    def test_description_nao_vazia(self):
        """Agente deve ter descrição para o root_agent saber quando acioná-lo."""
        assert self.agent.description and len(self.agent.description.strip()) > 0

    def test_instruction_nao_vazia(self):
        """Instruction deve existir (inclui regras de anti-alucinação e formato)."""
        assert self.agent.instruction and len(str(self.agent.instruction).strip()) > 0

    def test_tools_contem_google_search(self):
        """RN-A7-05: a única tool permitida é google_search.
        Adicionar qualquer outra tool quebra o Search Grounding da API Gemini."""
        assert self.agent.tools is not None
        assert len(self.agent.tools) >= 1

        tool_names = set()
        for t in self.agent.tools:
            # google_search pode ser o objeto built-in do ADK — checa nome de várias formas
            name = (
                getattr(t, "name", None)
                or getattr(t, "__name__", None)
                or type(t).__name__
                or ""
            )
            tool_names.add(str(name).lower())

        assert any("google_search" in n for n in tool_names), (
            f"Esperava google_search nas tools, encontrado: {tool_names}"
        )

    def test_apenas_uma_tool(self):
        """RN-A7-05: isolamento — mais de uma tool rompe o contrato do Search Grounding."""
        assert len(self.agent.tools) == 1, (
            f"A7 deve ter exatamente 1 tool (google_search), "
            f"encontrado {len(self.agent.tools)}: {self.agent.tools}"
        )

    def test_sem_after_agent_callback_interferente(self):
        """A7 não deve ter after_agent_callback que intercepte/modifique a resposta.
        Ele é agente lateral — sem filtros pós-emissão."""
        cb = getattr(self.agent, "after_agent_callback", None)
        assert cb is None, (
            f"A7 não deveria ter after_agent_callback, encontrado: {cb}"
        )

    def test_sem_after_tool_callback_interferente(self):
        """A7 não deve ter after_tool_callback (não tem tools próprias de lógica)."""
        cb = getattr(self.agent, "after_tool_callback", None)
        assert cb is None, (
            f"A7 não deveria ter after_tool_callback, encontrado: {cb}"
        )

    def test_instruction_menciona_nunca_invente_dados(self):
        """Instrução anti-alucinação (RN-A7-02) deve estar presente no texto."""
        instr = str(self.agent.instruction).lower()
        # "nunca invente" ou "não invente" são as formas usadas no prompt
        assert "invente" in instr or "invent" in instr, (
            "Instrução deve mencionar proibição de inventar dados (anti-alucinação)"
        )

    def test_instruction_menciona_fontes(self):
        """Seção de Fontes é obrigatória (RN-A7-03 / C8.3). Deve aparecer na instrução."""
        instr = str(self.agent.instruction).lower()
        assert "fonte" in instr or "source" in instr, (
            "Instrução deve mencionar a obrigatoriedade de citar fontes"
        )
