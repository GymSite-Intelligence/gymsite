"""
market_bundle.json — fatos pré-resolvidos por (cidade, bairro, uf).

Loader para A0 (substitui Deep Research na trilha feliz).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DIR = ROOT / "data" / "market_bundles"
BUNDLE_MAX_AGE_DAYS = 7

# Campos da "trilha viva" (trilha 3 da arquitetura): competição e aluguel são
# resolvidos NO RELATÓRIO (A3 competitor intel + enrichment OSM/portais), não no
# batch semanal. Ausência no bundle batch é ESPERADA — não degrada a trilha feliz
# nem justifica Deep Research (doc: nunca usar DR para competição/aluguel).
LIVE_TRAIL_FIELDS = frozenset({"competicao_osm", "aluguel_medio_m2"})


def _slug(cidade: str, bairro: str, uf: str) -> str:
    parts = [cidade.strip().lower(), (bairro or "").strip().lower(), uf.strip().upper()]
    return "_".join(p for p in parts if p)


def bundle_path(cidade: str, bairro: str, uf: str) -> Path:
    return BUNDLE_DIR / f"{_slug(cidade, bairro, uf)}.json"


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def bundle_is_fresh(bundle: dict[str, Any], *, max_age_days: int = BUNDLE_MAX_AGE_DAYS) -> bool:
    ts = _parse_ts(bundle.get("gerado_em") or bundle.get("valido_ate"))
    if ts is None:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
    return age.total_seconds() <= max_age_days * 86400


def load_market_bundle(
    cidade: str,
    bairro: str,
    uf: str,
) -> dict[str, Any] | None:
    # Armazém compartilhado (Supabase) primeiro quando habilitado — prod lê fresco
    # sem rebuild de imagem; cai pro FS local em dev/teste ou falha.
    try:
        from tools.market_store import fetch_bundle, supabase_enabled

        if supabase_enabled():
            remote = fetch_bundle(_slug(cidade, bairro, uf))
            if isinstance(remote, dict):
                return remote
    except Exception:
        pass

    path = bundle_path(cidade, bairro, uf)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_market_bundle(cidade: str, bairro: str, uf: str, bundle: dict[str, Any]) -> Path:
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    path = bundle_path(cidade, bairro, uf)
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    # Espelha no armazém compartilhado quando habilitado (best-effort).
    try:
        from tools.market_store import upsert_bundle

        upsert_bundle(_slug(cidade, bairro, uf), bundle)
    except Exception:
        pass
    return path


def a0_context_mode() -> str:
    """
    auto | ckan_bundle | deep_research_fallback
    """
    return (os.environ.get("A0_CONTEXT_SOURCE") or "auto").strip().lower()


def should_prefer_bundle() -> bool:
    mode = a0_context_mode()
    return mode in ("auto", "ckan_bundle", "bundle")


def must_not_call_deep_research() -> bool:
    """Fase C: modo estrito — A0 só bundle, sem DR."""
    return a0_context_mode() in ("ckan_bundle", "bundle_only")


def compute_bundle_stale(bundle: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Marca bundle degradado quando fontes ESTRUTURADAS de batch falham
    (demografia/CVM/SINAPI/freshness). Competição e aluguel NÃO entram aqui —
    são trilha viva (ver LIVE_TRAIL_FIELDS / live_trail_pending), resolvidas no
    relatório e não devem bloquear a trilha feliz do A0.
    Relatório pode seguir com DR parcial; A0 expõe stale no briefing.
    """
    reasons: list[str] = []
    if not bundle_is_fresh(bundle):
        reasons.append("bundle_expirado")

    sector = bundle.get("sector_benchmarks") or {}
    for emp in sector.get("empresas") or []:
        if not isinstance(emp, dict) or (emp.get("ticker") or "").upper() != "SMFT3":
            continue
        fonte = (emp.get("fonte") or "").upper()
        kpis = emp.get("kpis") or {}
        if "CVM" in fonte and kpis.get("margem_ebitda_pct") is None:
            reasons.append("cvm_smft3_incompleto")
        break

    capex = bundle.get("capex_indices") or {}
    if (capex.get("fonte_obra") or "").startswith("benchmark_fixo"):
        reasons.append("sinapi_fallback")

    return bool(reasons), reasons


