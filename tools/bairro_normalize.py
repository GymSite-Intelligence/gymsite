"""
Normalização de nomes de bairro para comparação entre fontes (Places, CNO, endereços).

Chave (`normalizar_bairro` / `fold_texto`): casefold, sem acento (NFD + Mn), espaços colapsados.
Exibição (`formatar_bairro_exibicao`): title case legível (ex.: ALDEOTA → Aldeota).
"""
from __future__ import annotations

import re
import unicodedata

# (bairro_fold, uf_fold) → nome canônico IBGE / renda_bairro.
# Usado em geocode, polígono e lookup de renda (ex.: "Lagoa" no RJ ≠ lagoa genérica).
_BAIRRO_ALIASES: dict[tuple[str, str], str] = {
    ("lagoa", "rj"): "Lagoa Rodrigo de Freitas",
    ("lagoa rodrigo de freitas", "rj"): "Lagoa Rodrigo de Freitas",
    ("rodrigo de freitas", "rj"): "Lagoa Rodrigo de Freitas",
}

# Piso em renda per capita (campo demografia.renda_media = renda_pc IBGE).
_SANITY_RENDA_MINIMA: dict[tuple[str, str], float] = {
    ("lagoa rodrigo de freitas", "rj"): 7000.0,
    ("leblon", "rj"): 7000.0,
    ("ipanema", "rj"): 6000.0,
}


def fold_texto(s: str) -> str:
    """Accent-insensitive fold: casefold + NFD + strip Mn + colapsa espaços.

    Parangaba ≡ Parangabá; Sao Paulo ≡ São Paulo; Coco ≡ Cocó.
    """
    s = (s or "").strip().casefold()
    if not s:
        return ""
    nfd = unicodedata.normalize("NFD", s)
    s = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def normalizar_bairro(s: str) -> str:
    """Chave canônica para match entre CNO, Places, formulário e endereços."""
    return fold_texto(s)


def resolver_bairro_canonico(bairro: str, *, uf: str = "", cidade: str = "") -> str:
    """Resolve alias popular → nome oficial (ex.: Lagoa/RJ → Lagoa Rodrigo de Freitas).

    Sem match devolve o bairro original stripado. `cidade` reservado para desambiguação futura.
    """
    del cidade
    raw = (bairro or "").strip()
    if not raw:
        return ""
    bn = normalizar_bairro(raw)
    uf_n = fold_texto(uf or "")
    if not bn or not uf_n:
        return raw
    return _BAIRRO_ALIASES.get((bn, uf_n), raw)


def sanity_renda_geocode(
    renda_media: float | None,
    bairro: str,
    *,
    uf: str = "",
) -> str | None:
    """Retorna mensagem de alerta se renda estiver abaixo do piso esperado do bairro."""
    if renda_media is None:
        return None
    try:
        renda = float(renda_media)
    except (TypeError, ValueError):
        return None
    bn = normalizar_bairro(resolver_bairro_canonico(bairro, uf=uf))
    uf_n = fold_texto(uf or "")
    piso = _SANITY_RENDA_MINIMA.get((bn, uf_n))
    if piso is None or renda >= piso:
        return None
    return (
        f"Renda R${renda:.2f} muito abaixo do esperado "
        f"(R${piso:.2f}) para {bairro}. Validar geocode manualmente."
    )


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
