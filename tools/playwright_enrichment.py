# tools/playwright_enrichment.py
"""
Enrichment de concorrentes via scraping do Google Knowledge Panel.

IMPORTANTE — Windows + Python 3.14 + ADK:
Usamos playwright.sync_api dentro de um thread separado via asyncio.to_thread,
porque playwright.async_api requer ProactorEventLoop no Windows mas o ADK
roda em SelectorEventLoop (NotImplementedError em create_subprocess_exec).
sync_api roda subprocess sincronamente, isolando do asyncio loop principal.

Captura dados não expostos pela Places API (New):
- Horários de pico (popular times)
- Posts da Google Business Profile (atualizações de mídias sociais)
- Taxa de resposta do dono a reviews
- Fotos recentes
"""
import asyncio
import re
from typing import Optional

# Import graceful — se Playwright não estiver instalado, tools retornam stub
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# Mapa textual de níveis de movimento → score numérico (0-3)
NIVEL_MOVIMENTO = {
    "não é movimentado": 0,
    "nao e movimentado": 0,
    "pouco movimentado": 1,
    "geralmente um pouco movimentado": 1,
    "movimentado": 2,
    "geralmente movimentado": 2,
    "bastante movimentado": 3,
    "geralmente bastante movimentado": 3,
    "muito movimentado": 3,
}

DIAS_SEMANA = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]


def _enriquecer_sync(nome_academia: str, cidade: str) -> dict:
    """
    Versão SÍNCRONA do scraping (roda em thread separada via asyncio.to_thread).
    Não chamar diretamente do código async — use enriquecer_concorrente_via_google.
    """
    base_result = {
        "nome_consultado": nome_academia,
        "cidade": cidade,
        "horarios_pico": {},
        "pico_semanal": None,
        "vale_semanal": None,
        "posts_recentes": [],
        "atividade_marketing": {},
        "scraping_status": "ok",
    }

    if not PLAYWRIGHT_AVAILABLE:
        base_result["scraping_status"] = "playwright_nao_instalado"
        base_result["instalacao"] = "pip install playwright && playwright install chromium"
        return base_result

    query = f"{nome_academia} {cidade} academia"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                locale="pt-BR",
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            page.goto(
                f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=pt-BR",
                timeout=20000,
                wait_until="domcontentloaded",
            )

            # Aguarda Knowledge Panel
            try:
                page.wait_for_selector("[role='complementary'], #rhs", timeout=8000)
            except PlaywrightTimeout:
                base_result["scraping_status"] = "knowledge_panel_nao_encontrado"
                browser.close()
                return base_result

            # Captura horários de pico (aria-labels têm texto completo)
            try:
                bars = page.locator("[aria-label*='Geralmente'], [aria-label*='movimentado']")
                count = bars.count()
                horarios = {}

                for i in range(min(count, 168)):
                    try:
                        label = bars.nth(i).get_attribute("aria-label", timeout=500)
                    except Exception:
                        continue
                    if not label:
                        continue
                    parsed = _parsear_aria_label(label)
                    if parsed:
                        dia, hora, nivel = parsed
                        horarios.setdefault(dia, []).append({
                            "hora": hora,
                            "nivel": nivel,
                            "nivel_score": NIVEL_MOVIMENTO.get(nivel.lower(), 0),
                        })

                base_result["horarios_pico"] = horarios

                if horarios:
                    todas_horas = []
                    for dia, lista in horarios.items():
                        for h in lista:
                            todas_horas.append((dia, h["hora"], h["nivel_score"]))
                    if todas_horas:
                        pico = max(todas_horas, key=lambda x: x[2])
                        vale = min(todas_horas, key=lambda x: x[2])
                        if pico[2] >= 2:
                            base_result["pico_semanal"] = f"{pico[0]} {pico[1]}h"
                        if vale[2] == 0:
                            base_result["vale_semanal"] = f"{vale[0]} {vale[1]}h"

            except Exception as e:
                base_result["horarios_pico_erro"] = str(e)[:200]

            # Captura posts da Google Business Profile
            try:
                posts_section = page.locator("text=Atualizações de mídias sociais").first
                if posts_section.count() > 0:
                    parent = posts_section.locator("xpath=ancestor::*[3]").first
                    posts_text = parent.inner_text(timeout=3000)
                    if posts_text:
                        linhas = [
                            l.strip() for l in posts_text.split("\n")
                            if l.strip() and "Atualizações" not in l and len(l.strip()) > 20
                        ]
                        base_result["posts_recentes"] = [
                            {"texto": l[:300]} for l in linhas[:5]
                        ]
                        if linhas:
                            base_result["atividade_marketing"] = {
                                "ultimo_post_resumo": linhas[0][:200],
                                "frequencia_estimada": "ativa" if len(linhas) >= 3 else "esporadica",
                                "qtd_posts_visiveis": len(linhas),
                            }
            except Exception as e:
                base_result["posts_erro"] = str(e)[:200]

            browser.close()

    except Exception as e:
        base_result["scraping_status"] = f"error: {str(e)[:200]}"

    return base_result


