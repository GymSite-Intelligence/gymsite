"""
Popular Times Tool — extrai horários de pico de fichas Google Maps.

DESCOBERTA TÉCNICA (validada em 2026-05-08, revisada 2026-06-03):
- Os 168 dados (24h × 7 dias) costumam estar no DOM após a seção carregar.
- Em fichas Smart Fit / redes grandes a seção **"Horários de pico"** é lazy:
  exige scroll no painel `.m6QErb` / `[role=main]` antes dos aria-labels.
- URLs `place/{nome}/@.../1sChIJ` redirecionam para `place//` (painel vazio);
  usar busca georreferenciada ou `googleMapsUri` com ftid `0x:0x`.
- Aria-label estável: "Movimento às HH:00: XX%."
- httpx puro NÃO funciona — Maps é SPA, dados vêm via JS bundle pós-load.
  matches_movimento_as = 0 em HTML cru de 178KB.
- Playwright + wait_for_selector funciona — encontra elementos off-screen.

PATTERN WINDOWS PYTHON 3.14 + ADK:
Usa playwright.sync_api dentro de asyncio.to_thread (mesmo motivo de
tools/playwright_enrichment.py): ADK roda em SelectorEventLoop e
playwright.async_api falha com NotImplementedError em
create_subprocess_exec. sync_api isola o subprocess do loop principal.

CACHE:
- TTL 7 dias para status="ok"
- TTL 1 dia para status="sem_popular_times" (Google pode passar a expor depois
  que ganha mais data points; reavalia cedo)
- Ordem: Supabase `cache_popular_times` (durável no Cloud Run) → FS
  `competitor_cache/` (dev / mesma instância). Write-through nos dois.
"""
import asyncio
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from tools.parametros_metodologia import param, param_int

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


CACHE_DIR = Path(__file__).resolve().parent.parent / "competitor_cache"
CACHE_TTL_OK_DAYS = 7
CACHE_TTL_SEM_DADOS_DAYS = 1

