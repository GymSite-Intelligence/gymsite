"""
A9 — PositioningStrategist (Análise de Posicionamento e Framework ERRC).

Consome os outputs de A0–A6 (via contexto ADK) e gera relatório estratégico
de posicionamento: Framework ERRC, mapa de serviços, GAPs, ticket recomendado
e veredito OCEANO_AZUL / TRANSICAO / VERMELHO.

ENTRADAS (state keys reais do pipeline — ver tools/pipeline_deps.py):
  - input_params / market_context → entrypoint / A0
  - inteligencia_competitiva + oferta_concorrentes → A3b
  - concorrentes_brutos → A3a (praça inteira p/ gaps)
  - analise_financeira → A4
  - relatorio_md → A6 (A8 pós-A9)
  - demanda_futura → entrypoint (api enrichment)
  - demografia_bairro → A6 (bridge after_agent; opcional p/ Brilliant Basics)

SAÍDAS:
  - relatorio_posicionamento_md / relatorio_posicionamento → persistência/PDF
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("gymsite.a9")

from google.adk.agents import Agent
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# Parser tolerante a str/JSON/fence (output_key grava echo do LLM como string):
# sem ele, `state.get(...) or {}` deixava str passar e `.get()` crashava dentro
# do try/except, desligando silenciosamente veredito determinístico + LangCache.
from tools.competitor_tools import _parse_market_context

_GENERATE_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=8192),  # pyright: ignore[reportCallIssue]
)

_RELATORIOS_DIR = Path(__file__).resolve().parent.parent / "metrics" / "relatorios"


def _parse_json_from_text(raw: str) -> dict:
    """Extrai JSON de resposta LLM (com ou sem fence ```json)."""
    txt = (raw or "").strip()
    if not txt:
        raise json.JSONDecodeError("resposta vazia", txt, 0)
    if "```json" in txt:
        txt = txt.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in txt:
        txt = txt.split("```", 1)[1].split("```", 1)[0].strip()
    parsed = json.loads(txt)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("JSON raiz não é objeto", txt, 0)
    return parsed


_RESSALVA_INDETERMINADO = (
    "Ressalva: modelo sugerido por benchmark do setor — o cruzamento renda local × "
    "concorrência ficou indeterminado neste run (validar demanda do bairro antes de decidir)."
)


def _emendar_ressalva(texto: str | None) -> str | None:
    """Append idempotente da ressalva de INDETERMINADO num resumo já consolidado."""
    if not texto or _RESSALVA_INDETERMINADO in texto:
        return texto
    return f"{texto.rstrip()} {_RESSALVA_INDETERMINADO}"


def _patch_relatorio_json(relatorio_local_id: str, posicionamento: dict) -> None:
    """Atualiza metrics/relatorios/<id>.json com posicionamento_estrategico. Se o
    veredito ficou INDETERMINADO, emenda a ressalva no resumo_executivo já gravado
    pelo A6 (o resumo nasce ANTES do A9 — sem isso ele recomenda modelo sem aviso)."""
    if not relatorio_local_id:
        return
    path = _RELATORIOS_DIR / f"{relatorio_local_id}.json"
    if not path.is_file():
        logger.warning(
            "A9 patch: arquivo não encontrado %s",
            path,
            extra={"agent": "A9"},
        )
        return
    try:
        rel = json.loads(path.read_text(encoding="utf-8"))
        out = rel.setdefault("output_consolidado", {})
        if not isinstance(out, dict):
            out = {}
            rel["output_consolidado"] = out
        out["posicionamento_estrategico"] = posicionamento
        if str(posicionamento.get("veredito_posicionamento") or "").upper() == "INDETERMINADO":
            contato = out.get("contato_decisor")
            if isinstance(contato, dict) and contato.get("resumo_executivo"):
                contato["resumo_executivo"] = _emendar_ressalva(contato["resumo_executivo"])
            if out.get("resumo_executivo"):
                out["resumo_executivo"] = _emendar_ressalva(out["resumo_executivo"])
        path.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            "A9 patch JSON local OK id=%s",
            relatorio_local_id,
            extra={"agent": "A9"},
        )
    except Exception as e:
        logger.warning(
            "A9 patch JSON local falhou id=%s: %s",
            relatorio_local_id,
            e,
            exc_info=True,
            extra={"agent": "A9"},
        )


