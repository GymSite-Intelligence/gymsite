"""
Normalização de nomes de bairro para comparação entre fontes (Places, CNO, endereços).

Chave (`normalizar_bairro`): minúsculas, sem acento, espaços colapsados.
Exibição (`formatar_bairro_exibicao`): title case legível (ex.: ALDEOTA → Aldeota).
"""
from __future__ import annotations

import re
import unicodedata


def normalizar_bairro(s: str) -> str:
    """Chave canônica para match entre CNO, Places, formulário e endereços."""
    s = (s or "").strip()
    if not s:
        return ""
    s = s.lower()
    nfkd = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def formatar_bairro_exibicao(s: str) -> str:
    """Label para UI a partir de texto cru (CNO costuma vir em MAIÚSCULAS)."""
    s = (s or "").strip()
    if not s:
        return ""
    return s.title()


def partes_bairro_alvo(s: str) -> list[str]:
    """
    Divide bairro composto em chaves normalizadas.
    Ex.: "Cocó / Guararapes", "Maraponga ou Montese".
    """
    if not (s or "").strip():
        return []
    raw = re.split(r"[,/]|(?:\s+ou\s+)", s, flags=re.IGNORECASE)
    out: list[str] = []
    for p in raw:
        chave = normalizar_bairro(p)
        if chave and chave not in out:
            out.append(chave)
    if not out:
        chave = normalizar_bairro(s)
        if chave:
            out.append(chave)
    return out


def bairro_coincide(a: str, b: str) -> bool:
    """True se as chaves normalizadas são iguais."""
    ka, kb = normalizar_bairro(a), normalizar_bairro(b)
    return bool(ka and kb and ka == kb)


def bairro_em_alvo(bairro: str, bairro_alvo: str) -> bool:
    """True se `bairro` bate com o alvo ou alguma parte composta."""
    chave = normalizar_bairro(bairro)
    if not chave:
        return False
    partes = partes_bairro_alvo(bairro_alvo)
    if not partes:
        return False
    return chave in partes
