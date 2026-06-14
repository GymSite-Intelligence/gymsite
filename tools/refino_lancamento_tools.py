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
    constru = (obra.get("nome") or obra.get("nome_empresarial") or "").strip()
    log = (obra.get("logradouro") or "").strip()
    num = (obra.get("numero_logradouro") or "").strip()
    bairro = (obra.get("bairro") or "").strip()
    return (f"empreendimento residencial lançamento construtora {constru} "
            f"{log} {num} {bairro} torres unidades amenidades academia")


def _grounding_lancamento(query: str) -> str:
    """Chama Gemini+Search (Vertex) pedindo JSON do empreendimento. Rede."""
    from google.genai import types
    from tools._genai_client import build_genai_client, generate_content_resilient

    client = build_genai_client()
    prompt = (
        "Busque a página oficial de lançamento do empreendimento imobiliário descrito e "
        "responda em JSON puro (sem markdown):\n"
        "{\n"
        '  "empreendimento": "<nome>", "construtora": "<nome>", "url": "<fonte>",\n'
        '  "torres": <int|null>, "unidades": <int total|null>,\n'
        '  "tipologia": "<studio|1-2 dorm|3+ dorm|comercial|misto|null>",\n'
        '  "amenidades": ["..."],\n'
        '  "endereco": {"cep": "<digits|null>", "numero": "<str|null>", "bairro": "<str|null>"}\n'
        "}\n"
        "Se não achar com confiança, retorne unidades=null. NÃO invente.\n\n"
        f"Descrição: {query}"
    )
    resp = generate_content_resilient(
        client, model="gemini-2.5-flash", contents=prompt,
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
        max_retries=2, base_delay=3.0,
    )
    return (resp.text or "").strip()


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


def refinar_demanda_via_lancamento(
    obra: dict,
    *,
    _grounding_fn: Callable[[str], str] | None = None,
) -> dict:
    """Refina uma obra via site do lançamento. Só ALTA confiança sobrescreve proxy.

    Retorna {unidades_exatas|None, tipologia, amenidade_fitness, fonte_url,
             confianca, metodo_match, empreendimento}. Nunca levanta.
    """
    base = {"unidades_exatas": None, "tipologia": None, "amenidade_fitness": False,
            "fonte_url": None, "confianca": "baixa", "metodo_match": "sem_match",
            "empreendimento": None}
    try:
        gfn = _grounding_fn or _grounding_lancamento
        ext = _extrair_lancamento(gfn(_montar_query(obra)))
        if not ext:
            return base
        confianca, metodo = _validar_match(obra, ext)
        unidades = _unidades_do_extraido(ext)
        return {
            # só sobrescreve o proxy quando o match é de ALTA confiança.
            "unidades_exatas": unidades if confianca == "alta" else None,
            "tipologia": ext.get("tipologia"),
            "amenidade_fitness": _tem_amenidade_fitness(ext),
            "fonte_url": ext.get("url"),
            "confianca": confianca,
            "metodo_match": metodo,
            "empreendimento": ext.get("empreendimento"),
        }
    except Exception as e:
        print(f"[refino_lancamento] falha: {type(e).__name__}: {e}")
        return base
