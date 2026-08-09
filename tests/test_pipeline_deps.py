"""Pipeline deps reverse — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para "fazer passar".
Só edite `tools/pipeline_deps.py` (mapa) e/ou o agente que quebrou o wiring até:

  python -m pytest tests/test_pipeline_deps.py -q --tb=short -x

sair com código 0.

Contrato: cada agente da esteira declara writes (contrato), reads (entradas)
e o grafo fecha — toda entrada tem produtor conhecido; toda escrita tem
consumidor (ou é terminal). Código-fonte do agente deve mencionar as chaves.
"""
from __future__ import annotations

from pathlib import Path

from tools.pipeline_deps import (
    AGENT_DEPS,
    ENTRYPOINT_WRITES,
    PIPELINE_ORDER,
    REVERSE_ORDER,
    TERMINAL_WRITES,
    consumers_of,
    producers,
    reverse_cards,
)

ROOT = Path(__file__).resolve().parents[1]


def test_ordem_pipeline_e_reverso_sao_espelho():
    assert list(reversed(PIPELINE_ORDER)) == list(REVERSE_ORDER)
    assert PIPELINE_ORDER == ("A0", "A1", "A2", "A3a", "A3b", "A4", "A6", "A9")


def test_todo_agente_tem_arquivo_e_contrato():
    for agent in PIPELINE_ORDER:
        dep = AGENT_DEPS[agent]
        assert dep["writes"], f"{agent} sem writes (contrato vazio)"
        assert dep["reads"] is not None
        path = ROOT / dep["file"]
        assert path.is_file(), f"{agent}: arquivo sumiu ({dep['file']})"


def test_toda_entrada_tem_produtor_conhecido():
    prod = producers()
    for agent, dep in AGENT_DEPS.items():
        for key in dep["reads"]:
            assert key in prod, (
                f"{agent} lê `{key}` sem produtor no mapa "
                f"(adicione write em algum agente ou em ENTRYPOINT_WRITES)"
            )


def test_toda_escrita_tem_consumidor_ou_e_terminal():
    for agent, dep in AGENT_DEPS.items():
        for key in dep["writes"]:
            cons = consumers_of(key)
            if cons:
                continue
            assert key in TERMINAL_WRITES, (
                f"{agent} escreve `{key}` órfã — ninguém lê e não está em "
                f"TERMINAL_WRITES (persistência/PDF)"
            )


def test_producers_unicos_por_chave():
    """Uma chave de state = um dono. Duplicata = bug de wiring."""
    seen: dict[str, str] = {}
    for key in ENTRYPOINT_WRITES:
        seen[key] = "entrypoint"
    for agent, dep in AGENT_DEPS.items():
        for key in dep["writes"]:
            assert key not in seen, (
                f"chave `{key}` escrita por {seen[key]} e {agent}"
            )
            seen[key] = agent


def test_fonte_do_agente_menciona_writes_e_reads_criticos():
    """Sanidade: o .py do agente cita as chaves que o mapa declara.

    Não exige AST — evita falso positivo por rename. Se a chave sumir do
    arquivo, o mapa ou o agente divergiram.
    """
    # Chaves curtas demais / genéricas demais pra grepar cegamente
    skip_read_check = frozenset({"input_params"})  # quase todos usam via helper
    for agent, dep in AGENT_DEPS.items():
        src = (ROOT / dep["file"]).read_text(encoding="utf-8")
        for key in dep["writes"]:
            assert key in src, f"{agent} deveria escrever `{key}` em {dep['file']}"
        for key in dep["reads"]:
            if key in skip_read_check:
                continue
            assert key in src, f"{agent} deveria ler `{key}` em {dep['file']}"


def test_cartoes_reverso_fecham_a9_ate_a0():
    cards = reverse_cards()
    assert [c["agent"] for c in cards] == list(REVERSE_ORDER)
    # A9: terminal + inputs de A3b/A4/A6/entrypoint
    a9 = cards[0]
    assert a9["agent"] == "A9"
    assert "persistência/PDF" in a9["consumers"]["relatorio_posicionamento"]
    sources = {i["key"]: i["from"] for i in a9["inputs"]}
    assert sources["inteligencia_competitiva"] == "A3b"
    assert sources["analise_financeira"] == "A4"
    assert sources["relatorio_md"] == "A6"
    assert sources["demografia_bairro"] == "A6"
    assert sources["demanda_futura"] == "entrypoint"
    # A0: só entrypoint input_params
    a0 = cards[-1]
    assert a0["agent"] == "A0"
    assert a0["inputs"] == [{"key": "input_params", "from": "entrypoint"}]
    assert consumers_of("market_context")  # A0 alimenta quase todos
