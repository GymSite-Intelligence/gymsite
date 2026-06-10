"""
tools/apollo_enrichment.py

Integração Apollo.io para contato de decisores (entrantes CNPJ).

Fluxo (doc atual):
  1. People API Search — mixed_people/api_search (sem e-mail; master key)
  2. People Enrichment — people/match (e-mail/LinkedIn; consome créditos)

Auth: header x-api-key (não ?api_key= na URL).
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

logger = logging.getLogger("gymsite.apollo")

_APOLLO_BASE = "https://api.apollo.io/api/v1"
_SENIORITIES = ("owner", "founder", "c_suite", "partner", "director", "head")
_PRIORITY_IN_TITLE = (
    ("owner", 1),
    ("founder", 1),
    ("ceo", 1),
    ("chief executive", 1),
    ("sócio", 2),
    ("socio", 2),
    ("partner", 2),
    ("proprietário", 2),
    ("proprietario", 2),
    ("director", 3),
    ("diretor", 3),
    ("gerente", 4),
    ("manager", 4),
)


def limpar_razao_social(nome: str) -> str:
    """Remove sufixos jurídicos BR para melhorar q_keywords no Apollo."""
    if not nome:
        return ""

    n = nome.upper().strip()
    pattern = (
        r"\b(LTDA|ME|EPP|EIRELI|S/?A|S\.A\.|LIMITADA|SOCIEDADE|"
        r"IND[UÚ]STRIA|COM[EÉ]RCIO|SERVI[CÇ]OS?|EIPLI)\b"
    )
    n = re.sub(pattern, "", n)
    n = re.sub(r"[^\w\s-]", "", n)
    return re.sub(r"\s+", " ", n).strip(" -")


def _apollo_headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "x-api-key": api_key,
    }


def _reveal_personal_emails() -> bool:
    return os.getenv("APOLLO_REVEAL_PERSONAL_EMAILS", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _apollo_post(path: str, api_key: str, query_pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """POST com parâmetros na query string (padrão Apollo REST)."""
    qs = urllib.parse.urlencode(query_pairs)
    url = f"{_APOLLO_BASE}{path}?{qs}" if qs else f"{_APOLLO_BASE}{path}"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers=_apollo_headers(api_key),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _search_query_pairs(keywords: str, cidade: str | None) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = [
        ("q_keywords", keywords),
        ("person_locations[]", "Brazil"),
        ("per_page", "5"),
        ("page", "1"),
    ]
    for s in _SENIORITIES:
        pairs.append(("person_seniorities[]", s))
    if cidade and cidade.strip():
        pairs.append(("person_locations[]", cidade.strip()))
    return pairs


def _search_people(
    api_key: str, keywords: str, cidade: str | None
) -> list[dict[str, Any]]:
    data = _apollo_post(
        "/mixed_people/api_search",
        api_key,
        _search_query_pairs(keywords, cidade),
    )
    people = data.get("people") or []
    return [p for p in people if isinstance(p, dict)]


def _pick_best_person(people: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not people:
        return None
    best: dict[str, Any] | None = None
    best_score = 99
    for p in people:
        title = (p.get("title") or "").lower()
        score = 10
        for key, val in _PRIORITY_IN_TITLE:
            if key in title:
                score = min(score, val)
        if score < best_score:
            best_score = score
            best = p
    return best or people[0]


def _person_display_name(person: dict[str, Any]) -> str:
    first = (person.get("first_name") or "").strip()
    last = (person.get("last_name") or person.get("last_name_obfuscated") or "").strip()
    if first and last:
        return f"{first} {last}".strip()
    return (person.get("name") or first or last or "").strip()


def _normalize_name_tokens(nome: str) -> set[str]:
    n = re.sub(r"[^\w\s]", " ", (nome or "").upper())
    return {t for t in n.split() if len(t) >= 2}


def _name_overlap_score(person_name: str, qsa_name: str) -> int:
    """Maior = melhor match entre nome Apollo e nome QSA."""
    p_tokens = _normalize_name_tokens(person_name)
    q_tokens = _normalize_name_tokens(qsa_name)
    if not p_tokens or not q_tokens:
        return 0
    overlap = len(p_tokens & q_tokens)
    if overlap >= 2:
        return overlap + 10
    if overlap == 1 and len(q_tokens) <= 2:
        return overlap + 5
    return overlap


def _pick_person_by_qsa_name(
    people: list[dict[str, Any]], nome_socio: str
) -> dict[str, Any] | None:
    if not people or not nome_socio.strip():
        return None
    best: dict[str, Any] | None = None
    best_score = 0
    for p in people:
        score = _name_overlap_score(_person_display_name(p), nome_socio)
        if score > best_score:
            best_score = score
            best = p
    return best if best_score > 0 else None


def _extract_phone_from_person(person: dict[str, Any]) -> str | None:
    direct = (person.get("sanitized_phone") or person.get("phone") or "").strip()
    if direct:
        digits = re.sub(r"\D", "", direct)
        if len(digits) >= 10:
            return digits
    phones = person.get("phone_numbers")
    if isinstance(phones, list):
        for entry in phones:
            if not isinstance(entry, dict):
                continue
            raw = (
                entry.get("sanitized_number")
                or entry.get("raw_number")
                or entry.get("number")
                or ""
            )
            digits = re.sub(r"\D", "", str(raw))
            if len(digits) >= 10:
                return digits
    return None


def _contato_from_apollo_person(
    src: dict[str, Any],
    *,
    fallback_name: str | None = None,
    fallback_title: str | None = None,
) -> dict[str, Any]:
    org_block = src.get("organization") if isinstance(src.get("organization"), dict) else {}
    return {
        "nome": _person_display_name(src) or fallback_name or "Não especificado",
        "cargo": (src.get("title") or fallback_title or "Sócio / Proprietário"),
        "email_direto": src.get("email") or None,
        "telefone_direto": _extract_phone_from_person(src),
        "linkedin_url": src.get("linkedin_url") or None,
        "empresa_match": org_block.get("name") or None,
        "apollo_person_id": src.get("id"),
        "fonte_apollo": src.get("_fonte_apollo") or "apollo",
    }


def _people_match(
    api_key: str,
    *,
    organization_name: str,
    person_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any] | None:
    """People Enrichment — revela e-mail/LinkedIn (créditos Apollo)."""
    pairs: list[tuple[str, str]] = [
        ("organization_name", organization_name),
    ]
    if person_id:
        pairs.append(("id", person_id))
    if name:
        pairs.append(("name", name))
    if _reveal_personal_emails():
        pairs.append(("reveal_personal_emails", "true"))

    data = _apollo_post("/people/match", api_key, pairs)
    person = data.get("person")
    return person if isinstance(person, dict) else None


def enriquecer_socio_qsa_com_apollo(
    organization_name: str,
    nome_socio: str,
    cidade: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Enriquece contato usando nome do QSA (sócio administrador) + razão social.

    Usado quando a busca genérica por empresa não retorna e-mail/telefone.
    Consome créditos Apollo (people/match).
    """
    api_key = os.getenv("APOLLO_API_KEY", "").strip()
    if not api_key:
        return None

    nome = (nome_socio or "").strip()
    org_for_match = (organization_name or "").strip()
    if len(nome) < 4 or len(org_for_match) < 3:
        return None

    query_org = limpar_razao_social(org_for_match) or org_for_match

    try:
        enriched = _people_match(
            api_key,
            organization_name=org_for_match,
            name=nome,
        )
        if enriched and (
            enriched.get("email")
            or _extract_phone_from_person(enriched)
            or enriched.get("linkedin_url")
        ):
            out = _contato_from_apollo_person(enriched, fallback_name=nome)
            out["fonte_apollo"] = "apollo_qsa_match"
            return out

        keywords = f"{nome} {query_org}".strip()
        people: list[dict[str, Any]] = []
        try:
            people = _search_people(api_key, keywords, cidade)
        except urllib.error.HTTPError as e:
            if e.code not in (403, 422):
                raise

        candidate = _pick_person_by_qsa_name(people, nome) or _pick_best_person(people)
        if not candidate:
            return None

        person_id = candidate.get("id")
        display = _person_display_name(candidate)
        enriched2 = _people_match(
            api_key,
            organization_name=org_for_match,
            person_id=str(person_id) if person_id else None,
            name=display or nome,
        )
        src = enriched2 or candidate
        if not (src.get("email") or _extract_phone_from_person(src) or src.get("linkedin_url")):
            return None
        out = _contato_from_apollo_person(
            src,
            fallback_name=nome,
            fallback_title=candidate.get("title"),
        )
        out["fonte_apollo"] = "apollo_qsa_search"
        return out

    except urllib.error.HTTPError as e:
        logger.warning(
            "Apollo QSA HTTP %s org=%r socio=%r: %s",
            e.code,
            query_org,
            nome[:40],
            _read_http_error_body(e),
        )
        return None
    except Exception as e:
        logger.warning("Apollo QSA erro org=%r socio=%r: %s", query_org, nome[:40], e)
        return None


