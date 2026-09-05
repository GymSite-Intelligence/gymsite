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
from typing import Callable, Mapping

_SENSITIVE_HEADER_NAMES = frozenset({
    "authorization",
    "x-claw-secret",
    "cookie",
    "x-api-key",
    "x-supabase-key",
    "proxy-authorization",
})

_CAPABILITY_HEADER_NAMES = frozenset({
    "x-access-token",
})

_CAPABILITY_MASK_KEYS = frozenset({
    "access_token",
    "access_code",
})


def mask_capability_token(value: str | None) -> str | None:
    """Mascara UUID capability — mantém últimos 4 chars para correlacionar logs."""
    if not value:
        return None
    v = value.strip()
    if len(v) <= 4:
        return "****"
    return f"{'*' * (len(v) - 4)}{v[-4:]}"


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


def mask_address(
    address: str | None,
    *,
    cidade: str | None = None,
    uf: str | None = None,
    bairro: str | None = None,
) -> str | None:
    """
    Remove número de porta/prédio; mantém bairro + cidade/UF quando possível.

    Ex.: "Rua X, 123, Aldeota, Fortaleza - CE" → "Aldeota, Fortaleza/CE"
    """
    if bairro and cidade:
        suffix = f"/{uf}" if uf else ""
        return f"{bairro}, {cidade}{suffix}"

    if not address:
        if cidade:
            return f"{cidade}/{uf}" if uf else cidade
        return None

    text = address
    text = re.sub(r"\bn[ºo°\.]\s*\d+[A-Za-z]?\b", "", text, flags=re.I)
    text = re.sub(r"-\s*\d+[A-Za-z]?\b", "", text)
    text = re.sub(r",\s*\d+[A-Za-z]?(?:\s*-\s*\d+)?\b", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ,-")

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) > 1:
        parts = parts[1:]  # remove logradouro

    location_parts: list[str] = []
    for part in parts:
        city_uf = re.match(r"^(.+?)\s*[-/]\s*([A-Za-z]{2})$", part)
        if city_uf:
            if not cidade:
                cidade = city_uf.group(1).strip()
            if not uf:
                uf = city_uf.group(2).upper()
            continue
        if cidade and part.lower() == cidade.lower():
            continue
        location_parts.append(part)

    if cidade:
        if not location_parts or location_parts[-1].lower() != cidade.lower():
            location_parts.append(cidade)

    result = ", ".join(location_parts)
    if uf and not result.upper().endswith(f"/{uf.upper()}"):
        result = f"{result}/{uf}"
    return result or None


def sanitize_state(state: dict) -> dict:
    """
    Cópia sanitizada do state ADK para telemetria (spans, logs).

    Estruturas aninhadas grandes viram placeholder — evita vazar PII ou
    dumps JSON completos no OpenTelemetry.
    """
    safe: dict = {}
    for key, value in state.items():
        if key == "contato_cnpj" and isinstance(value, dict):
            safe[key] = sanitize_dict(value, {
                "email": mask_email,
                "whatsapp": mask_phone,
                "telefone": mask_phone,
            })
        elif key == "cnpj" and isinstance(value, str):
            safe[key] = mask_cnpj(value)
        elif key in ("telefone", "whatsapp", "phone") and isinstance(value, str):
            safe[key] = mask_phone(value)
        elif key == "email" and isinstance(value, str):
            safe[key] = mask_email(value)
        elif key in ("endereco", "endereco_cnpj") and isinstance(value, str):
            safe[key] = mask_address(
                value,
                cidade=state.get("cidade") if isinstance(state.get("cidade"), str) else None,
                uf=state.get("uf") if isinstance(state.get("uf"), str) else None,
                bairro=state.get("bairro") if isinstance(state.get("bairro"), str) else None,
            )
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, dict):
            safe[key] = f"<dict:{len(value)}>"
        elif isinstance(value, list):
            safe[key] = f"<list:{len(value)}>"
        else:
            safe[key] = f"<{type(value).__name__}>"
    return safe


def safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Retorna cópia dos headers HTTP com credenciais redacted."""
    out: dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower in _SENSITIVE_HEADER_NAMES:
            out[key] = "[REDACTED]"
        elif lower in _CAPABILITY_HEADER_NAMES:
            out[key] = mask_capability_token(value) or "[REDACTED]"
        else:
            out[key] = value
    return out


_SPAN_MASK_BY_KEY: dict[str, Callable[[str], str | None]] = {
    "cnpj": mask_cnpj,
    "email": mask_email,
    "telefone": mask_phone,
    "whatsapp": mask_phone,
    "phone": mask_phone,
    "access_token": mask_capability_token,
    "access_code": mask_capability_token,
}


def safe_query_params(params: Mapping[str, str]) -> dict[str, str]:
    """Cópia de query params com capability tokens mascarados."""
    out: dict[str, str] = {}
    for key, value in params.items():
        if key.lower() in _CAPABILITY_MASK_KEYS or key.lower() == "token":
            masked = mask_capability_token(value)
            out[key] = masked if masked is not None else "[REDACTED]"
        else:
            out[key] = value
    return out


def safe_span_attribute(key: str, value: object) -> tuple[str, str] | None:
    """
    Sanitiza um par chave/valor antes de gravar em span OTel.

    Retorna (attr_name, safe_value) ou None se o valor deve ser omitido.
    """
    if value is None:
        return None
    if key in _SPAN_MASK_BY_KEY and isinstance(value, str):
        masked = _SPAN_MASK_BY_KEY[key](value)
        if masked is None:
            return None
        attr = "cnpj_masked" if key == "cnpj" else f"{key}_masked"
        return attr, str(masked)[:256]
    if key in ("endereco", "endereco_cnpj") and isinstance(value, str):
        masked = mask_address(value)
        return ("endereco_masked", str(masked)[:256]) if masked else None
    if isinstance(value, (str, int, float, bool)):
        if key.lower() in _SENSITIVE_HEADER_NAMES:
            return None
        return key, str(value)[:256]
    return None
