"""Regressão do gate de tipo (bug Cocó 4b211a02): parque estadual e arena de beach
passavam como concorrentes de academia por só existir blocklist de especialidades.
Valida o gate positivo (_FITNESS_NOME_KW / _FITNESS_TYPES) sem derrubar legítimos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.competitor_tools import _tipo_relevante, filtrar_concorrentes_bairro_tipo


def _c(nome, tipos=None, endereco="R. X - Cocó, Fortaleza"):
    return {"nome": nome, "tipos": tipos or [], "endereco": endereco}


def test_parque_estadual_fora():
    assert not _tipo_relevante(_c("Parque Estadual do Cocó", ["park", "tourist_attraction"]), "academia")


def test_arena_beach_fora_mesmo_sem_tipos():
    assert not _tipo_relevante(_c("ARENA COCÓ BEACH"), "academia")


def test_academia_legitima_por_tipo():
    assert _tipo_relevante(_c("Academia Smart Fit - Papicu", ["gym"]), "academia")


def test_parque_esportes_legitimo_sem_tipos():
    assert _tipo_relevante(_c("Parque Esportes"), "academia")


def test_especializada_continua_fora():
    assert not _tipo_relevante(_c("Eikō Artes Marciais", ["gym"]), "academia")
    assert not _tipo_relevante(_c("Academia de Boxe Cocó"), "academia")
    assert not _tipo_relevante(_c("Checkmat Bessa", ["gym"]), "academia")
    assert not _tipo_relevante(_c("Academia de Cordel do Vale", ["gym"]), "academia")
    assert not _tipo_relevante(_c("DoctorFit João Pessoa – Bessa", ["gym"]), "academia")
    assert not _tipo_relevante(_c("BOXDELAS – Academia para mulheres", ["gym"]), "academia")


def test_filtro_integrado_caso_coco():
    candidatos = [
        _c("Academia Smart Fit - Papicu", ["gym"]),
        _c("Parque Esportes", ["gym"]),
        _c("Academia VS Club - cocó/ Musculação", ["gym"]),
        _c("Parque Estadual do Cocó", ["park", "tourist_attraction"]),
        _c("ARENA COCÓ BEACH", []),
        _c("Eikō Artes Marciais", ["gym"]),
    ]
    out = filtrar_concorrentes_bairro_tipo(candidatos, bairro="Cocó", tipo_negocio="academia")
    nomes = {c["nome"] for c in out}
    assert "Parque Estadual do Cocó" not in nomes
    assert "ARENA COCÓ BEACH" not in nomes
    assert "Eikō Artes Marciais" not in nomes
    assert {"Academia Smart Fit - Papicu", "Parque Esportes",
            "Academia VS Club - cocó/ Musculação"} <= nomes


def test_salvaguarda_nao_zera_lista():
    candidatos = [_c("Parque Estadual do Cocó", ["park"]), _c("ARENA COCÓ BEACH", [])]
    out = filtrar_concorrentes_bairro_tipo(candidatos, bairro="Cocó", tipo_negocio="academia")
    assert len(out) == 2


def test_searchapi_tipo_pt_sem_injecao_gym():
    assert _tipo_relevante(_c("Onda Cocó", ["Academia"]), "academia")
    assert _tipo_relevante(_c("Corpo em Forma", ["Academia de ginástica"]), "academia")


def test_searchapi_tipo_pt_nao_fitness_fora():
    assert not _tipo_relevante(_c("Parque Estadual do Cocó", ["Parque estadual"]), "academia")
    assert not _tipo_relevante(_c("ARENA COCÓ BEACH", ["Quadra de beach tennis"]), "academia")
