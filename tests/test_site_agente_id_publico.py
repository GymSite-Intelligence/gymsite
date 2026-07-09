"""O crachá do especialista: a API fala id público nos DOIS sentidos.

`project_messages.agente` guarda o nome do Agent ADK (`Event.author` — "EngenheiroObra"),
porque é o autor real. Mas o front manda `engenheiro_obra` no POST; devolver o nome ADK no
GET obrigaria o front a manter um segundo mapa (P-008). A tradução vive na fronteira.
"""

from __future__ import annotations

import pytest

from agents_site.catalog import (
    DEGUSTACAO,
    ESPECIALISTAS,
    ROTEADOR_ADK,
    id_publico,
)


@pytest.mark.parametrize("agente_id,nome_adk", sorted(ESPECIALISTAS.items()))
def test_round_trip_do_id_publico(agente_id, nome_adk):
    """O id que o front MANDA é o id que ele RECEBE de volta."""
    assert id_publico(nome_adk) == agente_id


def test_roteador_vira_degustacao():
    """Quando o próprio roteador responde (ex.: pergunta de desambiguação)."""
    assert id_publico(ROTEADOR_ADK) == DEGUSTACAO


def test_sem_autor_nao_acende_cracha():
    """Mensagem do user, ou resposta gravada antes da migration."""
    assert id_publico(None) is None
    assert id_publico("") is None


def test_agente_desconhecido_nao_explode():
    """Agent novo em prod antes do catálogo subir: degrada pra None, não 500."""
    assert id_publico("AgenteQueAindaNaoExiste") is None
