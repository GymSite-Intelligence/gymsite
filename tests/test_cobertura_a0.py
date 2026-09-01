"""
Valida _build_cobertura_redes_a0 do A6.

Casos:
1. A3a emitiu redes_a0_nao_encontradas explicitamente (caso Eusébio)
2. Fallback: A3a antigo não emite, deduz a partir de inteligencia_competitiva
3. Tudo vazio (market_context sem redes do DR)

Eram asserções no corpo do módulo: o pytest as executava na COLETA, então uma
falha aqui abortava a coleta do repositório inteiro. Como `def test_`, a falha
fica contida neste arquivo.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "gymsite_intelligence" / ".env")

# Importa só o helper (não dispara o agent)
sys.path.insert(0, str(Path(__file__).parent))
from agents.a6_report_consolidator import _build_cobertura_redes_a0

_REDES_DR = {
    "principais_redes_concorrentes": [
        "Smart Fit", "Greenlife", "Selfit", "Dumbbells", "Porão Academia",
    ]
}


def test_a3a_moderno_emite_redes_nao_encontradas():
    """Geo-fence ativo: A3a entrega as listas prontas."""
    competitor_search = {
        "redes_a0_cobertas": ["Smart Fit", "Greenlife"],
        "redes_a0_nao_encontradas": ["Selfit", "Dumbbells", "Porão Academia"],
        "concorrentes_excluidos": [
            {"nome": "Clínica Pilates Reformer X", "motivo": "clinica_fisio"},
        ],
    }
    result = _build_cobertura_redes_a0(competitor_search, _REDES_DR, {})

    assert result["tem_redes_fantasma"] is True
    assert "Selfit" in result["redes_nao_encontradas"]
    assert "Smart Fit" in result["redes_cobertas"]
    assert len(result["concorrentes_excluidos"]) == 1


def test_a3a_legado_deduz_de_inteligencia_competitiva():
    """Sem os campos explícitos, deriva a cobertura do A3b."""
    inteligencia_competitiva = {
        "concorrentes_detalhados": [
            {"nome": "Smart Fit - Shopping Eusébio", "rating_geral": 3.9},
            {"nome": "Greenlife - Eusébio", "rating_geral": 4.4},
        ]
    }
    result = _build_cobertura_redes_a0({}, _REDES_DR, inteligencia_competitiva)

    assert "Smart Fit" in result["redes_cobertas"]
    assert "Selfit" in result["redes_nao_encontradas"]


def test_sem_redes_do_deep_research():
    result = _build_cobertura_redes_a0({}, {}, {})

    assert result["redes_solicitadas"] == []
    assert result["tem_redes_fantasma"] is False
