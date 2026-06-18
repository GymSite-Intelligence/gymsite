"""
Refino A4-grounded da demanda futura (Apêndice B) — verificação cruzada com o site
do lançamento do empreendimento.

Proxy área/75 é o PISO. Quando a obra CNO tem construtora/endereço, A4 faz grounding
(Vertex Search) na página do lançamento → torres×unidades EXATAS + tipologia +
amenidade fitness. Só sobrescreve o proxy em ALTA confiança (match por cep+número);
senão mantém proxy. Estimativa nunca piora — só sobe de confiança com fonte primária.

Objetivos (PLANO §2.1): (1) precisão; (2) validação residencial; (3) auditabilidade
(fonte citável); (4) gatilho do lead condominial (C).

Grounding é injetável (`_grounding_fn`) → testável sem rede.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import httpx

_AMENIDADE_FITNESS = ("academia", "fitness", "espaço fitness", "espaco fitness",
                      "wellness", "sala de ginástica", "sala de ginastica")


def _montar_query(obra: dict) -> str:
    # Liderar por ENDEREÇO (identifica o empreendimento na web); nome CNO costuma ser
    # SPE/LTDA (ruído). Cidade/UF ajudam a desambiguar.
    log = (obra.get("logradouro") or "").strip()
    num = (obra.get("numero_logradouro") or "").strip()
    bairro = (obra.get("bairro") or "").strip()
    cidade = (obra.get("cidade") or "").strip()
    uf = (obra.get("uf") or "").strip()
    return (f"empreendimento residencial lançamento apartamento {log} {num} {bairro} "
            f"{cidade} {uf} torres unidades amenidades academia")


# Portais/agregadores — NÃO são fonte primária da incorporadora (auditável só como apoio).
# Portais/agregadores — não são fonte primária. Instagram/Facebook NÃO entram:
# são canais OFICIAIS da construtora (2ª fonte de cruzamento).
_DOMINIOS_PORTAL = ("vivareal", "zapimoveis", "olx", "chavesnamao", "quintoandar",
                    "imovelweb", "lopes.com", "loft.com", "wimoveis", "netimoveis",
                    "google.com", "wikipedia")

# Agregadores regionais: hospedam o anúncio mas NÃO são o responsável (o responsável
# é o anunciante/corretor extraído do conteúdo, não o portal). Separado de _DOMINIOS_PORTAL
# pra não mexer no gate de fonte oficial. Recalibrável (mover p/ param quando crescer).
_AGREGADORES = _DOMINIOS_PORTAL + ("voudeimovel", "dfimoveis", "imovelguide",
                                   "casamineira", "mgfimoveis", "buscacuritiba", "wimoveis")
_2NIVEL_BR = {"com", "org", "net", "gov", "edu", "ind"}


def _dominio_registravel(url: str) -> tuple[str, str]:
    """(dominio_registravel, raiz). Trata .com.br/.org.br. SEM hardcode de marca —
    usa publicsuffix-lite (não `'x.com.br' in url`)."""
    from urllib.parse import urlparse

    host = (urlparse(url if "//" in url else "//" + url).netloc or "").lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 3 and parts[-1] == "br" and parts[-2] in _2NIVEL_BR:
        return ".".join(parts[-3:]), parts[-3]
    if len(parts) >= 2:
        return ".".join(parts[-2:]), parts[-2]
    return host, (parts[0] if parts else host)


def _classificar_dominio(url: str) -> tuple[str, str, str]:
    """(dominio, raiz, tipo). tipo: 'agregador' (anúncio de terceiro) | 'site_proprio'
    (incorporadora/imobiliária dona do domínio)."""
    dom, raiz = _dominio_registravel(url)
    tipo = "agregador" if any(a in dom for a in _AGREGADORES) else "site_proprio"
    return dom, raiz, tipo


def identificar_responsavel_obra(url: str | None, ext: dict | None) -> dict | None:
    """Determinístico: QUEM o cliente contata p/ parceria de MKT no lançamento.
    Cruza o domínio registrável (publicsuffix) com o conteúdo extraído da página
    (incorporadora 'Construção/Realização' + imobiliária 'Vendas/Corretora' + contato).
    Resolve o caso 'site não diz explícito': o responsável vem do crédito/rodapé, e se
    for site próprio sem 'vendas', a própria marca do domínio é o responsável.
    Retorna None se não há sinal nenhum."""
    ext = ext or {}
    incorporadora = str(ext.get("incorporadora") or ext.get("construtora") or "").strip() or None
    imob = str(ext.get("imobiliaria_vendas") or ext.get("corretora") or "").strip() or None
    contato = (str(ext.get("contato_vendas") or ext.get("whatsapp") or ext.get("telefone") or "").strip()
               or None)
    creci = str(ext.get("creci") or "").strip() or None
    dom = raiz = tipo = None
    if url:
        dom, raiz, tipo = _classificar_dominio(url)

    # Quem contatar: imobiliária de vendas > incorporadora > marca do domínio próprio.
    if imob:
        responsavel, base = imob, "imobiliaria_vendas (página)"
    elif tipo == "site_proprio" and (incorporadora or raiz):
        responsavel, base = (incorporadora or raiz.title()), "site_proprio (domínio/incorporadora)"
    elif incorporadora:
        responsavel, base = incorporadora, "incorporadora (página)"
    else:
        responsavel, base = None, "nao_identificado"

    if not any([responsavel, incorporadora, imob, contato]):
        return None
    return {
        "responsavel_parceria": responsavel,   # ← quem o cliente procura
        "incorporadora": incorporadora,
        "imobiliaria_vendas": imob,
        "contato": contato, "creci": creci,
        "dominio": dom, "tipo_dominio": tipo,
        "fonte_url": url, "base": base,
    }



def _extrair_fontes_grounding(resp: Any) -> list[dict]:
    """Citações REAIS do grounding (grounding_metadata) — fonte auditável.
    uri = redirect de atribuição Vertex; dominio = site real (web.domain)."""
    out: list[dict] = []
    try:
        for c in (getattr(resp, "candidates", None) or []):
            gm = getattr(c, "grounding_metadata", None)
            for ch in (getattr(gm, "grounding_chunks", None) or []):
                web = getattr(ch, "web", None)
                uri = getattr(web, "uri", None) if web else None
                if uri:
                    out.append({"uri": uri, "dominio": getattr(web, "domain", None),
                                "titulo": getattr(web, "title", None)})
    except Exception:
        pass
    return out


def _eh_portal(f: dict) -> bool:
    alvo = ((f.get("dominio") or "") + " " + (f.get("uri") or "")).lower()
    return any(p in alvo for p in _DOMINIOS_PORTAL)


def _fonte_preferida(fontes: list[dict]) -> str | None:
    """Prefere o site da construtora/incorporadora (não portal/agregador). Usa o domínio
    real (web.domain); retorna o uri (redirect de atribuição Vertex, link citável)."""
    if not fontes:
        return None
    for f in fontes:
        if not _eh_portal(f):
            return f.get("uri")
    return fontes[0].get("uri")


def _grounding_lancamento(query: str) -> dict:
    """Chama Gemini+Search (Vertex). Retorna {texto, fontes[]} — fontes = citações reais."""
    from google.genai import types
    from tools._genai_client import build_genai_client, generate_content_resilient

    client = build_genai_client()
    prompt = (
        "Você DEVE usar a ferramenta de busca (não responda de memória). Pesquise DUAS fontes "
        "da construtora/incorporadora do empreendimento descrito: (a) o SITE OFICIAL e "
        "(b) o INSTAGRAM oficial (instagram.com/...). Cruze as duas.\n"
        "1) Escreva 1-2 frases com o que encontrou, citando as fontes.\n"
        "2) Depois, AO FINAL, um bloco JSON exatamente neste formato:\n"
        "Procure também o BOOK/MEMORIAL/FICHA TÉCNICA em PDF do empreendimento (link direto .pdf).\n"
        "{\n"
        '  "empreendimento": "<nome>", "construtora": "<nome>", "instagram": "<url|null>",\n'
        '  "pdf_url": "<link direto do book/memorial/ficha em PDF|null>",\n'
        '  "torres": <int|null>, "andares": <int|null>, "unidades": <int total|null>,\n'
        '  "tipologia": "<studio|1-2 dorm|3+ dorm|comercial|misto|null>",\n'
        '  "amenidades": ["..."],\n'
        '  "endereco": {"cep": "<digits do endereço NA FONTE|null>", "numero": "<numero NA FONTE|null>", "bairro": "<bairro|null>"}\n'
        "}\n"
        "No campo endereco, ECOE o endereço que aparece NA FONTE (não o da pergunta) para validação. "
        "Preencha SÓ com o que a busca retornou; sem resultado confiável → unidades=null. NÃO invente.\n\n"
        f"Empreendimento (por endereço): {query}"
    )
    resp = generate_content_resilient(
        client, model="gemini-2.5-flash", contents=prompt,
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
        max_retries=2, base_delay=3.0,
    )
    return {"texto": (resp.text or "").strip(), "fontes": _extrair_fontes_grounding(resp)}


def _extrair_lancamento(texto: str) -> dict | None:
    """Parseia o JSON do grounding (tolera cercas markdown). None se inválido."""
    if not texto:
        return None
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip().rstrip("`").strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else None
    except json.JSONDecodeError:
        return None


def _unidades_do_extraido(ext: dict) -> float | None:
    u = ext.get("unidades")
    if isinstance(u, (int, float)) and u > 0:
        return float(u)
    torres = ext.get("torres")
    upt = ext.get("unidades_por_torre")
    if isinstance(torres, (int, float)) and isinstance(upt, (int, float)) and torres > 0 and upt > 0:
        return float(torres) * float(upt)
    return None


def _areas_plantas(ext: dict) -> list[float]:
    """Lista limpa de áreas privativas (m²) das plantas. Vazia se ausente."""
    raw = ext.get("areas_plantas")
    out: list[float] = []
    if isinstance(raw, list):
        for v in raw:
            try:
                a = float(str(v).replace(",", ".")) if not isinstance(v, (int, float)) else float(v)
            except (TypeError, ValueError):
                continue
            if 15 <= a <= 1000:  # planta residencial plausível
                out.append(round(a, 2))
    return out


def _obra_progresso(ext: dict) -> dict | None:
    """Normaliza o bloco de acompanhamento de obra (% total + acabamento + fase)."""
    o = ext.get("obra")
    if not isinstance(o, dict):
        return None
    def _pct(v):
        try:
            n = float(str(v).split("-")[-1].replace("%", "").strip())
            return int(max(0, min(100, n)))
        except (TypeError, ValueError):
            return None
    total = _pct(o.get("total_pct"))
    acab = _pct(o.get("acabamento_pct"))
    fase = str(o.get("fase") or "").strip().lower() or None
    if total is None and acab is None and not fase:
        return None
    return {"total_pct": total, "acabamento_pct": acab, "fase": fase}


def _tem_amenidade_fitness(ext: dict) -> bool:
    blob = " ".join(str(a) for a in (ext.get("amenidades") or [])).lower()
    return any(k in blob for k in _AMENIDADE_FITNESS)


def _digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _validar_match(obra: dict, ext: dict) -> tuple[str, str]:
    """Confiança do casamento obra↔lançamento. (confianca, metodo)."""
    end = ext.get("endereco") or {}
    cep_o, cep_e = _digits(obra.get("cep")), _digits(end.get("cep"))
    num_o, num_e = _digits(obra.get("numero_logradouro")), _digits(end.get("numero"))
    if cep_o and cep_o == cep_e and num_o and num_o == num_e:
        return "alta", "cep_numero"
    constru = (obra.get("nome") or "").lower()
    constru_e = str(ext.get("construtora") or "").lower()
    bairro_o = (obra.get("bairro") or "").strip().lower()
    bairro_e = str((end.get("bairro") or "")).strip().lower()
    tok = [t for t in re.split(r"\W+", constru) if len(t) >= 4]
    if constru_e and any(t in constru_e for t in tok) and bairro_o and bairro_o == bairro_e:
        return "media", "construtora_bairro"
    return "baixa", "sem_match"


def _rebaixar_sem_fonte(confianca: str, tem_fonte: bool) -> str:
    """Sem citação de grounding = não-auditável → rebaixa (alta→media, media→baixa)."""
    if tem_fonte:
        return confianca
    return {"alta": "media", "media": "baixa"}.get(confianca, "baixa")


def _eh_instagram(f: dict) -> bool:
    alvo = ((f.get("dominio") or "") + " " + (f.get("uri") or "")).lower()
    return "instagram.com" in alvo or "instagr.am" in alvo


def _instagram_url(fontes: list[dict], ext: dict) -> str | None:
    """Instagram oficial: do JSON do modelo ou de uma citação instagram.com."""
    ig = (ext.get("instagram") or "").strip()
    if ig:
        return ig
    for f in fontes:
        if _eh_instagram(f):
            return f.get("uri")
    return None


def _tem_site_oficial(fontes: list[dict]) -> bool:
    return any(not _eh_portal(f) and not _eh_instagram(f) for f in fontes)


# ── Refino v2: PDF do empreendimento (book/memorial) = fonte OURO ──────────────
# Construtora entrega o documento do empreendimento; Gemini multimodal LÊ o PDF
# (não raspa HTML) → extração de alta fidelidade da fonte primária.

def _baixar_pdf(url: str, *, max_mb: int = 15) -> bytes | None:
    """Baixa um PDF público com guardas (scheme, content-type, tamanho). None se inválido."""
    if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
        return None
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as c:
            r = c.get(url, headers={"User-Agent": "gymsite-intelligence/1.0"})
        if r.status_code != 200:
            return None
        ct = (r.headers.get("content-type") or "").lower()
        if "pdf" not in ct and not url.lower().endswith(".pdf"):
            return None
        if len(r.content) > max_mb * 1024 * 1024 or len(r.content) < 1000:
            return None
        return r.content
    except (httpx.HTTPError, OSError):
        return None


def _extrair_do_pdf(pdf_bytes: bytes) -> dict | None:
    """Gemini multimodal lê o PDF do empreendimento → JSON estruturado (fonte primária)."""
    from google.genai import types
    from tools._genai_client import build_genai_client, generate_content_resilient

    client = build_genai_client()
    prompt = (
        "Este PDF é o material oficial de um empreendimento imobiliário. Extraia em JSON puro:\n"
        "{\n"
        '  "empreendimento": "<nome>", "construtora": "<nome>",\n'
        '  "torres": <int|null>, "andares": <int|null>, "unidades": <int total|null>,\n'
        '  "tipologia": "<studio|1-2 dorm|3+ dorm|comercial|misto|null>",\n'
        '  "amenidades": ["..."],\n'
        '  "endereco": {"cep": "<digits|null>", "numero": "<str|null>", "bairro": "<str|null>"}\n'
        "}\nUse SÓ o que está no documento. NÃO invente."
    )
    part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    resp = generate_content_resilient(
        client, model="gemini-2.5-flash", contents=[part, prompt], max_retries=2, base_delay=3.0)
    return _extrair_lancamento((resp.text or "").strip())


def extrair_empreendimento_de_pdf_local(caminho_pdf: str) -> dict | None:
    """Caminho MANUAL (estilo NotebookLM): analista fornece o PDF do empreendimento
    (book/memorial gated, material de vendas) → Gemini multimodal lê → extração
    estruturada auditada. Para leads de alto valor (Fase C) onde a descoberta
    automática do PDF não passa (download gated). None se falhar."""
    try:
        data = Path(caminho_pdf).read_bytes()
    except OSError:
        return None
    if len(data) < 1000:
        return None
    try:
        return _extrair_do_pdf(data)
    except Exception as e:
        print(f"[refino_pdf_local] falha: {type(e).__name__}: {e}")
        return None


def _refino_via_pdf(pdf_url: str, obra: dict) -> dict | None:
    """Baixa o PDF do empreendimento e extrai via multimodal. None se falhar."""
    pdf = _baixar_pdf(pdf_url)
    if not pdf:
        return None
    try:
        ext = _extrair_do_pdf(pdf)
        if ext and _unidades_do_extraido(ext):
            ext["_pdf_url"] = pdf_url
            return ext
    except Exception as e:
        print(f"[refino_pdf] falha extração: {type(e).__name__}: {e}")
    return None


# ── Refino v3: FETCH da página do lançamento (listing/site) → extração exata ───
# O grounding acha a fonte (ex: voudeimovel) mas o snippet raramente traz a contagem
# de unidades. Aqui baixamos a PÁGINA e extraímos torres×unidades reais do conteúdo —
# fonte primária ≈ PDF. Aplica mesmo em "media" (nome+bairro), pois o número agora é
# observado na página, não proxy área÷m².

def _baixar_html(url: str, *, max_kb: int = 900) -> str | None:
    """Baixa HTML público (UA de browser, segue redirect — inclui redirect de
    atribuição do Vertex). None se inválido/não-HTML."""
    if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
        return None
    try:
        with httpx.Client(timeout=25.0, follow_redirects=True) as c:
            r = c.get(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "pt-BR,pt;q=0.9",
            })
        if r.status_code != 200:
            return None
        ct = (r.headers.get("content-type") or "").lower()
        if "html" not in ct and "text" not in ct:
            return None
        return r.text[: max_kb * 1024]
    except (httpx.HTTPError, OSError):
        return None


def _html_para_texto(html: str, *, max_chars: int = 26000) -> str:
    """HTML → texto enxuto p/ o extrator: preserva JSON-LD e __NEXT_DATA__ (onde sites
    SSR guardam torres/unidades), remove script/style/tags do resto."""
    blobs = re.findall(
        r'<script[^>]*application/(?:ld\+json|json)[^>]*>(.*?)</script>', html, re.S | re.I)
    nextdata = re.findall(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    corpo = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', html)
    corpo = re.sub(r'(?s)<[^>]+>', ' ', corpo)
    corpo = re.sub(r'\s+', ' ', corpo).strip()
    estrut = ' '.join(blobs + nextdata)[:10000]
    return (corpo[:max_chars] + (' [DADOS_ESTRUTURADOS] ' + estrut if estrut else ''))


def _extrair_do_html(html: str) -> dict | None:
    """Gemini lê o texto da página do empreendimento → JSON estruturado."""
    from tools._genai_client import build_genai_client, generate_content_resilient

    client = build_genai_client()
    texto = _html_para_texto(html)
    prompt = (
        "Texto de uma página de empreendimento imobiliário (lançamento). Extraia em JSON puro:\n"
        "{\n"
        '  "empreendimento": "<nome>", "construtora": "<nome>",\n'
        '  "torres": <int|null>, "andares": <int|null>, "unidades": <int total|null>,\n'
        '  "unidades_por_torre": <int|null>,\n'
        '  "tipologia": "<studio|1-2 dorm|3+ dorm|comercial|misto|null>",\n'
        '  "areas_plantas": [<m² privativo de CADA planta/tipologia, número>],\n'
        '  "dormitorios": <int|null>, "suites": "<str ex: 1 ou 2|null>", "vagas": "<str|null>",\n'
        '  "preco_base": <número R$ a partir de|null>, "previsao_entrega": "<AAAA-MM|null>",\n'
        '  "amenidades": ["..."],\n'
        '  "obra": {"total_pct": <int 0-100|null>, "acabamento_pct": <int 0-100|null>,\n'
        '           "fase": "<fundacao|estrutura|alvenaria|acabamento|entregue|null>"},\n'
        '  "incorporadora": "<construtora/realização/incorporação|null>",\n'
        '  "imobiliaria_vendas": "<imobiliária/corretora responsável pelas vendas|null>",\n'
        '  "contato_vendas": "<telefone/WhatsApp de vendas|null>", "creci": "<CRECI|null>",\n'
        '  "endereco": {"cep": "<digits|null>", "numero": "<str|null>", "bairro": "<str|null>"}\n'
        "}\n"
        "RESPONSÁVEL: 'incorporadora' = quem CONSTRÓI/realiza (rótulos Construção/Realização/"
        "Incorporação). 'imobiliaria_vendas' = quem VENDE (Vendas/Corretora/Imobiliária, mesmo "
        "no rodapé/créditos). 'contato_vendas' = telefone ou WhatsApp de vendas. Extraia mesmo "
        "que não esteja num cabeçalho destacado. Sem dado → null.\n"
        "REGRAS: 'unidades' = total de apartamentos do projeto inteiro (some torres se a "
        "página der por torre). 'areas_plantas' = lista das metragens privativas distintas. "
        "'obra' = se houver Acompanhamento das Obras com % de conclusão: total_pct é o % geral; "
        "acabamento_pct é o % da etapa de acabamento/pintura; fase é a etapa de maior peso em "
        "andamento. Use SÓ o que está no texto. NÃO invente. Sem dado → null.\n\n"
        "PÁGINA:\n" + texto
    )
    resp = generate_content_resilient(
        client, model="gemini-2.5-flash", contents=[prompt], max_retries=2, base_delay=3.0)
    return _extrair_lancamento((resp.text or "").strip())


def _refino_via_pagina(url: str, obra: dict) -> dict | None:
    """Baixa a página do lançamento e extrai unidades reais. None se falhar."""
    html = _baixar_html(url)
    if not html:
        return None
    try:
        ext = _extrair_do_html(html)
        if ext and _unidades_do_extraido(ext):
            ext["_pagina_url"] = url
            return ext
    except Exception as e:
        print(f"[refino_pagina] falha extração: {type(e).__name__}: {e}")
    return None


def _melhor_fonte_url(fontes: list[dict], ext: dict) -> str | None:
    """URL pra fetch: site oficial (não-portal/não-instagram) primeiro; senão qualquer
    citação com uri (o redirect de atribuição do Vertex resolve pra página real)."""
    for f in fontes:
        if not _eh_portal(f) and not _eh_instagram(f) and f.get("uri"):
            return f.get("uri")
    for f in fontes:
        if f.get("uri"):
            return f.get("uri")
    return ext.get("site") or ext.get("url") or None


def refinar_demanda_via_lancamento(
    obra: dict,
    *,
    _grounding_fn: Callable[[str], dict] | None = None,
    _pdf_fn: Callable[[str, dict], dict | None] | None = None,
    _pagina_fn: Callable[[str, dict], dict | None] | None = None,
) -> dict:
    """Refina uma obra via site da construtora/incorporadora. AUDITÁVEL: usa as CITAÇÕES
    reais do grounding (não o url auto-reportado). Só ALTA (match + fonte) sobrescreve proxy.

    Retorna {unidades_exatas|None, andares, tipologia, amenidade_fitness, fonte_url,
             fontes[], confianca, metodo_match, empreendimento, auditado}. Nunca levanta.
    """
    base = {"unidades_exatas": None, "andares": None, "tipologia": None,
            "amenidade_fitness": False, "fonte_url": None, "instagram_url": None,
            "fontes": [], "cruzado": False, "confianca": "baixa", "fonte_tipo": None,
            "metodo_match": "sem_match", "empreendimento": None, "auditado": False}
    try:
        gfn = _grounding_fn or _grounding_lancamento
        g = gfn(_montar_query(obra)) or {}
        texto, fontes = g.get("texto", ""), (g.get("fontes") or [])
        ext = _extrair_lancamento(texto)
        if not ext:
            return base

        # OURO: PDF do empreendimento (book/memorial) lido por multimodal → fonte primária.
        pdf_url = ext.get("pdf_url")
        if pdf_url:
            pdf_fn = _pdf_fn or _refino_via_pdf
            pdf_ext = pdf_fn(pdf_url, obra)
            if pdf_ext and _unidades_do_extraido(pdf_ext):
                return {
                    "unidades_exatas": _unidades_do_extraido(pdf_ext),
                    "andares": pdf_ext.get("andares"),
                    "tipologia": pdf_ext.get("tipologia"),
                    "amenidade_fitness": _tem_amenidade_fitness(pdf_ext),
                    "fonte_url": pdf_ext.get("_pdf_url") or pdf_url,
                    "instagram_url": _instagram_url(fontes, ext),
                    "fontes": fontes,
                    "cruzado": True,
                    "confianca": "alta",
                    "fonte_tipo": "pdf_empreendimento",
                    "metodo_match": "pdf_documento",
                    "empreendimento": pdf_ext.get("empreendimento") or ext.get("empreendimento"),
                    "auditado": True,
                }

        match, metodo = _validar_match(obra, ext)
        tem_fonte = bool(fontes)
        emp = ext.get("empreendimento")
        instagram = _instagram_url(fontes, ext)
        site_of = _tem_site_oficial(fontes)
        cruzado = site_of and bool(instagram)
        # Buscamos PELO endereço: empreendimento achado + fonte oficial = link estabelecido.
        #   sem fonte/empreendimento → baixa (não-auditável);
        #   achado + site oficial      → media;
        #   + cep/número ecoado bate   → alta;  + instagram cruza  → alta.
        oficial = site_of or bool(instagram)   # site OU instagram = canal oficial
        if not tem_fonte or not emp:
            confianca = "baixa"
        else:
            confianca = "media" if oficial else "baixa"
            if metodo == "cep_numero" or cruzado:
                confianca = "alta"
        unidades = _unidades_do_extraido(ext)
        fonte_tipo = "site_instagram" if oficial else None
        pagina_url = None

        # FETCH da página quando o grounding não fechou em ALTA: baixa a listing/site
        # achado e extrai unidades reais do conteúdo (não do snippet). Página = fonte
        # primária OBSERVADA → vale mesmo sem cep/número, desde que o BAIRRO confira
        # (a busca já foi por endereço). Match por bairro normalizado (tolera acento;
        # o nome CNO é SPE/LTDA e não casa com a construtora).
        if confianca != "alta" and tem_fonte:
            cand_url = _melhor_fonte_url(fontes, ext)
            pag_fn = _pagina_fn or _refino_via_pagina
            pag = pag_fn(cand_url, obra) if cand_url else None
            if pag and _unidades_do_extraido(pag):
                from tools.bairro_normalize import normalizar_bairro

                end_p = pag.get("endereco") or {}
                b_o = normalizar_bairro(obra.get("bairro") or "")
                b_p = normalizar_bairro(end_p.get("bairro") or "")
                if b_o and b_o == b_p:
                    cep_o, cep_p = _digits(obra.get("cep")), _digits(end_p.get("cep"))
                    num_o, num_p = _digits(obra.get("numero_logradouro")), _digits(end_p.get("numero"))
                    casou_endereco = bool(cep_o and cep_o == cep_p and num_o and num_o == num_p)
                    unidades = _unidades_do_extraido(pag)
                    ext = {**ext, **{k: v for k, v in pag.items() if v is not None}}
                    confianca = "alta" if casou_endereco else "media"
                    metodo = "pagina_cep_numero" if casou_endereco else "pagina_bairro"
                    fonte_tipo = "pagina_lancamento"
                    pagina_url = pag.get("_pagina_url") or cand_url

        # Unidades da PÁGINA são observadas → aplicam mesmo em "media"; do snippet,
        # só em "alta" (gate conservador original, evita adotar número de snippet ruim).
        aplica_unidades = confianca == "alta" or fonte_tipo == "pagina_lancamento"
        return {
            "unidades_exatas": unidades if aplica_unidades else None,
            "torres": ext.get("torres"),
            "andares": ext.get("andares"),
            "tipologia": ext.get("tipologia"),
            "amenidade_fitness": _tem_amenidade_fitness(ext),
            # Ficha técnica ampliada (A) — só quando veio da página/PDF.
            "areas_plantas": _areas_plantas(ext) or None,
            "dormitorios": ext.get("dormitorios"),
            "suites": ext.get("suites"),
            "vagas": ext.get("vagas"),
            "preco_base": ext.get("preco_base"),
            "previsao_entrega": ext.get("previsao_entrega"),
            "obra_progresso": _obra_progresso(ext),
            "responsavel": identificar_responsavel_obra(
                pagina_url or _fonte_preferida(fontes), ext),  # quem contatar p/ parceria
            "fonte_url": pagina_url or _fonte_preferida(fontes),   # citação REAL
            "instagram_url": instagram,
            "fontes": fontes,
            "cruzado": cruzado,
            "confianca": confianca,
            "fonte_tipo": fonte_tipo,
            "metodo_match": metodo,
            "empreendimento": ext.get("empreendimento"),
            "auditado": tem_fonte,
        }
    except Exception as e:
        print(f"[refino_lancamento] falha: {type(e).__name__}: {e}")
        return base
