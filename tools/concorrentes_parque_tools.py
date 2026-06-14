"""
Descoberta de concorrentes pelo parque CNPJ (registro-primeiro, Motor v2).

Inverte o A3: o parque CNPJ fitness (CNAE 9313100) descobre QUEM existe no bairro
(grátis, instantâneo, base própria); Places só ENRIQUECE (reviews/dores/geocode) os
que a lista trouxe — em vez de fazer a busca ampla "nearby gym" (lenta, cota Maps).

Fonte: public.cnpj_fitness_estabelecimentos (132k nacional). Sem lat/lng → geocode é
passo separado (só os do bairro, poucos). Bairro casa por normalização (sem acento).
"""
from __future__ import annotations

import os
from typing import Any, Callable

from tools.bairro_normalize import normalizar_bairro


def _supabase_rows(cidade: str, uf: str, limit: int = 5000) -> list[dict] | None:
    """Estabelecimentos fitness ATIVOS do município (filtro de bairro é em Python)."""
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not (os.environ.get("SUPABASE_URL") and key):
        return None
    try:
        from tools.supabase_client import load_create_client

        cli = load_create_client()(os.environ["SUPABASE_URL"], key)
        res = (cli.table("cnpj_fitness_estabelecimentos")
               .select("cnpj,razao_social,nome_fantasia,logradouro,numero,cep,bairro,"
                       "telefone,email,segmento_operacao,situacao_cadastral,cidade,uf")
               .eq("uf", (uf or "")[:2].upper())
               .ilike("cidade", (cidade or "").strip())
               .eq("situacao_cadastral", 2)
               .limit(limit).execute())
        return getattr(res, "data", None) or []
    except Exception as e:
        print(f"[concorrentes_parque] leitura falhou ({cidade}/{uf}): {type(e).__name__}: {e}")
        return None


def _to_concorrente(r: dict) -> dict:
    return {
        "cnpj": r.get("cnpj"),
        "nome": r.get("nome_fantasia") or r.get("razao_social"),
        "razao_social": r.get("razao_social"),
        "endereco": " ".join(x for x in [r.get("logradouro"), r.get("numero")] if x) or None,
        "bairro": r.get("bairro"),
        "cep": r.get("cep"),
        "telefone": r.get("telefone"),
        "email": r.get("email"),
        "segmento_operacao": r.get("segmento_operacao"),
        "fonte": "cnpj_parque",
    }


def listar_concorrentes_parque(
    cidade: str,
    uf: str,
    bairro: str | None = None,
    *,
    _rows_fn: Callable[[str, str], list[dict] | None] | None = None,
) -> dict[str, Any]:
    """Concorrentes (CNPJ fitness ativos) do bairro, do parque. Base do A3 (Places enriquece)."""
    rows_fn = _rows_fn or _supabase_rows
    rows = rows_fn(cidade, uf)
    if rows is None:
        return {"status": "indisponivel", "cidade": cidade, "uf": uf, "bairro": bairro}

    alvo = normalizar_bairro(bairro or "")
    if alvo:
        rows = [r for r in rows if normalizar_bairro(r.get("bairro") or "") == alvo]
    concorrentes = [_to_concorrente(r) for r in rows if r.get("cnpj")]
    return {
        "status": "ok",
        "cidade": cidade, "uf": uf, "bairro": bairro,
        "n": len(concorrentes),
        "concorrentes": concorrentes,
        "fonte": "parque CNPJ fitness (CNAE 9313100, ativos) — descoberta; Places enriquece",
        "nota": ("Lista de QUEM existe no bairro (registro-primeiro). Reviews/dores/pico/"
                 "geocode vêm do Places só para estes (não busca ampla)."),
    }