DIAS_SEMANA = ["domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado"]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _slug_place(place_id: str) -> str:
    """Sanitiza place_id pra nome de arquivo."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", place_id)[:80] or "anon"


def _cache_path(place_id: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_slug_place(place_id)}_peak.json"


def _cache_valido(path: Path, status_cached: str) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    ttl = CACHE_TTL_OK_DAYS if status_cached == "ok" else CACHE_TTL_SEM_DADOS_DAYS
    return (datetime.now() - mtime) < timedelta(days=ttl)


def _load_pico_cache(
    place_id: str,
    *,
    force_refresh: bool,
    nome: str,
    lat: float | None,
    lng: float | None,
) -> dict | None:
    """Hit order: Supabase `cache_popular_times` (Cloud Run) → FS legado.

    ADR/SPEC_a3a_store_v2: FS em `/tmp` some no CR — SB é a fonte durável.
    """
    if not place_id or force_refresh:
        return None

    # 1) Supabase
    try:
        from tools.cache_store import get_popular_times

        hit = get_popular_times(place_id)
        if hit.hit and isinstance(hit.payload, dict):
            row = hit.payload
            dados = row.get("payload") if isinstance(row.get("payload"), dict) else None
            if dados is None and row.get("status"):
                # row já é o payload em alguns upserts legados
                dados = {k: v for k, v in row.items() if k not in (
                    "place_id", "cached_at", "expires_at", "last_hit_at", "hit_count"
                )}
            if isinstance(dados, dict):
                cached_status = dados.get("status") or row.get("status") or "ok"
                if cached_status in ("ok", "sem_popular_times") and not _cache_deve_ignorar(
                    dados, force_refresh=False, nome=nome, lat=lat, lng=lng
                ):
                    out = dict(dados)
                    out["status"] = cached_status
                    out["cached"] = True
                    out["cache_fonte"] = "supabase"
                    return out
    except Exception:
        pass

    # 2) FS local (dev / warm same-instance)
    cp = _cache_path(place_id)
    if not cp.exists():
        return None
    try:
        dados = json.loads(cp.read_text(encoding="utf-8"))
        cached_status = dados.get("status", "ok")
        if _cache_valido(cp, cached_status) and not _cache_deve_ignorar(
            dados, force_refresh=False, nome=nome, lat=lat, lng=lng
        ):
            dados["cached"] = True
            dados["cache_fonte"] = "fs"
            return dados
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _save_pico_cache(place_id: str, resultado: dict) -> None:
    """Grava FS (best-effort) + Supabase TTL (obrigatório no hot-path CR)."""
    if not place_id:
        return
    status = resultado.get("status")
    if status not in ("ok", "sem_popular_times"):
        return
    try:
        cp = _cache_path(place_id)
        cp.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    try:
        from tools.cache_store import set_popular_times

        set_popular_times(
            place_id,
            resultado,
            status=status,
            ttl_days_ok=CACHE_TTL_OK_DAYS,
            ttl_days_sem_dados=CACHE_TTL_SEM_DADOS_DAYS,
        )
    except Exception:
        pass


def _parsear_aria_label(label: str):
    """
    Parse aria-label de popular times. Suporta 2 formatos:
    - PT-BR: "Movimento às 14:00: 52%." → ("14", 52)
    - EN:    "Busy at 6 PM: 87%."       → ("18", 87)
    Retorna None se padrão não bate.
    """
    # Formato PT-BR: "Movimento às HH:00: XX%."
    if "Movimento às" in label:
        try:
            depois_as = label.split("às ")[1]               # "14:00: 52%."
            hora = depois_as.split(":")[0].strip()          # "14"
            pct_str = label.split(": ")[-1].replace("%.", "").replace("%", "").strip()
            pct = int(pct_str)
            if 0 <= pct <= 100 and hora.isdigit() and 0 <= int(hora) <= 23:
                return (hora, pct)
        except (IndexError, ValueError):
            return None

    # Formato EN: "Busy at 6 PM: 87%." ou "Usually busy at 6 PM: 87%."
    if "Busy at" in label or "busy at" in label:
        try:
            # Extrai hora AM/PM: "Busy at 6 PM: 87%." → pct=87, hour=18
            m_hora = re.search(r"at (\d{1,2})\s*(AM|PM)", label, re.IGNORECASE)
            pct_str = label.split(": ")[-1].replace("%.", "").replace("%", "").strip()
            if m_hora:
                h = int(m_hora.group(1))
                period = m_hora.group(2).upper()
                if period == "PM" and h != 12:
                    h += 12
                elif period == "AM" and h == 12:
                    h = 0
                pct = int(pct_str)
                if 0 <= pct <= 100 and 0 <= h <= 23:
                    return (str(h), pct)
        except (IndexError, ValueError, AttributeError):
            return None

    return None


def _calcular_perfil(hora_pico_str: str, max_pct: int, min_pct: int, picos_altos: list) -> str:
    try:
        hora = int(hora_pico_str)
    except (ValueError, TypeError):
        return "indeterminado"
    spread = max_pct - min_pct
    if spread < param("pop_spread_24h_equilibrado"):
        return "24h_equilibrado"
    if len(picos_altos) >= param_int("pop_picos_min_multi"):
        return "multi_pico"
    if param_int("pop_hora_manha_ini") <= hora <= param_int("pop_hora_manha_fim"):
        return "manha_pico"
    if param_int("pop_hora_almoco_ini") <= hora <= param_int("pop_hora_almoco_fim"):
        return "almoco_pico"
    if param_int("pop_hora_tarde_ini") <= hora <= param_int("pop_hora_tarde_fim"):
        return "tarde_pico"
    return "noite_pico"


# Textos da seção de popular times (PT-BR / EN)
_SECAO_PICO_TEXTOS = (
    "Horários de pico",
    "Horários populares",
    "Popular times",
    "Movimento normal",
    "Usually busy",
)

_POPULAR_TIMES_SELECTORS = [
    '[aria-label*="Movimento às"]',
    '[aria-label*="Busy at"]',
    '[aria-label*="Usually busy"]',
    '[aria-label*="Geralmente"]',
    '[aria-label*="Movimento normal"]',
]

_PLACE_PANEL_SELECTORS = [
    "h1.DUwDvf",
    'h1[class*="DU"]',
    'button[data-value="Rota"]',
    'button[data-value="Directions"]',
    '[aria-label*="Salvar"]',
    '[aria-label*="Save"]',
    '[role="main"]',
]

_BUSCA_RESULTADO_SELECTORS = [
    "a.hfpxzc",
    ".Nv2PK a.hfpxzc",
    '[role="feed"] a.hfpxzc',
]


def _dismiss_maps_consent(page) -> bool:
    """Fecha banner de cookies (page + iframes)."""
    for texto in ("Aceitar tudo", "Concordo", "Accept all", "I agree", "Reject all"):
        try:
            btn = page.get_by_role("button", name=texto).first
            if btn.is_visible(timeout=1200):
                btn.click()
                page.wait_for_timeout(1200)
                return True
        except Exception:
            continue
    for frame in page.frames:
        for texto in ("Aceitar tudo", "Concordo", "Accept all"):
            try:
                btn = frame.get_by_role("button", name=texto).first
                if btn.is_visible(timeout=800):
                    btn.click()
                    page.wait_for_timeout(1200)
                    return True
            except Exception:
                continue
    return False


def _scroll_maps_panel(page, steps: int = 10, delta: int = 650, delay_ms: int = 550) -> None:
    """Scroll no painel lateral — força lazy-load de Horários de pico."""
    scroll_js = f"""
    () => {{
      const els = [
        document.querySelector('[role="main"]'),
        ...document.querySelectorAll('.m6QErb.DxyBCb'),
        ...document.querySelectorAll('.m6QErb'),
      ].filter(Boolean);
      for (const el of els) el.scrollTop += {delta};
      return els.length;
    }}
    """
    try:
        for _ in range(steps):
            page.evaluate(scroll_js)
            page.wait_for_timeout(delay_ms)
    except Exception:
        pass


def _painel_place_texto(page) -> str:
    try:
        return page.evaluate(
            "() => { const m = document.querySelector('[role=\"main\"]'); "
            "return m ? (m.innerText || '') : ''; }"
        ) or ""
    except Exception:
        return ""


def _painel_place_ok(page) -> bool:
    """Painel com ficha real (não stub de login / place// vazio)."""
    url = (page.url or "").lower()
    if "/maps/place//" in url or url.rstrip("/").endswith("/place"):
        return False
    txt = _painel_place_texto(page)
    if len(txt) < 280:
        return False
    if "Fazer login" in txt and "Horários de pico" not in txt and "Horários populares" not in txt:
        return False
    return True


def _abrir_primeiro_resultado_busca(page) -> bool:
    for sel in _BUSCA_RESULTADO_SELECTORS:
        try:
            page.wait_for_selector(sel, timeout=10000)
            page.locator(sel).first.click()
            page.wait_for_timeout(2800)
            return _painel_place_ok(page)
        except Exception:
            continue
    return False


def _scroll_ate_secao_pico(page) -> bool:
    """Rola até achar texto da seção ou aria-label de barra."""
    for _ in range(14):
        for texto in _SECAO_PICO_TEXTOS:
            try:
                loc = page.get_by_text(texto, exact=False).first
                if loc.count() and loc.is_visible(timeout=400):
                    loc.scroll_into_view_if_needed(timeout=2000)
                    page.wait_for_timeout(800)
                    return True
            except Exception:
                continue
        for sel in _POPULAR_TIMES_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.count():
                    loc.scroll_into_view_if_needed(timeout=2000)
                    page.wait_for_timeout(800)
                    return True
            except Exception:
                continue
        _scroll_maps_panel(page, steps=1, delta=700, delay_ms=500)
    return False


_RE_ARIA_MOVIMENTO_HTML = re.compile(
    r'aria-label="((?:Movimento[^"]{8,120}|(?:Usually )?Busy at[^"]{5,80}|Geralmente[^"]{5,80}))"',
    re.IGNORECASE,
)


def _coletar_movimentos_aria(page) -> list:
    movimentos = page.evaluate(
        "() => { const out = []; "
        "document.querySelectorAll('[aria-label]').forEach(el => { "
        "const l = el.getAttribute('aria-label') || ''; "
        "if (l.indexOf('Movimento \\u00e0s') !== -1 || l.indexOf('Busy at') !== -1 "
        "|| l.indexOf('Usually') !== -1 || l.indexOf('Geralmente') !== -1 "
        "|| /Movimento (?:normal|moderado|alto)/i.test(l)) out.push(l); "
        "}); return out; }"
    )
    if movimentos:
        return movimentos
    # Fallback: labels no HTML (off-screen / ainda não no DOM acessível via querySelector)
    try:
        html = page.content()
        found = _RE_ARIA_MOVIMENTO_HTML.findall(html)
        # dedupe preservando ordem
        seen: set[str] = set()
        out: list[str] = []
        for label in found:
            if label not in seen:
                seen.add(label)
                out.append(label)
        return out
    except Exception:
        return []


def _cache_deve_ignorar(
    dados: dict,
    *,
    force_refresh: bool,
    nome: str,
    lat: float | None,
    lng: float | None,
) -> bool:
    if force_refresh:
        return True
    if dados.get("status") != "sem_popular_times":
        return False
    # SearchAPI já respondeu "sem pico" — não reabrir Playwright por ter coords.
    if (dados.get("fonte") or "") == "searchapi":
        return False
    # Re-scrape só quando falso negativo Playwright (URL place//) + busca rica.
    return bool((nome or "").strip() and lat is not None and lng is not None)


def _calcular_oportunidade(resumo_por_dia: dict) -> str:
    if not resumo_por_dia:
        return "Dados insuficientes para análise de oportunidade."

    perfis = [r["perfil"] for r in resumo_por_dia.values()]

    dias_min = param_int("pop_dias_min_perfil")
    if perfis.count("tarde_pico") >= dias_min:
        return (
            "Concorrente concentrado no horário 17-20h. "
            "Oportunidade: programa diferenciado na manhã (06-10h) com personal incluso."
        )
    if perfis.count("manha_pico") >= dias_min:
        return (
            "Concorrente com pico matutino. "
            "Oportunidade: aulas noturnas premium e madrugada com personal."
        )
    if perfis.count("almoco_pico") >= dias_min:
        return (
            "Pico concentrado no almoço. "
            "Oportunidade: treinos express 30min manhã/noite para quem não pode no almoço."
        )

    dias_uteis = ["segunda", "terca", "quarta", "quinta"]
    dias_uteis_baixos = [
        d for d in dias_uteis
        if resumo_por_dia.get(d, {}).get("pct_vale", 100) <= param("pop_vale_midweek_max")
    ]
    if len(dias_uteis_baixos) >= param_int("pop_dias_min_vale_midweek"):
        return (
            f"Movimento muito baixo em dias úteis ({', '.join(dias_uteis_baixos)}). "
            "Oportunidade: programa de fidelização mid-week com benefícios exclusivos."
        )

    if perfis.count("24h_equilibrado") >= dias_min:
        return (
            "Academia bem distribuída ao longo do dia. "
            "Competir por horário não é vantagem — focar em diferencial de serviço/preço."
        )

    return (
        "Padrão de pico misto ao longo da semana. "
        "Analisar dia a dia para identificar janelas específicas de oportunidade."
    )


def _extrair_sync(
    maps_url: str,
    place_id: str,
    *,
    nome: str = "",
    cidade: str = "",
    lat: float | None = None,
    lng: float | None = None,
) -> dict:
    """
    Versão SÍNCRONA do scraping. Roda em thread separada via asyncio.to_thread.
    Não chamar diretamente do código async — use pesquisar_horarios_pico().
    """
    base_result = {
        "status": "indeterminado",
        "place_id": place_id,
        "maps_url": maps_url,
        "total_pontos_extraidos": 0,
        "dados_por_dia": {},
        "resumo_por_dia": {},
        "fonte": "playwright_maps_dom",
        "data_coleta": datetime.now().strftime("%Y-%m-%d"),
        "cached": False,
    }

    if not PLAYWRIGHT_AVAILABLE:
        base_result["status"] = "erro"
        base_result["motivo"] = "playwright_nao_instalado"
        return base_result

    movimentos: list = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="pt-BR",
                viewport={"width": 1280, "height": 900},
                extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
            )
            page = context.new_page()

            try:
                page.goto(maps_url, timeout=45000, wait_until="load")
                page.wait_for_timeout(2500)
                _dismiss_maps_consent(page)
                page.wait_for_timeout(1000)

                is_search = "/maps/search/" in (maps_url or "")
                if is_search and not _painel_place_ok(page):
                    if not _abrir_primeiro_resultado_busca(page):
                        base_result["status"] = "sem_popular_times"
                        base_result["motivo"] = (
                            "Busca Maps não abriu ficha do lugar — "
                            "sem resultado clicável no feed."
                        )
                        browser.close()
                        return base_result
                else:
                    panel_found = False
                    for panel_sel in _PLACE_PANEL_SELECTORS:
                        try:
                            page.wait_for_selector(
                                panel_sel, timeout=12000, state="attached"
                            )
                            panel_found = True
                            break
                        except PlaywrightTimeout:
                            continue
                    if not panel_found:
                        if nome and lat is not None and lng is not None:
                            from tools.maps_place_id import montar_maps_url_place

                            alt = montar_maps_url_place(
                                nome, place_id, lat, lng, cidade=cidade
                            )
                            if alt and alt != maps_url:
                                page.goto(alt, timeout=45000, wait_until="load")
                                page.wait_for_timeout(2500)
                                _dismiss_maps_consent(page)
                                if "/maps/search/" in alt:
                                    _abrir_primeiro_resultado_busca(page)
                                panel_found = True
                                for panel_sel in _PLACE_PANEL_SELECTORS:
                                    try:
                                        page.wait_for_selector(
                                            panel_sel, timeout=8000, state="attached"
                                        )
                                        panel_found = True
                                        break
                                    except PlaywrightTimeout:
                                        panel_found = False
                        if not panel_found:
                            base_result["status"] = "sem_popular_times"
                            base_result["motivo"] = (
                                "Painel do lugar não carregou no Google Maps "
                                "(URL inválida, login ou redirecionamento)."
                            )
                            browser.close()
                            return base_result

                _scroll_ate_secao_pico(page)
                page.wait_for_timeout(2000)

                popular_found_sel = None
                for sel in _POPULAR_TIMES_SELECTORS:
                    try:
                        page.wait_for_selector(sel, timeout=15000)
                        popular_found_sel = sel
                        break
                    except PlaywrightTimeout:
                        continue

                movimentos = _coletar_movimentos_aria(page)

                if len(movimentos) < 24:
                    _scroll_maps_panel(page, steps=8, delay_ms=700)
                    page.wait_for_timeout(2000)
                    for sel in _POPULAR_TIMES_SELECTORS:
                        try:
                            page.wait_for_selector(sel, timeout=8000)
                            popular_found_sel = sel
                            break
                        except PlaywrightTimeout:
                            continue
                    extra = _coletar_movimentos_aria(page)
                    if len(extra) > len(movimentos):
                        movimentos = extra

                if not movimentos:
                    base_result["status"] = "sem_popular_times"
                    preview = _painel_place_texto(page)[:120].replace("\n", " ")
                    base_result["motivo"] = (
                        "Gráfico Horários de pico não encontrado após scroll "
                        f"(painel {len(_painel_place_texto(page))} chars; "
                        f"prévia: {preview!r})."
                    )
                    browser.close()
                    return base_result
            finally:
                browser.close()

    except Exception as e:
        base_result["status"] = "erro"
        base_result["motivo"] = f"playwright_error: {str(e)[:200]}"
        return base_result

    if not movimentos:
        base_result["status"] = "sem_popular_times"
        base_result["motivo"] = (
            "Seção de pico visível mas nenhum aria-label Movimento/Busy extraído."
        )
        return base_result

    # Organizar movimentos em 7 dias × 24h.
    # Premissa de ordem (validada para Top Up CT Aldeota): domingo → sábado.
    total = len(movimentos)
    horas_por_dia = total // 7 if total >= 100 else 24

    dados_por_dia = {}
    for d, dia in enumerate(DIAS_SEMANA):
        bloco = movimentos[d * horas_por_dia : (d + 1) * horas_por_dia]
        horarios = {}
        for label in bloco:
            parsed = _parsear_aria_label(label)
            if parsed:
                hora, pct = parsed
                horarios[hora] = pct
        if horarios:
            dados_por_dia[dia] = horarios

    if not dados_por_dia:
        base_result["status"] = "erro"
        base_result["motivo"] = (
            f"wait_for_selector achou {total} aria-labels mas nenhum bateu "
            f"o padrão 'Movimento às HH:00: XX%.'"
        )
        return base_result

    # Resumo por dia
    resumo_por_dia = {}
    for dia, horas in dados_por_dia.items():
        if not horas:
            continue
        max_pct = max(horas.values())
        min_pct = min(horas.values())
        hora_pico = max(horas, key=horas.get)
        hora_vale = min(horas, key=horas.get)
        picos_altos = [h for h, p in horas.items() if p >= param("pop_pct_pico_alto")]
        resumo_por_dia[dia] = {
            "hora_pico": hora_pico,
            "pct_pico": max_pct,
            "hora_vale": hora_vale,
            "pct_vale": min_pct,
            "perfil": _calcular_perfil(hora_pico, max_pct, min_pct, picos_altos),
            "horas_superlotadas": sorted([h for h, p in horas.items() if p >= param("pop_pct_superlotado")]),
            "horas_livres": sorted([h for h, p in horas.items() if p <= param("pop_pct_livre")]),
        }

    dia_mais_movimentado = None
    if resumo_por_dia:
        dia_top = max(resumo_por_dia.items(), key=lambda x: x[1]["pct_pico"])
        dia_mais_movimentado = {
            "dia": dia_top[0],
            "hora": dia_top[1]["hora_pico"],
            "percentual": dia_top[1]["pct_pico"],
        }

    # Horários livres consolidados (≤ pop_pct_muito_livre% qualquer dia)
    _muito_livre = param("pop_pct_muito_livre")
    horarios_livres = []
    for dia, horas in dados_por_dia.items():
        for h, p in horas.items():
            if p <= _muito_livre:
                horarios_livres.append(f"{dia} {h}h ({p}%)")

    base_result.update({
        "status": "ok",
        "total_pontos_extraidos": total,
        "dias_completos": len(dados_por_dia),
        "dados_por_dia": dados_por_dia,
        "resumo_por_dia": resumo_por_dia,
        "dia_mais_movimentado": dia_mais_movimentado,
        "horarios_livres_semana": horarios_livres[:10],
        "oportunidade_horario": _calcular_oportunidade(resumo_por_dia),
    })

    return base_result


