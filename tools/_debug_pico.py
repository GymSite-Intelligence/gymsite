"""
Diagnóstico standalone do scraping de popular times.

Roda em headless=False com slowmo pra você ver o que o Playwright está
fazendo. Testa 2 caminhos (Search + Maps direto), tira screenshots e
dumpa todos os aria-labels relevantes.

Uso:
    cd C:\\Users\\marce\\gymsite_intelligence
    python -m tools._debug_pico

Output:
    debug/pico/
        01_search_pre_consent.png
        02_search_post_load.png
        03_search_aria_labels.txt
        04_search_knowledge_panel.html
        05_maps_post_load.png
        06_maps_aria_labels.txt
        07_maps_popular_times.html
"""
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERRO: Playwright não instalado. Rode: pip install playwright && playwright install chromium")
    sys.exit(1)


# Default targets — sobrescrever via CLI: python -m tools._debug_pico "Nome" "Cidade"
DEFAULT_TARGETS = [
    ("Shopping Iguatemi", "Fortaleza"),  # baseline: lugar lotado, popular times CERTO existe
    ("Smart Fit Papicu", "Fortaleza"),   # caso real do pipeline
]

DEBUG_DIR_BASE = Path(__file__).resolve().parent.parent / "debug" / "pico"
DEBUG_DIR_BASE.mkdir(parents=True, exist_ok=True)


# Keywords pra filtrar aria-labels relevantes a horários/movimento
# (cobre PT-BR, EN, e variações)
KEYWORDS_HORARIO = re.compile(
    r"(geralmente|movimentado|hora|horário|busy|popular|peak|movimentação|"
    r"segunda|terça|quarta|quinta|sexta|sábado|domingo|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"\b\d{1,2}h\b|\b\d{1,2}\s*(?:AM|PM)\b)",
    re.IGNORECASE,
)


def _dump_aria_labels(page, output_path: Path, contexto: str) -> int:
    """Extrai todos aria-labels da página e filtra os relevantes."""
    labels = page.evaluate("""
        () => {
            const result = [];
            document.querySelectorAll('[aria-label]').forEach(el => {
                const label = el.getAttribute('aria-label');
                if (label) {
                    result.push({
                        tag: el.tagName,
                        role: el.getAttribute('role') || '',
                        label: label,
                        visible: el.offsetParent !== null,
                    });
                }
            });
            return result;
        }
    """)

    relevantes = [l for l in labels if KEYWORDS_HORARIO.search(l["label"])]

    with output_path.open("w", encoding="utf-8") as f:
        f.write(f"=== {contexto} ===\n")
        f.write(f"Total aria-labels na página: {len(labels)}\n")
        f.write(f"Aria-labels relacionados a horário/movimento: {len(relevantes)}\n\n")
        f.write("--- AMOSTRA DE TODOS ARIA-LABELS (primeiros 30) ---\n")
        for l in labels[:30]:
            f.write(f"[{l['tag']}] role={l['role']!r} visible={l['visible']} :: {l['label']!r}\n")
        f.write("\n--- ARIA-LABELS RELEVANTES (filtrados) ---\n")
        for l in relevantes:
            f.write(f"[{l['tag']}] role={l['role']!r} visible={l['visible']} :: {l['label']!r}\n")

    return len(relevantes)


def _save_html_section(page, selector: str, output_path: Path, contexto: str) -> bool:
    """Salva HTML de uma seção pra inspeção offline."""
    try:
        loc = page.locator(selector).first
        if loc.count() == 0:
            output_path.write_text(f"=== {contexto} ===\nSeletor {selector!r} não encontrado.\n", encoding="utf-8")
            return False
        html = loc.evaluate("el => el.outerHTML")
        output_path.write_text(f"<!-- {contexto} -->\n<!-- selector: {selector} -->\n\n{html}", encoding="utf-8")
        return True
    except Exception as e:
        output_path.write_text(f"=== {contexto} ===\nERRO: {e}\n", encoding="utf-8")
        return False


def _dump_text_panel(page, output_path: Path, contexto: str) -> int:
    """Captura todo texto visível do painel [role='main'] (ficha completa)."""
    try:
        text = page.evaluate(
            "() => { const m = document.querySelector('[role=\"main\"]'); "
            "return m ? m.innerText : ''; }"
        )
    except Exception as e:
        text = f"ERRO ao extrair texto: {e}"
    output_path.write_text(f"=== {contexto} ===\n\n{text}", encoding="utf-8")
    return len(text or "")