def _tem_contato_apollo(data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    return bool(
        data.get("email_direto")
        or data.get("linkedin_url")
        or data.get("telefone_direto")
    )


def enriquecer_empresa_com_apollo(
    organization_name: str,
    cidade: Optional[str] = None,
    *,
    nome_socio_qsa: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Localiza decisor da empresa: busca (api_search) + enrichment (people/match).

    Requer APOLLO_API_KEY (idealmente master key para api_search).
    """
    api_key = os.getenv("APOLLO_API_KEY", "").strip()
    if not api_key:
        return None

    query_org = limpar_razao_social(organization_name)
    if not query_org or len(query_org) < 3:
        return None

    org_for_match = organization_name.strip() or query_org

    try:
        people: list[dict[str, Any]] = []
        try:
            people = _search_people(api_key, query_org, cidade)
            if not people and query_org != org_for_match:
                people = _search_people(api_key, org_for_match, cidade)
        except urllib.error.HTTPError as e:
            body = _read_http_error_body(e)
            if e.code in (403, 422):
                logger.info(
                    "Apollo api_search indisponível (%s) — tentando people/match direto: %s",
                    e.code,
                    body[:200],
                )
            else:
                raise

        candidate = _pick_best_person(people)
        person_id = (candidate or {}).get("id") if candidate else None
        display = _person_display_name(candidate) if candidate else None

        enriched = _people_match(
            api_key,
            organization_name=org_for_match,
            person_id=str(person_id) if person_id else None,
            name=display or None,
        )

        if not enriched and not candidate:
            if nome_socio_qsa:
                return enriquecer_socio_qsa_com_apollo(
                    org_for_match, nome_socio_qsa, cidade
                )
            return None

        src = enriched or candidate or {}
        out = _contato_from_apollo_person(
            src,
            fallback_name=display,
            fallback_title=(candidate or {}).get("title"),
        )
        out["empresa_match"] = out.get("empresa_match") or org_for_match
        out["apollo_person_id"] = out.get("apollo_person_id") or person_id
        out["fonte_apollo"] = "apollo_org_search"

        if not _tem_contato_apollo(out) and nome_socio_qsa:
            qsa_out = enriquecer_socio_qsa_com_apollo(
                org_for_match, nome_socio_qsa, cidade
            )
            if _tem_contato_apollo(qsa_out):
                return qsa_out
        return out if _tem_contato_apollo(out) else None

    except urllib.error.HTTPError as e:
        logger.warning(
            "Apollo HTTP %s para org=%r: %s",
            e.code,
            query_org,
            _read_http_error_body(e),
        )
        if nome_socio_qsa:
            return enriquecer_socio_qsa_com_apollo(
                org_for_match, nome_socio_qsa, cidade
            )
        return None
    except Exception as e:
        logger.warning("Apollo erro para org=%r: %s", query_org, e)
        if nome_socio_qsa:
            return enriquecer_socio_qsa_com_apollo(
                org_for_match, nome_socio_qsa, cidade
            )
        return None


def _read_http_error_body(e: urllib.error.HTTPError) -> str:
    try:
        return e.read().decode("utf-8", errors="replace")[:500]
    except Exception:
        return str(e.reason or e)