def _converter_searchapi(raw: dict, place_id: str) -> dict:
    """Converte payload SearchAPI (engine=google_maps_place) → shape interno.

    SearchAPI retorna `popular_times` com `live` + `chart`:
        chart: { monday: [{time: '6 AM', busyness_score: 0}, ...], ... }

    Convertemos pra `dados_por_dia: { segunda: { '00': 0, '01': 0, ...} }`
    pra ser drop-in com o resto do pipeline.
    """
    # SearchAPI envolve tudo em `place_result`. Compatível também com payload
    # achatado (caso a estrutura mude).
    place_result = raw.get("place_result") if isinstance(raw.get("place_result"), dict) else raw
    pt = place_result.get("popular_times") or {}
    chart = pt.get("chart") if isinstance(pt, dict) else None
    if not isinstance(chart, dict):
        return {
            "status": "sem_popular_times",
            "place_id": place_id,
            "dados_por_dia": {},
            "fonte": "searchapi",
            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
            "searchapi_calls": 1,
            "cached": False,
        }

    map_dias = {
        "monday": "segunda", "tuesday": "terca", "wednesday": "quarta",
        "thursday": "quinta", "friday": "sexta",
        "saturday": "sabado", "sunday": "domingo",
    }
    dados_por_dia: dict = {}
    for dia_en, items in chart.items():
        dia_pt = map_dias.get(dia_en.lower(), dia_en.lower())
        if not isinstance(items, list):
            continue
        horas: dict = {f"{h:02d}": 0 for h in range(24)}
        for item in items:
            if not isinstance(item, dict):
                continue
            time_str = (item.get("time") or "").strip()
            hora = None
            # SearchAPI PT (gl=br&hl=pt) retorna "06:00", "18:00" (24h).
            # SearchAPI EN retorna "6 AM", "2 PM" (12h). Tentar ambos.
            for fmt in ("%H:%M", "%I %p", "%I:%M %p"):
                try:
                    hora = datetime.strptime(time_str, fmt).hour
                    break
                except ValueError:
                    continue
            if hora is None:
                continue
            horas[f"{hora:02d}"] = int(item.get("busyness_score") or 0)
        dados_por_dia[dia_pt] = horas

    # Encontra pico semanal
    max_pct = -1
    dia_top = ""
    hora_top = ""
    for dia, hrs in dados_por_dia.items():
        for h, pct in hrs.items():
            if pct > max_pct:
                max_pct = pct
                dia_top = dia
                hora_top = h

    live = pt.get("live") or {}
    return {
        "status": "ok" if max_pct > 0 else "sem_popular_times",
        "place_id": place_id,
        "dados_por_dia": dados_por_dia,
        "resumo_por_dia": {},
        "dia_mais_movimentado": {
            "dia": dia_top,
            "hora": hora_top,
            "percentual": max(0, max_pct),
        },
        "ao_vivo": live,
        "fonte": "searchapi",
        "data_coleta": datetime.now().strftime("%Y-%m-%d"),
        "searchapi_calls": 1,
        "cached": False,
    }


