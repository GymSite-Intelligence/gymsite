"""Testes do narrador Claude headless — guardrail anti-alucinação + fallback seguro.

Não chama `claude` de verdade (determinístico/offline): mocka `_claude_headless`.
O ponto é provar que número estranho/âncora faltante → fallback determinístico.
"""
from decimal import Decimal

import tools.narrador_claude as nc

# âncoras = todo número que pode aparecer legitimamente, INCLUSIVE a escala "10" (de 10)
ANCORAS = ["APROVADO COM RESSALVAS", "Mid Market", "ALTO", "8", "6.0", "10", "79.062,50"]
FATOS = ("- veredito: APROVADO COM RESSALVAS\n- modelo: Mid Market\n- saturação: ALTO\n"
         "- concorrentes: 8\n- score: 6.0\n- aluguel: R$ 79.062,50")
FALLBACK = "Resumo determinístico de reserva."


def _texto_bom():
    return ("Cocó recebeu veredito APROVADO COM RESSALVAS para o modelo Mid Market, "
            "score 6.0 de 10. Saturação ALTO com 8 concorrentes. Aluguel R$ 79.062,50.")


# ---------- _numeros (valor decimal) ----------

def test_numeros_valor_decimal():
    assert nc._numeros("R$ 79.062,50") == {Decimal("79062.50")}
    assert nc._numeros("6.0") == {Decimal("6.0")}
    assert Decimal("8") in nc._numeros("8 concorrentes")


def test_numeros_6_0_distinto_de_60():
    # o bug antigo: ambos viravam '60'. Agora 6.0 != 60 por valor.
    assert nc._numeros("6.0") != nc._numeros("60")
    assert Decimal("60") not in nc._numeros("6.0")


def test_guardrail_rejeita_colisao_decimal():
    # âncora score 6.0 / escala 10; LLM alucina "60 concorrentes" → DEVE reprovar
    t = "Score 6.0 de 10, mas projetamos 60 concorrentes na praça."
    ok, motivo = nc._guardrail_ok(t, ["6.0", "10"])
    assert not ok and "não-ancorado" in motivo


# ---------- guardrail ----------

def test_guardrail_aprova_texto_fiel():
    ok, motivo = nc._guardrail_ok(_texto_bom(), ANCORAS)
    assert ok, motivo


def test_guardrail_reprova_ancora_textual_faltante():
    # tira "Mid Market" do texto
    t = _texto_bom().replace("Mid Market", "um modelo")
    ok, motivo = nc._guardrail_ok(t, ANCORAS)
    assert not ok and "ausente" in motivo


def test_guardrail_reprova_numero_inventado():
    # LLM alucina "12 concorrentes" / "R$ 95.000"
    t = _texto_bom() + " Estimamos ainda 12 unidades e custo de R$ 95.000."
    ok, motivo = nc._guardrail_ok(t, ANCORAS)
    assert not ok and "não-ancorado" in motivo


def test_guardrail_reprova_texto_vazio():
    ok, _ = nc._guardrail_ok("", ANCORAS)
    assert not ok


# ---------- narrar (fluxo completo, headless mockado) ----------

def test_narrar_desligado_usa_fallback(monkeypatch):
    monkeypatch.delenv("NARRADOR_CLAUDE_ENABLED", raising=False)
    r = nc.narrar(fatos_texto=FATOS, ancoras=ANCORAS, fallback=FALLBACK)
    assert r["fonte"] == "deterministico_fallback" and r["texto"] == FALLBACK


def test_narrar_ligado_texto_fiel_usa_claude(monkeypatch):
    monkeypatch.setenv("NARRADOR_CLAUDE_ENABLED", "1")
    monkeypatch.setattr(nc, "_claude_headless", lambda *a, **k: _texto_bom())
    r = nc.narrar(fatos_texto=FATOS, ancoras=ANCORAS, fallback=FALLBACK)
    assert r["fonte"] == "claude_subscription"
    assert "APROVADO COM RESSALVAS" in r["texto"]


def test_narrar_ligado_alucinacao_cai_no_fallback(monkeypatch):
    monkeypatch.setenv("NARRADOR_CLAUDE_ENABLED", "1")
    ruim = _texto_bom() + " Projetamos 999 alunos."
    monkeypatch.setattr(nc, "_claude_headless", lambda *a, **k: ruim)
    r = nc.narrar(fatos_texto=FATOS, ancoras=ANCORAS, fallback=FALLBACK)
    assert r["fonte"] == "deterministico_fallback" and "guardrail" in r["motivo"]


def test_narrar_ligado_headless_falha_cai_no_fallback(monkeypatch):
    monkeypatch.setenv("NARRADOR_CLAUDE_ENABLED", "1")
    monkeypatch.setattr(nc, "_claude_headless", lambda *a, **k: None)
    r = nc.narrar(fatos_texto=FATOS, ancoras=ANCORAS, fallback=FALLBACK)
    assert r["fonte"] == "deterministico_fallback" and r["texto"] == FALLBACK


def test_narrar_ligado_expansao_excessiva_cai_no_fallback(monkeypatch):
    # texto fiel aos números mas longo demais (>3x fallback) → guarda anti-prosa-nova
    monkeypatch.setenv("NARRADOR_CLAUDE_ENABLED", "1")
    longo = (_texto_bom() + " ") * 4
    monkeypatch.setattr(nc, "_claude_headless", lambda *a, **k: longo)
    r = nc.narrar(fatos_texto=FATOS, ancoras=ANCORAS, fallback=FALLBACK)
    assert r["fonte"] == "deterministico_fallback" and "expansao" in r["motivo"]
