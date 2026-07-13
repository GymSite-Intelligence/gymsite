from collections.abc import Coroutine
from typing import Any, Callable

MIN_SAMPLES_ALTA: int
MIN_SAMPLES_MEDIA: int

pesquisar_aluguel_municipio: Callable[..., Coroutine[Any, Any, dict[str, Any]]]

def pesquisar_aluguel_municipio_sync(
    cidade: str,
    uf: str = "",
    area_m2_min: int = 800,
    area_m2_max: int = 1500,
    keywords: tuple[str, ...] | None = None,
    *,
    bairro: str = "",
    use_playwright: bool | None = None,
) -> dict[str, Any]: ...

def aggregate_municipio(*args: Any, **kwargs: Any) -> dict[str, Any]: ...
def build_portal_search_urls(*args: Any, **kwargs: Any) -> dict[str, list[str]]: ...
def parse_listings_html(*args: Any, **kwargs: Any) -> list[dict[str, Any]]: ...
def _olx_ad_matches_municipio(*args: Any, **kwargs: Any) -> bool: ...
def _build_queries_aluguel(*args: Any, **kwargs: Any) -> list[tuple[str, str]]: ...
