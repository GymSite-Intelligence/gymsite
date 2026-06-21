"""bairros_municipio — cache persistente de bairros por município (Places → DB).

O form de Novo Relatório precisa da lista de bairros de um município. Antes isso
saía do Google Places a CADA sessão (12 chamadas paralelas no browser, ~R$0,20).
Aqui a varredura roda UMA vez por município no servidor, persiste em
`public.bairros_municipio` e os acessos seguintes servem do DB (grátis/instantâneo).

Fluxo de listar_bairros():
  1. Lê o registro de varredura (bairros_municipio_harvest). Se o município já foi
     varrido → devolve os bairros do DB (mesmo que poucos/zero).
  2. Se nunca foi varrido → varre o Places server-side, persiste e devolve.
  3. Qualquer erro de DB degrada limpo: varre o Places e devolve sem persistir
     (fonte 'places-nodb'), pra UI nunca ficar no escuro.

Contrato de bairro (espelha o frontend): {bairro, contexto, textoCompleto, placeId}.
"""
from __future__ import annotations

import logging
import os
import unicodedata
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("gymsite.bairros_municipio")

# Mesmos prefixos do sweep que rodava no browser (vogais + consoantes comuns;
# k/w/x/y/z raras ficam de fora pra economizar chamadas).
_PREFIXOS = list("abcdefgijlmnopqrstuv")
_TABLE = "bairros_municipio"
_HARVEST = "bairros_municipio_harvest"


def _norm(s: str) -> str:
    decomposed = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower().strip()


def _client():
    """Supabase service-role client (lazy). None se não configurado."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        logger.warning("Supabase client indisponível: %s", e)
        return None


def _harvest_places(municipio: str, uf: str) -> list[dict]:
    """Varre o Places por prefixo (server-side), dedup por placeId/bairro, ordena."""
    from tools.places_autocomplete import places_autocomplete

    vistos: dict[str, dict] = {}

    def _um(prefixo: str) -> list[dict]:
        r = places_autocomplete(input_text=prefixo, municipio=municipio, uf=uf)
        return r.get("suggestions") or []

    with ThreadPoolExecutor(max_workers=6) as ex:
        for sugestoes in ex.map(_um, _PREFIXOS):
            for b in sugestoes:
                chave = b.get("placeId") or b.get("textoCompleto") or b.get("bairro")
                if chave and chave not in vistos:
                    vistos[chave] = b
    bairros = list(vistos.values())
    bairros.sort(key=lambda b: _norm(b.get("bairro", "")))
    return bairros


def _ler_db(client, municipio_norm: str, uf: str) -> list[dict]:
    res = (
        client.table(_TABLE)
        .select("bairro,contexto,texto_completo,place_id")
        .eq("municipio_norm", municipio_norm)
        .eq("uf", uf)
        .order("bairro")
        .execute()
    )
    return [
        {
            "bairro": row["bairro"],
            "contexto": row.get("contexto") or "",
            "textoCompleto": row.get("texto_completo") or "",
            "placeId": row.get("place_id") or "",
        }
        for row in (res.data or [])
    ]


def _persistir(client, municipio: str, uf: str, municipio_norm: str, bairros: list[dict]) -> None:
    if bairros:
        linhas = [
            {
                "uf": uf,
                "municipio": municipio,
                "municipio_norm": municipio_norm,
                "bairro": b.get("bairro") or "",
                "contexto": b.get("contexto") or None,
                "texto_completo": b.get("textoCompleto") or None,
                "place_id": b.get("placeId") or None,
            }
            for b in bairros
            if b.get("bairro")
        ]
        # ignore_duplicates: índices únicos parciais (place_id / nome) colapsam repetidos.
        client.table(_TABLE).upsert(linhas, ignore_duplicates=True).execute()
    client.table(_HARVEST).upsert(
        {
            "municipio_norm": municipio_norm,
            "uf": uf,
            "n_bairros": len(bairros),
        }
    ).execute()


def listar_bairros(municipio: str, uf: str = "") -> dict:
    """Devolve {"bairros": [...], "fonte": str, "harvested": bool}.

    fonte ∈ {"db", "places", "places-nodb"}.
    """
    municipio = (municipio or "").strip()
    uf = (uf or "").strip().upper()
    if not municipio:
        return {"bairros": [], "fonte": "db", "harvested": False, "erro": "município vazio"}

    municipio_norm = _norm(municipio)
    client = _client()

    # Sem DB: degrada pra Places puro (não persiste).
    if client is None:
        try:
            bairros = _harvest_places(municipio, uf)
        except Exception as e:
            return {"bairros": [], "fonte": "places-nodb", "harvested": False,
                    "erro": f"{type(e).__name__}: {e}"}
        return {"bairros": bairros, "fonte": "places-nodb", "harvested": False}

    # 1. Já varrido? Serve do DB.
    try:
        h = (
            client.table(_HARVEST)
            .select("n_bairros")
            .eq("municipio_norm", municipio_norm)
            .eq("uf", uf)
            .limit(1)
            .execute()
        )
        if h.data:
            return {"bairros": _ler_db(client, municipio_norm, uf),
                    "fonte": "db", "harvested": True}
    except Exception as e:
        # DB de leitura quebrou → cai pro Places sem persistir.
        logger.warning("Leitura DB de bairros falhou (%s) — Places sem persist", e)
        try:
            return {"bairros": _harvest_places(municipio, uf),
                    "fonte": "places-nodb", "harvested": False}
        except Exception as e2:
            return {"bairros": [], "fonte": "places-nodb", "harvested": False,
                    "erro": f"{type(e2).__name__}: {e2}"}

    # 2. Nunca varrido: harvest + persist.
    try:
        bairros = _harvest_places(municipio, uf)
    except Exception as e:
        return {"bairros": [], "fonte": "places-nodb", "harvested": False,
                "erro": f"{type(e).__name__}: {e}"}
    # NÃO persistir varredura vazia: 0 bairros é quase sempre Places sem chave/billing,
    # não município sem bairros. Cachear isso envenenaria o cache (serviria vazio do DB
    # pra sempre). Deixa sem marcar como varrido → re-tenta quando o Places funcionar.
    if not bairros:
        return {"bairros": [], "fonte": "places-nodb", "harvested": False,
                "erro": "Places retornou 0 bairros (provável GOOGLE_MAPS_API_KEY/billing) — não cacheado"}
    try:
        _persistir(client, municipio, uf, municipio_norm, bairros)
        fonte = "places"
    except Exception as e:
        logger.warning("Persistência de bairros falhou (%s) — devolvendo sem cache", e)
        fonte = "places-nodb"
    return {"bairros": bairros, "fonte": fonte, "harvested": fonte == "places"}
