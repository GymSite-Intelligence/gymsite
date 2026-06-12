"""
db/supabase_writer.py — Adapter que grava o JSON canônico v1.1 do pipeline
ADK no banco Supabase (9 tabelas normalizadas).

Por que existe:
- Pipeline atual grava JSON em metrics/relatorios/rpt_<ts>.json (filesystem)
- Fase 2 (CRUD UI) precisa dos mesmos dados em Postgres pra queries SQL +
  multi-tenant + frontend Supabase JS

Filosofia:
- FILESYSTEM CONTINUA SENDO SOURCE-OF-TRUTH (não removemos nada do A6)
- Esta gravação é PARALELA e FAIL-SAFE: erro aqui NUNCA bloqueia pipeline
- Sem credenciais configuradas → no-op silencioso (logado, não crasha)

Variáveis de ambiente esperadas (em gymsite_intelligence/.env):
  SUPABASE_URL                  https://<project-ref>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY     chave service_role (não anon)
  SUPABASE_GYMSITE_ORG_ID       UUID da org Vectra (default no seed.sql)

Uso:
    from db.supabase_writer import write_relatorio_failsafe
    write_relatorio_failsafe(relatorio_dict, markdown_text)
"""
from __future__ import annotations

import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Diretório de logs do writer (best-effort — não bloqueia se falhar gravar log)
_LOG_DIR = Path(__file__).resolve().parent.parent / "metrics" / "supabase_writes"

# UUID default da org Vectra (criado pelo seed.sql)
_DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _log(level: str, msg: str, extra: Optional[dict] = None) -> None:
    """Log estruturado em metrics/supabase_writes/ + espelho no logging padrão.

    O espelho é obrigatório: o incidente de 29/05–10/06 (candidatos rejeitados
    por coluna inexistente) ficou 2 semanas registrado APENAS neste arquivo,
    invisível no console do worker."""
    import logging as _logging

    if level in ("error", "warn", "warning"):
        _logging.getLogger("gymsite.supabase_writer").log(
            _logging.ERROR if level == "error" else _logging.WARNING,
            "%s | %s", msg, json.dumps(extra or {}, ensure_ascii=False, default=str)[:300],
        )
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "level": level,
            "message": msg,
        }
        if extra:
            entry.update(extra)
        with (_LOG_DIR / "writer.log").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _get_client():
    """Cria cliente Supabase com service_role key. Retorna None se não configurado."""
    import logging
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        _log("error", "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY ausentes — persistência de relatórios DESABILITADA")
        logging.getLogger("gymsite.supabase_writer").error(
            "Supabase não configurado — relatório NÃO será persistido (defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY)"
        )
        return None
    try:
        # pyrefly: ignore [missing-import]
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        _log("error", f"falha ao criar cliente supabase: {e}")
        return None


# ============================================================================
# Mapeamento JSON canônico v1.1 → linhas das 9 tabelas
# ============================================================================

