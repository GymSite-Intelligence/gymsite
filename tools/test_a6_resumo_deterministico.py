"""Testes determinísticos para _resumo_executivo_deterministico (A6).

Coberturas:
  (a) candidato NO bairro alvo é nomeado no texto
  (b) candidato de bairro adjacente NÃO é nomeado → frase "nenhum imóvel in-spec"
  (c) saturação sempre do BAIRRO (n concorrentes), nunca "raio 3km"
  (d) modelo + payback + margem aparecem no texto
  (e) linha de zoneamento quando dict presente
"""
from agents.a6_report_consolidator import _resumo_executivo_deterministico

# ── Fixtures reutilizáveis ──────────────────────────────────────────────────

_CENARIOS_BASE = {
    "premium": {
        "modelo": "premium",
        "payback_meses": 18,
        "margem_liquida_pct": 22,
    },
}

_TOP3_NO_BAIRRO = [
    {
        "bairro": "Cocó",
        "endereco": "Av. Desembargador Moreira, 456 - Cocó, Fortaleza",
        "area_m2": 350,
        "titulo": "Galpão comercial no Cocó",
    },
]

_TOP3_BAIRRO_ADJACENTE = [
    {
        "bairro": "Meireles",
        "endereco": "Av. Beira Mar, 100 - Meireles, Fortaleza",
        "area_m2": 280,
        "titulo": "Sala comercial no Meireles",
    },
]


# ── (a) Candidato NO bairro é nomeado ─────────────────────────────────────

def test_candidato_no_bairro_e_nomeado():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Cocó",
        veredito="APROVADO",
        modelo_recomendado="premium",
        cenarios=_CENARIOS_BASE,
        nivel_saturacao="MODERADO",
        total_concorrentes=3,
        top_3=_TOP3_NO_BAIRRO,
        zoneamento=None,
    )
    # Candidato nomeado pelo endereço/título (primeiros 90 chars)
    assert "Av. Desembargador" in texto or "Cocó" in texto
    # Frase de "nenhum imóvel" NÃO deve aparecer
    assert "Nenhum imóvel" not in texto


# ── (b) Candidato de bairro adjacente NÃO é nomeado ──────────────────────

def test_candidato_fora_bairro_nao_e_nomeado():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Cocó",
        veredito="INVESTIGAR",
        modelo_recomendado="premium",
        cenarios=_CENARIOS_BASE,
        nivel_saturacao="BAIXO",
        total_concorrentes=1,
        top_3=_TOP3_BAIRRO_ADJACENTE,
        zoneamento=None,
    )
    # Não deve mencionar o candidato do Meireles como prioritário
    assert "Beira Mar" not in texto
    assert "Meireles" not in texto or "Nenhum imóvel" in texto
    # Deve cair na frase de fallback
    assert "Nenhum imóvel" in texto


# ── (c) Saturação sempre do bairro (n concorrentes), nunca "raio 3km" ─────

def test_saturacao_menciona_praca_canonica():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Maraponga",
        veredito="REPROVADO",
        modelo_recomendado="",
        cenarios={},
        nivel_saturacao="SATURADO",
        total_concorrentes=7,
        top_3=[],
        zoneamento=None,
    )
    assert "7 concorrentes" in texto
    assert "raio 1 km" in texto.lower()
    assert "3km" not in texto.lower()
    assert "3 km" not in texto.lower()
    assert "SATURADO" in texto


def test_saturacao_singular_quando_um_concorrente():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Papicu",
        veredito="APROVADO",
        modelo_recomendado="",
        cenarios={},
        nivel_saturacao="BAIXO",
        total_concorrentes=1,
        top_3=[],
        zoneamento=None,
    )
    assert "1 concorrente analisado na praça" in texto


# ── (d) Modelo + payback + margem aparecem no texto ───────────────────────

def test_modelo_payback_margem_no_texto():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Cocó",
        veredito="APROVADO",
        modelo_recomendado="premium",
        cenarios=_CENARIOS_BASE,
        nivel_saturacao="BAIXO",
        total_concorrentes=2,
        top_3=[],
        zoneamento=None,
    )
    assert "premium" in texto
    assert "payback 18 meses" in texto
    assert "margem 22%" in texto


def test_modelo_sem_cenario_nao_quebra():
    """Modelo recomendado sem entrada nos cenários → sem payback/margem, sem exceção."""
    texto = _resumo_executivo_deterministico(
        cidade="Recife",
        bairro="Boa Viagem",
        veredito="APROVADO",
        modelo_recomendado="low-cost",
        cenarios={},          # cenários vazios — modelo não encontrado
        nivel_saturacao="MODERADO",
        total_concorrentes=4,
        top_3=[],
        zoneamento=None,
    )
    # Não quebra e ainda contém o modelo e o veredito
    assert "low-cost" in texto
    assert "APROVADO" in texto
    # payback/margem não aparecem quando cenário não encontrado
    assert "payback" not in texto
    assert "margem" not in texto


# ── (e) Zoneamento line quando dict presente ──────────────────────────────

def test_zoneamento_dict_gera_linha():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Cocó",
        veredito="APROVADO",
        modelo_recomendado="",
        cenarios={},
        nivel_saturacao="BAIXO",
        total_concorrentes=2,
        top_3=[],
        zoneamento={"zona_sigla": "ZR-2", "compatibilidade": "PERMISSIVO"},
    )
    assert "ZR-2" in texto
    assert "permitida" in texto


def test_zoneamento_condicionado():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Aldeota",
        veredito="INVESTIGAR",
        modelo_recomendado="",
        cenarios={},
        nivel_saturacao="MODERADO",
        total_concorrentes=3,
        top_3=[],
        zoneamento={"zona_sigla": "ZI-1", "compatibilidade": "CONDICIONADO"},
    )
    assert "ZI-1" in texto
    assert "condicionada" in texto


def test_zoneamento_restrito():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Centro",
        veredito="REPROVADO",
        modelo_recomendado="",
        cenarios={},
        nivel_saturacao="SATURADO",
        total_concorrentes=5,
        top_3=[],
        zoneamento={"zona_sigla": "ZP-1", "compatibilidade": "RESTRITO"},
    )
    assert "ZP-1" in texto
    assert "vedada" in texto or "restrita" in texto


def test_zoneamento_none_nao_gera_linha():
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Meireles",
        veredito="APROVADO",
        modelo_recomendado="",
        cenarios={},
        nivel_saturacao="BAIXO",
        total_concorrentes=0,
        top_3=[],
        zoneamento=None,
    )
    assert "Zoneamento" not in texto


def test_zoneamento_sem_compatibilidade_nao_gera_linha():
    """Dict sem 'compatibilidade' → não renderiza a linha (requer ambos sig + comp)."""
    texto = _resumo_executivo_deterministico(
        cidade="Fortaleza",
        bairro="Meireles",
        veredito="APROVADO",
        modelo_recomendado="",
        cenarios={},
        nivel_saturacao="BAIXO",
        total_concorrentes=0,
        top_3=[],
        zoneamento={"zona_sigla": "ZR-1"},   # sem compatibilidade
    )
    assert "Zoneamento" not in texto
