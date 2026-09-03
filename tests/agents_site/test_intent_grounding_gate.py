"""Gate sanitário: pin Regulatório, bloqueia Maps, recusa prosa sem RAG."""
from __future__ import annotations

from types import SimpleNamespace

from agents_site.intent_gate import (
    MSG_ABSTENCAO_SANITARIA,
    aplicar_gate_grounding_sanitaria,
    intencao_sanitaria,
    loc_args_confiaveis,
    pin_especialista,
)
from agents_site.guardrails import gate_degustacao

_PID_ULTIMA = (
    "Para a Lanchonete a lista informada tem itens que devo manter registro "
    "atualizado no local para apreciação da vigilancia, poderia me indicar quais são eles?"
)


def test_intencao_sanitaria_no_pid():
    assert intencao_sanitaria(_PID_ULTIMA)
    assert intencao_sanitaria(
        "Qual são as documentações necessárias solicitadas pela vigilância sanitaria"
    )
    assert not intencao_sanitaria("Quantas academias tem no Cocó em Fortaleza?")


def test_pin_degustacao_sanitaria_vai_regulatorio():
    assert pin_especialista("degustacao", _PID_ULTIMA) == "regulatorio"
    assert pin_especialista("degustacao", "quantas academias no Cocó?") == "degustacao"
    assert pin_especialista("mercado", _PID_ULTIMA) == "regulatorio"


def test_loc_args_lixo_do_pid_rejeitados():
    assert not loc_args_confiaveis(
        {"cidade": "poderia", "bairro": "vigilancia", "uf": "ME"}
    )
    assert loc_args_confiaveis(
        {"cidade": "Navegantes", "bairro": "Centro", "uf": "SC"}
    )


def test_gate_maps_bloqueia_quando_pergunta_e_sanitaria():
    ctx = SimpleNamespace(state={"tier": "degustacao", "user_message": _PID_ULTIMA})
    tool = SimpleNamespace(name="buscar_concorrentes")
    out = gate_degustacao(tool, {"cidade": "Navegantes", "bairro": "Centro"}, ctx)
    assert out is not None
    assert out.get("bloqueado") is True
    assert "concorrência" in (out.get("mensagem") or "").lower() or "mapa" in (
        out.get("mensagem") or ""
    ).lower()


def test_gate_maps_bloqueia_args_que_nao_sao_lugar():
    ctx = SimpleNamespace(
        state={"tier": "degustacao", "user_message": "quantas academias?"}
    )
    tool = SimpleNamespace(name="buscar_concorrentes")
    out = gate_degustacao(
        tool,
        {"cidade": "poderia", "bairro": "vigilancia", "uf": "ME"},
        ctx,
    )
    assert out is not None
    assert out.get("bloqueado") is True


def test_loc_args_validos_inclui_sao_paulo():
    tool = SimpleNamespace(name="buscar_concorrentes")
    ctx = SimpleNamespace(
        state={"tier": "degustacao", "user_message": "quantas academias em Perdizes, São Paulo - SP?"}
    )
    # Antes: "São Paulo" quebrava o gate por causa de token "sao".
    out = gate_degustacao(tool, {"cidade": "São Paulo", "bairro": "Perdizes", "uf": "SP"}, ctx)
    assert out is None


def test_prosa_sem_rag_sanitaria_vira_abstencao():
    checklist = (
        "Mantenha planilhas de temperatura, POPs da RDC 216/2004 e "
        "certificado de pragas no local para a Vigilância."
    )
    texto, autor, acoes = aplicar_gate_grounding_sanitaria(
        _PID_ULTIMA,
        checklist,
        "Mercado",
        [
            {
                "ferramenta": "buscar_concorrentes",
                "resultado": {"total_concorrentes": 12, "query": "academia vigilancia poderia ME"},
            }
        ],
    )
    assert texto == MSG_ABSTENCAO_SANITARIA
    assert "RDC" not in texto
    assert "planilha" not in texto.lower()
    assert autor == "Regulatorio"
    assert acoes == []


def test_prosa_sanitaria_sem_tool_tambem_absteve():
    texto, _autor, acoes = aplicar_gate_grounding_sanitaria(
        "documentações da vigilância sanitaria",
        "- Alvará\n- CNPJ\n- AVCB\n- PMOC",
        "GymSiteSite",
        [],
    )
    assert texto == MSG_ABSTENCAO_SANITARIA
    assert acoes == []


def test_prosa_com_rag_regulatorio_passa():
    rag = {
        "ferramenta": "consultar_base_regulatoria",
        "resultado": {
            "n_docs": 2,
            "texto_rag": "Licença sanitária é municipal; confirme no protocolo local.",
        },
    }
    original = "A licença sanitária é municipal. Confirme no protocolo da prefeitura."
    texto, autor, acoes = aplicar_gate_grounding_sanitaria(
        _PID_ULTIMA,
        original,
        "Regulatorio",
        [rag],
    )
    assert texto == original
    assert autor == "Regulatorio"
    assert acoes == [rag]