def _a9_langcache_enabled() -> bool:
    return os.getenv("LANGCACHE_A9_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _resolve_location_from_state(state: dict) -> tuple[str, str]:
    """cidade/bairro vêm de input_params, market_context ou chaves legadas no state."""
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    cidade = (
        state.get("cidade")
        or state.get("input_cidade")
        or ip.get("cidade")
        or ""
    )
    bairro = (
        state.get("bairro")
        or state.get("input_bairro")
        or ip.get("bairro")
        or ""
    )
    if not cidade or not bairro:
        mc = _parse_market_context(state.get("market_context"))
        inner = (
            mc.get("market_context")
            if isinstance(mc.get("market_context"), dict)
            else mc
        )
        if isinstance(inner, dict):
            cidade = cidade or inner.get("cidade") or ""
            bairro = bairro or inner.get("bairro") or ""
    return str(cidade).strip().lower(), str(bairro).strip().lower()


def _resolve_uf_from_state(state: dict) -> str:
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    uf = state.get("uf") or state.get("input_uf") or ip.get("uf") or ""
    if not uf:
        mc = _parse_market_context(state.get("market_context"))
        inner = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
        if isinstance(inner, dict):
            uf = inner.get("uf") or ""
    return str(uf).strip()


def _a9_override_veredito_deterministico(state: dict, parsed: dict) -> None:
    """Sobrepõe veredito_posicionamento do LLM pelo HEADROOM DETERMINÍSTICO (renda real
    IBGE 2022 × ticket dos concorrentes). LLM mantém ERRC/markdown/gaps; o veredito +
    bloco headroom_renda viram sourced/auditáveis. Igual ao padrão do A4 (tool computa,
    LLM narra). Não inventa: sem renda/ticket → mantém o do LLM."""
    try:
        from tools.posicionamento_renda import avaliar_posicionamento

        cidade, bairro = _resolve_location_from_state(state)
        uf = _resolve_uf_from_state(state)
        if not (cidade and bairro):
            return
        ic = _parse_market_context(state.get("inteligencia_competitiva"))
        inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
        concorrentes = (
            (inner.get("concorrentes_detalhados") or inner.get("concorrentes") or [])
            if isinstance(inner, dict) else []
        )
        # Sinais da Zona de Percepção (§2.1): gaps reais + densidade competitiva.
        gaps_pre = _gaps_reais(state)
        tem_gaps = bool(gaps_pre)
        nivel_sat = (inner.get("nivel_saturacao") if isinstance(inner, dict) else None) or ""
        densidade_baixa = not str(nivel_sat).upper().startswith(("ALTO", "SATURAD"))
        hr = avaliar_posicionamento(cidade, uf, bairro, concorrentes=concorrentes,
                                    densidade_premium_baixa=densidade_baixa, tem_gaps=tem_gaps)
        if hr.get("status") != "ok":
            return
        parsed["headroom_renda"] = hr  # renda_pc/percentil/tier sempre determinísticos
        # §2.1 — Zona de Percepção determinística sobrepõe (campos novos no output do A9).
        if hr.get("zona_percepcao"):
            parsed["zona_percepcao"] = hr.get("zona_percepcao")
            parsed["zona_nome"] = hr.get("zona_nome")
            parsed["zona_descricao"] = hr.get("zona_descricao")
        # §2.2 — alertas financeiros/fiscais determinísticos (consome A4).
        try:
            parsed["alertas_financeiros_fiscais"] = _alertas_financeiros_fiscais(
                state, hr.get("tier_modelo_percentil"), hr.get("ticket_teto_sustentavel")
            )
        except Exception:
            logger.warning("A9 alertas fiscais falharam", exc_info=True, extra={"agent": "A9"})
        # GAPs determinísticos: o PDF/relatório lê gaps_identificados (output estruturado);
        # o LLM chutava genérico (Nutrição/Recovery/Silver). Sobrepõe pelo dado real da praça.
        # B1+B2: mapa + gaps via cobertura_competitiva (ponto único).
        try:
            from tools.cobertura_competitiva import aplicar_cobertura_no_posicionamento

            aplicar_cobertura_no_posicionamento(state, parsed)
        except Exception:
            logger.warning("A9 cobertura override falhou", exc_info=True, extra={"agent": "A9"})
            gaps_reais = _gaps_reais(state)
            if gaps_reais is not None:
                llm_gaps = parsed.get("gaps_identificados")
                if llm_gaps:
                    parsed["gaps_identificados_llm"] = llm_gaps
                parsed["gaps_identificados"] = [
                    f"{g} — nenhum concorrente da praça anuncia (oportunidade de CRIAR)" for g in gaps_reais
                ] if gaps_reais else ["Mercado coberto nos serviços-núcleo — foco em AUMENTAR/REDUZIR (qualidade/preço), não em CRIAR"]
                parsed["fonte_gaps"] = "deterministico_oferta_concorrentes (planos+IG)"
        vd = hr.get("veredito_posicionamento")
        if vd and vd != "INDETERMINADO":
            # RN-A9-014/015: A4 sem modelo não cede ao headroom.
            if parsed.get("fonte_veredito") == "a4_sem_modelo_viavel":
                pass
            else:
                llm_v = parsed.get("veredito_posicionamento")
                if llm_v and llm_v != vd:
                    parsed["veredito_posicionamento_llm"] = llm_v
                parsed["veredito_posicionamento"] = vd
                parsed["fonte_veredito"] = "deterministico_headroom_renda (IBGE Censo 2022)"
                logger.info(
                    "A9 veredito determinístico: %s (LLM dizia %s) headroom_ratio=%s",
                    vd, llm_v, hr.get("headroom_ratio"), extra={"agent": "A9"},
                )
    except Exception:
        logger.warning("A9 override determinístico falhou", exc_info=True, extra={"agent": "A9"})


def _a9_cache_prompt(state: dict) -> str:
    """
    Chave LangCache A9 — deve ser única por relatório + mercado.

    Inclui relatorio_id (evita HIT entre Parangaba vs Meireles quando cidade/bairro
    estavam vazios no state) e hash dos top-5 concorrentes.
    """
    cidade, bairro = _resolve_location_from_state(state)
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    tipo = str(
        state.get("tipo_negocio") or ip.get("tipo_negocio") or "academia"
    ).strip().lower()
    rel_id = str(
        state.get("relatorio_id") or state.get("relatorio_local_id") or ""
    ).strip()
    rid = rel_id.replace("-", "")[:32] if rel_id else "no_rid"

    # Hash dos top-5 concorrentes para evitar false positives
    ic = _parse_market_context(state.get("inteligencia_competitiva"))
    inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
    concorrentes = (
        (inner.get("concorrentes_detalhados") or inner.get("concorrentes") or [])
        if isinstance(inner, dict)
        else []
    )

    # Extrai identificadores únicos dos top-5 concorrentes
    top5_ids = []
    for c in concorrentes[:5]:
        if isinstance(c, dict):
            pid = c.get("place_id") or c.get("nome") or ""
            if pid:
                top5_ids.append(str(pid).strip().lower())

    # Hash determinístico dos concorrentes
    conc_hash = "none"
    if top5_ids:
        sorted_ids = sorted(top5_ids)
        conc_hash = hashlib.md5("|".join(sorted_ids).encode()).hexdigest()[:8]

    n_conc = len(concorrentes) if isinstance(concorrentes, list) else 0

    return f"positioning_a9:{rid}:{cidade}:{bairro}:{tipo}:conc_{n_conc}:{conc_hash}"


def _resumo_demanda_futura(df: dict) -> str | None:
    """Texto compacto da demanda futura datada para injetar no prompt do A9."""
    if not isinstance(df, dict) or df.get("status") != "ok" or not df.get("n_obras"):
        return None
    jan = df.get("janela_entrega") or {}
    linhas = []
    for o in (df.get("obras") or [])[:5]:
        emp = o.get("empreendimento") or o.get("construtora") or "?"
        linhas.append(
            f"  - {emp} ({o.get('bairro')}): {o.get('unidades_est')} un "
            f"[{o.get('unidades_fonte')}], entrega {o.get('entrega')}, "
            f"conf={o.get('confianca')}, fitness_amenidade={o.get('amenidade_fitness')}"
        )
    return (
        "## DEMANDA FUTURA DATADA (Apêndice B — obras residenciais no raio)\n"
        f"- obras em curso (entrega futura): {df.get('n_obras')}; "
        f"prováveis residenciais: {df.get('provavel_residencial_n')}\n"
        f"- captura fitness estimada (T+24): ~{df.get('captura_total_est')} alunos; "
        f"janela de entrega: {jan.get('de')}→{jan.get('ate')}\n"
        f"- refinadas (site/instagram/PDF da construtora, auditado): {df.get('refinadas')}\n"
        + ("\n".join(linhas) if linhas else "")
        + "\nUse isto para o insight de JANELA DE ENTRADA (timing de abertura antes "
          "da entrega para capturar a migração de CEP). Rotule confiança/fonte."
    )


# Bridge das chaves do _detectar_modalidades → rótulo do catálogo de serviços do A9.
_SERVICOS_CATALOGO = {
    "musculacao": "Musculação", "funcional": "Treino funcional/HIIT",
    "danca": "Aulas de dança", "spinning": "Spinning", "lutas": "Artes marciais",
    "yoga": "Yoga/Pilates", "pilates": "Yoga/Pilates", "crossfit": "Crossfit",
    "piscina": "Natação/Hidro", "nutricao": "Nutrição integrada",
    "avaliacao": "Avaliação física", "personal": "Personal (PT)",
    "recovery": "Recovery/fisioterapia", "estetica": "Sauna/estética",
    "area_kids": "Aulas/espaço kids",
}


def _servicos_do_concorrente(c: dict) -> set[str]:
    """Mapeia o que o concorrente REALMENTE oferece (nome + planos_precos.inclui +
    serviços do marketing) pros rótulos do catálogo, via _detectar_modalidades."""
    from tools.competitor_offer_mapper import _detectar_modalidades

    blob = " ".join([
        str(c.get("nome") or ""),
        " ".join(str(s) for s in (c.get("servicos_oferecidos") or []) if s),
        " ".join(
            f"{p.get('plano', '')} {' '.join(str(x) for x in (p.get('inclui') or []))}"
            for p in (c.get("planos_precos") or []) if isinstance(p, dict)
        ),
    ])
    svc = {_SERVICOS_CATALOGO[k] for k in _detectar_modalidades(blob) if k in _SERVICOS_CATALOGO}
    # serviços já detectados nas captions do IG (A3a/cache) — chaves do catálogo
    svc |= {_SERVICOS_CATALOGO[k] for k in (c.get("servicos_ig") or []) if k in _SERVICOS_CATALOGO}
    return svc


def _concorrentes_para_oferta(state: dict) -> list[dict]:
    """Base da penetração de serviços = a PRAÇA inteira do bairro, não só os detalhados.
    União com dedupe por nome de concorrentes_detalhados + academias_analisadas +
    top_independentes. Bug Cocó (4b211a02): com 'analisados a fundo: 1', TBOX (crossfit),
    Krav Maga (artes marciais) e S3 (personal) estavam MAPEADOS na praça mas fora da
    base — e viravam 'oportunidade de CRIAR' com porta especializada aberta na esquina."""
    from tools.competitor_tools import _parse_market_context

    ic = _parse_market_context(state.get("inteligencia_competitiva"))
    inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
    fontes: list[dict] = []
    for chave in ("concorrentes_detalhados", "academias_analisadas", "top_independentes"):
        for origem in (inner, ic):
            v = origem.get(chave) if isinstance(origem, dict) else None
            if v:
                fontes.extend(x for x in v if isinstance(x, dict))
                break
    # Brutos do A3a: a praça inteira PELO NOME (run 3f4e0b82: Krav Maga e S3 estavam
    # 'mapeados' mas invisíveis pro ERRC — academias_analisadas é chave do A6 e não
    # existe no state que o A9 lê; os brutos existem e carregam o nome).
    brutos = state.get("concorrentes_brutos")
    if isinstance(brutos, list):
        for x in brutos:
            if not isinstance(x, dict):
                continue
            dn = x.get("displayName")
            nm = x.get("nome") or (dn.get("text") if isinstance(dn, dict) else "")
            if nm:
                fontes.append({**x, "nome": nm})
    vistos: set[str] = set()
    out: list[dict] = []
    for c in fontes:
        nome = str(c.get("nome") or "").strip().lower()
        if not nome or nome in vistos:
            continue
        vistos.add(nome)
        out.append(c)
    return out


def _dores_da_praca(state: dict) -> set[str]:
    """Categorias de dor medidas nos reviews (A3b) — insumo do ERRC 'Brilliant Basics'
    (auditoria Gemini 05/07): quando o mercado cobre os serviços, a diferenciação vem
    de executar com excelência o que a praça executa mal — e as dores dizem O QUE."""
    from tools.competitor_tools import _parse_market_context

    ic = _parse_market_context(state.get("inteligencia_competitiva"))
    inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
    dores = (inner.get("dores_dominantes") if isinstance(inner, dict) else None) or []
    out: set[str] = set()
    for d in dores:
        if isinstance(d, dict):
            cat = str(d.get("categoria") or d.get("dor") or "").strip().lower()
        else:
            cat = str(d).strip().lower()
        if cat:
            out.add(cat.replace(" ", "_"))
    return out


def _publico_dominante(state: dict) -> tuple[str, int] | None:
    """(faixa de referência, %feminino) — PONTO 80: prioriza faixa-alvo do input
    (mesmo lastro da regra de gênero), não o segmento com maior headcount."""
    from tools.genero_estrategia import resolver_faixa_alvo

    demo = state.get("demografia_bairro")
    perfil = (demo or {}).get("perfil_idade_sexo_bairro") if isinstance(demo, dict) else None
    seg = (perfil or {}).get("segmentos") if isinstance(perfil, dict) else None
    if not isinstance(seg, dict) or not seg:
        return None

    faixa_alvo = resolver_faixa_alvo(state, perfil if isinstance(perfil, dict) else None)
    if faixa_alvo in seg and isinstance(seg[faixa_alvo], dict) and seg[faixa_alvo].get("total"):
        dados = seg[faixa_alvo]
        return faixa_alvo, int(round(float(dados.get("pct_mulheres") or 0)))

    faixa, dados = max(
        ((f, v) for f, v in seg.items() if isinstance(v, dict) and v.get("total")),
        key=lambda kv: kv[1]["total"], default=(None, None),
    )
    if not faixa:
        return None
    return faixa, int(round(float(dados.get("pct_mulheres") or 0)))


def _servicos_minerados_state(state: dict) -> set[str]:
    """Serviços minerados pelo offer_mapper (site+IG, praça inteira) direto do state —
    cobre os concorrentes fora do detalhado (CT Greenlife) cuja oferta não chega
    mesclada em nenhum dict do A3b/A6."""
    om = state.get("oferta_concorrentes")
    if isinstance(om, str):
        try:
            om = json.loads(om)
        except Exception:
            return set()
    inner = om.get("oferta_concorrentes") if isinstance(om, dict) else None
    svcs: set[str] = set()
    for v in (inner or {}).values():
        if isinstance(v, dict):
            svcs |= {_SERVICOS_CATALOGO[k] for k in (v.get("modalidades") or []) if k in _SERVICOS_CATALOGO}
    return svcs


def _oferta_minerada_por_nome(state: dict) -> dict[str, set[str]]:
    """Oferta minerada do state (offer_mapper) por NOME de concorrente → rótulos
    do catálogo. Mesma fonte que a página exibe (competidores.oferta_mapeada)."""
    om = state.get("oferta_concorrentes")
    if isinstance(om, str):
        try:
            om = json.loads(om)
        except Exception:
            return {}
    inner = om.get("oferta_concorrentes") if isinstance(om, dict) else None
    out: dict[str, set[str]] = {}
    for nome, v in (inner or {}).items():
        if isinstance(v, dict):
            out[str(nome)] = {
                _SERVICOS_CATALOGO[k] for k in (v.get("modalidades") or [])
                if k in _SERVICOS_CATALOGO
            }
    return out


def _penetracao_oferta_unificada(state: dict, concs: list[dict]) -> tuple["Counter", int]:
    """Penetração por serviço unindo, POR CONCORRENTE, o detalhado (_servicos_do_
    concorrente) e a oferta minerada do state. Concorrente que só existe na oferta
    minerada (fora do gate de análise, ex.: Parque Esportes) entra na contagem —
    gap só existe se NINGUÉM da praça oferece (task #40)."""
    from collections import Counter

    minerada = _oferta_minerada_por_nome(state)
    pen: Counter = Counter()
    nomes_vistos: set[str] = set()
    for c in concs:
        nome = str(c.get("nome") or "")
        nomes_vistos.add(nome)
        for s in _servicos_do_concorrente(c) | minerada.get(nome, set()):
            pen[s] += 1
    extras = {nome: svcs for nome, svcs in minerada.items() if nome not in nomes_vistos}
    for svcs in extras.values():
        for s in svcs:
            pen[s] += 1
    return pen, len(concs) + len(extras)


def _gaps_reais(state: dict) -> list[str] | None:
    """Lista determinística dos serviços que NENHUM concorrente da praça ANUNCIA.

    Preferência: cobertura_competitiva (B1+B2) → só gaps com incluir_no_errc.
    Fallback: praça unificada legado (detalhados + minerada).
    """
    try:
        from tools.cobertura_competitiva import (
            filtrar_gaps_universais,
            mapa_servicos_da_cobertura,
            montar_cobertura_from_state,
        )

        cov = state.get("cobertura_competitiva")
        if not isinstance(cov, dict) or not cov.get("oferta_por_gated"):
            cov = montar_cobertura_from_state(state)
        if isinstance(cov, dict) and cov.get("oferta_por_gated"):
            state["cobertura_competitiva"] = cov
            _mapa, pen = mapa_servicos_da_cobertura(cov)
            n = int(cov.get("n_com_oferta") or 0)
            if not n:
                return []
            brutos = sorted(
                s for s in set(_SERVICOS_CATALOGO.values()) if pen.get(s, 0) == 0
            )
            validados = filtrar_gaps_universais(brutos, cobertura=cov)
            return [g["servico"] for g in validados if g.get("incluir_no_errc")]
    except Exception:
        logger.warning("A9 gaps via cobertura falhou — fallback legado", exc_info=True, extra={"agent": "A9"})

    concs = _concorrentes_para_oferta(state)
    minerados = _servicos_minerados_state(state)
    if not concs and not minerados:
        return None
    oferecidos: set[str] = set(minerados)
    for c in concs:
        oferecidos |= _servicos_do_concorrente(c)
    return sorted(r for r in set(_SERVICOS_CATALOGO.values()) if r not in oferecidos)


def _resumo_oferta_e_gaps(state: dict) -> str | None:
    """Computa, do dado REAL dos concorrentes (planos_precos.inclui + modalidades),
    o que cada um oferece + os GAPs (serviço que NENHUM oferece). Injetado no A9 pra
    a ERRC parar de chutar 'Nutrição+Recovery' genérico — o gap vira derivado, não palpite."""
    from collections import Counter

    from tools.competitor_tools import _parse_market_context

    ic = _parse_market_context(state.get("inteligencia_competitiva"))
    inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
    concs = (inner.get("concorrentes_detalhados") if isinstance(inner, dict) else None) or []
    concs = [c for c in concs if isinstance(c, dict)]
    if not concs:
        return None

    pen: Counter = Counter()
    linhas: list[str] = []
    for c in concs:
        svc = _servicos_do_concorrente(c)
        for s in svc:
            pen[s] += 1
        precos = [
            p.get("preco_mensal") for p in (c.get("planos_precos") or [])
            if isinstance(p, dict) and p.get("preco_mensal")
        ]
        linha = f"- {c.get('nome', '?')}: {', '.join(sorted(svc)) or 'oferta não mapeada'}"
        if precos:
            linha += f" | planos: {', '.join(str(x) for x in precos[:3])}"
        linhas.append(linha)

    gaps = sorted(r for r in set(_SERVICOS_CATALOGO.values()) if pen.get(r, 0) == 0)
    out = [
        "[DADO REAL — OFERTA DOS CONCORRENTES — use pra preencher mapa_servicos e os GAPs. "
        "NÃO invente serviço; só conte como gap o que está na lista abaixo:]",
        *linhas,
        "",
        "GAPS REAIS (serviço que NENHUM concorrente oferece): "
        + (", ".join(gaps) if gaps else "NENHUM — mercado coberto; foque em AUMENTAR/REDUZIR (qualidade), não em CRIAR serviço."),
        "Penetração: " + ", ".join(f"{s}={n}/{len(concs)}" for s, n in pen.most_common()),
    ]
    return "\n".join(out)


def _sintese_posicionamento_deterministica(state: dict, parsed: dict) -> str:
    """Síntese curta do posicionamento dos campos JÁ determinísticos do A9: veredito
    (override headroom de renda), ticket recomendado, gaps reais (_gaps_reais) e demanda
    futura. NÃO é o markdown ERRC (esse o LLM gera) — é o resumo de fatos travados, fonte
    única e coerente. Usado como fonte+fallback da narração (mesmo padrão do A6)."""
    cidade, bairro = _resolve_location_from_state(state)
    loc = f"{bairro.title()}, {cidade.title()}" if cidade else (bairro.title() or "bairro alvo")
    vere = (parsed.get("veredito_posicionamento") or "indeterminado").strip()
    ticket = (parsed.get("recomendacao_ticket") or {}).get("ticket_recomendado")
    gaps = _gaps_reais(state) or []

    partes = [f"Posicionamento {loc}: veredito {vere}."]
    if ticket not in (None, "", "N/A"):
        partes.append(f"Ticket recomendado R$ {ticket}.")
    if gaps:
        partes.append(
            f"Gaps reais (serviço que nenhum concorrente oferece): {len(gaps)} — "
            f"{', '.join(gaps)}."
        )
    else:
        partes.append(
            "Mercado coberto: nenhum gap de serviço — diferenciação por qualidade, "
            "não por novo serviço."
        )
    df = state.get("demanda_futura") or {}
    if isinstance(df, dict) and df.get("status") == "ok" and df.get("captura_total_est"):
        partes.append(
            f"Demanda futura: ~{df.get('captura_total_est')} alunos potenciais de obras "
            f"no raio (janela de entrada antes da entrega)."
        )
    return " ".join(partes)


def _sintese_posicionamento_narrada(state: dict, parsed: dict) -> str:
    """Reescreve a síntese determinística de forma fluente via Claude headless (subscription,
    sem api_key → escapa dunning/custo-token). Guardrail trava veredito/número → fallback é a
    própria síntese determinística. Default OFF (NARRADOR_CLAUDE_ENABLED=0). Mesmo padrão do A6."""
    import re as _re

    from tools.narrador_claude import narrar

    det = _sintese_posicionamento_deterministica(state, parsed)
    vere = (parsed.get("veredito_posicionamento") or "").strip()
    nums = _re.findall(r"\d[\d.,]*\d|\d", det)
    ancoras = ([vere] if vere else []) + nums
    instrucao = (
        "Reescreva a síntese de posicionamento abaixo de forma fluente e profissional, "
        "em 2 a 3 frases em português do Brasil. NÃO altere, invente nem remova NENHUM "
        "número, veredito ou gap. Não use ferramentas; responda apenas o texto."
    )
    r = narrar(fatos_texto=det, ancoras=ancoras, fallback=det, instrucao=instrucao)
    if r.get("fonte") == "claude_subscription":
        logger.info("A9 síntese de posicionamento narrada via Claude headless (subscription)",
                    extra={"agent": "A9"})
    return r["texto"]


def _cenario_recomendado_a4(state: dict) -> dict:
    """Extrai o cenário RECOMENDADO do A4 (state['analise_financeira']) — fonte dos
    campos fiscais/ocupação novos (FASE 1): ticket_piso_ocupacao, ocupacao_pct,
    anexo_simples, fator_r, tributos_mensal. Tolerante: dict ou str (parseia)."""
    fin = _parse_market_context(state.get("analise_financeira"))
    if not isinstance(fin, dict):
        return {}
    # o A4 às vezes embrulha em {"analise_financeira": {...}}
    if isinstance(fin.get("analise_financeira"), dict):
        fin = fin["analise_financeira"]
    cenarios = fin.get("cenarios") if isinstance(fin.get("cenarios"), dict) else {}
    if not cenarios:
        return {}
    rec = fin.get("recomendacao") or fin.get("recomendacao_modelo") or fin.get("modelo_recomendado") or ""
    rec_l = str(rec).strip().lower()
    if rec_l in ("nenhum", "none"):
        return {}
    # casa pelo label do modelo OU pelo modelo_key; senão pega o primeiro cenário.
    for c in cenarios.values():
        if isinstance(c, dict) and (
            str(c.get("modelo") or "").strip().lower() == rec_l
            or str(c.get("modelo_key") or "").strip().lower() == rec_l
        ):
            return c
    primeiro = next((c for c in cenarios.values() if isinstance(c, dict)), {})
    return primeiro or {}


def _alertas_financeiros_fiscais(state: dict, tier: str | None, ticket_rec) -> list[dict]:
    """Alertas determinísticos (sem LLM) cruzando A9 × A4 — PLANO_MOTOR_FINANCEIRO_V3 §2.2
    + adendo M&A (Valuation readiness). 3 tipos:
      1. FATOR_R          — tier Mid/Premium: CNAE 9313-1/00 nasce Anexo V 15,5%; migra
                            Anexo III 6% só com folha+pró-labore ≥28% do faturamento.
      2. OCUPACAO_TICKET  — ticket_rec < ticket_piso_ocupacao do A4 (insustentável pelo aluguel).
      3. KPI_BENCHMARK    — metas por tier atreladas ao Valuation (múltiplo EBITDA Boutique 3,8-6,5x).
    Fonte sempre citada (determinístico/benchmark). Consome state['analise_financeira'] (A4)."""
    from tools.parametros_metodologia import param

    alertas: list[dict] = []
    tier_norm = str(tier or "").strip()
    is_mid_premium = tier_norm in ("Mid Market", "Premium")
    cen = _cenario_recomendado_a4(state)

    # ── 1) FATOR_R (gatilho tier Mid/Premium) ──
    if is_mid_premium:
        anexo_atual = cen.get("anexo_simples")
        fator_r = cen.get("fator_r")
        corte = param("fator_r_corte_folha")  # 0.28
        if anexo_atual:
            diag_anexo = (
                f"A4 projeta Anexo {anexo_atual} (Fator R = {fator_r} ≷ corte {corte:.0%})."
            )
        else:
            diag_anexo = "Anexo do A4 indisponível — assuma Anexo V (15,5%) até comprovar folha."
        alertas.append({
            "tipo": "FATOR_R",
            "severidade": "ALTA",
            "titulo": "Fator R: folha+pró-labore ≥28% migra o Simples do Anexo V (15,5%) p/ III (6%)",
            "diagnostico": (
                f"Academia (CNAE 9313-1/00, sem MEI) NASCE no Anexo V (15,5%). Só migra para o "
                f"Anexo III (6%) com folha+pró-labore ≥ {corte:.0%} do faturamento (Fator R). "
                f"{diag_anexo} Em tier {tier_norm}, proteger a folha é alavanca fiscal, não custo a cortar."
            ),
            "anexo_atual": anexo_atual,
            "fator_r": fator_r,
            "corte_fator_r": corte,
            "fonte": "deterministico (LC 123/2006 — Fator R) + A4 analise_financeira",
        })

    # ── 2) OCUPACAO_TICKET (ticket_rec < ticket_piso_ocupacao do A4) ──
    ticket_piso = cen.get("ticket_piso_ocupacao")
    ocup_pct = cen.get("ocupacao_pct")
    teto_ocup = cen.get("teto_ocupacao")
    if (isinstance(ticket_rec, (int, float)) and isinstance(ticket_piso, (int, float))
            and ticket_rec < ticket_piso):
        ocup_txt = f"{ocup_pct:.0%}" if isinstance(ocup_pct, (int, float)) else "indisponível"
        teto_txt = f"{teto_ocup:.0%}" if isinstance(teto_ocup, (int, float)) else "teto"
        alertas.append({
            "tipo": "OCUPACAO_TICKET",
            "severidade": "CRITICA",
            "titulo": "Ticket viável pela renda, mas insustentável pelo aluguel",
            "diagnostico": (
                f"O ticket recomendado (R$ {ticket_rec:.0f}) é menor que o piso de ocupação do A4 "
                f"(R$ {ticket_piso:.0f}) — o aluguel não cabe no teto. Ocupação projetada {ocup_txt} "
                f"> teto {teto_txt}: ticket sustentável pela renda, insustentável pelo aluguel. "
                f"Subir ticket, reduzir área ou renegociar locação."
            ),
            "ticket_recomendado": round(float(ticket_rec), 2),
            "ticket_piso_ocupacao": round(float(ticket_piso), 2),
            "ocupacao_pct": ocup_pct,
            "teto_ocupacao": teto_ocup,
            "fonte": "deterministico (A4 ticket_piso_ocupacao × teto de ocupação imobiliária)",
        })

    # ── 3) KPI_BENCHMARK (metas por tier, atreladas ao Valuation — adendo M&A) ──
    tier_key = {"Premium": "premium", "Mid Market": "mid", "Low Cost": "low"}.get(tier_norm, "mid")
    cac_max = param("cac_max_valuation")          # R$180
    ret_min = param("retencao_ano_min_valuation")  # 0.85
    ltv_key = "ltv_aluno_min_premium" if tier_key == "premium" else "ltv_aluno_min_mid"
    ltv_min = param(ltv_key) if tier_key in ("premium", "mid") else param("ltv_aluno_min_mid")
    mult_min = param(f"multiplo_ebitda_{tier_key}_min")
    mult_max = param(f"multiplo_ebitda_{tier_key}_max")
    alertas.append({
        "tipo": "KPI_BENCHMARK",
        "severidade": "MEDIA",
        "titulo": "KPIs de Valuation readiness (M&A) — blindam o plano contra otimismo e furo em due-diligence",
        "diagnostico": (
            f"Para sustentar o múltiplo do tier {tier_norm} ({mult_min:g}–{mult_max:g}× EBITDA; "
            f"Boutique/Premium 3,8–6,5×), o A4 e a operação precisam comprovar: "
            f"CAC < R$ {cac_max:.0f}/aluno, retenção anual > {ret_min:.0%} (churn < ~5%/mês), "
            f"LTV/aluno > R$ {ltv_min:.0f}. Teto de ocupação >15% derruba metade do valuation."
        ),
        "metas": {
            "cac_max": cac_max,
            "retencao_ano_min": ret_min,
            "ltv_aluno_min": ltv_min,
            "multiplo_ebitda": [mult_min, mult_max],
        },
        "fonte": "benchmark M&A (Boutique/Premium 3,8-6,5x EBITDA) + parametros_metodologia §2.5",
    })

    return alertas


def _build_errc_indeterminado(state: dict, motivo: str, fonte_veredito: str) -> dict:
    """Output A9 quando não dá para cravar posicionamento (ex.: A4 sem modelo viável)."""
    market = state.get("market_context") if isinstance(state.get("market_context"), dict) else {}
    cidade, bairro = _resolve_location_from_state(state)
    uf = _resolve_uf_from_state(state)
    out = {
        "markdown": (
            "## Posicionamento Estratégico\n\n"
            f"_Posicionamento indeterminado: {motivo}._\n\n"
            "_Sem modelo viável identificado pelo A4, não é possível "
            "recomendar ticket nem tier de posicionamento com confiança._\n\n"
            "_Revisar parâmetros financeiros (área, aluguel, ticket) antes de "
            "definir estratégia de mercado._\n"
        ),
        "veredito_posicionamento": "INDETERMINADO",
        "fonte_veredito": fonte_veredito,
        "zona_percepcao": None,
        "zona_nome": None,
        "zona_descricao": None,
        "recomendacao_ticket": {
            "ticket_recomendado": None,
            "ticket_mercado": None,
            "ticket_minimo": None,
            "ticket_maximo": None,
            "confianca": "indisponivel",
            "aviso": motivo,
        },
        "headroom_renda": None,
        "modelo_a4": "nenhum",
        "framework_errc": {
            "eliminar": [],
            "reduzir": [],
            "aumentar": [],
            "criar": [],
        },
        "gaps_identificados": [],
        "mapa_servicos": {},
        "alertas_financeiros_fiscais": [],
        "fonte_geracao": "deterministico_errc",
        "bairro": bairro or market.get("bairro"),
        "cidade": cidade or market.get("cidade"),
        "uf": uf or market.get("uf"),
    }
    # B1+B2: mapa/gaps competitivos independem do veredito financeiro.
    try:
        from tools.cobertura_competitiva import aplicar_cobertura_no_posicionamento

        aplicar_cobertura_no_posicionamento(state, out)
        criar = [
            g.get("gap") or g.get("servico")
            for g in (out.get("gaps_validados") or [])
            if g.get("incluir_no_errc")
        ]
        out["framework_errc"]["criar"] = (
            criar
            if criar
            else ["Mercado coberto nos serviços-núcleo — sem CRIAR; foco em AUMENTAR/REDUZIR."]
            if out.get("mapa_servicos")
            else []
        )
    except Exception:
        logger.warning("A9 cobertura no indeterminado falhou", exc_info=True, extra={"agent": "A9"})
    return out


def _errc_deterministica(state: dict) -> dict:
    """ERRC + posicionamento 100% DETERMINÍSTICO, da matéria-prima já calculada:
    headroom de renda (avaliar_posicionamento — IBGE Censo 2022 × ticket dos concorrentes),
    gaps reais e penetração da oferta real dos concorrentes (planos_precos + modalidades + IG).

    O LLM do A9 NUNCA produziu a matéria-prima — recebia tudo pronto e só narrava a ERRC.
    Aqui montamos a ERRC por TEMPLATE ancorado no dado. Retorna o dict no contrato do A9
    (markdown + campos estruturados), pronto pra ser o output do agente OU o fallback/fonte
    da narração via narrar(). Recalibrável via parametros_metodologia (params do headroom)."""
    from collections import Counter

    from tools.competitor_tools import _parse_market_context
    from tools.posicionamento_renda import avaliar_posicionamento

    # RN-A9-014: ancora no modelo A4; "nenhum" → INDETERMINADO sem ticket (RN-A9-015).
    fin = _parse_market_context(state.get("analise_financeira") or state.get("analise_financeira_pronto"))
    if isinstance(fin, dict) and isinstance(fin.get("analise_financeira"), dict):
        fin = fin["analise_financeira"]
    if not isinstance(fin, dict):
        fin = {}
    modelo_a4 = (
        fin.get("modelo_recomendado")
        or fin.get("recomendacao_modelo")
        or fin.get("recomendacao")
        or ""
    )
    if str(modelo_a4).strip().lower() in ("nenhum", "none"):
        alerta = fin.get("alerta_viabilidade") or "todos_cenarios_inviaveis"
        return _build_errc_indeterminado(
            state,
            motivo=f"A4 sem modelo viável (alerta: {alerta})",
            fonte_veredito="a4_sem_modelo_viavel",
        )

    cidade, bairro = _resolve_location_from_state(state)
    uf = _resolve_uf_from_state(state)
    loc = f"{bairro.title()}, {cidade.title()}" if cidade else (bairro.title() or "bairro alvo")

    ic = _parse_market_context(state.get("inteligencia_competitiva"))
    inner = ic.get("inteligencia_competitiva") if isinstance(ic.get("inteligencia_competitiva"), dict) else ic
    concs = [c for c in ((inner.get("concorrentes_detalhados") or inner.get("concorrentes") or [])
                         if isinstance(inner, dict) else []) if isinstance(c, dict)]
    nivel_sat = (inner.get("nivel_saturacao") if isinstance(inner, dict) else None) or "indeterminada"

    # penetração dos serviços do catálogo (universo) na oferta real dos concorrentes.
    # Calculado ANTES do avaliar_posicionamento → alimenta os sinais da Zona de Percepção.
    # B1+B2: preferência cobertura_competitiva (denominador = n_com_oferta); fallback legado.
    universo = sorted(set(_SERVICOS_CATALOGO.values()))
    mapa_servicos: dict = {}
    gaps: list[str] = []
    n = 0
    try:
        from tools.cobertura_competitiva import (
            aplicar_cobertura_no_posicionamento,
            montar_cobertura_from_state,
        )

        cov = state.get("cobertura_competitiva")
        if not isinstance(cov, dict) or not cov.get("oferta_por_gated"):
            cov = montar_cobertura_from_state(state)
        if isinstance(cov, dict) and cov.get("oferta_por_gated"):
            state["cobertura_competitiva"] = cov
            _tmp: dict = {}
            aplicar_cobertura_no_posicionamento(state, _tmp)
            mapa_servicos = _tmp.get("mapa_servicos") or {}
            gaps = [
                g["servico"]
                for g in (_tmp.get("gaps_validados") or [])
                if g.get("incluir_no_errc")
            ]
            n = int(cov.get("n_com_oferta") or 0)
    except Exception:
        logger.warning("A9 mapa via cobertura falhou — fallback", exc_info=True, extra={"agent": "A9"})
        mapa_servicos = {}
        gaps = []

    if not mapa_servicos:
        pen, n = _penetracao_oferta_unificada(state, concs)
        mapa_servicos = {
            s: {"oferecem": pen.get(s, 0), "de": n,
                "penetracao_pct": round(100 * pen.get(s, 0) / n) if n else 0}
            for s in universo
        }
        gaps = [s for s in universo if pen.get(s, 0) == 0] if n else []

    # Sinais da Zona de Percepção (§2.1): tem_gaps = há serviço que ninguém oferece;
    # densidade_baixa = saturação NÃO alta/saturada (poucos players no raio).
    tem_gaps = bool(gaps)
    densidade_baixa = not str(nivel_sat).upper().startswith(("ALTO", "SATURAD"))

    hr = (avaliar_posicionamento(cidade, uf, bairro, concorrentes=concs,
                                 densidade_premium_baixa=densidade_baixa, tem_gaps=tem_gaps)
          if (cidade and bairro) else {"status": "sem_local"})
    ok = hr.get("status") == "ok"
    veredito = (hr.get("veredito_posicionamento") if ok else None) or "INDETERMINADO"
    zona_percepcao = hr.get("zona_percepcao") if ok else None
    zona_nome = hr.get("zona_nome") if ok else None
    zona_descricao = hr.get("zona_descricao") if ok else None
    ticket_rec = hr.get("ticket_teto_sustentavel") if ok else None
    ticket_mkt = hr.get("ticket_mercado") if ok else None
    ratio = hr.get("headroom_ratio") if ok else None
    tier = hr.get("tier_modelo_percentil") if ok else None

    # RN-A9-015: veredito INDETERMINADO não crava ticket.
    if veredito == "INDETERMINADO":
        ticket_rec = None

    # banda de ticket: piso = mercado atual, teto = teto sustentável da renda (recomendado).
    ticket_min = round(ticket_mkt) if isinstance(ticket_mkt, (int, float)) else None
    ticket_max = round(ticket_rec) if isinstance(ticket_rec, (int, float)) else None

    # §2.3 — piso de ticket pela ocupação (aluguel) do A4 + flag de insustentabilidade.
    cen_a4 = _cenario_recomendado_a4(state)
    ticket_piso_ocupacao = cen_a4.get("ticket_piso_ocupacao")
    ticket_insustentavel_aluguel = bool(
        isinstance(ticket_rec, (int, float)) and isinstance(ticket_piso_ocupacao, (int, float))
        and ticket_rec < ticket_piso_ocupacao
    )

    # §2.2 — alertas financeiros/fiscais determinísticos (FATOR_R, OCUPACAO_TICKET, KPI_BENCHMARK).
    alertas_financeiros_fiscais = _alertas_financeiros_fiscais(state, tier, ticket_rec)

    # comparativo de mercado: menor plano REAL de cada concorrente + o recomendado.
    comparativo: dict = {}
    for c in concs:
        precos = [p.get("preco_mensal") for p in (c.get("planos_precos") or [])
                  if isinstance(p, dict) and p.get("preco_mensal")]
        precos = [float(x) for x in precos if isinstance(x, (int, float))]
        if precos:
            comparativo[str(c.get("nome") or "?")[:24]] = round(min(precos))
    comparativo = dict(list(comparativo.items())[:5])
    if isinstance(ticket_rec, (int, float)):
        comparativo["recomendado"] = round(ticket_rec)

    # ── 4 dimensões ERRC (template ANCORADO no dado, não no palpite do LLM) ──
    eliminar = ["Guerra de preço / planos genéricos low-cost — destrói margem no oceano vermelho."]
    if str(nivel_sat).upper().startswith("ALTO"):
        eliminar.append(f"Competir só por preço num mercado saturado ({n} concorrentes no bairro).")
    reduzir = ["CAC alto e complexidade operacional (mix de planos excessivo).",
               "Capacidade ociosa em horário de baixa — escalonar a grade."]
    if veredito == "VERMELHO":
        reduzir.append("Ambição premium sem lastro de renda (headroom baixo) — calibrar para o tier real.")
    # §2.4 — Trava ERRC: em tier Mid/Premium NÃO cortar folha/comissão. A folha vira
    # alavanca a PROTEGER (Fator R ≥28% migra Simples Anexo V→III + churn premium sobe se
    # corta equipe). Mantém os cortes de CAC/ociosidade acima; só adiciona a trava condicional.
    if str(tier or "").strip() in ("Mid Market", "Premium"):
        reduzir.append(
            f"PROTEGER a folha (NÃO cortar salário/comissão): em tier {tier} a folha é "
            f"alavanca, não custo — Fator R ≥28% migra o Simples do Anexo V (15,5%) p/ III (6%), "
            f"e cortar equipe dispara o churn premium. Reduza CAC e ociosidade, jamais a folha."
        )
    aumentar = []
    if ratio and veredito in ("OCEANO_AZUL", "TRANSICAO"):
        aumentar.append(
            f"Exclusividade, atendimento e margem por aluno — há espaço premium real "
            f"(headroom ratio {ratio}, tier {tier})."
        )
    else:
        aumentar.append("Retenção, NPS e comunidade — diferenciação por experiência (sem lastro premium).")
    aumentar.append("Ticket médio rumo ao teto sustentável da renda local.")
    # ── Brilliant Basics (auditoria Gemini 05/07): as DORES medidas nos reviews viram
    # diretriz nas 4 dimensões — "entregar com precisão o que a praça executa mal".
    # Cada item cita a dor/dado de origem (regra do carimbo).
    dores = _dores_da_praca(state)
    if {"contrato_abusivo", "contrato"} & dores:
        eliminar.append(
            "Atrito contratual — cancelamento livre e termos transparentes: "
            "'contrato abusivo' é dor medida nos reviews da praça (retenção por valor, não por multa)."
        )
    if {"atendimento_ruim", "atendimento"} & dores:
        eliminar.append(
            "Instrutor de salão passivo — equipe dimensionada pra acolhimento proativo: "
            "'atendimento ruim' é a dor mais citada da praça."
        )
    if {"ruido_alto", "ruido"} & dores:
        reduzir.append(
            "Pressão do horário de pico — escalonar grade e precificar off-peak: dissipa a "
            "superlotação de 17h–19h que gera a dor 'ruído alto' medida nos reviews."
        )
    if {"climatizacao", "estrutura_envelhecida", "equipamento_problema"} & dores:
        aumentar.append(
            "Conforto ambiental como diferencial defensável: climatização dimensionada pro "
            "calor local + manutenção preventiva com SLA de reparo — ataca as dores "
            "'climatização/estrutura/equipamento' medidas nos reviews da concorrência."
        )

    criar = ([f"{g} — nenhum concorrente da praça anuncia." for g in gaps]
             if gaps else ["Mercado coberto nos serviços-núcleo — sem CRIAR; foco em AUMENTAR/REDUZIR."])
    # Público maduro → comunidade de longevidade funcional (não disputar alta intensidade
    # já coberta). Derivado do Censo por setor na FAIXA-ALVO (PONTO 80), não do max headcount.
    _pub = _publico_dominante(state)
    if _pub and _pub[0] in ("40-59", "60+"):
        criar.append(
            f"Comunidade de longevidade funcional — mobilidade, saúde articular e hipertrofia "
            f"preventiva: o público-alvo da praça é {_pub[0]} ({_pub[1]}% feminino, "
            f"Censo 2022 por setor), que migra por previsibilidade e conforto, não por intensidade."
        )

    # PONTO 56: pauta ERRC no gênero da faixa-alvo (mesma regra do A6).
    try:
        from tools.genero_estrategia import extrair_genero_do_state, sugestoes_genero_errc

        _gdec = extrair_genero_do_state(state)
        for _sug in sugestoes_genero_errc(
            _gdec.get("genero") or "misto",
            _gdec.get("pct_mulheres") if _gdec.get("genero") == "feminino" else _gdec.get("pct_homens"),
        ):
            aumentar.append(_sug)
    except Exception:
        pass

    # ── markdown ──
    def _bul(xs):
        return "\n".join(f"- {x}" for x in xs)

    mapa_linhas = "\n".join(
        f"| {s} | {v['oferecem']}/{v['de']} | {v['penetracao_pct']}% |"
        for s, v in mapa_servicos.items()
    )
    tk_rec = f"R$ {ticket_rec:.0f}" if isinstance(ticket_rec, (int, float)) else "indisponível"
    tk_mkt = f"R$ {ticket_mkt:.0f}" if isinstance(ticket_mkt, (int, float)) else "indisponível"
    head = f" (headroom ratio {ratio}, tier {tier})" if ratio else ""
    # §2.1 — linha da Zona de Percepção (substitui as 3 caixas; veredito vira derivado).
    zona_linha = (
        f"**Zona de Percepção:** {zona_percepcao} — {zona_nome} ({zona_descricao})\n"
        if zona_percepcao else ""
    )
    # §2.3 — alerta de ticket insustentável pelo aluguel (cruza piso de ocupação do A4).
    ocup_linha = (
        f"**⚠️ Ticket viável pela renda mas insustentável pelo aluguel:** "
        f"piso de ocupação (A4) R$ {ticket_piso_ocupacao:.0f} > ticket recomendado {tk_rec}.\n"
        if ticket_insustentavel_aluguel and isinstance(ticket_piso_ocupacao, (int, float)) else ""
    )
    markdown = (
        f"## Posicionamento Estratégico — {loc}\n\n"
        f"{zona_linha}"
        f"**Veredito (legado):** {veredito}{head}\n"
        f"**Ticket recomendado:** {tk_rec} (teto sustentável da renda) · "
        f"**ticket de mercado atual:** {tk_mkt}\n"
        f"{ocup_linha}\n"
        f"### Framework ERRC\n"
        f"**ELIMINAR**\n{_bul(eliminar)}\n\n"
        f"**REDUZIR**\n{_bul(reduzir)}\n\n"
        f"**AUMENTAR**\n{_bul(aumentar)}\n\n"
        f"**CRIAR**\n{_bul(criar)}\n\n"
        f"### Mapa de serviços (penetração na praça)\n"
        f"| Serviço | Oferecem | Penetração |\n|---|---|---|\n{mapa_linhas}\n\n"
        f"_Fonte: headroom de renda (IBGE Censo 2022) + oferta real dos concorrentes "
        f"(planos + IG). ERRC determinística — recalibrável via parametros_metodologia._\n"
    )

    out = {
        "markdown": markdown,
        # §2.1 — 6 Zonas de Percepção (campos novos); veredito legado DERIVADO da zona (compat).
        "zona_percepcao": zona_percepcao,
        "zona_nome": zona_nome,
        "zona_descricao": zona_descricao,
        "veredito_posicionamento": veredito,
        "fonte_veredito": "deterministico_zona_percepcao (headroom IBGE Censo 2022) — veredito legado derivado",
        "recomendacao_ticket": {
            "ticket_recomendado": ticket_rec, "ticket_mercado": ticket_mkt,
            "ticket_minimo": ticket_min, "ticket_maximo": ticket_max,
            "comparativo_mercado": comparativo,
            "confianca": "indisponivel" if veredito == "INDETERMINADO" else "alta",
            # §2.3 — cruzamento com o piso de ocupação (aluguel) do A4.
            "ticket_piso_ocupacao": (
                round(float(ticket_piso_ocupacao), 2)
                if isinstance(ticket_piso_ocupacao, (int, float)) else None
            ),
            "ticket_insustentavel_aluguel": ticket_insustentavel_aluguel,
            "fonte": "ticket_teto_sustentavel = renda_pc × ticket_renda_pct_premium (param); piso de ocupação do A4",
        },
        "gaps_identificados": (
            [f"{g} — nenhum concorrente da praça anuncia (oportunidade de CRIAR)" for g in gaps]
            if gaps else ["Mercado coberto nos serviços-núcleo — foco em AUMENTAR/REDUZIR"]
        ),
        "fonte_gaps": (
            "deterministico_cobertura_competitiva_b1_b2"
            if isinstance(state.get("cobertura_competitiva"), dict)
            and (state.get("cobertura_competitiva") or {}).get("oferta_por_gated")
            else "deterministico_oferta_concorrentes (planos+IG)"
        ),
        "mapa_servicos": mapa_servicos,
        "framework_errc": {"eliminar": eliminar, "reduzir": reduzir,
                           "aumentar": aumentar, "criar": criar},
        # §2.2 — alertas determinísticos financeiros/fiscais (consome A4 analise_financeira).
        "alertas_financeiros_fiscais": alertas_financeiros_fiscais,
        "headroom_renda": hr if ok else None,
        "fonte_geracao": "deterministico_errc",
    }
    try:
        from tools.cobertura_competitiva import aplicar_cobertura_no_posicionamento

        aplicar_cobertura_no_posicionamento(state, out)
        # Reancora CRIAR no ERRC aos gaps já filtrados (B2).
        para_criar = [
            g.get("gap") or g.get("servico")
            for g in (out.get("gaps_validados") or [])
            if g.get("incluir_no_errc")
        ]
        if para_criar or out.get("gaps_validados") is not None:
            # Preserva bullets de público maduro / gênero já anexados em `criar`.
            extras = [
                x for x in criar
                if isinstance(x, str) and "nenhum concorrente" not in x.lower()
                and "mercado coberto" not in x.lower()
            ]
            base = (
                para_criar
                if para_criar
                else ["Mercado coberto nos serviços-núcleo — sem CRIAR; foco em AUMENTAR/REDUZIR."]
            )
            out["framework_errc"]["criar"] = [*base, *extras]
            # Markdown CRIAR: re-render leve só da seção seria caro; gaps_identificados
            # já está filtrado — o PDF estruturado é a fonte canônica.
    except Exception:
        logger.warning("A9 attach cobertura no return falhou", exc_info=True, extra={"agent": "A9"})
    return out


def _a9_inject_oferta_e_gaps(state: dict, llm_request) -> None:
    """Injeta a oferta real + gaps computados no prompt do A9 (substrato da ERRC)."""
    try:
        resumo = _resumo_oferta_e_gaps(state)
        if resumo and getattr(llm_request, "contents", None) is not None:
            llm_request.contents.append(
                types.Content(role="user", parts=[types.Part(text=resumo)])
            )
    except Exception:
        pass


def _a9_inject_demanda_futura(state: dict, llm_request) -> None:
    """Injeta o resumo da demanda futura no prompt do A9 (não vem na conversa A0-A6)."""
    try:
        resumo = _resumo_demanda_futura(state.get("demanda_futura") or {})
        if resumo and getattr(llm_request, "contents", None) is not None:
            llm_request.contents.append(
                types.Content(role="user", parts=[types.Part(text=resumo)])
            )
    except Exception:
        pass


def _a9_before_model_callback(callback_context, llm_request):
    """LangCache hit → retorna LlmResponse e pula gemini-3.6-flash (~30–90s)."""
    _state = getattr(callback_context, "state", {}) or {}
    _a9_inject_oferta_e_gaps(_state, llm_request)  # oferta real dos concorrentes + gaps
    _a9_inject_demanda_futura(_state, llm_request)
    if not _a9_langcache_enabled():
        return None
    try:
        from tools.langcache_client import langcache_search

        state = getattr(callback_context, "state", {}) or {}
        prompt_key = _a9_cache_prompt(state)

        # Hash do prompt completo como atributo para evitar false positives
        # quando dois prompts diferentes têm os mesmos primeiros 1024 chars
        full_prompt_hash = hashlib.sha256(prompt_key.encode()).hexdigest()[:16]

        # Threshold alto: chaves positioning_a9:* são parecidas entre bairros;
        # 0.88 causava o mesmo JSON em relatórios diferentes (Fortaleza).
        try:
            threshold = float(os.getenv("LANGCACHE_A9_SIMILARITY", "0.97"))
        except ValueError:
            threshold = 0.97

        cached = langcache_search(
            prompt_key,
            similarity_threshold=threshold,
            attributes={"prompt_hash": full_prompt_hash, "agent": "a9"},
        )
        if not cached:
            return None

        state["_a9_langcache_hit"] = True
        logger.info(
            "A9 LangCache HIT: %s",
            prompt_key[:80],
            extra={"agent": "A9", "cache_hit": True},
        )
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=cached)],
            ),
            turn_complete=True,
            custom_metadata={"langcache_hit": True},
        )
    except Exception:
        logger.warning(
            "A9 LangCache before_model falhou — prosseguindo sem cache",
            exc_info=True,
            extra={"agent": "A9"},
        )
        return None


