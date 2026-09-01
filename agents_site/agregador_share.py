"""Share determinístico Wellhub / TotalPass / GuruPass por município (SQL Eros)."""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("gymsite.agents_site.agregador_share")

_SHARE_KEYS = (
    "market share",
    "share",
    "participação",
    "participacao",
    "percentual",
    "cobertura",
    "%",
)
_AGREG_KEYS = (
    "wellhub",
    "gympass",
    "totalpass",
    "total pass",
    "gurupass",
    "guru pass",
    "agregador",
)
_CIDADE_ALIASES: tuple[tuple[str, str], ...] = (
    ("sao jose dos campos", "São José dos Campos"),
    ("rio de janeiro", "Rio de Janeiro"),
    ("belo horizonte", "Belo Horizonte"),
    ("porto alegre", "Porto Alegre"),
    ("joao pessoa", "João Pessoa"),
    ("joão pessoa", "João Pessoa"),
    ("sao paulo", "São Paulo"),
    ("são paulo", "São Paulo"),
    ("florianopolis", "Florianópolis"),
    ("florianópolis", "Florianópolis"),
    ("campo grande", "Campo Grande"),
    ("ribeirao preto", "Ribeirão Preto"),
    ("fortaleza", "Fortaleza"),
    ("curitiba", "Curitiba"),
    ("salvador", "Salvador"),
    ("campinas", "Campinas"),
    ("brasilia", "Brasília"),
    ("brasília", "Brasília"),
    ("goiania", "Goiânia"),
    ("goiânia", "Goiânia"),
    ("recife", "Recife"),
    ("manaus", "Manaus"),
    ("belem", "Belém"),
    ("belém", "Belém"),
    ("niteroi", "Niterói"),
    ("niterói", "Niterói"),
    ("guarulhos", "Guarulhos"),
    ("osasco", "Osasco"),
    ("santos", "Santos"),
)


def is_share_agregadores(pergunta: str) -> bool:
    q = (pergunta or "").casefold()
    if not any(k in q for k in _AGREG_KEYS):
        return False
    return any(k in q for k in _SHARE_KEYS)


def extract_municipio_share(pergunta: str) -> str | None:
    q = (pergunta or "").casefold()
    for alias, label in _CIDADE_ALIASES:
        if alias in q:
            return label
    return None


def share_from_rows(
    rows: list[dict],
    top_n: int = 25,
    brasil_override: dict | None = None,
    n_municipios_override: int | None = None,
) -> dict:
    brasil = {"wellhub": 0, "totalpass": 0, "gurupass": 0}
    munis: list[dict] = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        nome = str(raw.get("municipio") or "").strip()
        w = int(raw.get("wellhub") or 0)
        t = int(raw.get("totalpass") or 0)
        g = int(raw.get("gurupass") or 0)
        total = w + t + g
        if not nome or total <= 0:
            continue
        brasil["wellhub"] += w
        brasil["totalpass"] += t
        brasil["gurupass"] += g
        munis.append(
            {
                "municipio": nome,
                "wellhub": w,
                "totalpass": t,
                "gurupass": g,
                "total": total,
                "pct_wellhub": round(100.0 * w / total, 1),
                "pct_totalpass": round(100.0 * t / total, 1),
                "pct_gurupass": round(100.0 * g / total, 1),
            }
        )
    munis.sort(key=lambda x: (-x["total"], x["municipio"]))
    if isinstance(brasil_override, dict):
        brasil = {
            "wellhub": int(brasil_override.get("wellhub") or 0),
            "totalpass": int(brasil_override.get("totalpass") or 0),
            "gurupass": int(brasil_override.get("gurupass") or 0),
        }
    brasil_total = brasil["wellhub"] + brasil["totalpass"] + brasil["gurupass"]
    brasil_pct = {
        k: round(100.0 * v / brasil_total, 1) if brasil_total else 0.0
        for k, v in brasil.items()
    }
    top = munis[: max(1, top_n)]
    linhas = [
        "Share de academias credenciadas · catálogo Eros · ingest vigente",
        (
            f"Brasil: Wellhub {brasil['wellhub']} ({brasil_pct['wellhub']}%) · "
            f"TotalPass {brasil['totalpass']} ({brasil_pct['totalpass']}%) · "
            f"GuruPass {brasil['gurupass']} ({brasil_pct['gurupass']}%) · "
            f"base {brasil_total} unidades-catálogo · "
            f"{int(n_municipios_override) if n_municipios_override is not None else len(munis)} municípios"
        ),
        "Métrica: academias distintas (gym_id) por agregador e município. Não é check-in nem faturamento.",
    ]
    wellhub_teto = sum(1 for m in munis if m["wellhub"] == 100 and m["totalpass"] > 100)
    if wellhub_teto >= 3:
        linhas.append(
            "Aviso: Wellhub no Eros parece limitado a 100 academias por município (ingest parcial). "
            "O % municipal subestima Wellhub nessas cidades; o total Brasil é a leitura mais honesta."
        )
    linhas.append("Top municípios por volume:")
    for i, m in enumerate(top, 1):
        linhas.append(
            f"{i}. {m['municipio']} — Wellhub {m['wellhub']} ({m['pct_wellhub']}%) · "
            f"TotalPass {m['totalpass']} ({m['pct_totalpass']}%) · "
            f"GuruPass {m['gurupass']} ({m['pct_gurupass']}%) · total {m['total']}"
        )
    texto = "\n".join(linhas)
    return {
        "metrica": "share_credenciadas",
        "base": "academias distintas (gym_id) no catálogo Eros por município",
        "fonte": "Eros catálogo Wellhub + TotalPass + GuruPass",
        "janela": "ingest vigente no Eros",
        "brasil": {**brasil, "total": brasil_total, "pct": brasil_pct},
        "por_municipio_top": top,
        "n_municipios": int(n_municipios_override) if n_municipios_override is not None else len(munis),
        "n_docs": int(n_municipios_override) if n_municipios_override is not None else len(munis),
        "texto_rag": texto,
        "resultados": [
            {"titulo": m["municipio"], "uri": "", "trecho": (
                f"Wellhub {m['wellhub']} ({m['pct_wellhub']}%) · "
                f"TotalPass {m['totalpass']} ({m['pct_totalpass']}%) · "
                f"GuruPass {m['gurupass']} ({m['pct_gurupass']}%)"
            )}
            for m in top
        ],
    }


