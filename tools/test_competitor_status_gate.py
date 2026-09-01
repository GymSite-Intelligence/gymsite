"""Testes determinísticos para filtrar_concorrentes_bairro_tipo — gate de STATUS.

Coberturas:
  - CLOSED_PERMANENTLY é dropado
  - OPERATIONAL é mantido
  - status vazio/desconhecido é mantido
  - salvaguarda: se ZERO operacionais sobrariam, não dropa nenhum fechado
"""
from tools.competitor_tools import filtrar_concorrentes_bairro_tipo


def _academia(nome: str, status: str = "", bairro_no_nome: bool = True) -> dict:
    """Cria academia minimal para o gate de status. Por padrão inclui 'Cocó'
    no endereço para passar o filtro de bairro sem interferir nos asserts de status."""
    endereco = "Av. Engenheiro Santana Jr., 1 - Cocó, Fortaleza" if bairro_no_nome else "Av. X, 1"
    return {
        "nome": f"Academia {nome}" + (" Cocó" if bairro_no_nome else ""),
        "endereco": endereco,
        "status": status,
        "tipos": ["gym", "fitness_center"],
        "rating": 4.0,
        "num_avaliacoes": 100,
    }


# ── CLOSED_PERMANENTLY é dropado ──────────────────────────────────────────

def test_closed_permanently_e_dropado():
    fechada = _academia("Fechada", status="CLOSED_PERMANENTLY")
    operacional = _academia("Aberta", status="OPERATIONAL")

    resultado = filtrar_concorrentes_bairro_tipo(
        [operacional, fechada],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    nomes = [c["nome"] for c in resultado]
    assert "Academia Fechada Cocó" not in nomes
    assert "Academia Aberta Cocó" in nomes


def test_closed_temporarily_e_dropado():
    """CLOSED_TEMPORARILY também deve ser filtrado (contém 'CLOSED')."""
    temp = _academia("TempFechada", status="CLOSED_TEMPORARILY")
    op = _academia("Aberta", status="OPERATIONAL")

    resultado = filtrar_concorrentes_bairro_tipo(
        [op, temp],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    nomes = [c["nome"] for c in resultado]
    assert "Academia TempFechada Cocó" not in nomes
    assert "Academia Aberta Cocó" in nomes


# ── OPERATIONAL é mantido ─────────────────────────────────────────────────

def test_operational_e_mantido():
    op = _academia("SmartFit", status="OPERATIONAL")

    resultado = filtrar_concorrentes_bairro_tipo(
        [op],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    assert len(resultado) >= 1
    assert any("SmartFit" in c["nome"] for c in resultado)


# ── status vazio/desconhecido é mantido ───────────────────────────────────

def test_status_vazio_e_mantido():
    """Places às vezes não informa businessStatus — não deve dropar."""
    sem_status = _academia("SemStatus", status="")

    resultado = filtrar_concorrentes_bairro_tipo(
        [sem_status],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    assert len(resultado) >= 1


def test_status_desconhecido_e_mantido():
    """Status fora do vocabulário → mantido (não é CLOSED)."""
    desconhecido = _academia("Desconhecido", status="UNKNOWN_STATUS_XYZ")

    resultado = filtrar_concorrentes_bairro_tipo(
        [desconhecido],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    assert len(resultado) >= 1


def test_business_status_field_alternativo():
    """Aceita campo 'business_status' (variação do Places API)."""
    c = {
        "nome": "Academia AltField Cocó",
        "endereco": "Rua X, 1 - Cocó, Fortaleza",
        "business_status": "CLOSED_PERMANENTLY",
        "tipos": ["gym"],
    }
    op = _academia("Operacional", status="OPERATIONAL")

    resultado = filtrar_concorrentes_bairro_tipo(
        [op, c],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    nomes = [r["nome"] for r in resultado]
    assert "Academia AltField Cocó" not in nomes


# ── Salvaguarda: não dropa se sobrariam zero operacionais ─────────────────

def test_salvaguarda_nao_dropa_se_zero_operacionais():
    """Se TODOS os concorrentes estão fechados, salvaguarda mantém a lista inteira."""
    f1 = _academia("Fechada1", status="CLOSED_PERMANENTLY")
    f2 = _academia("Fechada2", status="CLOSED_PERMANENTLY")

    resultado = filtrar_concorrentes_bairro_tipo(
        [f1, f2],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    # Salvaguarda: com zero operacionais, lista original é preservada
    # (lógica: `if fechadas and operacionais:` — sem operacionais, não dropa)
    assert len(resultado) >= 2


def test_salvaguarda_um_operacional_e_um_fechado():
    """1 operacional + 1 fechado → fechado dropado, operacional mantido."""
    op = _academia("Op", status="OPERATIONAL")
    cl = _academia("Closed", status="CLOSED_PERMANENTLY")

    resultado = filtrar_concorrentes_bairro_tipo(
        [op, cl],
        bairro="Cocó",
        tipo_negocio="academia",
    )

    nomes = [r["nome"] for r in resultado]
    assert "Academia Op Cocó" in nomes
    assert "Academia Closed Cocó" not in nomes


def test_lista_vazia_retorna_vazia():
    resultado = filtrar_concorrentes_bairro_tipo(
        [],
        bairro="Cocó",
        tipo_negocio="academia",
    )
    assert resultado == []


def test_gate_tipo_dropa_cf_tbox_parque_esportes():
    """Academia tradicional: CF*/TBOX/Parque Esportes não contam no N do bairro."""
    base = [
        {"nome": "Academia Uniq Club", "tipos": ["gym"], "status": "OPERATIONAL"},
        {"nome": "CF Cangaço", "tipos": ["gym"], "status": "OPERATIONAL"},
        {"nome": "TBOX", "tipos": ["gym"], "status": "OPERATIONAL"},
        {"nome": "Parque Esportes", "tipos": ["gym"], "status": "OPERATIONAL"},
        {"nome": "CT Greenlife", "tipos": ["gym"], "status": "OPERATIONAL"},
    ]
    out = filtrar_concorrentes_bairro_tipo(
        base, bairro="Cocó", tipo_negocio="academia"
    )
    nomes = {c["nome"] for c in out}
    assert "Academia Uniq Club" in nomes
    assert "CT Greenlife" in nomes
    assert "CF Cangaço" not in nomes
    assert "TBOX" not in nomes
    assert "Parque Esportes" not in nomes