async def enriquecer_concorrente_via_google(
    nome_academia: str,
    cidade: str,
) -> dict:
    """
    Wrapper async que delega ao _enriquecer_sync via asyncio.to_thread.
    Isso evita o bug Windows + Python 3.14 + asyncio onde subprocess_exec
    falha com NotImplementedError no SelectorEventLoop padrão do ADK.

    Returns dict (mesmo quando scraping falha — graceful degradation).
    """
    try:
        return await asyncio.to_thread(_enriquecer_sync, nome_academia, cidade)
    except Exception as e:
        return {
            "nome_consultado": nome_academia,
            "cidade": cidade,
            "horarios_pico": {},
            "pico_semanal": None,
            "vale_semanal": None,
            "posts_recentes": [],
            "atividade_marketing": {},
            "scraping_status": f"thread_error: {str(e)[:200]}",
        }


def _parsear_aria_label(label: str) -> Optional[tuple]:
    """
    Parse aria-label do gráfico de horários do Google.
    Formato típico: "Quinta, 18h. Geralmente bastante movimentado"

    Retorna (dia_normalizado, hora_int, nivel_str) ou None.
    """
    label_low = label.lower()

    dia_encontrado = None
    label_norm = label_low.replace("á", "a").replace("ã", "a").replace("â", "a")
    for d in DIAS_SEMANA:
        if d in label_norm:
            dia_encontrado = d
            break
    if not dia_encontrado:
        return None

    m = re.search(r"(\d{1,2})\s*(?:h|:|hora)", label_low)
    if not m:
        return None
    hora = int(m.group(1))
    if not 0 <= hora <= 23:
        return None

    nivel = "desconhecido"
    for chave in NIVEL_MOVIMENTO:
        if chave in label_low:
            nivel = chave
            break

    return (dia_encontrado, hora, nivel)


def analisar_picos_competitivos(concorrentes_com_picos: list[dict]) -> dict:
    """
    Cruza horários de pico de TODOS os concorrentes para identificar:

    - picos_compartilhados: horários onde 2+ concorrentes estão LOTADOS
      → oportunidade de COUNTER-PROGRAMMING (promoção exatamente nesse horário)

    - vales_compartilhados: horários onde TODOS estão vazios
      → oportunidade passiva (público diurno, idosos, freelancers)

    - estrategias_acionaveis: lista de ações concretas
    """
    if not concorrentes_com_picos:
        return {
            "picos_compartilhados": [],
            "vales_compartilhados": [],
            "estrategias_acionaveis": [],
            "concorrentes_com_dados": 0,
        }

    matriz = {}
    n_concorrentes = 0

    for c in concorrentes_com_picos:
        if not isinstance(c, dict):
            continue
        nome = c.get("nome", "Desconhecido")
        horarios = c.get("horarios_pico", {})
        if not horarios or not isinstance(horarios, dict):
            continue
        n_concorrentes += 1

        for dia, lista_horas in horarios.items():
            # Defensivo: lista_horas pode vir como str, list de dict, ou list de str
            if not isinstance(lista_horas, list):
                continue
            for h in lista_horas:
                # Pula items que não são dicts (LLM às vezes passa strings tipo "19h")
                if not isinstance(h, dict):
                    continue
                hora = h.get("hora")
                score = h.get("nivel_score", 0)
                if hora is None:
                    continue
                key = (dia, hora)
                if key not in matriz:
                    matriz[key] = {"lotados": [], "vazios": [], "soma_score": 0, "n": 0}
                matriz[key]["soma_score"] += score
                matriz[key]["n"] += 1
                if score >= 3:
                    matriz[key]["lotados"].append(nome)
                elif score == 0:
                    matriz[key]["vazios"].append(nome)

    picos_compartilhados = []
    for (dia, hora), info in matriz.items():
        if len(info["lotados"]) >= 2:
            picos_compartilhados.append({
                "dia": dia,
                "hora": hora,
                "concorrentes_lotados": info["lotados"],
                "qtd_lotados": len(info["lotados"]),
            })

    vales_compartilhados = []
    for (dia, hora), info in matriz.items():
        if info["n"] >= 2 and len(info["vazios"]) == info["n"]:
            vales_compartilhados.append({
                "dia": dia,
                "hora": hora,
                "concorrentes_vazios": info["vazios"],
            })

    picos_compartilhados.sort(key=lambda x: (-x["qtd_lotados"], x["dia"], x["hora"]))
    vales_compartilhados.sort(key=lambda x: (x["dia"], x["hora"]))

    estrategias = []
    for p in picos_compartilhados[:5]:
        estrategias.append({
            "tipo": "counter_programming",
            "horario": f"{p['dia']} {p['hora']}h",
            "contexto": f"{p['qtd_lotados']} concorrentes lotados ({', '.join(p['concorrentes_lotados'][:3])})",
            "acao_recomendada": (
                f"Promoção 'Pico Time {p['hora']}h': day-pass R$5 + avaliação grátis. "
                f"Stories + ads geo-locais 30min antes."
            ),
        })

    for v in vales_compartilhados[:3]:
        estrategias.append({
            "tipo": "captura_vale",
            "horario": f"{v['dia']} {v['hora']}h",
            "contexto": f"Todos os concorrentes ({len(v['concorrentes_vazios'])}) vazios",
            "acao_recomendada": (
                f"Marketing pra públicos diurnos: aposentados, freelancers, mães. "
                f"Aulas exclusivas 'Hora Tranquila' nesse horário."
            ),
        })

    return {
        "picos_compartilhados": picos_compartilhados[:10],
        "vales_compartilhados": vales_compartilhados[:5],
        "estrategias_acionaveis": estrategias,
        "concorrentes_com_dados": n_concorrentes,
    }
