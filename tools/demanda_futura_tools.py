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

from tools.parametros_metodologia import ocupacao_por_tipologia, param, param_int, param_meta


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
    ocupacao_censo: float | None = None,
    areas_plantas: list[float] | None = None,
) -> dict[str, Any]:
    """Núcleo PURO — cadeia corrigida, fatores via FONTE real > param fallback.

    unidades_exatas (refino A4) sobrescreve o proxy area/m2_por_unidade.
    ocupacao_censo (IBGE Censo 2022 setor, média moradores REAL do bairro) é a FONTE da
    ocupação; o param ocupacao_* é só fallback rotulado quando o Censo não responde
    (regra de ouro: dado tem fonte/método, não hardcode). Retorna pool E captura
    (proxy ≠ fato) + fatores_usados com fonte.
    """
    area = max(0.0, float(area_total_m2 or 0))
    m2_un = param("m2_por_unidade")
    unidades = float(unidades_exatas) if unidades_exatas else (area / m2_un if m2_un else 0.0)

    # Moradores/unidade: prioriza a ÁREA-MÉDIA real das plantas (plantas variadas →
    # média confrontada com benchmark m²/morador), pois a tipologia textual é grossa.
    # Censo setor é fallback (média do bairro); param tipologia é último fallback.
    ocup_key = ocupacao_por_tipologia(tipologia)
    _areas = [float(a) for a in (areas_plantas or []) if isinstance(a, (int, float)) and a > 0]
    if _areas:
        area_media = sum(_areas) / len(_areas)
        m2_por_morador = param("m2_por_morador")
        # Relação área→moradores é SUB-linear: apto grande tem mais m² POR pessoa, não
        # proporcionalmente mais gente. Linear puro estourava (191 m² → 7,6 moradores).
        # Clampa no teto IBGE (max_moradores_por_unidade) e piso 1,0.
        teto = param("max_moradores_por_unidade")
        bruto = (area_media / m2_por_morador) if m2_por_morador else param(ocup_key)
        ocupacao = max(1.0, min(bruto, teto))
        ocup_fonte = {
            "valor": round(ocupacao, 2),
            "fonte": "área-média das plantas ÷ benchmark m²/morador (clamp teto IBGE)",
            "metodo": (f"média de {len(_areas)} plantas = {area_media:.1f} m² ÷ {m2_por_morador} "
                       f"m²/morador = {bruto:.1f} → clamp [1,0; {teto}]"),
            "m2_por_morador": param_meta("m2_por_morador"),
            "max_moradores_por_unidade": param_meta("max_moradores_por_unidade"),
        }
    elif ocupacao_censo and float(ocupacao_censo) > 0:
        ocupacao = float(ocupacao_censo)
        ocup_fonte = {
            "valor": round(ocupacao, 2),
            "fonte": "IBGE Censo 2022 por setor censitário (média de moradores do bairro)",
            "metodo": "agregado dos setores no raio do centróide do bairro",
        }
    else:
        ocupacao = param(ocup_key)
        ocup_fonte = {**param_meta(ocup_key), "nota": "fallback rotulado — Censo setor indisponível"}
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
            "ocupacao": ocup_fonte,
            "penetracao": param_meta(pen_key),
            "market_share": ({"valor": share, "fonte": "A4/anéis"} if market_share is not None else param_meta("market_share_default")),
            "inadimplencia": param_meta("inadimplencia_default"),
            "ticket_brl": {"valor": ticket, "fonte": "benchmark_setorial_canal2"},
            "m2_por_unidade": param_meta("m2_por_unidade"),
        },
    }


