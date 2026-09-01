"""
Cliente CKAN Action API v3 + API REST pública dados.gov.br.

Uso:
- Scout FEDERAL (dados.gov.br): API pública `/dados/api/publico/*`
  (OpenAPI https://dados.gov.br/v3/api-docs) — Action `/api/3/action/*`
  responde 401 mesmo com chave; não usar Action no federal.
- Scout MACRO: `search_datasets_macro` no federal → público + ORG_SEED
  + filtro client-side de temas/cobertura (lista não filtra por tema).
- Scout municipal: Action em portais abertos (ex. Fortaleza).
- Consumo: resource URL → APIs oficiais (IBGE, CVM), não só Solr.

Não é lookup determinístico município→1 dataset no federal.

Notas de campo (2026-06-12 / 2026-08-04):
- Header federal: `chave-api-dados-abertos` via CKAN_API_KEY.
- Lista pública filtra só: pagina, nomeConjuntoDados, idOrganizacao,
  dadosAbertos, isPrivado. Temas/cobertura só no GET por id.
- fq (Action) aceita str | list[str] — Solr multi-filter (municipais).
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PORTAL = "https://dados.gov.br"
PUBLIC_API_BASE = "https://dados.gov.br/dados/api"
DEFAULT_TIMEOUT_S = 25.0
PUBLIC_PAGE_SIZE = 15  # API ignora tamanhoPagina; ~15/página observado

# Portais municipais/estaduais CKAN abertos, por cidade (lowercase).
PORTAIS_MUNICIPAIS = {
    "fortaleza": "https://dados.fortaleza.ce.gov.br",
}

# Orgs seed (slug portal → UUID) — scout macro federal via idOrganizacao.
# Resolvidos 2026-08-04 via GET /dados/api/publico/organizacao
# (+ fazenda/anvisa/esporte 2026-08-27, mesma API paginada).
ORG_SEED: dict[str, dict[str, str]] = {
    "instituto-brasileiro-de-geografia-e-estatistica-ibge": {
        "id": "0a2ede4a-4c54-4303-af0a-6d163e242c15",
        "titulo": "IBGE",
    },
    "ministerio-das-cidades": {
        "id": "13fd6676-b886-4eb9-9445-cdd89409b128",
        "titulo": "MCID - Ministério das Cidades",
    },
    "distrito-federal": {
        "id": "ac03360b-5ca0-4ecd-a068-b27021fbcc41",
        "titulo": "Distrito Federal",
    },
    "prefeitura-de-belo-horizonte-pbh": {
        "id": "b9d31793-6399-4537-874d-b025512f82a2",
        "titulo": "PBH - Prefeitura de Belo Horizonte",
    },
    "estado-do-rio-de-janeiro": {
        "id": "00013bc9-1395-4127-b2ea-70a0028b66ed",
        "titulo": "Estado do Rio de Janeiro",
    },
    "ipea": {
        "id": "9682a084-6702-4bfc-9cec-7a46a37c1fbc",
        "titulo": "IPEA",
    },
    "prefeitura-municipal-de-fortaleza": {
        "id": "456c33ed-5c18-4a2c-a2ea-b76600e22d94",
        "titulo": "Prefeitura Municipal de Fortaleza",
    },
    "ministerio-da-economia-me": {
        "id": "fadff597-55a0-4619-8a81-cfecc9c0c2bb",
        "titulo": "Ministério da Economia (legado)",
    },
    "agencia-nacional-de-aguas-e-saneamento-basico": {
        "id": "39868dc2-d6b8-4b89-84e4-692c2fe17b25",
        "titulo": "ANA",
    },
    "estado-de-alagoas-al": {
        "id": "0bf70fd6-0730-445d-af78-d45c83d6a51e",
        "titulo": "Estado de Alagoas",
    },
    "ministerio-da-fazenda": {
        "id": "97bc0c8b-a7bf-49e0-a311-4db4ad897a10",
        "titulo": "Ministério da Fazenda",
    },
    "agencia-nacional-de-vigilancia-sanitaria-anvisa": {
        "id": "1a04b59b-c243-40d8-95f8-5cf3e10e4aea",
        "titulo": "ANVISA - Agência Nacional de Vigilância Sanitária",
    },
    "ministerio-do-esporte": {
        "id": "d0673d09-1824-44b1-98c7-7fdb1e7c1693",
        "titulo": "Ministério do Esporte",
    },
}

# Prioridade scout (alta → baixa). ANA/AL/ME no fim.
ORG_SEED_PRIORITY: tuple[str, ...] = (
    "instituto-brasileiro-de-geografia-e-estatistica-ibge",
    "ministerio-das-cidades",
    "distrito-federal",
    "prefeitura-de-belo-horizonte-pbh",
    "estado-do-rio-de-janeiro",
    "prefeitura-municipal-de-fortaleza",
    "ministerio-da-fazenda",
    "agencia-nacional-de-vigilancia-sanitaria-anvisa",
    "ministerio-do-esporte",
    "ipea",
    "ministerio-da-economia-me",
    "agencia-nacional-de-aguas-e-saneamento-basico",
    "estado-de-alagoas-al",
)

# Hints nomeConjuntoDados a partir de tema CGU (lista não filtra por tema).
GROUP_NOME_HINTS: dict[str, tuple[str, ...]] = {
    "Habitação": ("habitacao", "habit", "moradia", "domicilio"),
    "Urbanismo": ("urban", "bairro", "aglomerado"),
    "Planejamento e Gestão": ("planejamento", "pdad", "plano diretor"),
    "Economia e Finanças": ("pib", "renda", "economia"),
    "Esporte e Lazer": ("esporte", "lazer", "academia", "condicionamento fisico"),
    "Comércio e Serviços": ("comercio", "servico", "estabelecimento"),
    "Saúde": ("vigilancia sanitaria", "anvisa", "alvara", "licenca de funcionamento"),
    "Saneamento": ("saneamento", "esgoto"),
}

# Temas oficiais CGU (groups) — nomes idênticos ao PREENCHIMENTO-CKAN.md
# Ref: https://github.com/cgugovbr/guia-ckan/blob/master/PREENCHIMENTO-CKAN.md
CGU_GROUPS_ALL: tuple[str, ...] = (
    "Abastecimento",
    "Administração",
    "Agropecuária, Pesca e Extrativismo",
    "Comércio e Serviços",
    "Comunicações",
    "Cultura",
    "Defesa Nacional",
    "Economia e Finanças",
    "Educação",
    "Energia",
    "Esporte e Lazer",
    "Habitação",
    "Indústria",
    "Infraestrutura e Fomento",
    "Meio Ambiente",
    "Pesquisa e Desenvolvimento",
    "Planejamento e Gestão",
    "Previdência Social",
    "Proteção Social",
    "Relações Internacionais",
    "Saneamento",
    "Saúde",
    "Segurança e Ordem Pública",
    "Trabalho",
    "Transportes",
    "Urbanismo",
)

# Prioridade demografia / geo / habitação / oferta fitness
CGU_GROUPS_DEMO_GEO: tuple[str, ...] = (
    "Habitação",
    "Urbanismo",
    "Planejamento e Gestão",
    "Economia e Finanças",
    "Esporte e Lazer",
    "Comércio e Serviços",
)

# Extras customizados CGU (chave exatamente assim no package.extras)
CGU_EXTRA_KEYS: tuple[str, ...] = (
    "periodicidade",
    "coberturaTemporalInicio",
    "coberturaTemporalFim",
    "coberturaEspacial",  # FEDERAL | ESTADUAL | MUNICIPAL
    "valorCoberturaEspacial",  # UF ou IBGE 6 dígitos
    "granularidadeEspacial",
    "atualizacaoVersao",
    "descontinuado",
    "dataDescontinuacao",
    "observanciaLegal",
    "dadosAbertos",
    "relacaoOds",
    "ods",
    "dadosRacaEtnia",
    "dadosGenero",
)

_ACOES_GET = {
    "package_search",
    "package_show",
    "status_show",
    "organization_list",
    "group_list",
    "tag_list",
}


def _auth_headers(portal_base: str) -> dict[str, str]:
    """Header de autenticação por portal. dados.gov.br usa chave do gateway
    federal; CKAN puro usa Authorization."""
    key = os.getenv("CKAN_API_KEY", "").strip()
    if not key:
        return {}
    header = os.getenv("CKAN_API_KEY_HEADER", "").strip()
    if not header:
        header = "chave-api-dados-abertos" if "dados.gov.br" in portal_base else "Authorization"
    return {header: key}


def _public_headers() -> dict[str, str]:
    """Headers REST pública dados.gov (sempre chave federal se houver)."""
    headers = {"User-Agent": "gymsite-intelligence/1.0", "Accept": "application/json"}
    headers.update(_auth_headers(DEFAULT_PORTAL))
    return headers


def _is_dados_gov(portal_base: str | None) -> bool:
    return "dados.gov.br" in (portal_base or DEFAULT_PORTAL)


class CkanApiError(Exception):
    def __init__(self, action: str, message: str, *, help_text: str | None = None):
        super().__init__(f"CKAN {action}: {message}")
        self.action = action
        self.help_text = help_text


class DadosGovPublicError(Exception):
    def __init__(self, path: str, message: str):
        super().__init__(f"dados.gov public {path}: {message}")
        self.path = path


def dados_gov_public_get(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Any:
    """GET JSON em https://dados.gov.br/dados/api/... (OpenAPI v3)."""
    path = path if path.startswith("/") else f"/{path}"
    url = f"{PUBLIC_API_BASE}{path}"
    try:
        with httpx.Client(
            timeout=timeout_s, follow_redirects=True, headers=_public_headers()
        ) as client:
            resp = client.get(url, params=params or {})
    except httpx.HTTPError as exc:
        raise DadosGovPublicError(path, str(exc)) from exc
    if resp.status_code >= 400:
        raise DadosGovPublicError(path, f"HTTP {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise DadosGovPublicError(path, "resposta não é JSON") from exc


def list_conjuntos_dados(
    *,
    pagina: int = 1,
    nome_conjunto: str | None = None,
    id_organizacao: str | None = None,
    dados_abertos: bool | None = None,
    is_privado: str | bool | None = "false",
) -> list[dict[str, Any]]:
    """
    GET /publico/conjuntos-dados — filtros documentados no OpenAPI.
    Retorna lista (pode ser vazia). Paginação: ~15 itens/página.
    """
    params: dict[str, Any] = {"pagina": int(pagina)}
    if nome_conjunto:
        params["nomeConjuntoDados"] = nome_conjunto
    if id_organizacao:
        params["idOrganizacao"] = id_organizacao
    if dados_abertos is not None:
        params["dadosAbertos"] = dados_abertos
    if is_privado is not None:
        params["isPrivado"] = is_privado
    data = dados_gov_public_get("/publico/conjuntos-dados", params)
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def get_conjunto_dados(conjunto_id: str) -> dict[str, Any]:
    """GET /publico/conjuntos-dados/{id} — metadados CGU completos."""
    data = dados_gov_public_get(f"/publico/conjuntos-dados/{conjunto_id}")
    if not isinstance(data, dict):
        raise DadosGovPublicError(
            f"/publico/conjuntos-dados/{conjunto_id}", "result inválido"
        )
    return data


def list_temas_publico() -> list[dict[str, Any]]:
    """GET /temas — 26 temas VCGE do portal."""
    data = dados_gov_public_get("/temas")
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def resolve_org_seed(
    org_slugs: list[str] | None = None,
    *,
    priority_only: bool = True,
) -> list[tuple[str, str]]:
    """[(slug, uuid), ...] a partir de ORG_SEED / ORG_SEED_PRIORITY."""
    if org_slugs:
        out: list[tuple[str, str]] = []
        for slug in org_slugs:
            meta = ORG_SEED.get(slug)
            if not meta:
                logger.warning("ORG_SEED miss slug=%s", slug)
                continue
            out.append((slug, meta["id"]))
        return out
    order = ORG_SEED_PRIORITY if priority_only else tuple(ORG_SEED.keys())
    return [(s, ORG_SEED[s]["id"]) for s in order if s in ORG_SEED]


def _tema_labels(temas: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(temas, list):
        return out
    for t in temas:
        if isinstance(t, dict):
            label = t.get("title") or t.get("displayName") or t.get("name")
            if label:
                out.append(str(label))
        elif t:
            out.append(str(t))
    return out


def summarize_conjunto_publico(
    detail: dict[str, Any],
    *,
    portal: str = DEFAULT_PORTAL,
) -> dict[str, Any]:
    """Mesmo shape de summarize_package, a partir do JSON público."""
    temas = _tema_labels(detail.get("temas"))
    cobertura = detail.get("coberturaEspacial")
    valor = detail.get("valorCoberturaEspacial")
    if cobertura is not None:
        cobertura = str(cobertura).strip() or None
    if valor is not None:
        valor = str(valor).strip() or None
    descont = detail.get("descontinuado")
    discontinued = descont is True or str(descont).lower() == "true"
    org = detail.get("organizacao")
    resources = detail.get("recursos") or []
    n_res = len(resources) if isinstance(resources, list) else 0
    return {
        "id": detail.get("id"),
        "name": detail.get("nome") or detail.get("name"),
        "title": detail.get("titulo") or detail.get("title"),
        "organization": org,
        "portal": portal,
        "groups": temas,
        "cgu_extras": {
            k: str(detail[k])
            for k in CGU_EXTRA_KEYS
            if detail.get(k) is not None and str(detail.get(k)).strip() != ""
        },
        "discontinued": discontinued,
        "join_ibge6": valor if cobertura == "MUNICIPAL" else None,
        "join_uf": valor if cobertura == "ESTADUAL" else None,
        "metadata_modified": detail.get("dataUltimaAtualizacaoMetadados")
        or detail.get("dataCatalogacao"),
        "n_recursos": n_res,
        "api": "publico",
    }


def _matches_groups(summ: dict[str, Any], groups: list[str] | None) -> bool:
    if not groups:
        return True
    have = {g.casefold() for g in (summ.get("groups") or [])}
    want = {g.casefold() for g in groups}
    return bool(have & want)


def _matches_cobertura(
    summ: dict[str, Any],
    cobertura: str | None,
    valor: str | None,
) -> bool:
    extras = summ.get("cgu_extras") or {}
    if cobertura:
        got = (extras.get("coberturaEspacial") or "").upper()
        if got != cobertura.strip().upper():
            return False
    if valor:
        if (extras.get("valorCoberturaEspacial") or "").strip() != valor.strip():
            return False
    return True


def _nome_hints_for_groups(groups: list[str] | None) -> list[str]:
    if not groups:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for g in groups:
        for hint in GROUP_NOME_HINTS.get(g, ()):
            if hint not in seen:
                seen.add(hint)
                out.append(hint)
        # fallback: primeira palavra do tema sem acento grosso
        token = g.split()[0].casefold()
        if token not in seen and len(token) >= 4:
            seen.add(token)
            out.append(token)
    return out


def search_datasets_org_seed(
    *,
    org_slugs: list[str] | None = None,
    nome_queries: list[str] | None = None,
    groups: list[str] | None = None,
    cobertura: str | None = None,
    valor_cobertura: str | None = None,
    max_pages_per_org: int = 8,
    max_pages_per_nome: int = 3,
    enrich: bool = True,
    skip_discontinued: bool = True,
    require_group_match: bool = False,
) -> list[dict[str, Any]]:
    """
    Scout federal via ORG_SEED + API pública.

    - Varre idOrganizacao (páginas limitadas).
    - Opcional: nomeConjuntoDados (hints de tema ou queries explícitas).
    - enrich=True: GET detalhe (temas/cobertura reais; IPEA precisa disso).
    - groups/cobertura filtrados client-side no detalhe.
    - require_group_match=True: descarta se temas não cruzarem `groups`.
    """
    if not os.getenv("CKAN_API_KEY", "").strip():
        logger.warning("search_datasets_org_seed: falta CKAN_API_KEY")
        return []

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    nomes = list(nome_queries) if nome_queries else _nome_hints_for_groups(groups)

    def _ingest(items: list[dict[str, Any]], *, matched_via: str) -> None:
        for pkg in items:
            pid = str(pkg.get("id") or "")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            detail = pkg
            if enrich:
                try:
                    detail = get_conjunto_dados(pid)
                except DadosGovPublicError as exc:
                    logger.warning("get_conjunto falhou id=%s: %s", pid, exc)
                    detail = pkg
            summ = summarize_conjunto_publico(
                detail if isinstance(detail, dict) else pkg
            )
            if skip_discontinued and summ.get("discontinued"):
                continue
            if not _matches_cobertura(summ, cobertura, valor_cobertura):
                continue
            if require_group_match and not _matches_groups(summ, groups):
                continue
            if groups and _matches_groups(summ, groups):
                matched = next(
                    (
                        g
                        for g in groups
                        if g.casefold()
                        in {x.casefold() for x in (summ.get("groups") or [])}
                    ),
                    groups[0],
                )
                summ["matched_group"] = matched
            else:
                summ["matched_group"] = None
            summ["matched_via"] = matched_via
            out.append(summ)

    for slug, oid in resolve_org_seed(org_slugs):
        for page in range(1, max_pages_per_org + 1):
            try:
                items = list_conjuntos_dados(pagina=page, id_organizacao=oid)
            except DadosGovPublicError as exc:
                logger.warning("list org=%s page=%s: %s", slug, page, exc)
                break
            if not items:
                break
            _ingest(items, matched_via=f"org:{slug}")
            if len(items) < PUBLIC_PAGE_SIZE:
                break

    for nome in nomes:
        for page in range(1, max_pages_per_nome + 1):
            try:
                items = list_conjuntos_dados(pagina=page, nome_conjunto=nome)
            except DadosGovPublicError as exc:
                logger.warning("list nome=%s page=%s: %s", nome, page, exc)
                break
            if not items:
                break
            _ingest(items, matched_via=f"nome:{nome}")
            if len(items) < PUBLIC_PAGE_SIZE:
                break

    return out


def ckan_action(
    action: str,
    params: dict[str, Any] | None = None,
    *,
    portal_base: str = DEFAULT_PORTAL,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> Any:
    """
    GET (ações de leitura) ou POST /api/3/action/<action>.

    Retorna `result` quando success=true; senão levanta CkanApiError.
    Valores list em params viram query keys repetidas (ex.: fq=a&fq=b).
    """
    base = portal_base.rstrip("/")
    url = f"{base}/api/3/action/{action}"
    body = params or {}
    headers = {"User-Agent": "gymsite-intelligence/1.0", **_auth_headers(base)}
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True, headers=headers) as client:
            if action in _ACOES_GET:
                resp = client.get(url, params=body)
            else:
                resp = client.post(url, json=body)
    except httpx.HTTPError as exc:
        raise CkanApiError(action, str(exc)) from exc

    if resp.status_code >= 400:
        raise CkanApiError(action, f"HTTP {resp.status_code}: {resp.text[:300]}")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise CkanApiError(action, "resposta não é JSON") from exc

    if not payload.get("success"):
        err = payload.get("error") or {}
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise CkanApiError(action, msg or "success=false", help_text=payload.get("help"))

    return payload.get("result")


def package_search(
    query: str,
    *,
    rows: int = 10,
    start: int = 0,
    fq: str | list[str] | None = None,
    portal_base: str = DEFAULT_PORTAL,
) -> dict[str, Any]:
    """Busca facetada Solr via CKAN. `fq` pode ser um filtro ou lista."""
    params: dict[str, Any] = {"q": query, "rows": rows, "start": start}
    if fq:
        params["fq"] = fq if isinstance(fq, list) else [fq]
    result = ckan_action("package_search", params, portal_base=portal_base)
    if not isinstance(result, dict):
        return {"count": 0, "results": []}
    return result


def package_show(
    package_id: str,
    *,
    portal_base: str = DEFAULT_PORTAL,
) -> dict[str, Any]:
    """Metadados completos de um dataset (package)."""
    result = ckan_action(
        "package_show",
        {"id": package_id},
        portal_base=portal_base,
    )
    if not isinstance(result, dict):
        raise CkanApiError("package_show", "result inválido")
    return result


def extract_cgu_extras(pkg: dict[str, Any]) -> dict[str, str]:
    """Extrai extras oficiais CGU de um package (package_show / search hit)."""
    raw: dict[str, str] = {}
    for ex in pkg.get("extras") or []:
        if not isinstance(ex, dict):
            continue
        k = str(ex.get("key") or "").strip()
        v = str(ex.get("value") or "").strip()
        if k:
            raw[k] = v
    return {k: raw[k] for k in CGU_EXTRA_KEYS if k in raw}


def extract_groups(pkg: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for g in pkg.get("groups") or []:
        if isinstance(g, dict):
            name = g.get("display_name") or g.get("title") or g.get("name")
            if name:
                out.append(str(name))
        elif g:
            out.append(str(g))
    return out


def fq_group(group: str) -> str:
    """Filtro Solr para tema CGU (aspas — nomes com espaço/acento)."""
    g = (group or "").strip()
    return f'groups:"{g}"'


def fq_cobertura(
    cobertura: str | None = None,
    *,
    valor: str | None = None,
) -> list[str]:
    """
    Filtros extras CGU. Sintaxe Solr `extras_KEY` — portais sem índice
    de extras retornam 0 hits (esperado em municipais).
    """
    out: list[str] = []
    if cobertura:
        out.append(f"extras_coberturaEspacial:{cobertura.strip().upper()}")
    if valor:
        out.append(f"extras_valorCoberturaEspacial:{valor.strip()}")
    return out


def summarize_package(pkg: dict[str, Any], *, portal: str) -> dict[str, Any]:
    """Resumo estável pra catálogo / smoke / batch."""
    org = pkg.get("organization") or {}
    extras = extract_cgu_extras(pkg)
    discontinued = (extras.get("descontinuado") or "").lower() == "true"
    cobertura = extras.get("coberturaEspacial")
    valor = extras.get("valorCoberturaEspacial")
    return {
        "id": pkg.get("id"),
        "name": pkg.get("name"),
        "title": pkg.get("title"),
        "organization": org.get("title") if isinstance(org, dict) else org,
        "portal": portal,
        "groups": extract_groups(pkg),
        "cgu_extras": extras,
        "discontinued": discontinued,
        "join_ibge6": valor if cobertura == "MUNICIPAL" else None,
        "join_uf": valor if cobertura == "ESTADUAL" else None,
        "metadata_modified": pkg.get("metadata_modified"),
    }


def discover_demografia_queries(cidade: str, uf: str) -> list[str]:
    """Queries sugeridas para batch municipal (legado city-scoped)."""
    cidade = (cidade or "").strip()
    uf = (uf or "").strip().upper()
    return [
        f"{cidade} renda bairro",
        f"{cidade} {uf} censo demografia",
        f"{cidade} populacao ibge",
        "ipece fortaleza bairros" if cidade.lower() == "fortaleza" else f"ipece {cidade}",
    ]


def portais_para_cidade(cidade: str) -> list[str]:
    """Portais a consultar, em ordem: municipal aberto primeiro, federal depois
    (o federal exige CKAN_API_KEY — sem ela, é pulado com 1 warning)."""
    portais = []
    municipal = PORTAIS_MUNICIPAIS.get((cidade or "").strip().lower())
    if municipal:
        portais.append(municipal)
    if os.getenv("CKAN_API_KEY", "").strip():
        portais.append(DEFAULT_PORTAL)
    elif not municipal:
        portais.append(DEFAULT_PORTAL)
    return portais


def portais_macro(*, include_municipal: bool = False) -> list[str]:
    """Portais pro scout macro. Federal só com CKAN_API_KEY."""
    out: list[str] = []
    if os.getenv("CKAN_API_KEY", "").strip():
        out.append(DEFAULT_PORTAL)
    if include_municipal:
        out.extend(PORTAIS_MUNICIPAIS.values())
    elif not out:
        # sem key: ainda permite probe municipal (extras CGU ausentes)
        out.extend(PORTAIS_MUNICIPAIS.values())
    return out


def search_datasets_macro(
    *,
    groups: list[str] | None = None,
    q: str = "*:*",
    cobertura: str | None = None,
    valor_cobertura: str | None = None,
    rows_per_group: int = 10,
    portal_base: str | None = None,
    enrich: bool = True,
    skip_discontinued: bool = True,
    org_slugs: list[str] | None = None,
    max_pages_per_org: int = 8,
    require_group_match: bool = False,
) -> list[dict[str, Any]]:
    """
    Scout MACRO por tema CGU (+ extras opcionais). Não amarra a um município.

    Federal (dados.gov.br): API pública + ORG_SEED (Action /api/3 morta/401).
    Município / outro portal: package_search Solr (Action).

    `groups` default = CGU_GROUPS_DEMO_GEO.
    """
    groups = list(groups) if groups is not None else list(CGU_GROUPS_DEMO_GEO)
    portais = [portal_base] if portal_base else portais_macro(include_municipal=False)
    if not portais:
        logger.warning("search_datasets_macro: nenhum portal (falta CKAN_API_KEY?)")
        return []

    # Federal → REST pública
    if all(_is_dados_gov(p) for p in portais):
        return search_datasets_org_seed(
            org_slugs=org_slugs,
            groups=groups,
            cobertura=cobertura,
            valor_cobertura=valor_cobertura,
            max_pages_per_org=max_pages_per_org,
            # rows_per_group ≈ páginas de nome-hint (fraco); org pages dominante
            max_pages_per_nome=max(1, min(5, rows_per_group // 3 or 1)),
            enrich=enrich,
            skip_discontinued=skip_discontinued,
            require_group_match=require_group_match,
        )

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    extra_fq = fq_cobertura(cobertura, valor=valor_cobertura)

    for portal in portais:
        if _is_dados_gov(portal):
            out.extend(
                search_datasets_org_seed(
                    org_slugs=org_slugs,
                    groups=groups,
                    cobertura=cobertura,
                    valor_cobertura=valor_cobertura,
                    max_pages_per_org=max_pages_per_org,
                    enrich=enrich,
                    skip_discontinued=skip_discontinued,
                    require_group_match=require_group_match,
                )
            )
            continue
        for group in groups:
            fq: list[str] = [fq_group(group), *extra_fq]
            try:
                data = package_search(q, rows=rows_per_group, fq=fq, portal_base=portal)
            except CkanApiError as exc:
                try:
                    fq_alt = [f"groups:{group}", *extra_fq]
                    data = package_search(
                        q, rows=rows_per_group, fq=fq_alt, portal_base=portal
                    )
                except CkanApiError as exc2:
                    logger.warning(
                        "package_search macro falhou portal=%s group=%s: %s / %s",
                        portal,
                        group,
                        exc,
                        exc2,
                    )
                    continue
            for pkg in data.get("results") or []:
                if not isinstance(pkg, dict):
                    continue
                pid = str(pkg.get("id") or pkg.get("name") or "")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                full = pkg
                if enrich:
                    try:
                        full = package_show(pid, portal_base=portal)
                    except CkanApiError:
                        full = pkg
                summ = summarize_package(
                    full if isinstance(full, dict) else pkg, portal=portal
                )
                if skip_discontinued and summ.get("discontinued"):
                    continue
                summ["matched_group"] = group
                out.append(summ)
    return out


def search_datasets_for_city(
    cidade: str,
    uf: str,
    *,
    portal_base: str | None = None,
    max_per_query: int = 5,
) -> list[dict[str, Any]]:
    """
    Agrega resultados de package_search sem duplicar por id, varrendo o portal
    municipal (quando mapeado) e o federal (quando autenticado).
    Retorna lista resumida: id, name, title, organization, portal.

    Preferir `search_datasets_macro` pra descoberta federal por tema.
    """
    portais = [portal_base] if portal_base else portais_para_cidade(cidade)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for portal in portais:
        out.extend(_search_one_portal(cidade, uf, portal, max_per_query, seen))
    return out


def _search_one_portal(
    cidade: str,
    uf: str,
    portal: str,
    max_per_query: int,
    seen: set[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for q in discover_demografia_queries(cidade, uf):
        try:
            data = package_search(q, rows=max_per_query, portal_base=portal)
        except CkanApiError as exc:
            logger.warning("package_search falhou portal=%s q=%s: %s", portal, q, exc)
            continue
        for pkg in data.get("results") or []:
            if not isinstance(pkg, dict):
                continue
            pid = str(pkg.get("id") or pkg.get("name") or "")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            org = pkg.get("organization") or {}
            out.append(
                {
                    "id": pid,
                    "name": pkg.get("name"),
                    "title": pkg.get("title"),
                    "organization": org.get("title") if isinstance(org, dict) else org,
                    "portal": portal,
                }
            )
    return out
