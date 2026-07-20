"""Carimbo legal (P-000 §5 / P-002) — prompts + extração de citações estruturadas.

Formato canônico: valor · base · fonte · janela.
Fonte legal = lei/NBR/resolução + artigo — nunca canal Vertex nem arquivo .txt.
"""
from __future__ import annotations

import json
import re
from typing import Any

CITACOES_TOOL_RESULT_TIPO = "citacoes"

INSTRUCAO_CARIMBO_LEGAL = """
## CARIMBO OBRIGATÓRIO (P-000 §5 / P-002) — lei, NBR, resolução, prazo, anuidade ou exigência
Formato: valor · base · fonte · janela — MAS o middot NÃO vai no corpo da resposta.
No texto narrativo: escreva em português normal (ex.: "O CREF tem até 30 dias para deferir.").
No FINAL, emita JSON (o sistema extrai, remove da tela e mostra o carimbo colorido):
{"citacoes":[{"valor":"...","base":"...","fonte":"...","janela":"..."}]}

Regras da FONTE (campo `fonte` do JSON):
- OBRIGATÓRIO: norma real — Lei nº X/AAAA, Res. CONFEF nº X/AAAA, ABNT NBR X, IT-XX, COE + município.
- PROIBIDO: "Vertex AI Search", nome/slug de arquivo (ex.: regulatorio_anuidades_processo_2026),
  "conforme trecho recuperado", título do documento RAG, canal_retrieval.
- Se o trecho citar a norma (ex.: "Base: Resolução CONFEF nº 477/2023"), USE ESSA norma no campo fonte.
- Sem norma identificável no trecho → NÃO invente carimbo; diga que a base não trouxe a norma e oriente CREF/prefeitura.

Exemplos de JSON válido:
{"citacoes":[{"valor":"30 dias","base":"deferimento registro PJ no CREF","fonte":"Res. CONFEF nº 477/2023","janela":"2023"}]}
{"citacoes":[{"valor":"5 kN/m²","base":"carga de laje academia","fonte":"ABNT NBR 6120","janela":"2019"}]}
{"citacoes":[{"valor":"R$ 1.569,68","base":"anuidade PJ CREF valor-base nacional","fonte":"Res. CONFEF nº 596/2025","janela":"2026"}]}

Exigência municipal (alvará, COE, bombeiros, vigilância): só cite COM município + UF. Sem município → peça cidade/UF ou abstenha.

Só inclua no JSON itens com os 4 campos. `url` opcional — só deep-link real da norma (nunca invente).
""".strip()

_CAMPOS = ("valor", "base", "fonte", "janela")

# middot-carimbo no corpo (com ou sem crases) — removido na sanitização
_INLINE_CARIMBO = re.compile(
    r"`([^`·\n]+?)\s*·\s*([^`·\n]+?)\s*·\s*([^`·\n]+?)\s*·\s*([^`·\n]+?)`"
    r"|([^.\n`·]+?)\s*·\s*([^.\n`·]+?)\s*·\s*([^.\n`·]+?)\s*·\s*([^.\n`·]+?)(?=[.\n]|$)"
)

_FONTE_LEGAL = re.compile(
    r"(?i)\b("
    r"lei(\s+n[ºo°.]?)?|"
    r"res(olu[cç][aã]o)?(\s+n[ºo°.]?)?|"
    r"nbr|"
    r"abnt|"
    r"confef|"
    r"cref\d*|"
    r"it[-\s]?\d|"
    r"coe|"
    r"c[oó]digo\s+de\s+obras|"
    r"decreto"
    r")\b"
)


def _fonte_proibida(fonte: str) -> bool:
    f = fonte.lower().strip()
    if "vertex" in f:
        return True
    if "conforme trecho" in f or "trecho recuperado" in f:
        return True
    if f.endswith(".txt") or "regulatorio_" in f or "obra_" in f:
        return True
    # slug de arquivo RAG (snake_case longo sem norma)
    if "_" in f and not _FONTE_LEGAL.search(f):
        return True
    return False


def _fonte_parece_legal(fonte: str) -> bool:
    return bool(_FONTE_LEGAL.search(fonte))


def validar_citacao(raw: Any) -> dict[str, str] | None:
    """Aceita só citação com 4 campos e fonte = norma legal (não slug/canal)."""
    if not isinstance(raw, dict):
        return None
    out: dict[str, str] = {}
    for k in _CAMPOS:
        v = raw.get(k)
        if not isinstance(v, str) or not v.strip():
            return None
        out[k] = v.strip()
    if _fonte_proibida(out["fonte"]) or not _fonte_parece_legal(out["fonte"]):
        return None
    url = raw.get("url")
    if isinstance(url, str) and url.strip().startswith(("http://", "https://")):
        out["url"] = url.strip()
    return out


def remover_carimbos_inline(texto: str) -> str:
    """Corpo narrativo: tira middot-carimbo (fica só o valor). Stamp vem do JSON."""
    if not texto:
        return texto

    def _repl(m: re.Match[str]) -> str:
        if m.group(1) is not None:
            return m.group(1).strip()
        return (m.group(5) or "").strip()

    return _INLINE_CARIMBO.sub(_repl, texto)


def extrair_citacoes(texto: str) -> tuple[str, list[dict[str, str]]]:
    """Remove JSON `citacoes` do fim; limpa middot inline; devolve só carimbos válidos."""
    if not texto:
        return texto, []
    m = re.search(r"```(?:json)?\s*(\{.*\"citacoes\".*\})\s*```\s*$", texto, re.DOTALL)
    if not m:
        m = re.search(r"(\{\s*\"citacoes\".*\})\s*$", texto, re.DOTALL)
    citacoes: list[dict[str, str]] = []
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict) and isinstance(parsed.get("citacoes"), list):
                citacoes = [c for c in (validar_citacao(x) for x in parsed["citacoes"]) if c]
            texto = texto[: m.start()].rstrip()
        except (json.JSONDecodeError, TypeError):
            citacoes = []
    texto = remover_carimbos_inline(texto)
    return texto, citacoes


def pack_citacoes_tool_results(citacoes: list[dict[str, str]]) -> list[dict] | None:
    if not citacoes:
        return None
    return [{"tipo": CITACOES_TOOL_RESULT_TIPO, "itens": citacoes}]


def unpack_citacoes_from_msg(msg: dict) -> list[dict]:
    """Lê citacoes de campo dedicado ou de tool_results empacotado."""
    direct = msg.get("citacoes")
    if isinstance(direct, list) and direct:
        return [c for c in (validar_citacao(x) for x in direct) if c]
    out: list[dict] = []
    for item in msg.get("tool_results") or []:
        if not isinstance(item, dict):
            continue
        if item.get("tipo") != CITACOES_TOOL_RESULT_TIPO:
            continue
        for raw in item.get("itens") or []:
            c = validar_citacao(raw)
            if c:
                out.append(c)
    return out


def anotar_retrieval_legal(payload: dict, canal: str) -> dict:
    """Vertex = canal; remove rótulo `fonte` que o LLM ecoava como citação."""
    payload.pop("fonte", None)
    payload["canal_retrieval"] = canal
    payload["como_citar"] = (
        "No JSON citacoes.fonte use a NORMA do trecho (ex.: Res. CONFEF nº 477/2023, "
        "Lei nº 9.696/1998, ABNT NBR 6120). PROIBIDO: Vertex, slug/arquivo "
        "(regulatorio_*), 'conforme trecho recuperado', titulo do doc."
    )
    return payload
