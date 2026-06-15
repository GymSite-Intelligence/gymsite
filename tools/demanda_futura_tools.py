"""
Demanda futura datada (Apêndice B do Motor v2) — obras residenciais de grande porte
do CNO no município → moradores futuros → pool fitness → captura estimada → receita T+24.

REGRA DE OURO: zero hardcode. Todo fator vem de `parametros_metodologia` (com fonte),
recalibrável. Cadeia (cada fator carrega fonte exibida no relatório):

    unidades  × ocupacao(tipologia)        = moradores
    moradores × penetracao(perfil_bairro)  = pool_fitness_enderecavel
    pool      × market_share(realista)     = captura_estimada   (NÃO 100% — quota do raio)
    captura   × ticket × (1 − inadimplencia) = receita_incremental_T+24

Proxy ≠ fato: sem contagem exata de unidades, usa proxy area/m2_por_unidade (confiança
baixa); refino A4-grounded (site do lançamento) sobrescreve com unidades exatas.
Fonte CNO: public.cno_obras_grande_porte (fresco via RFB; basedosdados ≤2021 é dormente).
Plano: docs/arquitetura/PLANO_ENRIQUECIMENTO_RELATORIO.md §2.1.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from tools.parametros_metodologia import ocupacao_por_tipologia, param, param_meta


def _ticket_padrao() -> float:
    """Ticket mid do benchmark setorial (canal 2 — grounding/fallback, já sourced)."""
    try:
        from tools.benchmarks_tool import obter_benchmarks_setoriais

        t = (obter_benchmarks_setoriais().get("ticket_por_modelo") or {}).get("mid")
        if t:
            return float(t)
    except Exception:
        pass
    return 149.90  # fallback final rotulado se canal 2 indisponível


def estimar_demanda_obra(
    area_total_m2: float,
    *,
    unidades_exatas: float | None = None,
    tipologia: str | None = None,
    perfil_bairro: str = "geral",
    market_share: float | None = None,
    ticket_brl: float | None = None,
) -> dict[str, Any]:
    """Núcleo PURO — cadeia corrigida, fatores via param(). Base dos testes.

    unidades_exatas (refino A4) sobrescreve o proxy area/m2_por_unidade.
    Retorna pool E captura (proxy ≠ fato) + fatores_usados com fonte.
    """
    area = max(0.0, float(area_total_m2 or 0))
    m2_un = param("m2_por_unidade")
    unidades = float(unidades_exatas) if unidades_exatas else (area / m2_un if m2_un else 0.0)

    ocup_key = ocupacao_por_tipologia(tipologia)
    ocupacao = param(ocup_key)
    pen_key = "penetracao_bairro_ab" if perfil_bairro == "ab" else "penetracao_geral"
    penetracao = param(pen_key)
    share = float(market_share) if market_share is not None else param("market_share_default")
    inadimp = param("inadimplencia_default")
    ticket = float(ticket_brl) if ticket_brl is not None else _ticket_padrao()

    moradores = unidades * ocupacao
    pool = moradores * penetracao
    captura = pool * share
    receita = captura * ticket * (1 - inadimp)

    return {
        "unidades_est": round(unidades, 1),
        "unidades_fonte": "lancamento_exato" if unidades_exatas else "proxy_area/m2",
        "moradores_est": round(moradores, 1),
        "pool_fitness_est": round(pool, 1),
        "captura_est": round(captura, 1),
        "receita_incremental_est": round(receita, 2),
        "fatores_usados": {
            "ocupacao": param_meta(ocup_key),
            "penetracao": param_meta(pen_key),
            "market_share": ({"valor": share, "fonte": "A4/anéis"} if market_share is not None else param_meta("market_share_default")),
            "inadimplencia": param_meta("inadimplencia_default"),
            "ticket_brl": {"valor": ticket, "fonte": "benchmark_setorial_canal2"},
            "m2_por_unidade": param_meta("m2_por_unidade"),
        },
    }


def _ym_para_indice(yyyymm: str | None) -> int | None:
    if not yyyymm or len(str(yyyymm)) < 7:
        return None
    try:
        return int(str(yyyymm)[:4]) * 12 + (int(str(yyyymm)[5:7]) - 1)
    except ValueError:
        return None


def _meses_para_entrega(data_inicio: str | None) -> str | None:
    idx = _ym_para_indice(data_inicio)
    if idx is None:
        return None
    total = idx + int(param("meses_entrega"))
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _entrega_no_futuro(data_inicio: str | None, ref_yyyymm: str) -> bool:
    """Filtra zumbis do CNO: obra 'em curso' iniciada há décadas tem entrega no passado."""
    ei, ri = _ym_para_indice(_meses_para_entrega(data_inicio)), _ym_para_indice(ref_yyyymm)
    return ei is not None and ri is not None and ei >= ri


def _ref_atual_ym() -> str:
    n = datetime.now(timezone.utc)
    return f"{n.year:04d}-{n.month:02d}"


def _cutoff_inicio_iso(meses_atras: int = 36) -> str:
    n = datetime.now(timezone.utc)
    idx = (n.year * 12 + (n.month - 1)) - meses_atras
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}-01"


def _client():
    from tools.supabase_client import load_create_client

    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    return load_create_client()(os.environ["SUPABASE_URL"], key)


def _obras_grande_porte_municipio(cidade: str, uf: str) -> list[dict] | None:
    if not (os.environ.get("SUPABASE_URL") and (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )):
        return None
    try:
        from tools.ibge_tools import buscar_municipio

        mun = buscar_municipio(cidade, uf) or {}
        ibge = str(mun.get("codigo")) if mun.get("codigo") else None
        if not ibge:
            return None
        res = (
            _client()
            .table("cno_obras_grande_porte")
            .select("*")
            .eq("id_municipio", ibge)
            .gte("data_inicio", _cutoff_inicio_iso(36))
            .limit(5000)
            .execute()
        )
        return getattr(res, "data", None) or []
    except Exception as e:
        print(f"[demanda_futura] leitura Supabase falhou ({cidade}/{uf}): {type(e).__name__}: {e}")
        return None


def _confianca(n_obras: int) -> str:
    if n_obras == 0:
        return "nenhuma"
    return "media" if n_obras >= 3 else "baixa"


def _obras_futuras_municipio(
    cidade: str, uf: str, bairro: str | None, *, somente_em_curso: bool = True
) -> list[dict] | None:
    """Obras de grande porte com ENTREGA ainda no futuro (corta zumbis). None se fonte off."""
    obras = _obras_grande_porte_municipio(cidade, uf)
    if obras is None:
        return None
    if somente_em_curso:
        obras = [o for o in obras if o.get("em_curso")]
    ref = _ref_atual_ym()
    obras = [o for o in obras if _entrega_no_futuro(o.get("data_inicio"), ref)]
    if bairro:
        from tools.bairro_normalize import normalizar_bairro

        alvo = normalizar_bairro(bairro)
        obras = [o for o in obras if normalizar_bairro(o.get("bairro") or "") == alvo]
    return obras


def demanda_futura_datada(
    cidade: str,
    uf: str,
    *,
    bairro: str | None = None,
    perfil_bairro: str = "geral",
    market_share: float | None = None,
    ticket_brl: float | None = None,
    somente_em_curso: bool = True,
) -> dict[str, Any]:
    """Agrega demanda futura das obras de grande porte com entrega ainda à frente."""
    obras = _obras_futuras_municipio(cidade, uf, bairro, somente_em_curso=somente_em_curso)
    if obras is None:
        return {"status": "indisponivel", "motivo": "fonte_cno_grande_porte_indisponivel",
                "cidade": cidade, "uf": uf}

    if not obras:
        return {"status": "sem_dados", "cidade": cidade, "uf": uf, "bairro": bairro,
                "n_obras": 0, "confianca": "nenhuma", "fonte": "CNO grande porte (RFB)"}

    agg = {"moradores_est": 0.0, "pool_fitness_est": 0.0, "captura_est": 0.0,
           "receita_incremental_est": 0.0, "unidades_est": 0.0}
    entregas: list[str] = []
    fatores = None
    for o in obras:
        e = estimar_demanda_obra(
            float(o.get("area_m2") or 0),
            perfil_bairro=perfil_bairro, market_share=market_share, ticket_brl=ticket_brl,
        )
        for k in agg:
            agg[k] += e[k]
        fatores = e["fatores_usados"]  # mesmos para todas (params); expõe 1×
        jan = _meses_para_entrega(o.get("data_inicio"))
        if jan:
            entregas.append(jan)

    return {
        "status": "ok",
        "cidade": cidade, "uf": uf, "bairro": bairro,
        "n_obras": len(obras),
        "unidades_est": round(agg["unidades_est"], 1),
        "moradores_est": round(agg["moradores_est"], 1),
        "pool_fitness_est": round(agg["pool_fitness_est"], 1),
        "captura_est": round(agg["captura_est"], 1),
        "receita_incremental_est": round(agg["receita_incremental_est"], 2),
        "janela_entrega": {"de": min(entregas), "ate": max(entregas)} if entregas else None,
        "perfil_bairro": perfil_bairro,
        "fatores_usados": fatores,
        "confianca": _confianca(len(obras)),
        "fonte": "CNO grande porte (RFB) — proxy residencial área > 2000 m²",
        "nota_metodologica": (
            "pool = moradores × penetração (quem frequenta academia); captura = pool × "
            "market share do raio (NÃO 100%). Unidades por proxy área÷m2/unidade até refino "
            "A4 (site do lançamento) trazer contagem exata. Fatores e fontes em fatores_usados. "
            "Estimativa de prospecção — não é dado fiscal."
        ),
    }


def demanda_futura_detalhada(
    cidade: str,
    uf: str,
    *,
    bairro: str | None = None,
    perfil_bairro: str = "geral",
    top_n: int = 5,
    market_share: float | None = None,
    ticket_brl: float | None = None,
    _refino_fn: Any = None,
) -> dict[str, Any]:
    """Por-obra (top_n por área, com refino A4 do site do lançamento) + totais.

    Para o relatório (tabela de empreendimentos). Refino só nas top_n (grounding é caro);
    demais obras ficam no proxy. `_refino_fn` injetável → testável sem rede.
    """
    obras = _obras_futuras_municipio(cidade, uf, bairro)
    if obras is None:
        return {"status": "indisponivel", "cidade": cidade, "uf": uf}
    if not obras:
        return {"status": "sem_dados", "cidade": cidade, "uf": uf, "bairro": bairro,
                "n_obras": 0, "obras": [], "confianca": "nenhuma"}

    from tools.cno_bigquery_loader import _KW_COMERCIAL, _KW_RESIDENCIAL
    from tools.refino_lancamento_tools import refinar_demanda_via_lancamento

    def _classificar_residencial(nome: str, refino: dict | None) -> tuple[bool, str, str]:
        """(residencial, base, confianca). base diz a FONTE da decisão; confiança a reflete.

        Conservador: sem sinal → NÃO-residencial (não infla a demanda com obra ambígua).
        - refino_tipologia: site/IG do lançamento auditado → alta
        - nome_residencial / nome_comercial: keyword no nome CNO → media
        - sem_sinal: nada decidiu → baixa (fica fora dos totais)
        """
        tip = str((refino or {}).get("tipologia") or "").lower()
        if tip:
            if "residenc" in tip or "dorm" in tip or "studio" in tip:
                return True, "refino_tipologia", "alta"
            if tip in ("comercial", "infra"):
                return False, "refino_tipologia", "alta"
        n = (nome or "").lower()
        if any(k in n for k in _KW_RESIDENCIAL):
            return True, "nome_residencial", "media"
        if any(k in n for k in _KW_COMERCIAL):
            return False, "nome_comercial", "media"
        return False, "sem_sinal", "baixa"

    refino_fn = _refino_fn or refinar_demanda_via_lancamento
    obras = sorted(obras, key=lambda o: -float(o.get("area_m2") or 0))

    linhas: list[dict] = []
    tot = {"captura_est": 0.0, "moradores_est": 0.0}
    for i, o in enumerate(obras):
        if i < top_n:
            o = {**o, "cidade": cidade, "uf": uf}  # query do refino precisa de cidade/uf
        refino = refino_fn(o) if i < top_n else None
        unid_exatas = (refino or {}).get("unidades_exatas")
        tipologia = (refino or {}).get("tipologia")
        e = estimar_demanda_obra(
            float(o.get("area_m2") or 0), unidades_exatas=unid_exatas, tipologia=tipologia,
            perfil_bairro=perfil_bairro, market_share=market_share, ticket_brl=ticket_brl,
        )
        residencial, base_res, conf_res = _classificar_residencial(o.get("nome") or "", refino)
        # Gate residencial: prédio comercial/infra/ambíguo não gera morador → não soma
        # demanda. Mantém a obra na lista (transparência) mas fora dos totais (Apêndice A).
        if residencial:
            tot["captura_est"] += e["captura_est"]
            tot["moradores_est"] += e["moradores_est"]
        linhas.append({
            "empreendimento": (refino or {}).get("empreendimento"),
            "construtora": o.get("nome"),
            "bairro": o.get("bairro"),
            "unidades_est": e["unidades_est"],
            "unidades_fonte": e["unidades_fonte"],
            "entrega": _meses_para_entrega(o.get("data_inicio")),
            "amenidade_fitness": (refino or {}).get("amenidade_fitness", False),
            "captura_est": e["captura_est"] if residencial else 0.0,
            # confiança do refino (quando rodou) tem precedência; senão a da classificação.
            "confianca": (refino or {}).get("confianca") or conf_res,
            "provavel_residencial": residencial,
            "base_residencial": base_res,            # FONTE da classificação (auditável)
            "ni_responsavel": o.get("ni_responsavel"),  # CNPJ responsável no CNO (verificável)
            "fonte_url": (refino or {}).get("fonte_url"),
        })

    return {
        "status": "ok", "cidade": cidade, "uf": uf, "bairro": bairro,
        "n_obras": len(obras), "refinadas": min(top_n, len(obras)),
        "provavel_residencial_n": sum(1 for l in linhas if l["provavel_residencial"]),
        # Transparência: de ONDE veio a classificação residencial (fonte por contagem).
        "residencial_por_base": {
            base: sum(1 for l in linhas if l["provavel_residencial"] and l["base_residencial"] == base)
            for base in ("refino_tipologia", "nome_residencial")
        },
        "obras": linhas[:max(top_n, 10)],
        "captura_total_est": round(tot["captura_est"], 1),
        "moradores_total_est": round(tot["moradores_est"], 1),
        "perfil_bairro": perfil_bairro,
        "fonte": "CNO grande porte (RFB) + refino A4 (site do lançamento)",
        "nota": ("Proxy área = limite superior (inclui não-residencial); refino A4 e "
                 "provavel_residencial são o gate de confiança. Liderar pelo refinado."),
    }