def consultar_share_agregadores(pergunta: str) -> dict:
    """Share Brasil de academias credenciadas Wellhub × TotalPass × GuruPass por município.

    Contagem SQL (gym_id distinto). Não inventa %. Sem cidade na pergunta = Brasil inteiro.
    """
    base = (
        os.getenv("EROS_SUPABASE_URL") or os.getenv("SUPABASE_URL") or ""
    ).rstrip("/")
    key = (
        os.getenv("EROS_SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    )
    wellhub = (os.getenv("EROS_GROUP_ID_WELLHUB") or "").strip()
    totalpass = (os.getenv("EROS_GROUP_ID_TOTALPASS") or "").strip()
    gurupass = (os.getenv("EROS_GROUP_ID_GURUPASS") or "").strip()
    if not base or not key or not wellhub or not totalpass or not gurupass:
        return {
            "texto_rag": "",
            "n_docs": 0,
            "fonte": "Eros catálogo agregadores",
            "erro": (
                "eros_config_ausente: defina EROS_SUPABASE_URL, "
                "EROS_SUPABASE_SERVICE_ROLE_KEY, EROS_GROUP_ID_WELLHUB, "
                "EROS_GROUP_ID_TOTALPASS e EROS_GROUP_ID_GURUPASS"
            ),
        }
    municipio = extract_municipio_share(pergunta)
    payload = {
        "p_wellhub": wellhub,
        "p_totalpass": totalpass,
        "p_gurupass": gurupass,
        "p_municipio": municipio,
    }
    try:
        resp = httpx.post(
            f"{base}/rest/v1/rpc/aggregator_share_snapshot",
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90.0,
        )
        if resp.status_code >= 400:
            detail = (resp.text or "")[:300]
            logger.warning("aggregator_share_by_municipio HTTP %s: %s", resp.status_code, detail)
            return {
                "texto_rag": "",
                "n_docs": 0,
                "fonte": "Eros catálogo agregadores",
                "erro": f"falha_conexao_eros: HTTP {resp.status_code} {detail}",
            }
        data = resp.json() if resp.content else {}
        if isinstance(data, list):
            out = share_from_rows(data)
        elif isinstance(data, dict):
            rows = data.get("municipios") or []
            if not isinstance(rows, list):
                rows = []
            out = share_from_rows(
                rows,
                brasil_override=data.get("brasil") if isinstance(data.get("brasil"), dict) else None,
                n_municipios_override=(
                    int(data["n_municipios"])
                    if isinstance(data.get("n_municipios"), (int, float))
                    else None
                ),
            )
        else:
            out = share_from_rows([])
        if municipio:
            out["filtro_municipio"] = municipio
        if out["n_docs"] == 0:
            out["aviso_usuario"] = (
                "Catálogo Eros sem academias credenciadas para o recorte pedido."
            )
            out["status"] = "vazio"
        return out
    except Exception as e:  # noqa: BLE001
        logger.exception("consultar_share_agregadores falhou")
        return {
            "texto_rag": "",
            "n_docs": 0,
            "fonte": "Eros catálogo agregadores",
            "erro": f"falha_conexao_eros: {e}",
        }
