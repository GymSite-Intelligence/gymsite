"""
Google Distance Matrix API  distncia rodoviria real entre 2 pontos.

Cache em disco (tools/cache/distance_matrix/*.json)  chave por par
(origem, destino) com tolerncia de 0.001 (~100m). Distncias rodovirias
no mudam em horizonte de anos; cache infinito  seguro.

Custo: $5/1000 elements (Google Maps Platform pricing 2024).
Com cache, ~80-90% das anlises hit cache aps 50 cidades cobertas.

Variveis de ambiente necessrias:
    GOOGLE_DISTANCE_MATRIX_API_KEY  (ou GOOGLE_MAPS_API_KEY como fallback)
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Origens dos principais fornecedores fitness (lat, lng)
# ---------------------------------------------------------------------------
FORNECEDORES_ORIGEM: dict[str, tuple[float, float]] = {
    "movement":    (-23.6037, -46.9189),   # Cotia / SP
    "athletic":    (-29.1689, -51.1796),   # Caxias do Sul / RS
    "life_fitness":(-25.4477, -49.1903),   # Pinhais / PR
    "rhs":         (-22.4108, -47.5611),   # Rio Claro / SP
    "eleiko":      (-23.9608, -46.3331),   # Santos / SP  (porto importao)
    "default":     (-23.5505, -46.6333),   # So Paulo capital
}

# ---------------------------------------------------------------------------
# Diretrio de cache
# ---------------------------------------------------------------------------
CACHE_DIR = Path(__file__).parent / "cache" / "distance_matrix"


# ---------------------------------------------------------------------------
# Utilitrios de cache
# ---------------------------------------------------------------------------

def _cache_key(orig: tuple[float, float], dest: tuple[float, float]) -> str:
    """
    Gera chave MD5 do par (origem, destino) com snap a 0.001 (~100m).
    Mesma rota com coordenadas ligeiramente diferentes reutiliza o cache.
    """
    o_lat = round(orig[0], 3)
    o_lng = round(orig[1], 3)
    d_lat = round(dest[0], 3)
    d_lng = round(dest[1], 3)
    raw = f"{o_lat},{o_lng}->{d_lat},{d_lng}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _load_cache(key: str) -> Optional[dict]:
    path = _cache_path(key)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("distance_matrix: cache corrompido %s  %s", path, exc)
    return None


def _save_cache(key: str, data: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with _cache_path(key).open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("distance_matrix: no foi possvel salvar cache  %s", exc)


# ---------------------------------------------------------------------------
# Funo principal
# ---------------------------------------------------------------------------

def calcular_distancia_rodoviaria(
    origem_lat: float,
    origem_lng: float,
    destino_lat: float,
    destino_lng: float,
) -> Optional[dict]:
    """
    Retorna distncia rodoviria entre dois pontos via Google Distance Matrix API.

    Returns:
        {
            "distancia_km": float,
            "duracao_horas": float,
            "fonte": "google_distance_matrix" | "cache",
            "rota_resumo": str,   # ex: "via BR-116"
        }
        ou None se a API falhar (fallback acionado pelo chamador).
    """
    orig = (origem_lat, origem_lng)
    dest = (destino_lat, destino_lng)
    key = _cache_key(orig, dest)

    # 1. Tenta cache em disco
    cached = _load_cache(key)
    if cached is not None:
        cached["fonte"] = "cache"
        logger.debug("distance_matrix: cache HIT %s", key)
        return cached

    # 2. Resolve API key
    api_key = (
        os.environ.get("GOOGLE_DISTANCE_MATRIX_API_KEY")
        or os.environ.get("GOOGLE_MAPS_API_KEY")
        or os.environ.get("MAPS_API_KEY")
    )
    if not api_key:
        logger.warning(
            "distance_matrix: GOOGLE_DISTANCE_MATRIX_API_KEY no definida  "
            "usando fallback por UF."
        )
        return None

    # 3. Chama Google Distance Matrix via SDK oficial
    try:
        import googlemaps  # noqa: PLC0415  import lazy pra no quebrar se lib ausente

        client = googlemaps.Client(key=api_key)
        result = client.distance_matrix(
            origins=[(origem_lat, origem_lng)],
            destinations=[(destino_lat, destino_lng)],
            mode="driving",
            units="metric",
            language="pt-BR",
        )

        # Verifica status da resposta
        if result.get("status") != "OK":
            logger.warning(
                "distance_matrix: API status=%s", result.get("status")
            )
            return None

        element = result["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            logger.warning(
                "distance_matrix: element status=%s", element.get("status")
            )
            return None

        distancia_m = element["distance"]["value"]          # metros
        duracao_s   = element["duration"]["value"]          # segundos
        rota_resumo = element.get("distance", {}).get("text", "")

        data = {
            "distancia_km": round(distancia_m / 1000, 1),
            "duracao_horas": round(duracao_s / 3600, 2),
            "fonte": "google_distance_matrix",
            "rota_resumo": rota_resumo,
        }

        # 4. Salva no cache antes de retornar
        _save_cache(key, data)
        logger.info(
            "distance_matrix: %.0f km | %.1fh | %s",
            data["distancia_km"],
            data["duracao_horas"],
            rota_resumo,
        )
        return data

    except ImportError:
        logger.error(
            "distance_matrix: pacote 'googlemaps' no instalado. "
            "Execute: pip install googlemaps"
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("distance_matrix: erro inesperado  %s", exc)
        return None


# ---------------------------------------------------------------------------
# Helper orientado a fornecedor
# ---------------------------------------------------------------------------

def distancia_fornecedor_para_cidade(
    fornecedor_key: str,
    destino_lat: float,
    destino_lng: float,
) -> Optional[dict]:
    """
    Atalho: calcula distncia do fornecedor conhecido at o destino.

    Args:
        fornecedor_key: chave em FORNECEDORES_ORIGEM (ex: "movement").
                        Usa "default" (SP capital) se no reconhecido.
        destino_lat / destino_lng: coordenadas do municpio de destino.
    """
    origem = FORNECEDORES_ORIGEM.get(fornecedor_key, FORNECEDORES_ORIGEM["default"])
    return calcular_distancia_rodoviaria(origem[0], origem[1], destino_lat, destino_lng)
