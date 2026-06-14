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
from typing import Any, Callable

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
_DOMINIOS_PORTAL = ("vivareal", "zapimoveis", "olx", "chavesnamao", "quintoandar",
                    "imovelweb", "lopes.com", "loft.com", "wimoveis", "netimoveis",
                    "google.com", "wikipedia", "facebook", "instagram")


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
        "Você DEVE usar a ferramenta de busca (não responda de memória). "
        "Pesquise a página oficial da construtora/incorporadora do empreendimento descrito.\n"
        "1) Escreva 1-2 frases com o que encontrou, citando a fonte.\n"
        "2) Depois, AO FINAL, um bloco JSON exatamente neste formato:\n"
        "{\n"
        '  "empreendimento": "<nome>", "construtora": "<nome>",\n'
        '  "torres": <int|null>, "andares": <int|null>, "unidades": <int total|null>,\n'
        '  "tipologia": "<studio|1-2 dorm|3+ dorm|comercial|misto|null>",\n'
        '  "amenidades": ["..."],\n'
        '  "endereco": {"cep": "<digits|null>", "numero": "<str|null>", "bairro": "<str|null>"}\n'
        "}\n"
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


def refinar_demanda_via_lancamento(
    obra: dict,
    *,
    _grounding_fn: Callable[[str], dict] | None = None,
) -> dict:
    """Refina uma obra via site da construtora/incorporadora. AUDITÁVEL: usa as CITAÇÕES
    reais do grounding (não o url auto-reportado). Só ALTA (match + fonte) sobrescreve proxy.

    Retorna {unidades_exatas|None, andares, tipologia, amenidade_fitness, fonte_url,
             fontes[], confianca, metodo_match, empreendimento, auditado}. Nunca levanta.
    """
    base = {"unidades_exatas": None, "andares": None, "tipologia": None,
            "amenidade_fitness": False, "fonte_url": None, "fontes": [],
            "confianca": "baixa", "metodo_match": "sem_match", "empreendimento": None,
            "auditado": False}
    try:
        gfn = _grounding_fn or _grounding_lancamento
        g = gfn(_montar_query(obra)) or {}
        texto, fontes = g.get("texto", ""), (g.get("fontes") or [])
        ext = _extrair_lancamento(texto)
        if not ext:
            return base
        match, metodo = _validar_match(obra, ext)
        tem_fonte = bool(fontes)
        confianca = _rebaixar_sem_fonte(match, tem_fonte)  # gate de auditabilidade
        unidades = _unidades_do_extraido(ext)
        return {
            "unidades_exatas": unidades if confianca == "alta" else None,
            "andares": ext.get("andares"),
            "tipologia": ext.get("tipologia"),
            "amenidade_fitness": _tem_amenidade_fitness(ext),
            "fonte_url": _fonte_preferida(fontes),   # citação REAL, não auto-reportada
            "fontes": fontes,
            "confianca": confianca,
            "metodo_match": metodo,
            "empreendimento": ext.get("empreendimento"),
            "auditado": tem_fonte,
        }
    except Exception as e:
        print(f"[refino_lancamento] falha: {type(e).__name__}: {e}")
        return base
