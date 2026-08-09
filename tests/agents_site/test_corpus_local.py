from agents_site.corpus_local import buscar_corpus_local


def test_corpus_regulatorio_recupera_cref():
    out = buscar_corpus_local("CREF PJ registro academia", dominio="regulatorio", n=3)
    assert out["status"] == "ok"
    assert out["n_docs"] >= 1
    assert out["fonte"].startswith("corpus_local")
    assert any(
        "CREF" in (r.get("trecho") or "").upper() or "CREF" in (r.get("titulo") or "").upper()
        for r in out["resultados"]
    )


def test_corpus_dominio_vazio_status_vazio():
    out = buscar_corpus_local("xyzzy-no-match-qqq", dominio="tecnico", n=2)
    assert out["n_docs"] == 0
    assert out["status"] in ("vazio", "ok")