def live_trail_pending(bundle: dict[str, Any]) -> list[str]:
    """
    Campos de trilha viva ainda não preenchidos no bundle batch — informativo.
    O relatório os resolve via A3 (competição) e enrichment (aluguel/portais);
    NÃO disparam stale nem Deep Research.
    """
    pend: list[str] = []
    comp = bundle.get("competicao_local") or {}
    if comp.get("status") != "ok":
        pend.append("competicao_osm")
    aluguel = bundle.get("aluguel_portais") or {}
    if not aluguel.get("n_validos"):
        pend.append("aluguel_medio_m2")
    return pend


def compress_bundle_for_llm(bundle: dict[str, Any]) -> str:
    """Prompt compacto: enrichment + demografia + sector (para smoke / A0)."""
    lines = [bundle_to_briefing_md(bundle)]
    comp = bundle.get("competicao_local") or {}
    if comp.get("status") == "ok":
        lines.append(
            f"OSM: {comp.get('total_unidades_osm')} un.; "
            f"redes={', '.join(comp.get('redes_detectadas_osm') or [])}"
        )
    return "\n".join(lines)


def bundle_to_briefing_md(bundle: dict[str, Any]) -> str:
    """Markdown compacto para A0 (substituto parcial do Deep Research)."""
    loc = bundle.get("local") or {}
    demo_m = (bundle.get("demografia") or {}).get("municipio") or {}
    demo_b = (bundle.get("demografia") or {}).get("bairro") or {}
    sector = bundle.get("sector_benchmarks") or {}
    comp = bundle.get("competicao_local") or {}
    aluguel = bundle.get("aluguel_portais") or {}
    bcb = bundle.get("bcb_imobiliario") or {}
    missing = bundle.get("missing_fields") or []

    lines = [
        f"# Briefing de mercado (market_bundle) — {loc.get('bairro')}, {loc.get('cidade')}/{loc.get('uf')}",
        "",
        f"**Gerado em:** {bundle.get('gerado_em', 'n/d')}",
        f"**Stale:** {bundle.get('stale', False)}",
        "",
        "## Demografia (município)",
        f"- População: {demo_m.get('populacao_total', 'dados_nao_disponiveis')}",
        f"- Renda média: {demo_m.get('renda_media_domiciliar', 'dados_nao_disponiveis')}",
        f"- Fonte: {demo_m.get('fonte', 'n/d')} ({demo_m.get('renda_granularidade', 'n/d')})",
        "",
        "## Demografia (bairro)",
        f"- Renda média bairro: {demo_b.get('renda_media', 'dados_nao_disponiveis')}",
        f"- Fonte: {demo_b.get('fonte', 'n/d')}",
        "",
        "## Concorrência local (OSM)",
    ]
    if comp.get("status") == "ok":
        lines.append(
            f"- Unidades no raio: {comp.get('total_unidades_osm', 0)}; "
            f"redes: {', '.join(comp.get('redes_detectadas_osm') or []) or 'n/d'}"
        )
    else:
        lines.append("- dados_nao_disponiveis (OSM)")

    lines.extend(["", "## Aluguel (portais)"])
    if aluguel.get("n_validos"):
        med = aluguel.get("mediana_r_m2") or aluguel.get("p50_r_m2")
        lines.append(
            f"- Mediana R$/m²: {med}; n={aluguel.get('n_validos')}; "
            f"confiança: {aluguel.get('confianca', 'n/d')}"
        )
    else:
        lines.append("- dados_nao_disponiveis")

    lines.extend(["", "## Macro (BCB)"])
    if bcb.get("ok"):
        lines.append(f"- Fonte: {bcb.get('fonte', 'BCB Olinda')}")
    else:
        lines.append("- dados_nao_disponiveis")

    empresas = sector.get("empresas") or []
    if empresas:
        lines.extend(["", "## Benchmarks setor listado (CVM/RI)"])
        for e in empresas[:3]:
            if isinstance(e, dict):
                k = e.get("kpis") or {}
                lines.append(
                    f"- {e.get('nome')} ({e.get('ticker')}): "
                    f"EBITDA margem ~{k.get('margem_ebitda_pct')}% — {e.get('fonte')}"
                )

    franq = bundle.get("franquias_referencia") or {}
    if franq.get("redes"):
        lines.extend(["", "## Franquias (curadoria — referência)"])
        for r in (franq.get("redes") or [])[:5]:
            if isinstance(r, dict):
                lines.append(
                    f"- {r.get('nome')}: ticket ~R$ {r.get('ticket_tipico_brl')} ({r.get('modelo')})"
                )

    legal = bundle.get("legal_fees") or {}
    if legal.get("disponivel"):
        taxas = legal.get("taxas") or {}
        alvara = taxas.get("alvara_funcionamento_brl") or {}
        lines.extend(
            [
                "",
                "## Taxas municipais (piloto)",
                f"- Alvará (faixa): R$ {alvara.get('min')}–{alvara.get('max')} — {legal.get('fonte')}",
            ]
        )

    stale_reasons = bundle.get("stale_reasons") or []
    if stale_reasons:
        lines.extend(["", "## Degradação de dados", *[f"- {r}" for r in stale_reasons]])

    live_pend = [m for m in missing if m in LIVE_TRAIL_FIELDS]
    dr_pend = [m for m in missing if m not in LIVE_TRAIL_FIELDS]
    if live_pend:
        lines.extend(
            ["", "## Pendências de trilha viva (resolver no relatório via A3/enrichment — NÃO Deep Research)", *[f"- {m}" for m in live_pend]]
        )
    if dr_pend:
        lines.extend(["", "## Campos pendentes (considerar Deep Research fallback)", *[f"- {m}" for m in dr_pend]])

    lines.append("")
    lines.append("*(Não inventar redes concorrentes a partir deste texto — usar OSM no JSON final.)*")
    return "\n".join(lines)


