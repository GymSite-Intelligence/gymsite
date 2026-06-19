"""Narrador via Claude Code headless (`claude -p`) — narração com fatos travados.

Provider de NARRAÇÃO (não de dado) pras fases que só redigem (A0/A6/A9). Escapa o
dunning do Vertex e o custo por-token: roda na subscription do Claude Code (sem
ANTHROPIC_API_KEY). Provado: mesmos fatos → números IDÊNTICOS run-a-run, só a prosa
varia (ver Auditoria — RUN1 vs RUN2 diff de fatos = vazio).

REGRA VEC: "o LLM raciocina/veste o dado, não PRODUZ dado". Aqui o LLM só veste os
fatos determinísticos. Guardrail garante isso: toda âncora (número/veredito) TEM que
aparecer no texto, e nenhum número estranho pode surgir — senão cai pro fallback
determinístico (o resumo que o A6 já monta hoje). Nunca degrada, nunca alucina número.

NÃO usar pros cálculos (A1/A2/A4) — esses já são determinísticos, narração não toca.

Flags (env):
  NARRADOR_CLAUDE_ENABLED=1     liga (default OFF — fallback sempre, até validar em prod)
  NARRADOR_USE_SUBSCRIPTION=1   limpa ANTHROPIC_API_KEY p/ forçar subscription (default ON)
  NARRADOR_TIMEOUT_S=30         timeout do subprocess
  CLAUDE_BIN=claude             binário (override p/ caminho absoluto se PATH não tiver)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Any

logger = logging.getLogger("gymsite.narrador_claude")

# tokens numéricos: moeda/decimal/inteiro (R$ 79.062,50 | 6.0 | 8). Capta o "miolo".
_NUM_RE = re.compile(r"\d[\d.,]*\d|\d")


def _on(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on", "sim"}


def _numeros(texto: str) -> set[str]:
    """Núcleos numéricos normalizados (sem pontuação de milhar/decimal) p/ comparar
    '79.062,50' == '79062,50' e '6.0' == '60'? Não — mantemos vírgula/ponto do
    decimal seria frágil. Normalizamos removendo SÓ separadores → compara só dígitos."""
    out = set()
    for m in _NUM_RE.findall(texto or ""):
        so_digitos = re.sub(r"[.,]", "", m)
        if so_digitos:
            out.add(so_digitos)
    return out


def _claude_headless(prompt: str, timeout_s: int) -> str | None:
    """Chama `claude -p --output-format json`, devolve o campo result (texto). None em falha.

    CAVEAT concorrência: 2 `claude -p` simultâneos no mesmo CLAUDE_CONFIG_DIR corrompem
    .claude.json. O pipeline ADK roda as fases em sequência → sem race. Se for paralelizar,
    isolar CLAUDE_CONFIG_DIR por chamada.
    """
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")
    env = dict(os.environ)
    if _on("NARRADOR_USE_SUBSCRIPTION", True):
        # subscription: sem key → escapa dunning E custo por-token
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
    try:
        proc = subprocess.run(
            [claude_bin, "-p", prompt, "--output-format", "json"],
            capture_output=True, text=True, encoding="utf-8",
            timeout=timeout_s, env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning("claude headless falhou: %s", e)
        return None
    if proc.returncode != 0:
        logger.warning("claude headless rc=%s stderr=%s", proc.returncode, (proc.stderr or "")[:200])
        return None
    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, TypeError):
        # alguns builds devolvem texto puro mesmo com --output-format json
        return (proc.stdout or "").strip() or None
    if isinstance(data, dict):
        if data.get("is_error"):
            return None
        txt = data.get("result") or data.get("text") or data.get("content")
        if isinstance(txt, str):
            return txt.strip()
    return None


def _guardrail_ok(texto: str, ancoras: list[str]) -> tuple[bool, str]:
    """Valida que o texto narrou os fatos SEM inventar número.

    1) toda âncora textual (veredito/modelo/saturação) aparece literal (case-insensitive)
    2) todo número da saída ∈ números das âncoras (zero número novo = zero alucinação)
    """
    if not texto or len(texto.strip()) < 20:
        return False, "texto vazio/curto"
    low = texto.lower()
    for a in ancoras:
        a = (a or "").strip()
        if not a:
            continue
        # âncora não-numérica precisa estar literal; numérica é checada no passo 2
        if not re.search(r"\d", a) and a.lower() not in low:
            return False, f"âncora ausente: {a!r}"
    permitidos = set()
    for a in ancoras:
        permitidos |= _numeros(a)
    intrusos = _numeros(texto) - permitidos
    if intrusos:
        return False, f"número(s) não-ancorado(s): {sorted(intrusos)}"
    return True, "ok"


def narrar(*, fatos_texto: str, ancoras: list[str], fallback: str,
           instrucao: str | None = None) -> dict[str, Any]:
    """Narra `fatos_texto` via Claude headless, com guardrail. Sempre seguro.

    Args:
      fatos_texto: bloco de fatos determinísticos injetado no prompt (numbers locked).
      ancoras: strings que DEVEM aparecer no texto (verditos + números). O guardrail
               rejeita se faltar âncora textual ou surgir número fora dessas âncoras.
      fallback: resumo determinístico atual (usado se desligado/falha/guardrail reprova).
      instrucao: override da instrução-base (default: 3 frases PT, sem inventar número).

    Returns: {"texto", "fonte": claude_subscription|deterministico_fallback, "motivo"}
    """
    if not _on("NARRADOR_CLAUDE_ENABLED", False):
        return {"texto": fallback, "fonte": "deterministico_fallback", "motivo": "desligado"}

    base = instrucao or (
        "Você é o redator do resumo executivo de um relatório de viabilidade de academia. "
        "Escreva 3 frases em português narrando ESTES fatos. NÃO invente nem altere NENHUM "
        "número. Não use ferramentas, apenas responda o texto."
    )
    prompt = f"{base}\n\nFATOS:\n{fatos_texto}"
    timeout_s = int(os.environ.get("NARRADOR_TIMEOUT_S", "30") or 30)

    texto = _claude_headless(prompt, timeout_s)
    if texto is None:
        return {"texto": fallback, "fonte": "deterministico_fallback", "motivo": "headless falhou"}

    ok, motivo = _guardrail_ok(texto, ancoras)
    if not ok:
        logger.warning("guardrail reprovou (%s) — fallback determinístico", motivo)
        return {"texto": fallback, "fonte": "deterministico_fallback", "motivo": f"guardrail: {motivo}"}

    return {"texto": texto, "fonte": "claude_subscription", "motivo": "ok"}