def _a9_after_model_callback(callback_context, llm_response):
    """Persiste output A9 no LangCache para runs futuros."""
    if not _a9_langcache_enabled():
        return llm_response
    try:
        from tools.langcache_client import langcache_set

        state = getattr(callback_context, "state", {}) or {}
        content = getattr(llm_response, "content", None)
        text = ""
        if content and getattr(content, "parts", None):
            for part in content.parts:
                if getattr(part, "text", None):
                    text += part.text
        text = text.strip()

        meta = getattr(llm_response, "custom_metadata", None) or {}
        if meta.get("langcache_hit"):
            return llm_response

        if text:
            prompt_key = _a9_cache_prompt(state)
            full_prompt_hash = hashlib.sha256(prompt_key.encode()).hexdigest()[:16]

            langcache_set(
                prompt_key,
                text,
                attributes={"prompt_hash": full_prompt_hash, "agent": "a9"},
            )
            logger.debug("A9 LangCache SET OK", extra={"agent": "A9"})
    except Exception:
        logger.warning(
            "A9 LangCache after_model falhou",
            exc_info=True,
            extra={"agent": "A9"},
        )
    return llm_response


def _a9_after_agent_callback(callback_context):
    """Parseia JSON do output_key e persiste no state + JSON local + Supabase."""
    start = time.perf_counter()
    try:
        state = getattr(callback_context, "state", {}) or {}
        raw = state.get("relatorio_posicionamento_md")
        if isinstance(raw, dict):
            parsed = raw
        else:
            parsed = _parse_json_from_text(str(raw or ""))

        # C6.2: valida o output do LLM contra o contrato (leniente — loga divergência,
        # não rejeita). Pega malformação de campo cedo sem quebrar o pipeline tolerante.
        try:
            from models.pipeline_schemas import A9Output, validar_lenient

            parsed = validar_lenient(A9Output, parsed, agente="A9")
        except Exception:
            pass

        state["relatorio_posicionamento"] = parsed
        # Veredito DETERMINÍSTICO (headroom de renda) sobrepõe o do LLM — sourced/auditável.
        _a9_override_veredito_deterministico(state, parsed)
        # B1+B2: garante mapa/gaps mesmo se o override saiu cedo (sem cidade / headroom).
        try:
            from tools.cobertura_competitiva import aplicar_cobertura_no_posicionamento

            aplicar_cobertura_no_posicionamento(state, parsed)
        except Exception:
            logger.warning("A9 after_agent cobertura falhou", exc_info=True, extra={"agent": "A9"})
        try:
            from tools.matriz_demo_saturacao import attach_matriz_demo_saturacao

            attach_matriz_demo_saturacao(state, parsed)
        except Exception:
            logger.warning("A9 matriz_demo_saturacao falhou", exc_info=True, extra={"agent": "A9"})
        try:
            from tools.absorcao_margem_fresca import attach_absorcao_margem_fresca

            attach_absorcao_margem_fresca(state, parsed)
        except Exception:
            logger.warning("A9 absorcao_margem_fresca falhou", exc_info=True, extra={"agent": "A9"})
        # Síntese de posicionamento narrada (Claude headless quando ligado; fallback
        # determinístico). Pós-override → usa o veredito determinístico. Default OFF.
        try:
            parsed["sintese_posicionamento"] = _sintese_posicionamento_narrada(state, parsed)
        except Exception as e:
            logger.warning("A9 síntese posicionamento falhou: %s", e, extra={"agent": "A9"})
        if parsed.get("markdown"):
            state["relatorio_posicionamento_md"] = parsed["markdown"]
        if state.get("_a9_langcache_hit"):
            parsed["fonte_geracao"] = "langcache"
            parsed["cache_prompt"] = _a9_cache_prompt(state)[:200]

        veredito = parsed.get("veredito_posicionamento", "N/A")
        gaps = len(parsed.get("gaps_identificados") or [])
        ticket = (parsed.get("recomendacao_ticket") or {}).get("ticket_recomendado", "N/A")
        logger.info(
            "A9 posicionamento OK: veredito=%s gaps=%d ticket=R$%s",
            veredito,
            gaps,
            ticket,
            extra={"agent": "A9"},
        )

        local_id = state.get("relatorio_local_id")
        if isinstance(local_id, str) and local_id:
            _patch_relatorio_json(local_id, parsed)

        rel_uuid = state.get("relatorio_id")
        if isinstance(rel_uuid, str) and rel_uuid:
            try:
                from db.supabase_writer import (
                    append_ressalva_resumo_failsafe,
                    write_posicionamento_failsafe,
                )

                write_posicionamento_failsafe(rel_uuid, parsed)
                if str(parsed.get("veredito_posicionamento") or "").upper() == "INDETERMINADO":
                    append_ressalva_resumo_failsafe(rel_uuid, _RESSALVA_INDETERMINADO)
            except Exception as e:
                logger.warning(
                    "A9 Supabase posicionamento falhou: %s",
                    e,
                    exc_info=True,
                    extra={"agent": "A9"},
                )

        # A8 roda AQUI (pós-A9), não mais no after-A6: só neste ponto o posicionamento
        # do A9 está disponível, então o validador enxerga modelo (A4) × tier/ticket (A9)
        # × veredito e checa a coerência cross-agente (INV-3/4/5). Recarrega o JSON local,
        # que _patch_relatorio_json acabou de atualizar com o posicionamento. Fail-safe.
        try:
            from tools.a8_runner import persist_validacao, run_a8_validation

            relatorio_full = None
            if isinstance(local_id, str) and local_id:
                _p = _RELATORIOS_DIR / f"{local_id}.json"
                if _p.is_file():
                    relatorio_full = json.loads(_p.read_text(encoding="utf-8"))
            markdown = state.get("relatorio_md") if isinstance(state.get("relatorio_md"), str) else ""
            validacao = run_a8_validation(markdown, state, relatorio=relatorio_full)
            if validacao:
                if relatorio_full is not None and isinstance(local_id, str):
                    relatorio_full["validacao_a8"] = validacao
                    (_RELATORIOS_DIR / f"{local_id}.json").write_text(
                        json.dumps(relatorio_full, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                rid = rel_uuid or local_id
                org_id = (
                    (relatorio_full or {}).get("org_id")
                    or os.getenv("SUPABASE_GYMSITE_ORG_ID")
                    or "00000000-0000-0000-0000-000000000001"
                )
                if rid:
                    persist_validacao(str(rid), str(org_id), validacao)
        except Exception:
            logger.warning(
                "A9 A8 validation/persist falhou",
                exc_info=True,
                extra={"agent": "A9"},
            )

        elapsed = time.perf_counter() - start
        logger.info(
            "A9 after_agent completed in %.2fs",
            elapsed,
            extra={"agent": "A9"},
        )

    except json.JSONDecodeError as e:
        st = getattr(callback_context, "state", {}) or {}
        raw_preview = str(st.get("relatorio_posicionamento_md") or "")[:2000]
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Falha ao parsear JSON: {e}",
            "raw_output": raw_preview,
        }
        logger.error(
            "A9 ERRO ao parsear JSON",
            exc_info=True,
            extra={"agent": "A9"},
        )
    except Exception as e:
        callback_context.state["relatorio_posicionamento"] = {
            "erro": f"Erro inesperado: {e}",
        }
        logger.error(
            "A9 ERRO inesperado no after_agent",
            exc_info=True,
            extra={"agent": "A9"},
        )


# ─────────────────────────────────────────────────────────────────────────────
# A9 DETERMINÍSTICO (BaseAgent, sem LLM).
#
# Antes era LlmAgent (Gemini Pro) que SÓ narrava a ERRC: a matéria-prima (headroom
# de renda IBGE, gaps reais, penetração da oferta dos concorrentes) já vinha pronta e
# determinística, injetada no prompt; o veredito/gaps/ticket eram override determinístico
# DEPOIS. O LLM nunca produziu dado — só vestia. Determinizado via _errc_deterministica:
# elimina variância, custo Gemini Pro (~R$100/mês) e a exposição ao dunning/Vertex.
#
# A síntese executiva fluente segue no _a9_after_agent_callback (narrar() via Claude
# headless/subscription, opcional, default OFF). A ERRC markdown é template determinístico.
# ─────────────────────────────────────────────────────────────────────────────
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions


class PositioningStrategistAgent(BaseAgent):
    """A9 determinístico: monta a ERRC + posicionamento por template da matéria-prima
    já calculada. Grava o dict no contrato do A9; o after_agent_callback parseia (dict
    direto), confirma o veredito determinístico, narra a síntese e persiste."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        try:
            parsed = _errc_deterministica(state)
        except Exception as e:  # nunca derruba o pipeline
            parsed = {
                "erro": f"{type(e).__name__}: {e}",
                "veredito_posicionamento": "INDETERMINADO",
                "markdown": "",
                "fonte_geracao": "deterministico_errc",
            }
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            # dict (não string): o _a9_after_agent_callback usa parsed=raw direto.
            actions=EventActions(state_delta={
                "relatorio_posicionamento_md": parsed,
                "relatorio_posicionamento": parsed,
            }),
        )


positioning_strategist_agent = PositioningStrategistAgent(
    name="PositioningStrategist",
    description=(
        "A9 determinístico (sem LLM): monta ERRC + veredito + ticket + GAPs + mapa de "
        "serviços da matéria-prima determinística (headroom de renda IBGE Censo 2022 + "
        "oferta real dos concorrentes). Síntese executiva fluente opcional via Claude headless."
    ),
)
positioning_strategist_agent.after_agent_callback = _a9_after_agent_callback
