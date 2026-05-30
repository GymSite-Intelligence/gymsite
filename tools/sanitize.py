"""
Sanitização de dados sensíveis — LGPD + segurança.

Uso:
    from tools.sanitize import mask_cnpj, mask_phone, mask_email, sanitize_dict

    safe = sanitize_dict(oportunidade, {
        "cnpj": mask_cnpj,
        "telefone": mask_phone,
        "email": mask_email,
    })
"""
from __future__ import annotations

import re
from typing import Callable


def mask_cnpj(cnpj: str | None) -> str | None:
    """Mascara CNPJ: 12.345.678/0001-99 → 12.***.***/0001-99"""
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", cnpj)
    if len(digits) != 14:
        return cnpj
    return f"{digits[:2]}.***.***/{digits[8:12]}-{digits[12:]}"


def mask_phone(phone: str | None) -> str | None:
    """Mascara telefone: +5585999999999 → +55 ** *****-9999"""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8:
        return phone
    return f"+{digits[:2]} ** *****-{digits[-4:]}"


def mask_email(email: str | None) -> str | None:
    """Mascara email: joao@academia.com.br → jo***@academia.com.br"""
    if not email or "@" not in email:
        return email
    user, domain = email.split("@", 1)
    visible = user[:2] if len(user) >= 2 else user[:1]
    return f"{visible}***@{domain}"


def redact(_value: str | None) -> str | None:
    """Remove completamente um valor sensível."""
    return None


def sanitize_dict(data: dict, rules: dict[str, Callable]) -> dict:
    """
    Aplica regras de sanitização em um dict.

    rules = {"cnpj": mask_cnpj, "telefone": mask_phone}
    """
    out = dict(data)
    for key, fn in rules.items():
        if key in out:
            out[key] = fn(out[key])
    return out
