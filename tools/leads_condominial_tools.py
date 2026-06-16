"""
Leads de academia condominial (Apêndice C do Motor v2) — módulo de prospecção B2B.

Empreendimento residencial em obra COM amenidade fitness → lead de equipamento.
Cadeia: CNO grande porte (RFB) → refino A4 (amenidade fitness no lançamento) →
CNPJ incorporadora → RFB QSA (sócio) → Apollo (decisor operacional + contato) →
public.oportunidades_prospeccao.

Lead perecível/datado: equipamento compra-se 3-6 meses antes da entrega. Vectra
fecha com o frete na entrega. Comprador do lead: fornecedor/locadora de equipamento.

Rede (refino/RFB/Apollo) injetável → testável sem rede. Roda em batch/CLI, não no
hot-path do relatório. Plano: docs/arquitetura/PLANO_ENRIQUECIMENTO_RELATORIO.md §2.4.
"""
from __future__ import annotations

import argparse
import os
import re
from typing import Any, Callable

_ORIGEM = "demanda_futura_condominial"


def _digits(s: Any) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _prioridade(entrega: str | None, janela_compra_meses: int = 4) -> str:
    """Prioridade pela proximidade da janela de compra de equipamento (entrega − N meses)."""
    from tools.demanda_futura_tools import _meses_para_entrega, _ref_atual_ym, _ym_para_indice

    ei = _ym_para_indice(entrega)
    ri = _ym_para_indice(_ref_atual_ym())
    if ei is None or ri is None:
        return "media"
    meses_ate_compra = (ei - ri) - janela_compra_meses
    if meses_ate_compra <= 6:
        return "alta"      # comprar logo
    if meses_ate_compra <= 18:
        return "media"
    return "baixa"


def _montar_lead(obra: dict, refino: dict, rfb: dict, apollo: dict | None,
                 cidade: str, uf: str) -> dict:
    """Linha para oportunidades_prospeccao (pura)."""
    cnpj = _digits(obra.get("ni_responsavel"))
    entrega = None
    try:
        from tools.demanda_futura_tools import _meses_para_entrega
        entrega = _meses_para_entrega(obra.get("data_inicio"))
    except Exception:
        pass
    contato = {
        "socio_qsa": (rfb or {}).get("socio_administrador"),
        "decisor_apollo": apollo or None,
        "instagram_construtora": refino.get("instagram_url"),
        "fonte_lancamento": refino.get("fonte_url"),
    }
    return {
        "cnpj": cnpj or None,
        "cno": obra.get("id_cno"),
        "cidade": cidade, "uf": uf,
        "municipio_codigo": obra.get("id_municipio_rf"),
        "razao_social": (rfb or {}).get("razao_social"),
        "nome_fantasia": refino.get("empreendimento"),
        "segmento_operacao": "academia_condominial",
        "nome_obra": obra.get("nome"),
        "situacao_obra": "em_curso" if obra.get("em_curso") else obra.get("situacao"),
        "area_total_m2": float(obra.get("area_m2") or 0) or None,
        "data_inicio_obra": obra.get("data_inicio"),
        "endereco_cno": {"logradouro": obra.get("logradouro"), "numero": obra.get("numero_logradouro"),
                         "bairro": obra.get("bairro"), "cep": obra.get("cep")},
        "contato_cnpj": contato,
        "score_match": {"alta": 0.9, "media": 0.6, "baixa": 0.3}.get(refino.get("confianca"), 0.3),
        "motivo_match": (f"empreendimento residencial com amenidade fitness "
                         f"(refino {refino.get('fonte_tipo') or 'grounding'}, "
                         f"conf={refino.get('confianca')}); entrega {entrega}"),
        "status": "novo",
        "prioridade": _prioridade(entrega),
        "origem": _ORIGEM,
    }


def _supabase():
    from tools.supabase_client import load_create_client

    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    return load_create_client()(os.environ["SUPABASE_URL"], key)


def _ja_existe(cli, cno: str) -> bool:
    try:
        r = cli.table("oportunidades_prospeccao").select("id").eq("cno", cno).eq("origem", _ORIGEM).limit(1).execute()
        return bool(getattr(r, "data", None))
    except Exception:
        return False


def leads_academia_condominial(
    cidade: str,
    uf: str,
    *,
    top_n: int = 8,
    dry_run: bool = False,
    _refino_fn: Callable[[dict], dict] | None = None,
    _rfb_fn: Callable[[str], dict] | None = None,
    _apollo_fn: Callable[..., dict | None] | None = None,
) -> dict[str, Any]:
    """Gera leads condominiais (obra residencial + amenidade fitness) → Supabase."""
    from tools.demanda_futura_tools import _obras_futuras_municipio

    obras = _obras_futuras_municipio(cidade, uf, None)
    if obras is None:
        return {"status": "indisponivel", "cidade": cidade, "uf": uf}
    obras = sorted(obras, key=lambda o: -float(o.get("area_m2") or 0))[:top_n]

    refino_fn = _refino_fn
    if refino_fn is None:
        from tools.refino_lancamento_tools import refinar_demanda_via_lancamento
        refino_fn = lambda o: refinar_demanda_via_lancamento({**o, "cidade": cidade, "uf": uf})
    if _rfb_fn is None:
        from tools.cnpj_enrichment import _fetch_receita
        _rfb_fn = _fetch_receita
    if _apollo_fn is None:
        from tools.apollo_enrichment import enriquecer_empresa_com_apollo
        _apollo_fn = enriquecer_empresa_com_apollo

    leads: list[dict] = []
    for o in obras:
        refino = refino_fn(o) or {}
        if not refino.get("amenidade_fitness"):
            continue  # GATILHO: só empreendimento com academia/fitness nas amenidades
        cnpj = _digits(o.get("ni_responsavel"))
        rfb = _rfb_fn(cnpj) if len(cnpj) == 14 else {}
        razao = (rfb or {}).get("razao_social")
        socio = ((rfb or {}).get("socio_administrador") or {}).get("nome") if isinstance(rfb, dict) else None
        apollo = None
        if razao:
            try:
                apollo = _apollo_fn(razao, cidade, nome_socio_qsa=socio)
            except Exception:
                apollo = None
        leads.append(_montar_lead(o, refino, rfb or {}, apollo, cidade, uf))

    out = {"status": "ok", "cidade": cidade, "uf": uf, "leads": leads, "n": len(leads), "upserted": 0}
    if dry_run or not leads:
        return out
    cli = _supabase()
    for lead in leads:
        if lead.get("cno") and not _ja_existe(cli, lead["cno"]):
            try:
                cli.table("oportunidades_prospeccao").insert(lead).execute()
                out["upserted"] += 1
            except Exception as e:
                print(f"[leads_condominial] insert falhou cno={lead.get('cno')}: {type(e).__name__}: {e}")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Leads de academia condominial (Apêndice C)")
    p.add_argument("--cidade", required=True)
    p.add_argument("--uf", required=True)
    p.add_argument("--top-n", type=int, default=8)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    from dotenv import load_dotenv
    load_dotenv(".env")
    r = leads_academia_condominial(args.cidade, args.uf, top_n=args.top_n, dry_run=args.dry_run)
    print(f"status={r['status']} leads={r.get('n')} upserted={r.get('upserted')}")
    for l in (r.get("leads") or [])[:10]:
        d = (l.get("contato_cnpj") or {}).get("decisor_apollo")
        print(f"  {l.get('nome_fantasia') or l.get('nome_obra')} | {l.get('razao_social')} | "
              f"prio={l.get('prioridade')} | decisor={'sim' if d else 'nao'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