def _save_main_panel_html(page, output_path: Path, contexto: str) -> bool:
    """Salva HTML completo do main panel (pra inspeção offline / análise de seletores)."""
    try:
        html = page.evaluate(
            "() => { const m = document.querySelector('[role=\"main\"]'); "
            "return m ? m.outerHTML : ''; }"
        )
        if not html:
            output_path.write_text(f"=== {contexto} ===\nMain panel não encontrado.\n", encoding="utf-8")
            return False
        output_path.write_text(f"<!-- {contexto} -->\n\n{html}", encoding="utf-8")
        return True
    except Exception as e:
        output_path.write_text(f"=== {contexto} ===\nERRO: {e}\n", encoding="utf-8")
        return False


def _scroll_main(page, steps: int = 6, delta: int = 600, delay_ms: int = 700):
    """Scroll progressivo no painel [role='main'] pra forçar lazy-load."""
    try:
        for _ in range(steps):
            page.evaluate(
                f"() => {{ const m = document.querySelector('[role=\"main\"]'); "
                f"if (m) m.scrollTop += {delta}; }}"
            )
            page.wait_for_timeout(delay_ms)
    except Exception:
        pass


def _detectar_secoes(text: str) -> dict:
    """Verifica quais seções estratégicas aparecem no texto extraído."""
    padroes = {
        "resumo_avaliacoes_ia": r"(resumo de avalia|review summary|sobre as avalia)",
        "preco_por_pessoa": r"(pre[çc]o por pessoa|faixa de pre[çc]o|pre[çc]o m[ée]dio|price range|por pessoa)",
        "horarios_populares": r"(hor[áa]rios? populares|popular times|hor[áa]rio movimentado)",
        "highlights_acessibilidade": r"(acess[íi]vel|wheelchair|cadeira de rodas)",
        "highlights_wifi": r"(wi-?fi)",
        "highlights_estacionamento": r"(estacionamento|parking)",
        "n_avaliacoes": r"(\d+\.?\d*\s*(?:mil)?\s*avalia)",
        "fotos_qtd": r"(\d+\s+fotos?)",
        "site_oficial": r"(site|website)",
        "telefone": r"(\(\d{2}\)\s*\d{4,5}-?\d{4}|\+55)",
    }
    return {k: bool(re.search(p, text, re.IGNORECASE)) for k, p in padroes.items()}


