"""
Popular Times Tool — extrai horários de pico de fichas Google Maps.

DESCOBERTA TÉCNICA (validada em 2026-05-08):
- Os 168 dados (24h × 7 dias) estão no DOM **pré-renderizado**, off-screen
  (top: 931px enquanto viewport é 855px). Não precisa scroll.
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
"""
import asyncio
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

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


def _parsear_aria_label(label: str):
    """
    "Movimento às 14:00: 52%." → ("14", 52). Retorna None se padrão não bate.
    """
    if "Movimento às" not in label:
        return None
    try:
        depois_as = label.split("às ")[1]               # "14:00: 52%."
        hora = depois_as.split(":")[0].strip()          # "14"
        pct_str = label.split(": ")[-1].replace("%.", "").replace("%", "").strip()
        pct = int(pct_str)
        if 0 <= pct <= 100 and hora.isdigit() and 0 <= int(hora) <= 23:
            return (hora, pct)
    except (IndexError, ValueError):
        return None
    return None


def _calcular_perfil(hora_pico_str: str, max_pct: int, min_pct: int, picos_altos: list) -> str:
    try:
        hora = int(hora_pico_str)
    except (ValueError, TypeError):
        return "indeterminado"
    spread = max_pct - min_pct
    if spread < 25:
        return "24h_equilibrado"
    if len(picos_altos) >= 5:
        return "multi_pico"
    if 6 <= hora <= 10:
        return "manha_pico"
    if 11 <= hora <= 15:
        return "almoco_pico"
    if 16 <= hora <= 20:
        return "tarde_pico"
    return "noite_pico"


def _calcular_oportunidade(resumo_por_dia: dict) -> str:
    if not resumo_por_dia:
        return "Dados insuficientes para análise de oportunidade."

    perfis = [r["perfil"] for r in resumo_por_dia.values()]

    if perfis.count("tarde_pico") >= 4:
        return (
            "Concorrente concentrado no horário 17-20h. "
            "Oportunidade: programa diferenciado na manhã (06-10h) com personal incluso."
        )
    if perfis.count("manha_pico") >= 4:
        return (
            "Concorrente com pico matutino. "
            "Oportunidade: aulas noturnas premium e madrugada com personal."
        )
    if perfis.count("almoco_pico") >= 4:
        return (
            "Pico concentrado no almoço. "
            "Oportunidade: treinos express 30min manhã/noite para quem não pode no almoço."
        )

    dias_uteis = ["segunda", "terca", "quarta", "quinta"]
    dias_uteis_baixos = [
        d for d in dias_uteis
        if resumo_por_dia.get(d, {}).get("pct_vale", 100) <= 20
    ]
    if len(dias_uteis_baixos) >= 2:
        return (
            f"Movimento muito baixo em dias úteis ({', '.join(dias_uteis_baixos)}). "
            "Oportunidade: programa de fidelização mid-week com benefícios exclusivos."
        )

    if perfis.count("24h_equilibrado") >= 4:
        return (
            "Academia bem distribuída ao longo do dia. "
            "Competir por horário não é vantagem — focar em diferencial de serviço/preço."
        )

    return (
        "Padrão de pico misto ao longo da semana. "
        "Analisar dia a dia para identificar janelas específicas de oportunidade."
    )


