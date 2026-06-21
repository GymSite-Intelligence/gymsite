"""Regressão do gate _eh_academia_tradicional contra os types PT do SearchAPI.

Bug VEC: o gate só reconhecia type EN ("gym"/"fitness_center") do Places API novo.
O caminho barato (SearchAPI engine=google_maps) devolve type em PT ("Academia",
"Sala de fitness") → a inclusão-por-tipo virava código morto e cortava academia
real de nome neutro. Caso-canário: "Parque Estadual do Cocó" (parque) vs "Parque
Esportes" (academia) — nome igual em "Parque", só o type separa.

Offline: testa a função pura, sem rede.
"""
import tools.competitor_tools as ct


def _gate(nome, *tipos):
    return ct._eh_academia_tradicional({"nome": nome, "tipos": list(tipos)})


# ── Academia real com type PT + nome neutro (os falsos-cortes do bug) ──────────

def test_type_pt_academia_nome_neutro_inclui():
    # CT Greenlife / S3 / CF Cangaço: nome sem "academia/fit", type PT "Academia"
    for nome in ("CT Greenlife", "S3 - Treinamento Personalizado", "CF Cangaço"):
        ok, motivo = _gate(nome, "Academia")
        assert ok, f"{nome!r} deveria INCLUIR (type PT Academia), veio: {motivo}"


def test_type_pt_sala_de_fitness_inclui():
    ok, motivo = _gate("TBOX", "Sala de fitness")
    assert ok, motivo


# ── Caso-canário: as duas "Parque*" separadas só pelo type ────────────────────

def test_parque_academia_vs_parque_natural():
    inclui, _ = _gate("Parque Esportes", "Academia")
    corta, motivo = _gate("Parque Estadual do Cocó", "Parque estadual", "Parque ecológico")
    assert inclui, "Parque Esportes (type Academia) deve INCLUIR"
    assert not corta and "parque" in motivo, "Parque Estadual deve CORTAR por type forte"


# ── Ruído de modalidade por type PT ───────────────────────────────────────────

def test_escola_natacao_corta():
    ok, motivo = _gate("Parque Esportes Aqua - Complexo Aquático", "Escola de natação")
    assert not ok and "modalidade" in motivo


def test_pilates_studio_corta():
    ok, motivo = _gate("Instituto Pilates Cocó", "Estúdio de pilates")
    assert not ok and "modalidade" in motivo


# ── Multiesporte: academia COM piscina fica (qualificador + type-gym) ─────────

def test_academia_multiesporte_com_natacao_inclui():
    # VS Club: nome tem "academia/musculação", type Academia → fica mesmo citando natação
    ok, motivo = _gate("Academia VS Club - Musculação, natação", "Academia")
    assert ok, motivo


def test_type_modalidade_mas_com_gym_inclui():
    # se vier "Estúdio de pilates" JUNTO de "Academia", não corta (multiesporte)
    ok, motivo = _gate("EveryLife Studio", "Estúdio de pilates", "Academia")
    assert ok, motivo


# ── Não regrediu: EN do Places novo ainda funciona ────────────────────────────

def test_type_en_gym_ainda_inclui():
    ok, _ = _gate("Some Gym", "gym")
    assert ok


def test_clinica_medica_corta():
    ok, motivo = _gate("Clínica X", "physiotherapist")
    assert not ok and "forte" in motivo
