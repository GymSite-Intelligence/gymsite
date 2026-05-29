"""
tools/cnpj_fitness_tools.py

Consulta entrantes e parque ativo via CNPJ Aberto (RFB), snapshot mensal.
Ingestão filtra CNAE 9313100; na API de produto usamos o termo **parque ativo**.

Este módulo NÃO baixa os dados (isso é tarefa do loader mensal). Ele só lê do
Supabase para enriquecer o pipeline (A0/A6).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from tools.cnpj_segment_classifier import (
    SEGMENTOS_PARQUE_COMERCIAL,
    agregar_por_segmento,
    classificar_segmento,
    composicao_com_percentuais,
)
from tools.cnpj_segment_places import refinar_classificacao

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)


def nome_exibicao_cnpj(
    nome_fantasia: str | None,
    razao_social: str | None,
) -> tuple[str | None, str | None, str | None]:
    """
    Nome para UI/prospecção: fantasia se houver; senão razão social.

    Retorna (nome_exibicao, nome_fantasia_limpo, inferido_de).
    inferido_de = 'razao_social' quando não há fantasia e usamos a razão.
    """
    fantasia = (nome_fantasia or "").strip()
    razao = (razao_social or "").strip()
    if fantasia:
        return fantasia, fantasia, None
    if razao:
        return razao, None, "razao_social"
    return None, None, None
load_dotenv(_ROOT / "gymsite_intelligence" / ".env", override=False)


def _supabase_client():
    import os
    from supabase import create_client

    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    return create_client(url, key)


def _format_cnpj(cnpj: str) -> str:
    d = re.sub(r"\D", "", cnpj or "")
    if len(d) != 14:
        return cnpj or ""
    return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def _format_endereco(row: dict) -> str:
    parts = [
        (row.get("logradouro") or "").strip(),
        (row.get("numero") or "").strip(),
        (row.get("complemento") or "").strip(),
    ]
    parts = [p for p in parts if p]
    return ", ".join(parts)


def _classificar_row(
    row: dict,
    *,
    validar_places: bool = False,
    cidade: str = "",
    uf: str = "",
) -> dict[str, Any]:
    base = classificar_segmento(
        row.get("nome_fantasia"),
        row.get("cnae_fiscal_principal"),
        row.get("cnaes_secundarios"),
        razao_social=row.get("razao_social"),
    )
    if validar_places:
        endereco = _format_endereco(row) or None
        base = refinar_classificacao(
            base,
            nome_fantasia=row.get("nome_fantasia"),
            endereco=endereco,
            cidade=cidade,
            uf=uf,
            force=True,
        )
    return base.to_dict()


def _segmento_from_row(row: dict, **kwargs) -> str:
    return _classificar_row(row, **kwargs)["segmento_operacao"]


def _row_to_entrante(
    row: dict,
    *,
    validar_places: bool = False,
    cidade: str = "",
    uf: str = "",
) -> dict[str, Any]:
    fantasia = (row.get("nome_fantasia") or "").strip()
    razao = (row.get("razao_social") or "").strip()
    bairro = (row.get("bairro") or "").strip()
    nome_exibicao, fantasia_out, inferido_de = nome_exibicao_cnpj(fantasia, razao)
    email = (row.get("email") or "").strip() or None
    telefone = (row.get("telefone") or "").strip() or None
    cls = _classificar_row(
        row, validar_places=validar_places, cidade=cidade, uf=uf
    )
    return {
        "cnpj": row.get("cnpj", ""),
        "cnpj_formatado": _format_cnpj(row.get("cnpj", "")),
        "nome_fantasia": fantasia_out,
        "razao_social": razao or None,
        "nome_exibicao": nome_exibicao,
        "nome_fantasia_inferido_de": inferido_de,
        "razao_social_indisponivel": not bool(razao),
        "bairro": bairro or None,
        "email_empresa": email,
        "telefone_empresa": telefone,
        "data_abertura": row.get("data_inicio_atividade"),
        "endereco": _format_endereco(row) or None,
        "cep": (row.get("cep") or "").strip() or None,
        "cnae_principal": row.get("cnae_fiscal_principal"),
        "ref_month": row.get("ref_month"),
        "contato_validado": False,
        "contato_validado_em": None,
        "contato_validado_por": None,
        **cls,
    }


def _fetch_estabelecimentos_paginado(
    sb,
    *,
    cidade: str,
    uf: str,
    fields: str,
    page_size: int = 1000,
) -> list[dict]:
    offset = 0
    all_rows: list[dict] = []
    while True:
        q = (
            sb.table("cnpj_fitness_estabelecimentos")
            .select(fields)
            .range(offset, offset + page_size - 1)
        )
        if cidade:
            q = q.eq("cidade", cidade)
        if uf:
            q = q.eq("uf", uf[:2].upper())
        res = q.execute()
        batch = [r for r in (res.data or []) if isinstance(r, dict)]
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_rows


def composicao_parque_cnpj(cidade: str, uf: str = "") -> dict[str, Any]:
    """Contagem e % do parque ativo por segmento_operacao."""
    sb = _supabase_client()
    if sb is None:
        return {"status": "indisponivel", "motivo": "supabase_nao_configurado"}

    rows = _fetch_estabelecimentos_paginado(
        sb,
        cidade=cidade,
        uf=uf,
        fields="nome_fantasia, cnae_fiscal_principal, cnaes_secundarios",
    )
    classificacoes = [_classificar_row(r) for r in rows]
    segmentos = [
        c["segmento_operacao"]
        for c in classificacoes
        if c.get("incluir_no_parque", True)
    ]
    counts = agregar_por_segmento(segmentos)
    comp = composicao_com_percentuais(counts)
    saude = sum(1 for c in classificacoes if c["segmento_operacao"] == "saude_clinica")
    baixa = sum(1 for c in classificacoes if c.get("segmento_confianca") == "baixa")
    return {
        "status": "ok",
        "total": len(rows),
        "parque_comercial_total": len(segmentos),
        "excluidos_saude_clinica": saude,
        "pendentes_validacao": baixa,
        "composicao_parque": comp,
        "composicao_parque_contagem": counts,
    }


def listar_unidades_cnpj_no_bairro(
    cidade: str,
    bairro: str,
    uf: str = "",
    *,
    limit: int = 25,
) -> dict[str, Any]:
    """
    Terceiro canal de competição local: parque ativo CNPJ (CNAE fitness) filtrado por bairro.

    Usado quando Google Places e Overpass falham ou retornam vazio.
    """
    from tools.bairro_normalize import bairro_em_alvo, normalizar_bairro, partes_bairro_alvo

    sb = _supabase_client()
    if sb is None:
        return {
            "status": "indisponivel",
            "motivo": "supabase_nao_configurado",
            "unidades": [],
        }
    if not (cidade or "").strip():
        return {"status": "erro", "motivo": "cidade_ausente", "unidades": []}

    fields = (
        "cnpj, nome_fantasia, razao_social, bairro, logradouro, numero, complemento, "
        "cep, situacao_cadastral, cnae_fiscal_principal, cnaes_secundarios"
    )
    try:
        rows = _fetch_estabelecimentos_paginado(
            sb, cidade=cidade, uf=uf, fields=fields, page_size=800
        )
    except Exception as exc:
        return {"status": "erro", "motivo": str(exc), "unidades": []}

    partes = partes_bairro_alvo(bairro)
    unidades: list[dict[str, Any]] = []
    for r in rows:
        sit = r.get("situacao_cadastral")
        if sit is not None:
            try:
                if int(sit) != 2:
                    continue
            except (TypeError, ValueError):
                pass
        cls = _classificar_row(r)
        if not cls.get("incluir_no_parque", True):
            continue
        bairro_row = (r.get("bairro") or "").strip()
        if partes:
            if not bairro_em_alvo(bairro_row, bairro):
                log_norm = normalizar_bairro(r.get("logradouro") or "")
                if not any(p in log_norm for p in partes if len(p) >= 4):
                    continue
        fantasia = (r.get("nome_fantasia") or "").strip()
        razao = (r.get("razao_social") or "").strip()
        nome_exib, fantasia_out, inferido_de = nome_exibicao_cnpj(fantasia, razao)
        nome = nome_exib or "Unidade CNPJ"
        unidades.append(
            {
                "nome": nome,
                "nome_exibicao": nome_exib,
                "nome_fantasia": fantasia_out,
                "razao_social": razao or None,
                "nome_fantasia_inferido_de": inferido_de,
                "endereco": _format_endereco(r) or bairro_row or cidade,
                "cnpj": r.get("cnpj"),
                "bairro": bairro_row or None,
                "segmento_operacao": cls.get("segmento_operacao"),
                "fonte_busca": "cnpj_rfb",
            }
        )
        if len(unidades) >= limit:
            break

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf,
        "bairro_consultado": bairro,
        "fonte": "cnpj_rfb_parque_ativo",
        "total": len(unidades),
        "unidades": unidades,
        "nota": (
            "Unidades com CNAE fitness no município (RFB), filtradas por bairro normalizado. "
            "Não substitui rating/reviews do Maps."
        ),
    }


def _places_validate_enabled() -> bool:
    import os

    return os.getenv("CNPJ_SEGMENT_PLACES_VALIDATE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def listar_entrantes_cnpj_fitness(
    cidade: str,
    uf: str = "",
    dias: int = 90,
    *,
    limit: int = 50,
    validar_places: bool | None = None,
    enriquecer: bool | None = None,
) -> dict[str, Any]:
    """
    Lista estabelecimentos fitness com início de atividade nos últimos `dias`.
    Usado pelo A6 para enriquecer o relatório (prospecção / entrantes).

    enriquecer=False pula ReceitaWS/QSA (recomendado no A0 — dados RFB já bastam).
    """
    sb = _supabase_client()
    hoje = date.today()
    cutoff = hoje - timedelta(days=max(int(dias), 1))
    if sb is None:
        return {
            "status": "indisponivel",
            "motivo": "supabase_nao_configurado",
            "cidade": cidade,
            "uf": uf,
            "dias": dias,
            "cutoff": cutoff.isoformat(),
            "total": 0,
            "entrantes": [],
        }

    fields_base = (
        "cnpj, nome_fantasia, razao_social, bairro, email, telefone, "
        "data_inicio_atividade, cep, logradouro, numero, complemento, "
        "cnae_fiscal_principal, cnaes_secundarios, ref_month"
    )
    q = (
        sb.table("cnpj_fitness_estabelecimentos")
        .select(fields_base)
        .gte("data_inicio_atividade", cutoff.isoformat())
        .order("data_inicio_atividade", desc=True)
        .limit(max(1, min(int(limit), 200)))
    )
    if cidade:
        q = q.eq("cidade", cidade)
    if uf:
        q = q.eq("uf", uf[:2].upper())

    try:
        res = q.execute()
    except Exception as exc:
        if "razao_social" in str(exc).lower() or "bairro" in str(exc).lower():
            q = (
                sb.table("cnpj_fitness_estabelecimentos")
                .select(
                    "cnpj, nome_fantasia, data_inicio_atividade, cep, logradouro, "
                    "numero, complemento, cnae_fiscal_principal, cnaes_secundarios, ref_month"
                )
                .gte("data_inicio_atividade", cutoff.isoformat())
                .order("data_inicio_atividade", desc=True)
                .limit(max(1, min(int(limit), 200)))
            )
            if cidade:
                q = q.eq("cidade", cidade)
            if uf:
                q = q.eq("uf", uf[:2].upper())
            res = q.execute()
        else:
            raise
    rows = res.data or []
    do_places = (
        _places_validate_enabled() if validar_places is None else validar_places
    )
    entrantes = [
        _row_to_entrante(
            r,
            validar_places=do_places,
            cidade=cidade,
            uf=uf[:2].upper() if uf else "",
        )
        for r in rows
        if isinstance(r, dict)
    ]
    meta_enr: dict[str, Any] = {"enriquecimento": "nao_executado"}
    if enriquecer is False:
        meta_enr = {"enriquecimento": "desligado", "motivo": "enriquecer=False"}
    else:
        try:
            from tools.cnpj_enrichment import enriquecer_entrantes

            entrantes, meta_enr = enriquecer_entrantes(entrantes)
        except Exception as exc:
            meta_enr = {"enriquecimento": "erro", "motivo": str(exc)}
    seg_entrantes = agregar_por_segmento(
        e["segmento_operacao"] for e in entrantes if e.get("incluir_no_parque", True)
    )
    pendentes = sum(1 for e in entrantes if e.get("segmento_requer_validacao"))

    incompletos = sum(1 for e in entrantes if not e.get("dados_completos"))
    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf[:2].upper() if uf else "",
        "dias": int(dias),
        "cutoff": cutoff.isoformat(),
        "total": len(entrantes),
        "entrantes": entrantes,
        "entrantes_incompletos": incompletos,
        "enriquecimento_meta": meta_enr,
        "novas_unidades_90d_por_segmento": seg_entrantes,
        "segmentos_pendentes_validacao": pendentes,
        "validacao_places_ativa": do_places,
        "fonte": "RFB CNPJ Aberto (snapshot mensal, via Supabase)",
        "data_coleta": hoje.isoformat(),
        "nota": (
            "Abertura = data_inicio_atividade no CNPJ. Segmento por nome/CNAE "
            "(sem bucket 'outro'). Confiança baixa pode ser refinada com "
            "CNPJ_SEGMENT_PLACES_VALIDATE=1 + Google Places."
        ),
    }


def count_parque_ativo(cidade: str, uf: str = "") -> int | None:
    """Total de unidades no parque ativo (snapshot CNPJ mais recente, município/UF)."""
    return _count_cnpj_fitness_ativas_impl(cidade, uf)


def count_cnpj_fitness_ativas(cidade: str, uf: str = "") -> int | None:
    """Alias legado — preferir count_parque_ativo."""
    return count_parque_ativo(cidade, uf)


def _count_cnpj_fitness_ativas_impl(cidade: str, uf: str = "") -> int | None:
    sb = _supabase_client()
    if sb is None:
        return None
    try:
        q = sb.table("cnpj_fitness_estabelecimentos").select("cnpj", count="exact")
        if cidade:
            q = q.eq("cidade", cidade)
        if uf:
            q = q.eq("uf", uf[:2].upper())
        res = q.execute()
        return int(res.count) if res.count is not None else len(res.data or [])
    except Exception:
        return None


def _resumo_cnpj_from_lista(
    lista: dict[str, Any],
    cidade: str,
    uf: str,
    dias: int,
) -> dict[str, Any]:
    """Monta resumo a partir de um bloco já retornado por listar_entrantes_cnpj_fitness."""
    if lista.get("status") != "ok":
        return lista

    rows = lista.get("entrantes") or []
    serie: dict[str, int] = {}
    for e in rows:
        d = e.get("data_abertura")
        if not d:
            continue
        ano = str(d)[:4]
        serie[ano] = serie.get(ano, 0) + 1

    parque_ativo = count_parque_ativo(cidade, uf)
    comp_block = composicao_parque_cnpj(cidade, uf)
    composicao = (
        comp_block.get("composicao_parque") if comp_block.get("status") == "ok" else {}
    )
    novas_por_seg = lista.get("novas_unidades_90d_por_segmento") or {}

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": uf[:2].upper() if uf else "",
        "dias": int(dias),
        "cutoff": lista.get("cutoff"),
        "novos_cnpj_fitness_90d": lista.get("total", len(rows)),
        "parque_ativo_total": parque_ativo,
        "parque_comercial_total": comp_block.get("parque_comercial_total"),
        "excluidos_saude_clinica": comp_block.get("excluidos_saude_clinica"),
        "pendentes_validacao": comp_block.get("pendentes_validacao"),
        # Alias legado (relatórios gerados antes da v1.8)
        "academias_ativas_cidade_cnpj": parque_ativo,
        "composicao_parque": composicao,
        "novas_unidades_90d_por_segmento": novas_por_seg,
        "segmentos_pendentes_validacao": lista.get("segmentos_pendentes_validacao"),
        "serie_aberturas_anual": dict(sorted(serie.items())),
        "fonte": lista.get("fonte"),
        "data_coleta": lista.get("data_coleta"),
    }


def resumo_cnpj_fitness(cidade: str, uf: str = "", dias: int = 90) -> dict[str, Any]:
    """
    Retorna um resumo leve para o ContextBuilder (A0) e para o relatório (A6).

    Espera que a tabela `cnpj_fitness_estabelecimentos` esteja populada por
    um loader mensal.
    """
    sb = _supabase_client()
    if sb is None:
        return {
            "status": "indisponivel",
            "motivo": "supabase_nao_configurado",
            "cidade": cidade,
            "uf": uf,
            "dias": dias,
        }

    lista = listar_entrantes_cnpj_fitness(cidade, uf, dias, limit=200)
    return _resumo_cnpj_from_lista(lista, cidade, uf, dias)


def _segmento_lider(contagens: dict[str, int]) -> tuple[str | None, int]:
    if not contagens:
        return None, 0
    seg, n = max(contagens.items(), key=lambda kv: kv[1])
    return seg, int(n)


def dados_parque_cnpj_para_a0(
    cidade: str,
    uf: str = "",
    dias: int = 90,
    bairro: str = "",
    *,
    cno_dir: str = "",
) -> dict[str, Any]:
    """
    Fatos do parque CNPJ (+ CNO opcional) para o A0 — sem narrativa interpretativa.

    O A0 só deve reportar o que está aqui e no Deep Research; não inventar.
    """
    # Uma única consulta: sem Places validate (A0 usa CNAE/nome) e sem ReceitaWS.
    entrantes_block = listar_entrantes_cnpj_fitness(
        cidade,
        uf,
        dias,
        limit=200,
        validar_places=False,
        enriquecer=False,
    )
    if entrantes_block.get("status") != "ok":
        return entrantes_block

    resumo = _resumo_cnpj_from_lista(entrantes_block, cidade, uf, dias)
    if resumo.get("status") != "ok":
        return resumo

    amostra = []
    for e in (entrantes_block.get("entrantes") or [])[:15]:
        amostra.append(
            {
                "nome_fantasia": e.get("nome_fantasia"),
                "segmento": e.get("segmento_operacao"),
                "segmento_label": e.get("segmento_label"),
                "confianca": e.get("segmento_confianca"),
                "data_abertura": e.get("data_abertura"),
                "bairro_endereco": (e.get("endereco") or "")[:80],
            }
        )

    parque_com = int(resumo.get("parque_comercial_total") or 0)
    novos = int(resumo.get("novos_cnpj_fitness_90d") or 0)
    taxa_renovacao = round(100.0 * novos / parque_com, 2) if parque_com else None

    comp = resumo.get("composicao_parque") or {}
    parque_counts = {k: int(v.get("count", 0)) for k, v in comp.items() if isinstance(v, dict)}
    seg_parque, n_parque = _segmento_lider(parque_counts)

    novas_seg = resumo.get("novas_unidades_90d_por_segmento") or {}
    seg_entrada, n_entrada = _segmento_lider(
        {k: int(v) for k, v in novas_seg.items() if isinstance(v, (int, float))}
    )

    divergencia_segmento = (
        seg_parque
        and seg_entrada
        and seg_parque != seg_entrada
    )

    import os
    from pathlib import Path

    cno_block: dict[str, Any] = {"status": "nao_configurado"}
    cno_path = (cno_dir or os.getenv("CNO_DATA_DIR", "")).strip()
    if not cno_path or not Path(cno_path).is_dir():
        cno_path_host = (os.getenv("CNO_DATA_DIR_HOST", "")).strip()
        if cno_path_host and Path(cno_path_host).is_dir():
            cno_path = cno_path_host
    if cno_path and Path(cno_path).is_dir():
        try:
            from tools.cno_fitness_tools import cruzar_entrantes_obras_cno

            cno_block = cruzar_entrantes_obras_cno(
                cno_dir=cno_path,
                cidade=cidade,
                uf=uf,
                bairro=bairro,
                dias=dias,
                limit=50,
            )
        except Exception as exc:
            cno_block = {"status": "erro", "motivo": str(exc)}

    return {
        "status": "ok",
        "cidade": cidade,
        "uf": resumo.get("uf") or uf[:2].upper(),
        "bairro_alvo": bairro or None,
        "dias_janela": int(dias),
        "metricas_objetivas": {
            "parque_ativo_total": resumo.get("parque_ativo_total"),
            "parque_comercial_total": parque_com,
            "excluidos_saude_clinica": resumo.get("excluidos_saude_clinica"),
            "pendentes_validacao": resumo.get("pendentes_validacao"),
            "novos_cnpj_fitness_90d": novos,
            "composicao_parque": comp,
            "novas_unidades_90d_por_segmento": novas_seg,
            "serie_aberturas_anual": resumo.get("serie_aberturas_anual"),
            "fonte_entrantes": resumo.get("fonte"),
            "data_coleta": resumo.get("data_coleta"),
        },
        "indicadores_derivados": {
            "taxa_renovacao_parque_90d_pct": taxa_renovacao,
            "segmento_dominante_parque": seg_parque,
            "segmento_dominante_entradas_90d": seg_entrada,
            "unidades_entrantes_segmento_lider": n_entrada,
            "divergencia_parque_vs_aberturas": divergencia_segmento,
            "entrantes_places_validados": False,
            "segmentos_pendentes_validacao": resumo.get("pendentes_validacao"),
        },
        "amostra_entrantes_recentes": amostra,
        "cruzamento_cno": cno_block,
        "lacunas_conhecidas": [
            "CNPJ não traz área m² nem faturamento — área só via CNO com match.",
            "Matrículas e receita mensal = projeção A4 (m² × matr/m² × ticket), não dado fiscal.",
            "Obras em curso no CNO = parâmetro de prospecção; match com entrant é amostral.",
            "Sem match CNO: não inferir porte da unidade.",
        ],
    }


def analise_parque_ativo_para_a0(
    cidade: str, uf: str = "", dias: int = 90, bairro: str = ""
) -> dict[str, Any]:
    """Alias legado → dados_parque_cnpj_para_a0."""
    return dados_parque_cnpj_para_a0(cidade, uf, dias, bairro)