def _tentar_searchapi(place_id: str) -> dict | None:
    """Tier 0 — SearchAPI google_maps_place (cache compartilhado com reviews).

    1 call → popular_times + review_results. Cache em cache_places_details;
    também seeda cache_reviews. Miss de rede → None (próximo tier).
    """
    if not place_id:
        return None
    try:
        from tools.searchapi_maps_place import (
            get_or_fetch_maps_place,
            seed_reviews_cache_from_place,
        )

        raw = get_or_fetch_maps_place(place_id)
        if not raw:
            return None
        seed_reviews_cache_from_place(place_id, raw)
        return _converter_searchapi(raw, place_id)
    except Exception as e:
        print(f"[searchapi] {place_id}: {type(e).__name__}: {str(e)[:140]}")
        return None


def _converter_populartimes_lib(raw: dict, place_id: str) -> dict:
    """Converte resposta da lib populartimes pro shape interno (compat com Playwright)."""
    pt = raw.get("populartimes") or []
    dados_por_dia: dict = {}
    if isinstance(pt, list):
        for dia_dict in pt:
            if not isinstance(dia_dict, dict):
                continue
            nome_dia = (dia_dict.get("name") or "").lower()
            # lib usa "Monday", "Tuesday", ... → mapeia pra pt-BR
            map_dias = {
                "monday": "segunda", "tuesday": "terca", "wednesday": "quarta",
                "thursday": "quinta", "friday": "sexta",
                "saturday": "sabado", "sunday": "domingo",
            }
            dia_pt = map_dias.get(nome_dia, nome_dia)
            data_arr = dia_dict.get("data") or []
            if isinstance(data_arr, list) and len(data_arr) >= 24:
                dados_por_dia[dia_pt] = {
                    f"{h:02d}": int(data_arr[h] or 0) for h in range(24)
                }

    if not dados_por_dia:
        return {
            "status": "sem_popular_times",
            "place_id": place_id,
            "dados_por_dia": {},
            "resumo_por_dia": {},
            "fonte": "populartimes_lib",
            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
            "places_api_calls": 1,
            "cached": False,
        }

    # Encontra dia/hora mais movimentado
    max_pct = -1
    dia_top = ""
    hora_top = ""
    for dia, horas in dados_por_dia.items():
        for h, pct in horas.items():
            if pct > max_pct:
                max_pct = pct
                dia_top = dia
                hora_top = h

    return {
        "status": "ok",
        "place_id": place_id,
        "dados_por_dia": dados_por_dia,
        "resumo_por_dia": {},
        "dia_mais_movimentado": {
            "dia": dia_top,
            "hora": hora_top,
            "percentual": max_pct,
        },
        "current_popularity": raw.get("current_popularity"),
        "time_spent": raw.get("time_spent"),
        "fonte": "populartimes_lib",
        "data_coleta": datetime.now().strftime("%Y-%m-%d"),
        "places_api_calls": 1,
        "cached": False,
    }


