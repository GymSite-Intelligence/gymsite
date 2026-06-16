"""
Minera obras fitness do CNO via BigQuery basedosdados → Supabase public.cno_obras_fitness.

Carga NACIONAL (sem lista de município): filtra fitness no Brasil inteiro, pipeline
consulta por município no read. Espelha a Trilha 3 (parque CNPJ).
Ver docs/arquitetura/COMPILADO_FONTES_DADOS.md §7.2.

v1: caminho keyword + área (self-contained). Cruzamento CNAE 9313100 (alta confiança)
= fase 2 via join SQL no Supabase (cno_obras_fitness × parque_cnpj_fitness).

Uso:
    python -m tools.cno_bigquery_loader            # nacional
    python -m tools.cno_bigquery_loader --dry-run  # só conta, não grava
"""
from __future__ import annotations

import argparse
import os

from tools.basedosdados_loader import run_query
from tools.cno_fitness_tools import _KEYWORDS_OBRA_FITNESS, _eh_obra_fitness

_TABLE = "`basedosdados.br_me_cno.microdados`"
_SITUACAO_EM_CURSO = {"01", "02", "03", "04", "1", "2", "3", "4"}


def _keyword_regex() -> str:
    # keywords já são lowercase; regex case-insensitive aplicado no LOWER() do SQL.
    return "|".join(k.replace(" ", r"\s") for k in _KEYWORDS_OBRA_FITNESS)


def _query_candidatos() -> str:
    return f"""
    SELECT id_cno, nome_empresarial, nome_responsavel, area,
           cep, tipo_logradouro, logradouro, numero_logradouro, bairro,
           sigla_uf, id_municipio, id_municipio_rf,
           situacao, data_inicio, data_situacao,
           ni_responsavel, qualificacao_responsavel
    FROM {_TABLE}
    WHERE area BETWEEN 80 AND 8000
      AND REGEXP_CONTAINS(
            LOWER(CONCAT(COALESCE(nome_empresarial,''),' ',COALESCE(nome_responsavel,''))),
            r'{_keyword_regex()}')
    """


def _iso(d) -> str | None:
    return d.isoformat() if d is not None and hasattr(d, "isoformat") else (d or None)


def _to_row(r: dict) -> dict | None:
    nome_emp = (r.get("nome_empresarial") or "").strip()
    nome_resp = (r.get("nome_responsavel") or "").strip()
    # Classifica na combinação (mesmo alvo do filtro BQ); display usa o melhor nome.
    nome_class = (nome_emp + " " + nome_resp).strip()
    nome = nome_emp or nome_resp
    area = float(r.get("area") or 0)
    eh, metodo = _eh_obra_fitness(nome_class, area, None)  # v1: só keyword (CNAE = fase 2)
    if not eh:
        return None
    situacao = (r.get("situacao") or "").strip()
    return {
        "id_cno": r.get("id_cno"),
        "nome": nome or None,
        "nome_empresarial": r.get("nome_empresarial"),
        "nome_responsavel": r.get("nome_responsavel"),
        "area_m2": area or None,
        "cep": r.get("cep"),
        "tipo_logradouro": r.get("tipo_logradouro"),
        "logradouro": r.get("logradouro"),
        "numero_logradouro": r.get("numero_logradouro"),
        "bairro": r.get("bairro"),
        "sigla_uf": r.get("sigla_uf"),
        "id_municipio": r.get("id_municipio"),
        "id_municipio_rf": r.get("id_municipio_rf"),
        "situacao": situacao or None,
        "em_curso": situacao in _SITUACAO_EM_CURSO,
        "data_inicio": _iso(r.get("data_inicio")),
        "data_situacao": _iso(r.get("data_situacao")),
        "ni_responsavel": r.get("ni_responsavel"),
        "qualificacao_responsavel": r.get("qualificacao_responsavel"),
        "metodo_classificacao": metodo,
        "fonte": "basedosdados.br_me_cno",
    }


