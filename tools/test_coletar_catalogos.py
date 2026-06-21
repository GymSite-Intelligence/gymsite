"""Coletor de catálogos — helpers puros (`_slug`, filtro de PDFs em `buscar_pdfs`)."""
import tools.coletar_catalogos_fornecedores as cc


def test_slug():
    assert cc._slug("Righetto Fitness") == "righetto-fitness"
    assert cc._slug("Kikos Pro / Life") == "kikos-pro-life"
    assert cc._slug("Físicus AÇÃO") == "fisicus-acao"
    assert cc._slug("") == "doc"


def test_buscar_pdfs_filtra_so_pdf_e_dedupa(monkeypatch):
    class _Resp:
        def raise_for_status(self): pass
        def json(self):
            return {"organic_results": [
                {"title": "Catálogo 2025", "link": "https://x.com/cat.pdf"},
                {"title": "Página", "link": "https://x.com/produtos"},          # não-pdf → fora
                {"title": "Dup", "link": "https://x.com/cat.pdf"},              # dup → fora
                {"title": "Outro", "link": "https://y.com/manual.PDF"},        # .PDF maiúsculo → entra
            ]}

    monkeypatch.setattr(cc.httpx, "get", lambda *a, **k: _Resp())
    achados = cc.buscar_pdfs("Fornecedor X", n=10, key="fake")
    urls = [a["url"] for a in achados]
    assert urls == ["https://x.com/cat.pdf", "https://y.com/manual.PDF"]


def test_buscar_pdfs_respeita_n(monkeypatch):
    class _Resp:
        def raise_for_status(self): pass
        def json(self):
            return {"organic_results": [{"title": str(i), "link": f"https://x.com/{i}.pdf"}
                                        for i in range(10)]}

    monkeypatch.setattr(cc.httpx, "get", lambda *a, **k: _Resp())
    assert len(cc.buscar_pdfs("X", n=3, key="fake")) == 3


def test_buscar_pdfs_erro_degrada(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("timeout")

    monkeypatch.setattr(cc.httpx, "get", _boom)
    assert cc.buscar_pdfs("X", n=3, key="fake") == []