_avisou_sem_chave_legacy = False
_avisou_searchapi_429 = False


def _tentar_populartimes_lib(place_id: str) -> dict | None:
    """Tenta extrair via biblioteca `populartimes` (Google Places API legacy).

    Exige PLACES_API_KEY_LEGACY dedicada. A chave Maps server NÃO serve de
    fallback: ela é restrita às APIs novas (split de chaves 2026-06-11) e cada
    tentativa gerava REQUEST_DENIED por concorrente — só ruído no log.
    """
    global _avisou_sem_chave_legacy
    if not place_id:
        return None
    try:
        import os
        import populartimes  # type: ignore[import-not-found]
        api_key = os.environ.get("PLACES_API_KEY_LEGACY", "").strip()
        if not api_key:
            if not _avisou_sem_chave_legacy:
                _avisou_sem_chave_legacy = True
                print("[popular_times lib] PLACES_API_KEY_LEGACY ausente — tier desabilitado (Playwright assume)")
            return None
        raw = populartimes.get_id(api_key, place_id)
        return _converter_populartimes_lib(raw, place_id)
    except ImportError:
        return None
    except Exception as e:
        # REQUEST_DENIED, place_id inválido, etc. — cai pro fallback Playwright
        print(f"[popular_times lib] {place_id}: {type(e).__name__}: {str(e)[:140]}")
        return None