def _supabase():
    from tools.supabase_client import load_create_client

    create_client = load_create_client()
    url = os.environ["SUPABASE_URL"]
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    return create_client(url, key)


def minerar(*, dry_run: bool = False, chunk: int = 500) -> dict:
    candidatos = run_query(_query_candidatos())
    rows = [row for r in candidatos if (row := _to_row(r))]
    out = {"candidatos_bq": len(candidatos), "fitness_validados": len(rows), "upserted": 0}
    if dry_run or not rows:
        return out
    cli = _supabase()
    for i in range(0, len(rows), chunk):
        batch = rows[i : i + chunk]
        # PRECEDÊNCIA: basedosdados é ≤2021 (backfill histórico). ignore_duplicates
        # = INSERT ON CONFLICT DO NOTHING — só preenche id_cno ausente, NUNCA
        # sobrescreve linha existente (que pode ter dado fresco do rfb_cno_loader
        # mensal). Sem isso, re-rodar este loader após o RFB regredia 2026→2021.
        cli.table("cno_obras_fitness").upsert(
            batch, on_conflict="id_cno", ignore_duplicates=True
        ).execute()
        out["upserted"] += len(batch)
    return out


# ── Fase B: obras de grande porte (proxy residencial) → demanda futura ─────────
_TABLE_GP = "public.cno_obras_grande_porte"
# Exclusões: fitness (tem tabela própria) + comercial/institucional óbvio.
# Exclui não-residencial: comercial/institucional + INFRA/obra pública/serviço
# (proxy residencial é ruidoso; refino A4 é o gate final de residencial).
_KW_COMERCIAL = (
    # comercial / institucional
    "hospital", "escola", "universidade", "faculdade", "shopping", "galpao", "galpão",
    "posto", "igreja", "hotel", "prefeitura", "secretaria", "terminal", "ginasio",
    "ginásio", "estadio", "estádio", "creche", "presidio", "presídio", "supermercado",
    "industria", "indústria", "fabrica", "fábrica", "armazem", "armázem", "armazém",
    "clinica", "clínica", "delegacia", "quartel", "camara", "câmara", "tribunal", "forum",
    # infra / obra pública / serviço (não geram moradores)
    "barragem", "rodovia", "ponte", "viaduto", "saneamento", "esgoto", "adutora",
    "drenagem", "pavimenta", "subestacao", "subestação", "transmissao", "transmissão",
    "terraplan", "aeroporto", "ferrovia", "reservatorio", "reservatório", "estacao de",
    "estação de", "servicos comuns de engenharia", "serviços comuns de engenharia",
    "manutencao", "manutenção", "reforma", "ampliacao", "ampliação", "restauracao",
    "restauração", "consorcio", "consórcio", "duto", "linha de", "usina", "porto",
    "vias e logradouros", "sistema viario", "sistema viário", "granel", "cais",
    "eolic", "eólic", "solar", "air hub", "aterro", "sanitario", "sanitário",
)

# Sinal POSITIVO de residencial (sobe confiança do proxy; refino A4 confirma).
_KW_RESIDENCIAL = (
    "residencial", "edificio", "edifício", "condominio", "condomínio", "empreendimento imobiliario",
    "empreendimento imobiliário", "incorporac", "incorporaç", "morada", "reserva", "ville",
    "jardim", "torre", "vila ", "village", "parque residencial", "loteamento",
)
# Gate grande porte recalibrável via parametros_metodologia (zero-hardcode).
# Default rotulado (_DEFAULTS) se Supabase indisponível.
from tools.parametros_metodologia import param_int

_AREA_GP_MIN = param_int("cno_area_gp_min_m2")
_AREA_GP_MAX = param_int("cno_area_gp_max_m2")  # corta mega-infra (não é prédio residencial)


def _regex_or(keywords) -> str:
    return "|".join(k.replace(" ", r"\s") for k in keywords)


