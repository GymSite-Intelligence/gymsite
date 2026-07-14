"""Parse e resolução de localização no chat de degustação (site-agent).

Prioridade: hint JSON explícito → bloco [contexto_localizacao:…] → regex na mensagem
→ localização já persistida no projeto. Matching accent-insensitive via fold_texto.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from tools.bairro_normalize import fold_texto, formatar_bairro_exibicao

_UFS = frozenset({
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
})

_TIPO_KW: tuple[tuple[str, str], ...] = (
    ("crossfit", "crossfit"),
    ("pilates", "studio_pilates"),
    ("funcional", "studio_funcional"),
    ("academia", "academia"),
    ("academias", "academia"),
    ("gym", "academia"),
)

_CONTEXTO_RE = re.compile(
    r"\[contexto_localizacao:\s*([^\]]+)\]",
    re.IGNORECASE,
)

# Parangaba, Fortaleza - CE | Parangaba, Fortaleza, CE
_VIRGULA_UF_RE = re.compile(
    r"^\s*([^,;\n]+?)\s*,\s*([^,;\n\-]+?)\s*[,-]?\s*([A-Za-z]{2})\s*[\?\.]?\s*$",
    re.IGNORECASE,
)
# Parangabá Fortaleza CE (três tokens, UF no fim)
_TRES_TOKENS_UF_RE = re.compile(
    r"^\s*(.+?)\s+(\S+)\s+([A-Za-z]{2})\s*[\?\.]?\s*$",
)


@dataclass
class LocalizacaoResolvida:
    bairro: str = ""
    cidade: str = ""
    uf: str = ""
    tipo_negocio: str = ""
    origem: str = ""  # hint_json | contexto | mensagem | previa | ""
    confirme: bool = False
    completa: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if self.bairro:
            out["bairro"] = self.bairro
        if self.cidade:
            out["cidade"] = self.cidade
        if self.uf:
            out["uf"] = self.uf
        if self.tipo_negocio:
            out["tipo_negocio"] = self.tipo_negocio
        return out


def _title_loc(s: str) -> str:
    return formatar_bairro_exibicao((s or "").strip())


def _norm_uf(uf: str | None) -> str:
    u = (uf or "").strip().upper()
    return u if u in _UFS else ""


def _parse_kv_blob(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in re.split(r"[;|]", blob):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        key = fold_texto(k).replace(" ", "_")
        val = v.strip().strip("\"'")
        if key and val:
            out[key] = val
    return out


def extrair_bloco_contexto(mensagem: str) -> tuple[str, dict[str, str]]:
    """Remove [contexto_localizacao:…] da mensagem e devolve (msg_limpa, kv)."""
    msg = mensagem or ""
    m = _CONTEXTO_RE.search(msg)
    if not m:
        return msg, {}
    kv = _parse_kv_blob(m.group(1))
    limpa = (_CONTEXTO_RE.sub("", msg)).strip()
    return limpa, kv


def inferir_tipo_negocio(mensagem: str) -> str:
    folded = fold_texto(mensagem)
    for kw, tipo in _TIPO_KW:
        if fold_texto(kw) in folded:
            return tipo
    return ""


def _from_parts(
    bairro: str,
    cidade: str,
    uf: str = "",
    *,
    tipo: str = "",
    origem: str,
) -> LocalizacaoResolvida:
    b = _title_loc(bairro)
    c = _title_loc(cidade)
    u = _norm_uf(uf)
    completa = bool(b and c)
    return LocalizacaoResolvida(
        bairro=b,
        cidade=c,
        uf=u,
        tipo_negocio=tipo,
        origem=origem,
        confirme=False,
        completa=completa,
    )


def parse_localizacao_mensagem(mensagem: str) -> LocalizacaoResolvida:
    """Extrai bairro/cidade/UF de frases comuns (accent-insensitive nas comparações)."""
    msg = (mensagem or "").strip()
    if not msg:
        return LocalizacaoResolvida()

    tipo = inferir_tipo_negocio(msg)

    m = re.search(r"\bbairro\s+(.+?)\s+em\s+(.+)", msg, re.IGNORECASE)
    if m:
        bairro = m.group(1).strip(" ,;")
        rest = m.group(2).strip().rstrip("?!.")
        tokens = rest.split()
        uf = ""
        if tokens and _norm_uf(tokens[-1]):
            uf = tokens[-1].upper()
            cidade = " ".join(tokens[:-1]).strip(" ,;-")
        else:
            cidade = rest.strip(" ,;-")
        if bairro and cidade:
            return _from_parts(bairro, cidade, uf, tipo=tipo, origem="mensagem")

    m = re.search(r"\bno\s+([^,]+?)\s*,\s*([A-Za-zÀ-ÿ].*)", msg, re.IGNORECASE)
    if m:
        rest = m.group(2).strip().rstrip("?!.")
        tokens = rest.split()
        uf = ""
        if tokens and _norm_uf(tokens[-1]):
            uf = tokens[-1].upper()
            cidade = " ".join(tokens[:-1]).strip(" ,;-")
        else:
            cidade = rest.strip(" ,;-")
        if m.group(1).strip() and cidade:
            return _from_parts(m.group(1), cidade, uf, tipo=tipo, origem="mensagem")

    m = _VIRGULA_UF_RE.match(msg)
    if m:
        return _from_parts(m.group(1), m.group(2), m.group(3), tipo=tipo, origem="mensagem")

    m = _TRES_TOKENS_UF_RE.match(msg)
    if m and _norm_uf(m.group(3)):
        return _from_parts(m.group(1), m.group(2), m.group(3), tipo=tipo, origem="mensagem")

    return LocalizacaoResolvida(tipo_negocio=tipo, origem="")


def _from_hint_dict(hint: dict[str, Any] | None, *, origem: str) -> LocalizacaoResolvida:
    if not hint or not isinstance(hint, dict):
        return LocalizacaoResolvida()
    bairro = (hint.get("bairro") or hint.get("bairro_ascii") or "").strip()
    cidade = (hint.get("cidade") or "").strip()
    uf = _norm_uf(hint.get("uf"))
    tipo = (hint.get("tipo_negocio") or "").strip()
    if not (bairro or cidade):
        return LocalizacaoResolvida(tipo_negocio=tipo, origem=origem if tipo else "")
    return _from_parts(bairro, cidade, uf, tipo=tipo, origem=origem)


def mesmos_lugares(a: str, b: str) -> bool:
    fa, fb = fold_texto(a), fold_texto(b)
    return bool(fa and fb and fa == fb)


def resolver_localizacao(
    mensagem: str,
    *,
    hint: Optional[dict[str, Any]] = None,
    previa: Optional[dict[str, Any]] = None,
) -> LocalizacaoResolvida:
    """Resolve localização canônica. Preferência: hint JSON > bloco contexto > parse > prévia."""
    msg_limpa, ctx_kv = extrair_bloco_contexto(mensagem)
    tipo_msg = inferir_tipo_negocio(msg_limpa)

    candidatos = [
        _from_hint_dict(hint, origem="hint_json"),
        _from_hint_dict(ctx_kv, origem="contexto"),
        parse_localizacao_mensagem(msg_limpa),
        _from_hint_dict(previa, origem="previa"),
    ]

    escolhido = LocalizacaoResolvida()
    for cand in candidatos:
        if cand.completa:
            escolhido = cand
            break
        if not escolhido.bairro and not escolhido.cidade and (cand.bairro or cand.cidade):
            escolhido = cand

    if not escolhido.tipo_negocio:
        escolhido.tipo_negocio = tipo_msg or (previa or {}).get("tipo_negocio", "") or ""

    # Ambiguidade real: só cidade/UF, sem bairro — pede confirmação fechada
    if escolhido.cidade and not escolhido.bairro:
        escolhido.confirme = True
        escolhido.completa = False
    elif escolhido.completa:
        escolhido.confirme = False

    escolhido.extras["mensagem_limpa"] = msg_limpa
    return escolhido


def injetar_contexto_localizacao(mensagem: str, loc: LocalizacaoResolvida) -> str:
    """Prefixa a mensagem com bloco canônico p/ o LLM NÃO reperguntar."""
    msg_limpa = loc.extras.get("mensagem_limpa") or extrair_bloco_contexto(mensagem)[0]
    if not loc.completa and not loc.confirme:
        return msg_limpa

    parts = []
    if loc.bairro:
        parts.append(f"bairro={loc.bairro}")
        parts.append(f"bairro_ascii={fold_texto(loc.bairro)}")
    if loc.cidade:
        parts.append(f"cidade={loc.cidade}")
    if loc.uf:
        parts.append(f"uf={loc.uf}")
    if loc.tipo_negocio:
        parts.append(f"tipo_negocio={loc.tipo_negocio}")

    bloco = "[localizacao_resolvida: " + "; ".join(parts) + "]"
    if loc.confirme:
        bloco += (
            f"\n[pedido_confirmacao: Confirma {loc.bairro or '?'} / "
            f"{loc.cidade or '?'} / {loc.uf or '?'}?]"
        )
    if not msg_limpa:
        return bloco
    return f"{bloco}\n{msg_limpa}"