def diagnosticar_search(target_nome: str, target_cidade: str, debug_dir: Path):
    """Caminho atual do código: google.com/search com Knowledge Panel."""
    print("\n" + "=" * 60)
    print(f"DIAGNÓSTICO 1 — Google Search + Knowledge Panel  [{target_nome}]")
    print("=" * 60)

    query = f"{target_nome} {target_cidade}"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}&hl=pt-BR"
    print(f"URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400)
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

        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.screenshot(path=str(debug_dir / "01_search_pre_consent.png"))
        print(f"  ✓ Screenshot pre-consent: {debug_dir / '01_search_pre_consent.png'}")

        # Tenta dismissar consent — busca em iframes também (consent.google.com)
        consent_resolved = False
        for texto_botao in ["Aceitar tudo", "Concordo", "Accept all", "I agree", "Aceitar todos", "Reject all", "Rejeitar tudo"]:
            try:
                btn = page.get_by_role("button", name=texto_botao).first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    print(f"  ✓ Consent dismissed (page): '{texto_botao}'")
                    consent_resolved = True
                    page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        # Se não achou na page, busca em todos os frames (consent.google.com geralmente é iframe)
        if not consent_resolved:
            for frame in page.frames:
                for texto_botao in ["Aceitar tudo", "Concordo", "Accept all", "I agree", "Reject all"]:
                    try:
                        btn = frame.get_by_role("button", name=texto_botao).first
                        if btn.is_visible(timeout=1000):
                            btn.click()
                            print(f"  ✓ Consent dismissed (iframe {frame.url[:60]}): '{texto_botao}'")
                            consent_resolved = True
                            page.wait_for_timeout(2000)
                            break
                    except Exception:
                        continue
                if consent_resolved:
                    break

        if not consent_resolved:
            print(f"  ⚠ Consent NÃO foi dismissado — pode bloquear renderização")

        # Tenta wait Knowledge Panel
        try:
            page.wait_for_selector("[role='complementary'], #rhs, [data-attrid]", timeout=8000)
            print("  ✓ Knowledge Panel encontrado")
        except PlaywrightTimeout:
            print("  ✗ Knowledge Panel NÃO encontrado em 8s")

        page.wait_for_timeout(2500)  # tempo extra pra widget carregar
        page.screenshot(path=str(debug_dir / "02_search_post_load.png"), full_page=True)
        print(f"  ✓ Screenshot post-load: {debug_dir / '02_search_post_load.png'}")

        n = _dump_aria_labels(page, debug_dir / "03_search_aria_labels.txt", "GOOGLE SEARCH")
        print(f"  → {n} aria-labels relevantes encontrados (ver 03_search_aria_labels.txt)")

        # Tenta salvar HTML do Knowledge Panel
        seletores_kp = [
            ("[role='complementary']", "complementary"),
            ("#rhs", "rhs"),
            ("[data-attrid='kc:/local:popular times']", "popular_times_attrid"),
        ]
        for selector, slug in seletores_kp:
            ok = _save_html_section(
                page, selector,
                debug_dir / f"04_search_knowledge_panel_{slug}.html",
                f"Search Knowledge Panel via {selector}",
            )
            if ok:
                print(f"  ✓ HTML salvo via selector {selector}")
                break

        browser.close()
        return n


def diagnosticar_maps(target_nome: str, target_cidade: str, debug_dir: Path):
    """Caminho alternativo: Google Maps direto."""
    print("\n" + "=" * 60)
    print(f"DIAGNÓSTICO 2 — Google Maps direto  [{target_nome}]")
    print("=" * 60)

    query = f"{target_nome} {target_cidade}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl=pt-BR"
    print(f"URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400)
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

        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Consent dialog do Maps
        for texto_botao in ["Aceitar tudo", "Concordo", "Accept all", "I agree"]:
            try:
                btn = page.get_by_role("button", name=texto_botao).first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    print(f"  ✓ Dismissed consent: '{texto_botao}'")
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                continue

        # Espera o card do place
        try:
            page.wait_for_selector("[role='main'], div[role='dialog']", timeout=10000)
            print("  ✓ Card do place encontrado")
        except PlaywrightTimeout:
            print("  ✗ Card do place NÃO encontrado em 10s")

        page.wait_for_timeout(3000)  # extra pro popular times carregar (lazy)

        # Faz scroll progressivo no painel esquerdo (popular times é lazy-loaded
        # mais embaixo na visão geral)
        try:
            for _ in range(6):
                page.evaluate(
                    "() => { const main = document.querySelector('[role=\"main\"]'); "
                    "if (main) main.scrollTop += 600; }"
                )
                page.wait_for_timeout(800)
        except Exception:
            pass

        page.screenshot(path=str(debug_dir / "05_maps_post_load.png"), full_page=True)
        print(f"  ✓ Screenshot post-load: {debug_dir / '05_maps_post_load.png'}")

        n = _dump_aria_labels(page, debug_dir / "06_maps_aria_labels.txt", "GOOGLE MAPS")
        print(f"  → {n} aria-labels relevantes encontrados (ver 06_maps_aria_labels.txt)")

        # Tenta extrair seção de "Horários populares" via texto
        achou_secao = False
        for sel_text in ["Horários populares", "Popular times", "Horários de pico", "Movimentação"]:
            try:
                loc = page.get_by_text(sel_text, exact=False).first
                if loc.count() > 0 and loc.is_visible():
                    parent = loc.locator("xpath=ancestor::*[5]").first
                    html = parent.evaluate("el => el.outerHTML")
                    out = debug_dir / "07_maps_popular_times.html"
                    out.write_text(
                        f"<!-- via texto: {sel_text!r} -->\n\n{html}",
                        encoding="utf-8",
                    )
                    print(f"  ✓ Seção '{sel_text}' salva em {out.name}")
                    achou_secao = True
                    break
            except Exception:
                continue

        if not achou_secao:
            (debug_dir / "07_maps_popular_times.html").write_text(
                "Nenhuma seção 'Horários populares' / 'Popular times' encontrada por texto.",
                encoding="utf-8",
            )
            print("  ✗ Nenhuma seção 'Horários populares' encontrada por busca de texto")

        # ── EXPANSÃO: capturar ficha completa (texto visível + HTML) ──
        # Tab "Visão geral" é o estado padrão. Garante posição inicial e captura.
        try:
            page.evaluate("() => { const m = document.querySelector('[role=\"main\"]'); if (m) m.scrollTop = 0; }")
            page.wait_for_timeout(500)
            _scroll_main(page, steps=8, delta=500, delay_ms=600)
        except Exception:
            pass

        n_text_overview = _dump_text_panel(
            page,
            debug_dir / "08_maps_visao_geral_text.txt",
            f"VISÃO GERAL — {target_nome}",
        )
        print(f"  ✓ Visão Geral: {n_text_overview} chars de texto capturados")

        _save_main_panel_html(
            page,
            debug_dir / "09_maps_main_panel.html",
            f"MAPS MAIN PANEL — {target_nome}",
        )

        # Tab "Avaliações" — onde mora o resumo IA + reviews completas
        try:
            avaliacoes_tab = page.locator("button[role='tab']").filter(has_text="Avaliações").first
            if avaliacoes_tab.count() > 0 and avaliacoes_tab.is_visible():
                avaliacoes_tab.click()
                page.wait_for_timeout(2500)
                _scroll_main(page, steps=4, delta=600, delay_ms=600)
                n_text_av = _dump_text_panel(
                    page,
                    debug_dir / "10_maps_avaliacoes_text.txt",
                    f"AVALIAÇÕES — {target_nome}",
                )
                page.screenshot(path=str(debug_dir / "11_maps_avaliacoes.png"), full_page=True)
                print(f"  ✓ Tab Avaliações capturada: {n_text_av} chars")
            else:
                (debug_dir / "10_maps_avaliacoes_text.txt").write_text(
                    "Tab 'Avaliações' não encontrada/visível.", encoding="utf-8",
                )
                print("  ✗ Tab Avaliações não encontrada")
        except Exception as e:
            (debug_dir / "10_maps_avaliacoes_text.txt").write_text(
                f"ERRO ao clicar tab Avaliações: {e}", encoding="utf-8",
            )
            print(f"  ✗ Tab Avaliações falhou: {e}")

        # Tab "Sobre" — onde moram highlights/atributos (Wi-Fi, acessível, etc.)
        try:
            sobre_tab = page.locator("button[role='tab']").filter(has_text="Sobre").first
            if sobre_tab.count() > 0 and sobre_tab.is_visible():
                sobre_tab.click()
                page.wait_for_timeout(2000)
                _scroll_main(page, steps=4, delta=500, delay_ms=500)
                n_text_sobre = _dump_text_panel(
                    page,
                    debug_dir / "12_maps_sobre_text.txt",
                    f"SOBRE — {target_nome}",
                )
                print(f"  ✓ Tab Sobre capturada: {n_text_sobre} chars")
            else:
                (debug_dir / "12_maps_sobre_text.txt").write_text(
                    "Tab 'Sobre' não encontrada/visível.", encoding="utf-8",
                )
                print("  ✗ Tab Sobre não encontrada")
        except Exception as e:
            (debug_dir / "12_maps_sobre_text.txt").write_text(
                f"ERRO ao clicar tab Sobre: {e}", encoding="utf-8",
            )
            print(f"  ✗ Tab Sobre falhou: {e}")

        # Detecta padrões de seções estratégicas no texto consolidado
        texto_completo = ""
        for fname in ["08_maps_visao_geral_text.txt", "10_maps_avaliacoes_text.txt", "12_maps_sobre_text.txt"]:
            fp = debug_dir / fname
            if fp.exists():
                texto_completo += "\n\n" + fp.read_text(encoding="utf-8")

        secoes = _detectar_secoes(texto_completo)
        relatorio = "\n".join(
            f"  {'✓' if v else '✗'}  {k.replace('_', ' ')}"
            for k, v in secoes.items()
        )
        (debug_dir / "13_maps_secoes_detectadas.txt").write_text(
            f"=== SEÇÕES ESTRATÉGICAS DETECTADAS — {target_nome} ===\n\n{relatorio}\n",
            encoding="utf-8",
        )
        print(f"  → Seções estratégicas detectadas:")
        for k, v in secoes.items():
            print(f"      {'✓' if v else '✗'}  {k.replace('_', ' ')}")

        browser.close()
        return n


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def main():
    if len(sys.argv) >= 3:
        targets = [(sys.argv[1], sys.argv[2])]
    else:
        targets = DEFAULT_TARGETS

    resumo = []
    for nome, cidade in targets:
        slug = f"{_slug(nome)}__{_slug(cidade)}"
        debug_dir = DEBUG_DIR_BASE / slug
        debug_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n\n###  TARGET: {nome} — {cidade}")
        print(f"###  Output: {debug_dir}")

        n_search = diagnosticar_search(nome, cidade, debug_dir)
        n_maps = diagnosticar_maps(nome, cidade, debug_dir)
        resumo.append((nome, cidade, n_search, n_maps, debug_dir))

    print("\n" + "=" * 60)
    print("RESUMO GERAL")
    print("=" * 60)
    print(f"{'Target':<40} {'Search':>8} {'Maps':>8}")
    for nome, cidade, ns, nm, _ in resumo:
        print(f"{(nome + ' / ' + cidade)[:39]:<40} {ns:>8} {nm:>8}")

    print("\nArquivos por target:")
    for *_, debug_dir in resumo:
        print(f"  {debug_dir}")

    print("\nArquivos-chave para colar no chat (em ordem de prioridade):")
    print("  1. 13_maps_secoes_detectadas.txt  ← veredito rápido por target")
    print("  2. 08_maps_visao_geral_text.txt   ← texto da Visão Geral")
    print("  3. 10_maps_avaliacoes_text.txt    ← resumo IA + reviews completas")
    print("  4. 12_maps_sobre_text.txt         ← highlights/atributos")
    print("  5. 06_maps_aria_labels.txt        ← seletores pra grep offline")


if __name__ == "__main__":
    main()