def _query_grande_porte(*, count_only: bool = False) -> str:
    cols = "count(*) as n" if count_only else (
        "id_cno, nome_empresarial, nome_responsavel, area, cep, tipo_logradouro, "
        "logradouro, numero_logradouro, bairro, sigla_uf, id_municipio, id_municipio_rf, "
        "situacao, data_inicio, data_situacao, ni_responsavel"
    )
    return f"""
    SELECT {cols}
    FROM {_TABLE}
    WHERE area BETWEEN {_AREA_GP_MIN} AND {_AREA_GP_MAX}
      AND situacao IN ('01','02','03','04','1','2','3','4')
      AND NOT REGEXP_CONTAINS(
            LOWER(CONCAT(COALESCE(nome_empresarial,''),' ',COALESCE(nome_responsavel,''))),
            r'{_regex_or(_KEYWORDS_OBRA_FITNESS)}')
      AND NOT REGEXP_CONTAINS(
            LOWER(CONCAT(COALESCE(nome_empresarial,''),' ',COALESCE(nome_responsavel,''))),
            r'{_regex_or(_KW_COMERCIAL)}')
    """


def _to_row_gp(r: dict) -> dict:
    situacao = (r.get("situacao") or "").strip()
    return {
        "id_cno": r.get("id_cno"),
        "nome": (r.get("nome_empresarial") or r.get("nome_responsavel") or "").strip() or None,
        "area_m2": float(r.get("area") or 0) or None,
        "cep": r.get("cep"),
        "tipo_logradouro": r.get("tipo_logradouro"),
        "logradouro": r.get("logradouro"),
        "numero_logradouro": r.get("numero_logradouro"),
        "bairro": r.get("bairro"),
        "sigla_uf": r.get("sigla_uf"),
        "id_municipio": r.get("id_municipio"),
        "id_municipio_rf": r.get("id_municipio_rf"),
        "situacao": situacao or None,
        "em_curso": situacao in _SITUACAO_EM_CURSO,
        "data_inicio": _iso(r.get("data_inicio")),
        "data_situacao": _iso(r.get("data_situacao")),
        "ni_responsavel": r.get("ni_responsavel"),
        "fonte": "basedosdados.br_me_cno",
    }


def contar_grande_porte() -> int:
    return int((run_query(_query_grande_porte(count_only=True)) or [{}])[0].get("n", 0))


def minerar_grande_porte(*, dry_run: bool = False, chunk: int = 500) -> dict:
    linhas = run_query(_query_grande_porte())
    rows = [_to_row_gp(r) for r in linhas if r.get("id_cno")]
    out = {"obras_bq": len(linhas), "rows": len(rows), "upserted": 0}
    if dry_run or not rows:
        return out
    cli = _supabase()
    for i in range(0, len(rows), chunk):
        batch = rows[i : i + chunk]
        # PRECEDÊNCIA: ver minerar() — backfill histórico não sobrescreve dado
        # fresco do rfb_cno_loader (ignore_duplicates = ON CONFLICT DO NOTHING).
        cli.table("cno_obras_grande_porte").upsert(
            batch, on_conflict="id_cno", ignore_duplicates=True
        ).execute()
        out["upserted"] += len(batch)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Minera CNO do BigQuery → Supabase")
    p.add_argument("--dry-run", action="store_true", help="conta, não grava")
    p.add_argument("--grande-porte", action="store_true", help="minera obras grande porte (Fase B)")
    args = p.parse_args()
    if args.grande_porte:
        if args.dry_run:
            print(f"grande_porte candidatos_bq={contar_grande_porte()}")
            return 0
        r = minerar_grande_porte()
        print(f"grande_porte obras_bq={r['obras_bq']} upserted={r['upserted']}")
        return 0
    res = minerar(dry_run=args.dry_run)
    print(
        f"candidatos_bq={res['candidatos_bq']} "
        f"fitness_validados={res['fitness_validados']} "
        f"upserted={res['upserted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