def _janela_quente(obra_prog: dict | None) -> dict | None:
    """Gatilho de timing/MKT (C): obra na reta final → entrega iminente → avisar o
    cliente p/ contatar construtora/corretor antes da concorrência. Thresholds em param."""
    if not isinstance(obra_prog, dict):
        return None
    total = obra_prog.get("total_pct")
    acab = obra_prog.get("acabamento_pct")
    fase = (obra_prog.get("fase") or "").strip().lower()
    th_acab = param_int("obra_acabamento_threshold_pct")
    th_total = param_int("obra_total_threshold_pct")
    quente = (
        (isinstance(acab, (int, float)) and acab >= th_acab)
        or (isinstance(total, (int, float)) and total >= th_total)
        or fase in ("acabamento", "entregue")
    )
    if not quente:
        return None
    return {
        "ativo": True, "total_pct": total, "acabamento_pct": acab, "fase": fase or None,
        "diretriz": (
            "Obra na reta final (entrega iminente) — contate a construtora/corretor AGORA "
            "para ação de marketing e capte os futuros moradores antes da concorrência."
        ),
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


def _cutoff_inicio_iso(meses_atras: int | None = None) -> str:
    # Janela retroativa recalibrável (zero-hardcode); default rotulado em _DEFAULTS.
    if meses_atras is None:
        meses_atras = param_int("cutoff_obras_meses")
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
            .gte("data_inicio", _cutoff_inicio_iso())
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
    perfil_bairro: str = "auto",
    market_share: float | None = None,
    ticket_brl: float | None = None,
    somente_em_curso: bool = True,
    _demo_fn: Any = None,
) -> dict[str, Any]:
    """Agrega demanda futura das obras de grande porte com entrega ainda à frente."""
    obras = _obras_futuras_municipio(cidade, uf, bairro, somente_em_curso=somente_em_curso)
    if obras is None:
        return {"status": "indisponivel", "motivo": "fonte_cno_grande_porte_indisponivel",
                "cidade": cidade, "uf": uf}

    if not obras:
        return {"status": "sem_dados", "cidade": cidade, "uf": uf, "bairro": bairro,
                "n_obras": 0, "confianca": "nenhuma", "fonte": "CNO grande porte (RFB)"}

    # Perfil A/B derivado da renda real do bairro ("auto"); valor explícito é honrado.
    perfil_fonte: dict | None = None
    if perfil_bairro == "auto":
        perfil_bairro, perfil_fonte = _perfil_renda_bairro(cidade, uf, bairro, obras, _demo_fn)

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
        "perfil_bairro_fonte": perfil_fonte,
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


def _ocupacao_censo_bairro(
    cidade: str, uf: str, bairro: str | None, obras: list[dict],
    _censo_fn: Any = None,
) -> tuple[float | None, dict | None]:
    """(media_moradores, bloco_censo) do Censo 2022 setor no centróide do bairro.

    FONTE real da ocupação (regra de ouro); best-effort — falha → (None, None) e o
    estimador cai no param fallback. id_municipio vem das obras CNO (acelera a query BQ).
    """
    try:
        from tools.censo_setor_tools import demografia_setor_censo
        from tools.maps_tools import geocode_endereco

        censo_fn = _censo_fn or demografia_setor_censo
        end = f"{bairro}, {cidade}, Brasil" if (bairro or "").strip() else f"{cidade}, Brasil"
        geo = geocode_endereco(end)
        lat, lng = geo.get("lat"), geo.get("lng")
        if lat is None or lng is None:
            return None, None
        idm = next((str(o.get("id_municipio")) for o in obras if o.get("id_municipio")), None)
        censo = censo_fn(lat, lng, id_municipio=idm)
        if censo and censo.get("media_moradores"):
            return float(censo["media_moradores"]), censo
    except Exception as exc:
        print(f"[demanda] ocupação Censo falhou: {type(exc).__name__}: {exc}")
    return None, None


def _perfil_renda_bairro(
    cidade: str, uf: str, bairro: str | None, obras: list[dict],
    _demo_fn: Any = None,
) -> tuple[str, dict | None]:
    """(perfil, meta) derivado da renda REAL do bairro (CKAN IDH-Renda + renda pc).

    Corrige o capenga de sempre usar penetração 'geral': bairro alta renda (ex.: Cocó
    IDH-Renda 0,89) passa a usar penetração A/B. best-effort — sem dado → ('geral', meta).
    id_municipio vem das obras CNO (acelera a query Censo).
    """
    try:
        from tools.demografia_bairro_tools import classificar_perfil_bairro

        # Renda-only (CKAN IDH-Renda): evita re-geocode/Censo já feito em
        # _ocupacao_censo_bairro. _demo_fn injetável → testável sem rede.
        def _renda_ckan(_c, _u, _b, *, id_municipio=None):
            from tools.bairro_renda_loader import enrich_demografia_bairro
            b = (enrich_demografia_bairro({}, _c, _b, _u).get("bairro") or {})
            return {"renda_media": b.get("renda_media"), "idh_renda": b.get("idh_renda")}

        demo_fn = _demo_fn or _renda_ckan
        idm = next((str(o.get("id_municipio")) for o in obras if o.get("id_municipio")), None)
        demo = demo_fn(cidade, uf, bairro, id_municipio=idm)
        cls = classificar_perfil_bairro(demo.get("renda_media"), demo.get("idh_renda"))
        return cls["perfil"], cls
    except Exception as exc:
        print(f"[demanda] perfil renda falhou: {type(exc).__name__}: {exc}")
    return "geral", {"perfil": "geral", "base": "erro", "confianca": "baixa",
                     "fonte": "derivação de perfil falhou — penetração geral"}


