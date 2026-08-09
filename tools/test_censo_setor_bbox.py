"""TDD: censo_setor por bbox do polígono (não limit cego do município)."""


def test_carregar_setores_bbox_pagina(monkeypatch):
    """Simula PostgREST page=1000: sem bbox pegaria página truncada; com bbox usa filtros."""
    from tools import censo_setor_tools as m

    calls = []

    class FakeQ:
        def __init__(self):
            self.filters = {}
            self._range = None

        def select(self, *_a, **_k):
            return self

        def eq(self, k, v):
            self.filters[k] = v
            return self

        def gte(self, k, v):
            self.filters[f"gte_{k}"] = v
            return self

        def lte(self, k, v):
            self.filters[f"lte_{k}"] = v
            return self

        def range(self, a, b):
            self._range = (a, b)
            return self

        def execute(self):
            calls.append(dict(self.filters, range=self._range))
            # Uma página com 2 setores dentro do bbox pedido
            return type("R", (), {"data": [
                {"lat": -3.747, "lng": -38.482, "pessoas": 100},
                {"lat": -3.748, "lng": -38.483, "pessoas": 50},
            ]})()

    class FakeTable:
        def select(self, *a, **k):
            return FakeQ().select(*a, **k)

    class FakeSB:
        def table(self, _name):
            return FakeTable()

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(
        "tools.supabase_client.load_create_client",
        lambda: (lambda *_a, **_k: FakeSB()),
    )

    ring = [(-38.50, -3.76), (-38.46, -3.76), (-38.46, -3.73), (-38.50, -3.73), (-38.50, -3.76)]
    rows = m.carregar_setores_censo("2304400", ring=ring)
    assert len(rows) == 2
    assert calls, "deve ter batido no Supabase"
    assert "gte_lat" in calls[0] and "lte_lat" in calls[0]
    assert "gte_lng" in calls[0] and "lte_lng" in calls[0]


def test_carregar_setores_injecao_rows():
    from tools.censo_setor_tools import carregar_setores_censo

    rows = [{"lat": 1, "lng": 2, "pessoas": 9}]
    assert carregar_setores_censo("2304400", _rows=rows) == rows