def carregar_market_bundle(cidade: str, bairro: str, uf: str) -> str:
    """
    Tool ADK: carrega bundle fresco e retorna briefing markdown.

    Se ausente ou expirado, retorna instrução para usar Deep Research.
    """
    bundle = load_market_bundle(cidade, bairro, uf)
    if not bundle or not bundle_is_fresh(bundle):
        if must_not_call_deep_research():
            return (
                f"<!-- market_bundle status=missing cidade={cidade} bairro={bairro} -->\n\n"
                f"**market_bundle** indisponível ou expirado. "
                f"`A0_CONTEXT_SOURCE=ckan_bundle` proíbe Deep Research — rode o batch semanal."
            )
        return (
            f"<!-- market_bundle status=missing cidade={cidade} bairro={bairro} -->\n\n"
            f"**market_bundle** indisponível ou expirado para {cidade}/{bairro}/{uf}. "
            "Use `rodar_deep_research` para campos qualitativos ou rode "
            "`python scripts/batch/build_market_bundles.py` no batch."
        )

    header = (
        f"<!-- market_bundle\n"
        f"     cidade: {cidade}\n"
        f"     bairro: {bairro}\n"
        f"     uf: {uf}\n"
        f"     version: {bundle.get('version', '1.0')}\n"
        f"     gerado_em: {bundle.get('gerado_em')}\n"
        f"-->\n\n"
    )
    return header + bundle_to_briefing_md(bundle)


def inject_market_bundle_context(
    cidade: str,
    bairro: str,
    uf: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Injeta bundle no state da sessão API quando fresco."""
    if not should_prefer_bundle():
        return context

    bundle = load_market_bundle(cidade, bairro, uf)
    context = dict(context)
    if not bundle:
        context["market_bundle_available"] = False
        return context

    context["market_bundle"] = bundle
    context["market_bundle_available"] = True
    context["market_bundle_fresh"] = bundle_is_fresh(bundle)
    context["market_bundle_briefing_md"] = bundle_to_briefing_md(bundle)

    missing = bundle.get("missing_fields") or []
    # Trilha viva (competição/aluguel) é preenchida no relatório por A3/enrichment;
    # não conta como lacuna estrutural que exige Deep Research.
    batch_missing = [m for m in missing if m not in LIVE_TRAIL_FIELDS]
    live_pending = [m for m in missing if m in LIVE_TRAIL_FIELDS]
    stale = bundle.get("stale", False)
    context["market_bundle_live_pending"] = live_pending
    if must_not_call_deep_research():
        context["skip_deep_research"] = bool(context.get("market_bundle_fresh"))
        context["a0_bundle_only"] = True
    elif context.get("market_bundle_fresh") and not batch_missing and not stale:
        # Trilha feliz: fatos estruturados completos → A0 sem Deep Research,
        # mesmo com competição/aluguel pendentes (relatório resolve live).
        context["skip_deep_research"] = True
        context["market_bundle_partial"] = bool(live_pending)
    elif context.get("market_bundle_fresh"):
        context["skip_deep_research"] = False
        context["market_bundle_partial"] = True
    return context