def demanda_futura_detalhada(
    cidade: str,
    uf: str,
    *,
    bairro: str | None = None,
    perfil_bairro: str = "auto",
    top_n: int = 5,
    market_share: float | None = None,
    ticket_brl: float | None = None,
    _refino_fn: Any = None,
    _refino_det_fn: Any = None,
    _censo_fn: Any = None,
    _demo_fn: Any = None,
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

    # Ocupação do bairro: FONTE = IBGE Censo 2022 por setor (média moradores real do
    # bairro); o param ocupacao_* é só fallback. Busca 1x pelo centróide (best-effort).
    ocupacao_censo, censo_bloco = _ocupacao_censo_bairro(cidade, uf, bairro, obras, _censo_fn)

    # Perfil A/B: FONTE = renda real do bairro (CKAN IDH-Renda + renda pc). "auto" deriva;
    # valor explícito ("ab"/"geral") do caller é honrado. Corrige o capenga do default "geral".
    perfil_fonte: dict | None = None
    if perfil_bairro == "auto":
        perfil_bairro, perfil_fonte = _perfil_renda_bairro(cidade, uf, bairro, obras, _demo_fn)

    linhas: list[dict] = []
    tot = {"captura_est": 0.0, "moradores_est": 0.0, "receita_est": 0.0}
    from tools.lancamento_fetcher import refinar_lancamento_deterministico

    refino_det_fn = _refino_det_fn or refinar_lancamento_deterministico
    for i, o in enumerate(obras):
        o = {**o, "cidade": cidade, "uf": uf}  # query dos refinos precisa de cidade/uf
        # Camada determinística PRIMEIRO (barata → TODAS as obras): página do
        # lançamento via SearchAPI+httpx (SPEC_REFINO_LANCAMENTO_DETERMINISTICO —
        # o proxy área/75 inventava unidades, ex.: Like 129 vs 88 reais). Grounding
        # LLM vira FALLBACK e continua restrito às top_n (custo).
        refino = refino_det_fn(o)
        if refino is None and i < top_n:
            refino = refino_fn(o)
        unid_exatas = (refino or {}).get("unidades_exatas")
        tipologia = (refino or {}).get("tipologia")
        areas_plantas = (refino or {}).get("areas_plantas")
        e = estimar_demanda_obra(
            float(o.get("area_m2") or 0), unidades_exatas=unid_exatas, tipologia=tipologia,
            perfil_bairro=perfil_bairro, market_share=market_share, ticket_brl=ticket_brl,
            ocupacao_censo=ocupacao_censo, areas_plantas=areas_plantas,
        )
        janela = _janela_quente((refino or {}).get("obra_progresso"))
        entrega = (refino or {}).get("previsao_entrega") or _meses_para_entrega(o.get("data_inicio"))
        residencial, base_res, conf_res = _classificar_residencial(o.get("nome") or "", refino)
        # Gate residencial: prédio comercial/infra/ambíguo não gera morador → não soma
        # demanda. Mantém a obra na lista (transparência) mas fora dos totais (Apêndice A).
        if residencial:
            tot["captura_est"] += e["captura_est"]
            tot["moradores_est"] += e["moradores_est"]
            tot["receita_est"] += e["receita_incremental_est"]
        linhas.append({
            "empreendimento": (refino or {}).get("empreendimento"),
            "construtora": o.get("nome"),
            "bairro": o.get("bairro"),
            "unidades_est": e["unidades_est"],
            "unidades_fonte": e["unidades_fonte"],
            "entrega": entrega,
            "amenidade_fitness": (refino or {}).get("amenidade_fitness", False),
            # Ficha técnica ampliada (A) — só quando o refino leu a página/PDF.
            "areas_plantas": (refino or {}).get("areas_plantas"),
            "area_privativa_media": (round(sum(areas_plantas) / len(areas_plantas), 1)
                                     if areas_plantas else None),
            "dormitorios": (refino or {}).get("dormitorios"),
            "suites": (refino or {}).get("suites"),
            "vagas": (refino or {}).get("vagas"),
            "preco_base": (refino or {}).get("preco_base"),
            "obra_progresso": (refino or {}).get("obra_progresso"),
            "responsavel": (refino or {}).get("responsavel"),  # quem contatar p/ parceria
            "janela_quente": janela,            # gatilho timing/MKT (C)
            "ocupacao_fonte": e["fatores_usados"]["ocupacao"],  # auditável (B)
            # Cadeia clara pro usuário: moradores (Censo) → membros captáveis (nossa
            # fatia) → receita/mês. Tudo 0 em obra não-residencial (fora do gate).
            "moradores_est": e["moradores_est"] if residencial else 0.0,
            "captura_est": e["captura_est"] if residencial else 0.0,  # membros captáveis
            "receita_mensal_est": e["receita_incremental_est"] if residencial else 0.0,
            # confiança do refino (quando rodou) tem precedência; senão a da classificação.
            "confianca": (refino or {}).get("confianca") or conf_res,
            "provavel_residencial": residencial,
            "base_residencial": base_res,            # FONTE da classificação (auditável)
            "ni_responsavel": o.get("ni_responsavel"),  # CNPJ responsável no CNO (verificável)
            "fonte_url": (refino or {}).get("fonte_url"),
        })

    # Radar de pré-lançamentos (Task #12): venda SEM CNO ainda — informativo,
    # NUNCA soma nos totais (sem registro = sem carimbo). Fail-soft.
    radar_pre = []
    try:
        from tools.lancamento_fetcher import radar_pre_lancamentos

        if bairro:
            radar_pre = radar_pre_lancamentos(bairro, cidade, obras_cno=obras)
    except Exception:
        logger.warning("radar pré-lançamentos falhou", exc_info=True)

    return {
        "status": "ok", "cidade": cidade, "uf": uf, "bairro": bairro,
        "radar_pre_lancamentos": radar_pre,
        "n_obras": len(obras), "refinadas": min(top_n, len(obras)),
        "provavel_residencial_n": sum(1 for l in linhas if l["provavel_residencial"]),
        # Transparência: de ONDE veio a classificação residencial (fonte por contagem).
        "residencial_por_base": {
            base: sum(1 for l in linhas if l["provavel_residencial"] and l["base_residencial"] == base)
            for base in ("refino_tipologia", "nome_residencial")
        },
        "obras": linhas[:max(top_n, 10)],
        # Janela quente (C): obras na reta final → gatilho de MKT pro cliente.
        "janela_quente_n": sum(1 for l in linhas if l.get("janela_quente")),
        "janelas_quentes": [
            {"empreendimento": l.get("empreendimento") or l.get("construtora"),
             "obra_progresso": l.get("obra_progresso"), "fonte_url": l.get("fonte_url"),
             "responsavel": l.get("responsavel"), "captura_est": l.get("captura_est")}
            for l in linhas if l.get("janela_quente")
        ],
        "captura_total_est": round(tot["captura_est"], 1),       # membros captáveis (T+24)
        "moradores_total_est": round(tot["moradores_est"], 1),   # moradores novos (Censo)
        "receita_total_mensal_est": round(tot["receita_est"], 2),  # R$/mês de receita futura
        # Demografia do bairro (Censo 2022 setor) usada como FONTE da ocupação; null = caiu no fallback param.
        "demografia_censo_bairro": censo_bloco,
        "ocupacao_fonte": "censo_2022_setor" if ocupacao_censo else "param_fallback",
        "perfil_bairro": perfil_bairro,
        "perfil_bairro_fonte": perfil_fonte,  # base/confiança/fonte da derivação A/B (auditável)
        "fonte": "CNO grande porte (RFB) + refino A4 (site do lançamento)",
        "nota": ("Proxy área = limite superior (inclui não-residencial); refino A4 e "
                 "provavel_residencial são o gate de confiança. Liderar pelo refinado."),
    }