def _safe_get(d: dict, *keys, default=None):
    """Navega d[k1][k2]... retornando default se algo for None/missing."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _row_relatorios(rel: dict, markdown: Optional[str], org_id: str) -> dict:
    """Header do relatório (1 row)."""
    return {
        # id é gerado pelo Postgres (default gen_random_uuid())
        "org_id": org_id,
        "user_id": None,  # pipeline rodando sem user logado — fica NULL
        "tipo_relatorio": rel.get("tipo_relatorio", "prospeccao_academia"),
        "status": "done",
        "adk_run_id": rel.get("id"),  # rpt_<ts> do A6
        "data_execucao": rel.get("data_execucao"),
        "schema_version": _safe_get(rel, "metadata_execucao", "schema_version", default="1.1"),
        "markdown_completo": markdown,
        "notas_usuario": None,
    }


def _row_inputs(rel: dict, relatorio_id: str) -> dict:
    inp = rel.get("input_canonico") or {}
    return {
        "relatorio_id": relatorio_id,
        "cidade": inp.get("cidade") or "",
        "uf": (inp.get("uf") or "")[:2] or None,
        "bairro": inp.get("bairro") or "",
        "area_m2_min": int(inp.get("area_m2_min") or 1000),
        "area_m2_max": int(inp.get("area_m2_max") or 1500),
        "publico_alvo": inp.get("publico_alvo") or "25-40",
        # Schema v1.4: gênero default "misto" pra retrocompat com JSONs v1.1-v1.3
        # (que não tinham o campo).
        "genero_alvo": inp.get("genero_alvo") or "misto",
        # Schema v1.5: tamanho preset Smart Fit-style. Default "m" (mais comum)
        # pra JSONs v1.1-v1.4 sem o campo.
        "tamanho_preset": inp.get("tamanho_preset") or "m",
        "tipo_negocio": inp.get("tipo_negocio") or "academia",
        "estacionamento_obrigatorio": bool(inp.get("estacionamento_obrigatorio", True)),
        "bairros_indicados": inp.get("bairros_indicados") or [],
        "metadados": {},
    }


def _aluguel_auditoria(rel: dict) -> dict:
    """Amostras de aluguel do market_bundle → colunas de auditoria (12/06).

    Copiadas direto do bundle local (NUNCA passam pelo LLM): cada anúncio
    com preço, m², R$/m², portal e URL clicável — a fonte 'Portais (N=33)'
    vira expansível e auditável na UI. Best-effort: sem bundle → vazio."""
    try:
        inp = rel.get("input_canonico") or {}
        cidade = inp.get("cidade") or ""
        bairro = inp.get("bairro") or ""
        uf = inp.get("uf") or ""
        if not cidade:
            return {}
        from tools.market_bundle import load_market_bundle

        bundle = load_market_bundle(cidade, bairro, uf) or {}
        alug = bundle.get("aluguel_portais") or {}
        amostras = alug.get("amostras") or []
        if not amostras:
            return {}
        return {
            "aluguel_amostras": amostras[:30],
            "aluguel_fonte_meta": {
                "fonte": alug.get("fonte"),
                "n_validos": alug.get("n_validos"),
                "confianca": alug.get("confianca"),
                "categoria_gate": alug.get("categoria_gate"),
                "descartadas_residenciais": alug.get("descartadas_residenciais"),
                "faixa_rs_m2": alug.get("faixa_rs_m2"),
                "coletado_em": bundle.get("gerado_em"),
            },
        }
    except Exception:
        return {}


def _row_outputs(rel: dict, relatorio_id: str) -> dict:
    out = rel.get("output_consolidado") or {}
    sr = out.get("scores_regionais") or {}
    return {
        "relatorio_id": relatorio_id,
        "veredito": out.get("veredito") or "REPROVADO",
        "score_bairro": out.get("score_bairro"),
        "score_top1_candidato": out.get("score_top1_candidato"),
        "score_demografico": sr.get("demografico"),
        "score_concorrencia": sr.get("competitivo") or sr.get("concorrencia"),
        "score_viabilidade": sr.get("viabilidade"),
        "nivel_saturacao": out.get("nivel_saturacao"),
        "rating_medio_concorrentes": out.get("rating_medio_concorrentes"),
        "total_concorrentes_analisados": out.get("total_concorrentes_analisados"),
        "modelo_recomendado": out.get("modelo_recomendado"),
        "aluguel_mensal": out.get("aluguel_mensal"),
        "fonte_aluguel": _safe_get(out, "contato_decisor", "fonte_aluguel")
                         or out.get("fonte_aluguel"),
        "aluguel_min_m2": out.get("aluguel_min_m2_observado"),
        "aluguel_max_m2": out.get("aluguel_max_m2_observado"),
        "aluguel_mediana_m2": out.get("aluguel_mediana_m2_observado"),
        **_aluguel_auditoria(rel),
        "queries_aluguel_com_dados": _safe_get(
            out, "contato_decisor", "aluguel_pesquisa_detalhes", "queries_com_dados",
            default=0,
        ),
        "posicionamento_recomendado": out.get("posicionamento_recomendado"),
        "resumo_executivo": _safe_get(out, "contato_decisor", "resumo_executivo")
                            or out.get("resumo_executivo"),
        "justificativa_financeira": _safe_get(
            out, "contato_decisor", "resumo_analise_financeira", "justificativa"
        ),
        "contato_decisor": out.get("contato_decisor") or {},
        # Schema v1.2: market_context COMPLETO do A0 (ticket, renda, faixa
        # etária, insights, regulamentação). Em v1.1 ficava só metadata.
        # Fallback pra metadata_execucao garante compat com JSONs v1.1 antigos.
        "market_context": out.get("market_context") or (rel.get("metadata_execucao") or {}),
        # Schema v1.4: cobertura A0 — exposta como JSONB pra consultas SQL
        # do tipo "quais relatórios o DR errou redes que não existem locally?".
        # Quando v1.4 ausente (relatórios antigos), grava {} pra não quebrar.
        "cobertura_redes_a0": out.get("cobertura_redes_a0") or {},
        "entrantes_cnpj_90d": out.get("entrantes_cnpj_90d") or {},
        "obras_cno_em_curso": out.get("obras_cno_em_curso") or {},
        "alertas": out.get("alertas_financeiros") or [],
        # embedding fica NULL — gerado depois por job de RAG
    }


def _rows_candidatos(rel: dict, relatorio_id: str) -> list[dict]:
    cands = _safe_get(rel, "output_consolidado", "top_3_candidatos", default=[]) or []
    rows = []
    for pos, c in enumerate(cands[:10], start=1):
        if not isinstance(c, dict):
            continue
        rows.append({
            "relatorio_id": relatorio_id,
            "posicao": pos,
            "nome": (c.get("nome") or "?")[:255],
            "endereco": c.get("endereco"),
            "place_id": c.get("place_id"),
            "tipo": (c.get("tipos") or ["establishment"])[0] if c.get("tipos") else None,
            "area_estimada_m2": c.get("area_estimada_m2"),
            "lat": c.get("lat"),
            "lng": c.get("lng"),
            "score_geoscout": c.get("score_geoscout"),
            "score_ancoragem": c.get("score_ancoragem"),
            "score_geral": c.get("score_geral"),
            "motivo": c.get("motivo"),
            "estimativa_visibilidade": c.get("estimativa_visibilidade"),
            "avenida_principal": c.get("avenida_principal"),
            "qualidade_sinal": c.get("qualidade_sinal"),
            "polos_geradores": c.get("polos_geradores") or [],
            "tipos_google": c.get("tipos") or [],
            "street_view_url": c.get("street_view_url"),
            "status_business": c.get("status"),
            # Contact Data — fix do FieldMask em maps_tools.py
            "telefone": c.get("telefone") or None,
            "website": c.get("website") or None,
            "tem_24h": bool(c.get("tem_24h", False)),
            "listing_url": c.get("listing_url") or (
                c.get("website") if c.get("fonte") == "listing" else None
            ),
            "listing_id": c.get("listing_id") or None,
            "price_raw": c.get("price_raw") or None,
            "listing_source": c.get("source") or None,
            "proximo_passo": c.get("proximo_passo"),
            "tipo_imovel_codigo_onr": c.get("tipo_imovel_codigo_onr"),
            "tipo_imovel_label": c.get("tipo_imovel_label"),
            "modalidade": c.get("modalidade"),
            "cartorio": c.get("cartorio") if isinstance(c.get("cartorio"), dict) else None,
        })
    return rows


def _build_oferta_lookup(rel: dict) -> dict:
    """
    A3c CompetitorMapper (shadow) grava `oferta_concorrentes.oferta_concorrentes`
    com chaves = place_id ou nome do concorrente. Retorna lookup achatado
    {place_id_ou_nome_lower: oferta_normalizada} pra _rows_competidores.
    """
    raiz = rel.get("oferta_concorrentes") if isinstance(rel, dict) else None
    if not isinstance(raiz, dict):
        return {}
    # A3c output_key emite o JSON inteiro; campo interno também chamado oferta_concorrentes
    mapeamento = raiz.get("oferta_concorrentes") if isinstance(raiz.get("oferta_concorrentes"), dict) else raiz
    if not isinstance(mapeamento, dict):
        return {}
    lookup: dict[str, dict] = {}
    for chave, oferta in mapeamento.items():
        if not isinstance(oferta, dict):
            continue
        if chave:
            lookup[str(chave).lower()] = oferta
        nome_no_oferta = oferta.get("nome")
        if nome_no_oferta:
            lookup[str(nome_no_oferta).lower()] = oferta
    return lookup


def _merge_atividade_marketing(c: dict) -> dict | None:
    """Preserva posts/marketing e anexa aba Sobre (Places API) quando existir."""
    base = c.get("atividade_marketing")
    sobre = c.get("atributos_sobre")
    if not sobre and not base:
        return None
    out: dict = dict(base) if isinstance(base, dict) else {}
    if isinstance(sobre, dict) and sobre:
        out["sobre"] = sobre
    return out or None


_GEO_PRESERVE_FIELDS = ("lat", "lng", "place_id", "distancia_km", "google_maps_uri")


def _norm_coord(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        if f == 0.0:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _competidor_geo_key(place_id: Any, nome: Any) -> str | None:
    if place_id:
        key = str(place_id).strip().lower()
        if key:
            return key
    n = (nome or "").strip().lower()
    return n or None


def _fetch_competidores_geo_lookup(client: Any, relatorio_id: str) -> dict[str, dict]:
    """
    Lê coordenadas já gravadas antes do delete+insert (re-run / UPDATE relatório).
    Chave = place_id (lower) ou nome (lower).
    """
    try:
        res = (
            client.table("competidores")
            .select("place_id,nome,lat,lng,distancia_km,google_maps_uri")
            .eq("relatorio_id", relatorio_id)
            .execute()
        )
    except Exception as e:
        _log("warn", f"falha ao ler geo existente competidores: {e}", {"relatorio_id": relatorio_id})
        return {}
    lookup: dict[str, dict] = {}
    for row in res.data or []:
        if not isinstance(row, dict):
            continue
        key = _competidor_geo_key(row.get("place_id"), row.get("nome"))
        if not key:
            continue
        lat = _norm_coord(row.get("lat"))
        lng = _norm_coord(row.get("lng"))
        if lat is None and lng is None and not row.get("place_id"):
            continue
        lookup[key] = {
            "place_id": row.get("place_id"),
            "lat": lat if lat is not None else row.get("lat"),
            "lng": lng if lng is not None else row.get("lng"),
            "distancia_km": row.get("distancia_km"),
            "google_maps_uri": (row.get("google_maps_uri") or "").strip() or None,
        }
    return lookup


def _merge_competidor_geo_row(row: dict, geo_lookup: dict[str, dict] | None) -> dict:
    """Não sobrescreve lat/lng/place_id já persistidos quando o payload novo vem sem coords."""
    if not geo_lookup:
        return row
    key = _competidor_geo_key(row.get("place_id"), row.get("nome"))
    if not key:
        return row
    prev = geo_lookup.get(key)
    if not prev:
        return row
    for field in _GEO_PRESERVE_FIELDS:
        if row.get(field) is None and prev.get(field) is not None:
            row[field] = prev[field]
    return row


def _rows_competidores(
    rel: dict,
    relatorio_id: str,
    *,
    geo_preserve: dict[str, dict] | None = None,
) -> list[dict]:
    comps = _safe_get(rel, "output_consolidado", "competitors_set", default=[]) or []
    oferta_lookup = _build_oferta_lookup(rel)
    rows = []
    for c in comps:
        if not isinstance(c, dict):
            continue
        telefone = (c.get("telefone") or "").strip() or None
        website = (c.get("website") or "").strip() or None
        # Gera link WhatsApp se telefone disponível — mesmo padrão de A5 ContactHunter
        whatsapp_link = None
        if telefone:
            try:
                from tools.contact_tools import formatar_contato_whatsapp
                whatsapp_link = formatar_contato_whatsapp(
                    telefone,
                    f"Olá! Sou consultor de expansão e gostaria de conversar sobre {c.get('nome', 'sua academia')}.",
                )
            except Exception:
                whatsapp_link = None
        # Lookup A3c (shadow): por place_id ou nome
        oferta_mapeada = None
        place_id = c.get("place_id")
        nome_lower = (c.get("nome") or "").lower()
        if place_id:
            oferta_mapeada = oferta_lookup.get(str(place_id).lower())
        if not oferta_mapeada and nome_lower:
            oferta_mapeada = oferta_lookup.get(nome_lower)
        dist = c.get("distancia_km")
        try:
            dist_f = round(float(dist), 2) if dist is not None else None
        except (TypeError, ValueError):
            dist_f = None
        row = {
            "relatorio_id": relatorio_id,
            "nome": (c.get("nome") or "?")[:255],
            "endereco": c.get("endereco"),
            "bairro_concorrente": c.get("bairro_concorrente"),
            "place_id": place_id,
            "lat": _norm_coord(c.get("lat")),
            "lng": _norm_coord(c.get("lng")),
            "distancia_km": dist_f,
            "google_maps_uri": (c.get("google_maps_uri") or "").strip() or None,
            "rating_oficial": c.get("rating_geral") or c.get("rating_oficial"),
            "num_avaliacoes": c.get("num_avaliacoes"),
            "tem_24h": bool(c.get("tem_24h", False)),
            "reviews": c.get("reviews_traduzidas") or c.get("reviews") or [],
            "horarios_pico": c.get("horarios_pico"),
            "pico_semanal": c.get("pico_semanal"),
            "planos_precos": c.get("planos_precos"),
            "instagram_profile": c.get("instagram_profile"),
            "atividade_marketing": _merge_atividade_marketing(c),
            "origem_busca": c.get("origem_busca") or "nearby",
            # Sprint 2026-05-12: Places API contact data — antes ignorada pelo writer
            "telefone": telefone,
            "website": website,
            "whatsapp_link": whatsapp_link,
            # A3c shadow — GymSite #127. NULL nos top 6+ (limite 5) ou
            # competidores sem fonte (website/IG).
            "oferta_mapeada": oferta_mapeada,
        }
        rows.append(_merge_competidor_geo_row(row, geo_preserve))
    return rows


def _rows_cenarios(rel: dict, relatorio_id: str) -> list[dict]:
    """
    Mapeia viabilidade_3_cenarios → linhas cenarios_financeiros.

    Schema v2: 12 colunas detalhadas de custos + capex breakdown +
    3 calibrações de matrícula + pico simultâneo + TIR/VPL.

    Backward-compat: JSONs v1 (sem campos novos) ainda gravam — campos
    novos viram NULL no banco.
    """
    cenarios = _safe_get(rel, "output_consolidado", "viabilidade_3_cenarios", default={}) or {}
    rows = []
    for modelo in ("low", "mid", "premium"):
        c = cenarios.get(modelo) or {}
        if not isinstance(c, dict) or not c:
            continue

        # Demanda v2 (com fallback gracioso pra v1)
        matr = c.get("matriculas") or {}
        matr_cons = _safe_get(matr, "conservador", "valor", default=None)
        matr_real = _safe_get(matr, "realista", "valor", default=None) or c.get("alunos_projetados")
        matr_agres = _safe_get(matr, "agressivo", "valor", default=None)
        matr_por_m2_real = _safe_get(matr, "realista", "matr_por_m2", default=None)

        # Custos detalhados (12 linhas v2; fallback NULL se v1)
        custos = c.get("custos_detalhados") or {}

        # CAPEX detalhado (v2; fallback do total v1)
        capex_d = c.get("capex_detalhado") or {}
        capex_total = c.get("capex_total") or c.get("capex_estimado")

        # Gate A4 (caso Bessa 11/06): cenário sem breakdown gravava NULLs que
        # o front convertia em zeros — KPI "aluguel R$ 0" e payback fake.
        # Consistência mínima: aluguel do output cobre custo_aluguel ausente;
        # warning ruidoso pro run ficar visível no log (não derruba o write —
        # agregados ainda têm valor; o viewer degrada com elegância).
        if not custos.get("aluguel"):
            aluguel_out = _safe_get(rel, "output_consolidado", "aluguel_mensal", default=None)
            if aluguel_out:
                custos = {**custos, "aluguel": aluguel_out}
            _log(
                "warning",
                f"A4 sem breakdown de custos no cenário {modelo} "
                f"(relatorio {relatorio_id}) — custo_aluguel "
                f"{'preenchido' if aluguel_out else 'AUSENTE'} via aluguel_mensal do output",
            )

        rows.append({
            "relatorio_id": relatorio_id,
            "modelo": modelo,
            "ticket_medio": c.get("ticket_medio"),

            # Demanda v2
            "matriculas_conservador": matr_cons,
            "matriculas_realista": matr_real,
            "matriculas_agressivo": matr_agres,
            "matr_por_m2_realista": matr_por_m2_real,
            "capacidade_simultanea_pico": c.get("capacidade_simultanea_pico")
                                          or c.get("capacidade_maxima_alunos"),
            "frequencia_semanal_aluno": c.get("frequencia_semanal_aluno"),
            "pico_share": c.get("pico_share"),
            "alunos_pico_calculado": c.get("alunos_pico_calculado"),
            "folga_capacidade_pct": c.get("folga_capacidade_pct"),

            # Backward-compat v1
            "capacidade_maxima_alunos": c.get("capacidade_maxima_alunos"),
            "alunos_projetados": c.get("alunos_projetados"),
            "alunos_break_even": c.get("alunos_break_even"),

            # Receita
            "ticket_realizado_estimado": c.get("ticket_realizado_estimado"),
            "taxa_inadimplencia": c.get("taxa_inadimplencia"),
            "taxa_cancelamento_mensal": c.get("taxa_cancelamento_mensal"),
            "receita_mensal": c.get("receita_mensal"),

            # Custos detalhados (12 linhas)
            "custo_aluguel": custos.get("aluguel"),
            "custo_condominio": custos.get("condominio"),
            "custo_iptu": custos.get("iptu"),
            "custo_energia": custos.get("energia"),
            "custo_agua": custos.get("agua"),
            "custo_internet": custos.get("internet"),
            "custo_folha": custos.get("folha"),
            "custo_manutencao": custos.get("manutencao"),
            "custo_contabilidade": custos.get("contabilidade"),
            "custo_sistema_gestao": custos.get("sistema_gestao"),
            "custo_seguro": custos.get("seguro"),
            "custo_outros": custos.get("outros"),
            "custos_fixos_total": c.get("custos_fixos_total") or c.get("custos_fixos"),

            "marketing_pct_faturamento": c.get("marketing_pct_faturamento"),
            "marketing_mensal": c.get("marketing_mensal"),

            "custos_totais": c.get("custos_totais"),
            "lucro_mensal_estimado": c.get("lucro_mensal_estimado"),
            "margem_percentual": c.get("margem_percentual"),

            # Investimento detalhado
            "capex_equipamentos": capex_d.get("equipamentos"),
            "capex_obra_adaptacao": capex_d.get("obra_adaptacao"),
            "capex_projeto_arquitetonico": capex_d.get("projeto_arquitetonico"),
            "capex_alvara_e_taxas": capex_d.get("alvara_e_taxas"),
            "capex_contingencia_pct": capex_d.get("contingencia_pct"),
            "capex_contingencia_valor": capex_d.get("contingencia_valor"),
            "capex_total": capex_total,

            "capital_giro_meses": c.get("capital_giro_meses"),
            "capital_giro": c.get("capital_giro"),
            "investimento_total": c.get("investimento_total"),
            "payback_meses": c.get("payback_meses"),
            "tir_anual_pct": c.get("tir_anual_pct"),
            "vpl_5_anos": c.get("vpl_5_anos"),

            # Veredito
            "viabilidade": c.get("viabilidade") or "INVIAVEL",
            "justificativa": c.get("justificativa"),

            # Backward-compat
            "capex_estimado": c.get("capex_estimado") or capex_total,
            "custos_fixos": c.get("custos_fixos") or c.get("custos_fixos_total"),
        })
    return rows


def _rows_sensibilidade(rel: dict, relatorio_id: str, cenario_ids: dict[str, str]) -> list[dict]:
    """
    Mapeia sensibilidade dos 3 cenários → linhas sensibilidade_cenarios.

    Args:
        cenario_ids: mapa de modelo (low/mid/premium) → UUID do cenário recém-criado
                     (vem do retorno do insert em cenarios_financeiros).
    """
    cenarios = _safe_get(rel, "output_consolidado", "viabilidade_3_cenarios", default={}) or {}
    rows = []
    for modelo in ("low", "mid", "premium"):
        c = cenarios.get(modelo) or {}
        if not isinstance(c, dict):
            continue
        sens_list = c.get("sensibilidade") or []
        cenario_uuid = cenario_ids.get(modelo)
        if not cenario_uuid or not sens_list:
            continue
        for s in sens_list:
            if not isinstance(s, dict):
                continue
            rows.append({
                "cenario_id": cenario_uuid,
                "relatorio_id": relatorio_id,
                "modelo": modelo,
                "stress_id": s.get("id"),
                "stress_label": s.get("label"),
                "lucro_mensal": s.get("lucro_mensal"),
                "margem_percentual": s.get("margem_percentual"),
                "payback_meses": s.get("payback_meses"),
                "viabilidade": s.get("viabilidade") or "INVIAVEL",
            })
    return rows


def _rows_bairros_alternativos(rel: dict, relatorio_id: str) -> list[dict]:
    items = _safe_get(rel, "output_consolidado", "bairros_alternativos", default=[]) or []
    rows = []
    for ordem, b in enumerate(items):
        if not isinstance(b, dict):
            continue
        rows.append({
            "relatorio_id": relatorio_id,
            "bairro": (b.get("bairro") or "?")[:255],
            "motivo": b.get("motivo"),
            "status_competitivo": b.get("status"),
            "ticket_sugerido": b.get("ticket_sugerido") or b.get("ticket"),
            "prioridade": b.get("prioridade_ajustada") or b.get("prioridade") or "MEDIA",
            "concorrentes_no_bairro": b.get("concorrentes_no_bairro"),
            "academias_existentes": b.get("academias_existentes") or [],
            "metodologia": b.get("metodologia"),
            "ordem": ordem,
        })
    return rows


# ============================================================================
# API pública
# ============================================================================

def write_relatorio_to_supabase(
    relatorio: dict,
    markdown: Optional[str] = None,
    org_id: Optional[str] = None,
    relatorio_id: Optional[str] = None,
) -> Optional[str]:
    """
    Grava o relatório canônico v1.1 no Supabase em todas as 9 tabelas.

    Se `relatorio_id` é passado, faz UPDATE no header existente (caso API
    HTTP pré-criou um stub com status='queued'). Caso contrário, INSERT
    cria novo header com UUID gerado pelo Postgres.

    Retorna o `relatorio_id` (UUID), ou None se falhou ou credenciais ausentes.
    Esta função PODE lançar exceção. Para uso seguro no pipeline ADK,
    chame via `write_relatorio_failsafe`.
    """
    client = _get_client()
    if client is None:
        _log("info", "no-op (credenciais Supabase ausentes)", {"id": relatorio.get("id")})
        return None

    org_id = org_id or os.getenv("SUPABASE_GYMSITE_ORG_ID") or _DEFAULT_ORG_ID
    t0 = time.time()

    # 1. Header relatórios — INSERT novo OU UPDATE existente (modo API HTTP)
    header_row = _row_relatorios(relatorio, markdown, org_id)
    skip_inputs = False
    geo_preserve: dict[str, dict] = {}
    if relatorio_id:
        # API HTTP pré-criou stub — UPDATE com payload final + filhos via insert
        client.table("relatorios").update(header_row).eq("id", relatorio_id).execute()
        geo_preserve = _fetch_competidores_geo_lookup(client, relatorio_id)
        # Limpar filhos antes de reinserir (idempotência).
        # IMPORTANTE: NÃO deletar `relatorio_inputs` — eles foram inseridos
        # pelo endpoint POST /api/relatorios com os params do form do usuário.
        # O A6 reconstrói `input_canonico` lendo do `market_context` state, mas
        # isso pode ficar vazio se o root_agent não propagou os params (bug
        # upstream). Preservar a row original evita perder cidade/bairro.
        for child in ("relatorio_outputs", "candidatos",
                      "competidores", "bairros_alternativos",
                      "sensibilidade_cenarios", "cenarios_financeiros"):
            client.table(child).delete().eq("relatorio_id", relatorio_id).execute()
        skip_inputs = True
    else:
        res = client.table("relatorios").insert(header_row).execute()
        if not res.data:
            raise RuntimeError(f"insert em relatorios retornou vazio: {res}")
        relatorio_id = res.data[0]["id"]

    # 2. Tabelas 1:1 (inputs + outputs)
    # Em modo API HTTP, a row de inputs já existe (criada pelo POST) — preservar
    if not skip_inputs:
        client.table("relatorio_inputs").insert(_row_inputs(relatorio, relatorio_id)).execute()
    client.table("relatorio_outputs").insert(_row_outputs(relatorio, relatorio_id)).execute()

    # 3. Tabelas N:1 simples
    for table, rows_fn in [
        ("candidatos", _rows_candidatos),
        ("bairros_alternativos", _rows_bairros_alternativos),
    ]:
        rows = rows_fn(relatorio, relatorio_id)
        if rows:
            client.table(table).insert(rows).execute()

    rows_comp = _rows_competidores(relatorio, relatorio_id, geo_preserve=geo_preserve)
    if rows_comp:
        client.table("competidores").insert(rows_comp).execute()

    # 4. Cenários — precisa capturar IDs gerados pra ligar sensibilidade
    rows_cenarios = _rows_cenarios(relatorio, relatorio_id)
    cenario_ids: dict[str, str] = {}
    if rows_cenarios:
        cen_resp = client.table("cenarios_financeiros").insert(rows_cenarios).execute()
        # Mapeia modelo → uuid retornado (necessário pra FK em sensibilidade)
        for row in cen_resp.data or []:
            modelo = row.get("modelo")
            if modelo:
                cenario_ids[modelo] = row["id"]

    # 5. Sensibilidade (3 stress tests × 3 cenários = 9 rows) — depende dos IDs
    rows_sens = _rows_sensibilidade(relatorio, relatorio_id, cenario_ids)
    if rows_sens:
        client.table("sensibilidade_cenarios").insert(rows_sens).execute()

    elapsed = round(time.time() - t0, 2)
    _log("success", f"gravado {relatorio_id} em {elapsed}s", {
        "id_pipeline": relatorio.get("id"),
        "relatorio_uuid": relatorio_id,
        "elapsed_s": elapsed,
    })
    return relatorio_id


def write_relatorio_failsafe(
    relatorio: dict,
    markdown: Optional[str] = None,
    org_id: Optional[str] = None,
    relatorio_id: Optional[str] = None,
) -> Optional[str]:
    """
    Wrapper fail-safe: NUNCA propaga exceção pro pipeline.

    Se Supabase falhar (sem credenciais, rede, schema desatualizado, RLS bloqueado),
    apenas loga e segue. Filesystem em metrics/relatorios/*.json continua intacto
    como source-of-truth.
    """
    try:
        return write_relatorio_to_supabase(relatorio, markdown, org_id, relatorio_id)
    except Exception as e:
        _log("error", f"falha gravar Supabase: {e}", {
            "id_pipeline": relatorio.get("id"),
            "exception": type(e).__name__,
            "traceback": traceback.format_exc()[:500],
        })
        return None


def write_posicionamento_to_supabase(
    relatorio_id: str,
    posicionamento: dict,
) -> bool:
    """
    Atualiza relatorio_outputs.posicionamento_estrategico após A9.
    Chamado pelo callback do A9 — coluna pode não existir em schemas antigos.
    """
    client = _get_client()
    if client is None:
        _log("info", "no-op posicionamento (credenciais ausentes)", {"relatorio_id": relatorio_id})
        return False
    if not relatorio_id or not isinstance(posicionamento, dict):
        return False
    client.table("relatorio_outputs").update(
        {"posicionamento_estrategico": posicionamento},
    ).eq("relatorio_id", relatorio_id).execute()
    _log("success", "posicionamento_estrategico gravado", {"relatorio_id": relatorio_id})
    return True


def write_posicionamento_failsafe(relatorio_id: str, posicionamento: dict) -> bool:
    """Wrapper fail-safe para patch de posicionamento pós-A9."""
    try:
        return write_posicionamento_to_supabase(relatorio_id, posicionamento)
    except Exception as e:
        _log("error", f"falha gravar posicionamento: {e}", {
            "relatorio_id": relatorio_id,
            "exception": type(e).__name__,
            "traceback": traceback.format_exc()[:500],
        })
        return False