async def pesquisar_horarios_pico(
    maps_url: str,
    place_id: str = "",
    *,
    nome: str = "",
    cidade: str = "",
    lat: float | None = None,
    lng: float | None = None,
    force_refresh: bool = False,
    place_raw: dict | None = None,
) -> dict:
    """
    Extrai horários de pico (7 dias × 24h) de uma ficha Google Maps.

    Estratégia em 3 tiers (cascata):
      0. SearchAPI google_maps_place (ou `place_raw` já buscado no A3a)
      1. Lib `populartimes` (Places API legacy) — gratuita mas frágil
      2. Playwright sync_api — OFF no hot-path (`POPULAR_TIMES_PLAYWRIGHT=1`)

    Args:
        maps_url: URL da ficha
        place_id: Place ID Google (necessário pra cache 7 dias e Tiers 0/1)
        place_raw: payload SearchAPI já em memória (A3a) — evita 2ª call + PW

    Returns:
        Dict com: status, dados_por_dia, resumo_por_dia, dia_mais_movimentado, etc.
    """
    import os as _os

    from tools.maps_place_id import extrair_hex_ftid_de_url, montar_maps_url_place

    hex_ftid = extrair_hex_ftid_de_url(maps_url)

    # Cache hit? Supabase primeiro (CR), FS depois. force_refresh ignora ambos.
    if place_id:
        cached = _load_pico_cache(
            place_id,
            force_refresh=force_refresh,
            nome=nome,
            lat=lat,
            lng=lng,
        )
        if cached is not None:
            return cached

    # Tier 0a: place já buscado no A3a (mesmo processo) — zero rede.
    if isinstance(place_raw, dict) and place_raw:
        resultado_place = _converter_searchapi(place_raw, place_id or "")
        if place_id:
            _save_pico_cache(place_id, resultado_place)
        return resultado_place

    # Tier 0b: SearchAPI
    resultado_searchapi = await asyncio.to_thread(_tentar_searchapi, place_id)
    # Qualquer resposta SearchAPI (ok OU sem_popular_times) fecha o caso —
    # NÃO cai em Playwright (long-pole ~300s/gym no smoke Cocó).
    if resultado_searchapi is not None:
        if place_id:
            _save_pico_cache(place_id, resultado_searchapi)
        return resultado_searchapi

    # Tier 1: lib populartimes (rápida, sem Chrome) — abandonware, raramente OK
    resultado_lib = await asyncio.to_thread(_tentar_populartimes_lib, place_id)
    if resultado_lib and resultado_lib.get("status") == "ok":
        if place_id:
            _save_pico_cache(place_id, resultado_lib)
        return resultado_lib

    allow_pw = (_os.getenv("POPULAR_TIMES_PLAYWRIGHT") or "0").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if not allow_pw:
        resultado = {
            "status": "sem_popular_times",
            "motivo": "playwright_skip_hot_path",
            "place_id": place_id,
            "maps_url": maps_url,
            "dados_por_dia": {},
            "resumo_por_dia": {},
            "fonte": "playwright_skipped",
            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
            "cached": False,
        }
        if place_id:
            _save_pico_cache(place_id, resultado)
        return resultado

    # Normaliza URL Playwright: evita place/{nome}/1sChIJ (vira place// vazio)
    url_playwright = maps_url
    if place_id:
        broken = (
            not maps_url
            or "place//" in maps_url
            or "/place//@" in maps_url
            or (
                "/maps/place/" in maps_url
                and "q=place_id:" not in maps_url
                and "1s0x" not in maps_url
                and "/maps/search/" not in maps_url
            )
        )
        if broken:
            url_playwright = montar_maps_url_place(
                nome, place_id, lat, lng, cidade=cidade, hex_ftid=hex_ftid or ""
            ) or maps_url

    # Tier 2: Playwright fallback (opt-in)
    try:
        resultado = await asyncio.to_thread(
            _extrair_sync,
            url_playwright,
            place_id,
            nome=nome,
            cidade=cidade,
            lat=lat,
            lng=lng,
        )
    except Exception as e:
        return {
            "status": "erro",
            "motivo": f"thread_error: {str(e)[:200]}",
            "place_id": place_id,
            "maps_url": maps_url,
            "dados_por_dia": {},
            "resumo_por_dia": {},
            "fonte": "playwright_maps_dom",
            "data_coleta": datetime.now().strftime("%Y-%m-%d"),
            "cached": False,
        }

    # Retry busca georreferenciada se primeira URL ainda falhou
    if (
        resultado.get("status") != "ok"
        and place_id
        and nome
        and lat is not None
        and lng is not None
    ):
        try:
            alt_url = montar_maps_url_place(
                nome, place_id, lat, lng, cidade=cidade, hex_ftid=hex_ftid or ""
            )
            if alt_url and alt_url != url_playwright:
                alt = await asyncio.to_thread(
                    _extrair_sync,
                    alt_url,
                    place_id,
                    nome=nome,
                    cidade=cidade,
                    lat=lat,
                    lng=lng,
                )
                if alt.get("status") == "ok":
                    resultado = alt
                    resultado["maps_url"] = alt_url
        except Exception:
            pass

    # Salva cache (mesmo pra sem_popular_times — TTL menor evita re-tentativa em loop)
    if place_id and resultado.get("status") in ("ok", "sem_popular_times"):
        _save_pico_cache(place_id, resultado)

    return resultado
