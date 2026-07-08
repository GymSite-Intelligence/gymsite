"""Tasks do run 3f4e0b82: (a) lookup do MRLR imune a acento ('Coco' → 'Cocó' via
bairro_norm — o miss derrubava o aluguel determinístico e o fallback de portal
saltava 60→170/m²); (b) categoria interna (atendimento_ruim) nunca vaza pro texto."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.aluguel_mrlr import aluguel_deterministico


def _sb_mock(renda_rows_por_filtro):
    """Supabase fake: .table('renda_bairro')... — 1ª query usa eq(bairro_norm),
    fallback usa ilike(bairro). municipio_pib devolve dado válido."""
    sb = MagicMock()

    class _Q:
        def __init__(self, table):
            self.table = table
            self.filtros = {}

        def select(self, *_): return self
        def limit(self, *_): return self

        def ilike(self, col, val):
            self.filtros[f"ilike:{col}"] = val
            return self

        def eq(self, col, val):
            self.filtros[f"eq:{col}"] = val
            return self

        def execute(self):
            r = MagicMock()
            if self.table == "renda_bairro":
                if "eq:bairro_norm" in self.filtros:
                    r.data = renda_rows_por_filtro.get("norm") or []
                else:
                    r.data = renda_rows_por_filtro.get("ilike") or []
            else:  # municipio_pib
                r.data = [{"populacao": 2400000, "pib_reais": 73000000000.0,
                           "pib_per_capita": 30000.0}]
            return r

    sb.table.side_effect = lambda t: _Q(t)
    return sb


def test_coco_sem_acento_resolve_via_bairro_norm(monkeypatch):
    import tools.aluguel_mrlr as m
    monkeypatch.setattr(m, "_sb", lambda: _sb_mock({
        "norm": [{"municipio_cod": "2304400", "percentil_municipio": 0.99}],
        "ilike": [],
    }))
    out = aluguel_deterministico(area_m2=900, cidade="Fortaleza", bairro="Coco")
    assert out["status"] == "ok", out
    assert out["inputs"]["renda_percentil"] == 0.99
    assert "MRLR" in out["fonte"]


def test_fallback_ilike_quando_norm_nao_acha(monkeypatch):
    import tools.aluguel_mrlr as m
    monkeypatch.setattr(m, "_sb", lambda: _sb_mock({
        "norm": [],
        "ilike": [{"municipio_cod": "2304400", "percentil_municipio": 0.5}],
    }))
    out = aluguel_deterministico(area_m2=900, cidade="Fortaleza", bairro="Cocó")
    assert out["status"] == "ok", out


def test_texto_posicionamento_sem_underscore():
    """Guarda de fonte: as frases do posicionamento passam pelo humanizador
    (categoria interna tipo atendimento_ruim nunca chega crua ao cliente)."""
    import inspect

    import agents.a3b_competitor_analysis as a3b
    src = inspect.getsource(a3b)
    assert "_humano(top_dor)" in src
    assert "_humano(top_opp)" in src
    assert "_humano(top_serv)" in src