def _extrair_sync(maps_url: str, place_id: str) -> dict:
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

    movimentos = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="pt-BR",
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            try:
                page.goto(maps_url, timeout=25000, wait_until="domcontentloaded")

                # wait_for_selector encontra elementos off-screen mas no DOM —
                # não precisa scroll. Se timeout, local não tem popular_times.
                try:
                    page.wait_for_selector(
                        '[aria-label*="Movimento às"]',
                        timeout=10000,
                    )
                except PlaywrightTimeout:
                    base_result["status"] = "sem_popular_times"
                    base_result["motivo"] = (
                        "Local não possui gráfico de horários de pico no Google Maps "
                        "(visitas insuficientes ou Google optou por não exibir)."
                    )
                    browser.close()
                    return base_result

                # Extrai todos os aria-labels de movimento de uma vez via JS
                movimentos = page.evaluate(
                    "() => { const out = []; "
                    "document.querySelectorAll('[aria-label]').forEach(el => { "
                    "const l = el.getAttribute('aria-label') || ''; "
                    "if (l.indexOf('Movimento às') !== -1) out.push(l); }); "
                    "return out; }"
                )
            finally:
                browser.close()

    except Exception as e:
        base_result["status"] = "erro"
        base_result["motivo"] = f"playwright_error: {str(e)[:200]}"
        return base_result

    if not movimentos:
        base_result["status"] = "sem_popular_times"
        base_result["motivo"] = "wait_for_selector passou mas evaluate retornou vazio"
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
        picos_altos = [h for h, p in horas.items() if p >= 70]
        resumo_por_dia[dia] = {
            "hora_pico": hora_pico,
            "pct_pico": max_pct,
            "hora_vale": hora_vale,
            "pct_vale": min_pct,
            "perfil": _calcular_perfil(hora_pico, max_pct, min_pct, picos_altos),
            "horas_superlotadas": sorted([h for h, p in horas.items() if p >= 80]),
            "horas_livres": sorted([h for h, p in horas.items() if p <= 20]),
        }

    dia_mais_movimentado = None
    if resumo_por_dia:
        dia_top = max(resumo_por_dia.items(), key=lambda x: x[1]["pct_pico"])
        dia_mais_movimentado = {
            "dia": dia_top[0],
            "hora": dia_top[1]["hora_pico"],
            "percentual": dia_top[1]["pct_pico"],
        }

    # Horários livres consolidados (≤ 15% qualquer dia)
    horarios_livres = []
    for dia, horas in dados_por_dia.items():
        for h, p in horas.items():
            if p <= 15:
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
    """Tier 0 — SearchAPI (free tier 100 req/mês).

    Quando SEARCHAPI_KEY definida, faz GET em /search?engine=google_maps_place.
    Retorna None se chave ausente ou falha — caller cai pro próximo tier.
    """
    if not place_id:
        return None
    try:
        import os
        import requests
        api_key = os.environ.get("SEARCHAPI_KEY", "").strip()
        if not api_key:
            return None
        resp = requests.get(
            "https://www.searchapi.io/api/v1/search",
            params={
                "engine": "google_maps_place",
                "place_id": place_id,
                "hl": "pt",
                "gl": "br",
                "api_key": api_key,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[searchapi] {place_id}: HTTP {resp.status_code}: {resp.text[:140]}")
            return None
        return _converter_searchapi(resp.json(), place_id)
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


def _tentar_populartimes_lib(place_id: str) -> dict | None:
    """Tenta extrair via biblioteca `populartimes` (Google Places API legacy).

    Retorna None se a lib não está instalada, place_id vazio, ou se a Places
    API legacy não está habilitada no projeto (REQUEST_DENIED).
    """
    if not place_id:
        return None
    try:
        import os
        import populartimes  # type: ignore[import-not-found]
        # Preferir chave dedicada (PLACES_API_KEY_LEGACY) — restrita à Places API
        # legacy. Fallback pra chave Maps compartilhada quando não definida.
        api_key = (
            os.environ.get("PLACES_API_KEY_LEGACY")
            or os.environ.get("GOOGLE_MAPS_API_KEY", "")
        )
        if not api_key:
            return None
        raw = populartimes.get_id(api_key, place_id)
        return _converter_populartimes_lib(raw, place_id)
    except ImportError:
        return None
    except Exception as e:
        # REQUEST_DENIED, place_id inválido, etc. — cai pro fallback Playwright
        print(f"[popular_times lib] {place_id}: {type(e).__name__}: {str(e)[:140]}")
        return None


async def pesquisar_horarios_pico(maps_url: str, place_id: str = "") -> dict:
    """
    Extrai horários de pico (7 dias × 24h) de uma ficha Google Maps.

    Estratégia em 3 tiers (cascata):
      0. SearchAPI free tier (100 req/mês) — quando SEARCHAPI_KEY definida
      1. Lib `populartimes` (Places API legacy) — gratuita mas frágil
      2. Playwright sync_api scraping — último recurso

    Args:
        maps_url: URL da ficha
        place_id: Place ID Google (necessário pra cache 7 dias e Tiers 0/1)

    Returns:
        Dict com: status, dados_por_dia, resumo_por_dia, dia_mais_movimentado, etc.
    """
    # Cache hit?
    if place_id:
        cp = _cache_path(place_id)
        if cp.exists():
            try:
                dados = json.loads(cp.read_text(encoding="utf-8"))
                cached_status = dados.get("status", "ok")
                if _cache_valido(cp, cached_status):
                    dados["cached"] = True
                    return dados
            except (json.JSONDecodeError, OSError):
                pass

    # Tier 0: SearchAPI (free tier 100 req/mês)
    resultado_searchapi = await asyncio.to_thread(_tentar_searchapi, place_id)
    if resultado_searchapi and resultado_searchapi.get("status") == "ok":
        if place_id:
            try:
                cp = _cache_path(place_id)
                cp.write_text(
                    json.dumps(resultado_searchapi, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError:
                pass
        return resultado_searchapi

    # Tier 1: lib populartimes (rápida, sem Chrome) — abandonware, raramente OK
    resultado_lib = await asyncio.to_thread(_tentar_populartimes_lib, place_id)
    if resultado_lib and resultado_lib.get("status") == "ok":
        if place_id:
            try:
                cp = _cache_path(place_id)
                cp.write_text(
                    json.dumps(resultado_lib, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError:
                pass
        return resultado_lib

    # Tier 2: Playwright fallback
    try:
        resultado = await asyncio.to_thread(_extrair_sync, maps_url, place_id)
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

    # Salva cache (mesmo pra sem_popular_times — TTL menor evita re-tentativa em loop)
    if place_id and resultado.get("status") in ("ok", "sem_popular_times"):
        try:
            cp = _cache_path(place_id)
            cp.write_text(
                json.dumps(resultado, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    return resultado
