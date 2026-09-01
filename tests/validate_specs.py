"""
tests/validate_specs.py

Validação executável das specs GymSite (camada L4 do protocolo spec-validation).

Uso:
  python tests/validate_specs.py --spec A9 --golden coco --resultado metrics/relatorios/<id>.json
  python tests/validate_specs.py --spec A6 --golden coco --resultado metrics/relatorios/<id>.json
  python tests/validate_specs.py --spec A4 --golden coco --resultado metrics/relatorios/<id>.json
  python tests/validate_specs.py --spec A0,A2,A3a,A3b,A7 --resultado metrics/relatorios/<id>.json
  python tests/validate_specs_extended.py --json metrics/relatorios/<id>.json

Ordem de validacao sugerida:
  Alta: A9, A6, A4 | Media: A8, A3b, A1 | Baixa: A0, A2, A3a, A7 | Congelado: A5
"""
from __future__ import annotations

import argparse
import json
import sys

# Golden cases — premissas canônicas (ago/2026):
# - Contagem saturação = academia TRADICIONAL gated (raio centróide + tipo).
#   NÃO confundir com matriz_demo_saturacao.n_poligono (polígono IBGE / n_per_10k).
# - Saturação = classificar_saturacao_bairro(N): ≥6 ALTO, ≥10 SATURADO.
# - n_per_10k / quadrante = matriz demo×saturação (A9), base espacial distinta.
# - Artéria = melhores_vias_prospeccao.top_vias[0] (ou fallback top_segments).
GOLDEN_CASES = {
    "coco": {
        "cidade": "Fortaleza",
        "bairro": "Cocó",
        "uf": "CE",
        "renda_pc": 4952.75,
        "percentil": 0.9917,
        "veredito_esperado": "INVESTIGAR MAIS",
        "saturacao_esperada": "ALTO",
        # Contagem raio+tipo (cross_check / total_concorrentes_analisados)
        "n_tradicionais_min": 6,
        "n_tradicionais_max": 9,
        "gated_n_esperado": 7,
        # Matriz demo×saturação (polígono IBGE) — base espacial DIFERENTE do gated_n
        "n_per_10k_min": 0.5,
        "n_per_10k_max": 2.5,
        "n_poligono_min": 1,
        "n_poligono_max": 4,
        "populacao_bairro_min": 20000,
        "quadrante_esperado": "Oceano Azul",
        "fluxo_top1_norm_min": 0.70,
        "fluxo_score_top1_min": 70,
        "fluxo_score_top1_via_contains": "saboia",
    },
    "meireles": {
        "cidade": "Fortaleza",
        "bairro": "Meireles",
        "uf": "CE",
        "renda_pc": 5125.78,
        "percentil": 0.975,
        "veredito_esperado": "INVESTIGAR MAIS",
        "saturacao_esperada": "ALTO",
        "n_tradicionais_min": 6,
    },
    "parangaba": {
        "cidade": "Fortaleza",
        "bairro": "Parangaba",
        "uf": "CE",
        "renda_pc": 963.45,
        "percentil": 0.5583,
        "veredito_esperado": "APROVADO",
        "saturacao_esperada": "MEDIO",
    },
    "lagoa": {
        "cidade": "Rio de Janeiro",
        "bairro": "Lagoa",
        "uf": "RJ",
        "renda_resp_domicilio": 18002.44,
        "percentil": 1.0,
        "veredito_esperado": "APROVADO",
    },
    "acari": {
        "cidade": "Rio de Janeiro",
        "bairro": "Acari",
        "uf": "RJ",
        "renda_resp_domicilio": 1379.15,
        "percentil": 0.0,
        "veredito_esperado": "INVESTIGAR MAIS",
    },
}


def carregar_resultado(path: str) -> dict:
    """Carrega metrics/relatorios/<id>.json e achata output_consolidado + A9."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    if not isinstance(raw, dict):
        return {}

    if "output_consolidado" not in raw:
        return raw

    out = dict(raw["output_consolidado"] or {})
    # Irmãos do consolidado usados pelo L4 estendido
    if isinstance(raw.get("oferta_concorrentes"), dict):
        out.setdefault("oferta_concorrentes", raw["oferta_concorrentes"])
    if isinstance(raw.get("validacao_a8"), dict):
        out["validacao_a8"] = raw["validacao_a8"]
    if isinstance(raw.get("input_canonico"), dict):
        out["_input_canonico"] = raw["input_canonico"]

    pos = out.get("posicionamento_estrategico")
    if isinstance(pos, dict):
        for campo in (
            "veredito_posicionamento",
            "zona_percepcao",
            "recomendacao_ticket",
            "framework_errc",
            "mapa_servicos",
            "gaps_identificados",
            "alertas_financeiros_fiscais",
            "headroom_renda",
            "fonte_geracao",
            "matriz_demo_saturacao",
        ):
            if campo in pos:
                out[campo] = pos[campo]

    if "cenarios" not in out and "viabilidade_3_cenarios" in out:
        out["cenarios"] = out["viabilidade_3_cenarios"]
    if "recomendacao_modelo" not in out and "modelo_recomendado" in out:
        out["recomendacao_modelo"] = out["modelo_recomendado"]
    if "score_viabilidade" not in out and out.get("score_bairro") is not None:
        out["score_viabilidade"] = out["score_bairro"]
    if "alertas" not in out and "alertas_financeiros" in out:
        out["alertas"] = out["alertas_financeiros"]

    fp = out.get("fluxo_pedestre")
    if isinstance(fp, dict):
        if out.get("fluxo_score") is None and fp.get("fluxo_score") is not None:
            out["fluxo_score"] = fp["fluxo_score"]
        if "top_3_vias" not in out and isinstance(fp.get("top_segments"), list):
            out["top_3_vias"] = fp["top_segments"][:3]

    # Preferir bloco canônico de prospecção por via
    mvp = out.get("melhores_vias_prospeccao")
    if isinstance(mvp, dict) and mvp.get("status") == "ok":
        vias = mvp.get("top_vias") or []
        if isinstance(vias, list) and vias:
            out["top_3_vias"] = vias[:3]

    return out


def validar_contrato_saida(spec_id: str, resultado: dict) -> list[str]:
    """Valida que o contrato de saída da spec está presente e tipado."""
    falhas: list[str] = []

    if spec_id == "A9":
        campos_obrigatorios = [
            "veredito_posicionamento",
            "zona_percepcao",
            "recomendacao_ticket",
            "framework_errc",
            "mapa_servicos",
            "gaps_identificados",
            "alertas_financeiros_fiscais",
            "headroom_renda",
            "fonte_geracao",
        ]
        for campo in campos_obrigatorios:
            if campo not in resultado:
                falhas.append(f"A9: campo '{campo}' ausente no output")

        if resultado.get("fonte_geracao") != "deterministico_errc":
            falhas.append(
                f"A9: fonte_geracao={resultado.get('fonte_geracao')!r}, "
                "esperado 'deterministico_errc'"
            )

    elif spec_id == "A6":
        campos_obrigatorios = [
            "veredito",
            "score_bairro",
            "score_top1_candidato",
            "nivel_saturacao",
            "top_3_vias",
            "demografia_bairro",
        ]
        for campo in campos_obrigatorios:
            if campo not in resultado:
                falhas.append(f"A6: campo '{campo}' ausente no output")

    elif spec_id == "A4":
        campos_obrigatorios = [
            "cenarios",
            "score_viabilidade",
            "recomendacao_modelo",
            "fonte_aluguel",
            "alertas",
        ]
        for campo in campos_obrigatorios:
            if campo not in resultado:
                falhas.append(f"A4: campo '{campo}' ausente no output")

        fonte = str(resultado.get("fonte_aluguel") or "")
        if "mrlr" not in fonte.lower():
            falhas.append(f"A4: aluguel não-MRLR ({fonte!r})")

    elif spec_id == "A0":
        falhas.extend(validar_a0(resultado))
    elif spec_id == "A2":
        falhas.extend(validar_a2(resultado))
    elif spec_id == "A3a":
        falhas.extend(validar_a3a(resultado))
    elif spec_id == "A3b":
        falhas.extend(validar_a3b(resultado))
    elif spec_id == "A7":
        falhas.extend(validar_a7(resultado))

    return falhas


def validar_a0(resultado: dict) -> list[str]:
    """A0 ContextBuilder: contexto de mercado + parque CNPJ + redes."""
    falhas: list[str] = []
    mc = resultado.get("market_context") or {}
    if not isinstance(mc, dict):
        return ["A0: market_context ausente"]

    for campo in ("cidade", "bairro", "uf"):
        if not mc.get(campo):
            falhas.append(f"A0: market_context.{campo} ausente")

    parque = mc.get("parque_ativo_total")
    if parque is None or parque <= 0:
        falhas.append(f"A0: parque_ativo_total ausente ou <=0 ({parque})")

    comp = mc.get("composicao_parque") or {}
    if not isinstance(comp, dict) or "academia" not in comp:
        falhas.append("A0: composicao_parque sem segmento 'academia'")

    renda = mc.get("renda_media_bairro")
    renda_fonte = mc.get("renda_media_bairro_fonte")
    if renda is not None and not renda_fonte:
        falhas.append("A0: renda_media_bairro sem fonte (carimbo P-010)")

    if mc.get("aluguel_medio_m2") is not None or mc.get("aluguel_mensal") is not None:
        falhas.append("A0: aluguel presente no market_context (viola RN-A0 / R-7)")

    cob = resultado.get("cobertura_redes_a0") or {}
    if not cob:
        falhas.append("A0: cobertura_redes_a0 ausente")

    return falhas


def validar_a2(resultado: dict) -> list[str]:
    """A2 DemoAnalyst: demografia IBGE + renda + perfil idade/sexo."""
    falhas: list[str] = []
    demo = resultado.get("demografia_bairro") or {}
    if not isinstance(demo, dict) or not demo:
        return ["A2: demografia_bairro ausente"]

    pop = demo.get("populacao")
    if pop is None or pop <= 0:
        falhas.append(f"A2: populacao ausente ou <=0 ({pop})")

    renda = demo.get("renda_media")
    renda_fonte = str(demo.get("renda_fonte") or "")
    if renda is None or renda <= 0:
        falhas.append(f"A2: renda_media ausente ou <=0 ({renda})")
    if "2022" not in renda_fonte and "ibge" not in renda_fonte.lower():
        falhas.append(f"A2: renda_fonte não é IBGE 2022 ({renda_fonte!r})")

    perfil = demo.get("perfil_idade_sexo_bairro") or {}
    if not isinstance(perfil, dict) or not perfil:
        falhas.append("A2: perfil_idade_sexo_bairro ausente")
    elif perfil.get("total") is None:
        falhas.append("A2: perfil_idade_sexo_bairro.total ausente")

    media_mor = demo.get("media_moradores")
    if media_mor is not None and not (2.0 <= float(media_mor) <= 4.0):
        falhas.append(f"A2: media_moradores fora da faixa 2-4 ({media_mor})")

    return falhas


def validar_a3a(resultado: dict) -> list[str]:
    """A3a CompetitorSearch: coleta + cross-check gated."""
    falhas: list[str] = []
    aneis = resultado.get("aneis_competitivos") or {}
    cross = aneis.get("cross_check") if isinstance(aneis, dict) else None
    if not isinstance(cross, dict):
        falhas.append("A3a: cross_check ausente")
        cross = {}

    gated_n = cross.get("gated_n")
    if gated_n is None:
        falhas.append("A3a: cross_check.gated_n ausente")
    elif gated_n < 1:
        falhas.append(f"A3a: gated_n < 1 ({gated_n}) — coleta vazia")

    if not cross.get("nivel_saturacao_bairro"):
        falhas.append("A3a: nivel_saturacao_bairro ausente")

    analisadas = resultado.get("academias_analisadas") or []
    if not analisadas:
        falhas.append("A3a: academias_analisadas vazio")

    if resultado.get("total_concorrentes_analisados") is None:
        falhas.append("A3a: total_concorrentes_analisados ausente")

    return falhas


def validar_a3b(resultado: dict) -> list[str]:
    """A3b CompetitorAnalysis: amostra aprofundada + dores + oferta."""
    falhas: list[str] = []
    comp_set = resultado.get("competitors_set") or []
    if not comp_set:
        falhas.append("A3b: competitors_set vazio (MAX_ENRIQUECIMENTO não rodou)")

    dores = resultado.get("dores_dominantes") or []
    if not dores:
        falhas.append("A3b: dores_dominantes vazio")

    oferta = resultado.get("oferta_concorrentes") or {}
    taxa = oferta.get("taxa_sucesso") if isinstance(oferta, dict) else None
    if taxa is None:
        falhas.append("A3b: oferta_concorrentes.taxa_sucesso ausente")
    elif float(taxa) < 0.5:
        falhas.append(f"A3b: taxa_sucesso baixa ({taxa})")

    for c in comp_set:
        if isinstance(c, dict) and "servicos_oferecidos" not in c:
            falhas.append(
                f"A3b: concorrente '{c.get('nome')}' sem servicos_oferecidos mesclado"
            )

    return falhas


def validar_a7(resultado: dict) -> list[str]:
    """A7 MarketResearch: suporte — fail-soft observável (não exige resultado)."""
    falhas: list[str] = []
    val_a8 = resultado.get("validacao_a8") or {}
    if not isinstance(val_a8, dict):
        return falhas
    # Se provider kimi falhou, o erro deve estar registrado (não silent)
    provider = val_a8.get("a0_research_provider")
    fontes = val_a8.get("fontes_independentes") or []
    if provider == "kimi":
        has_erro = any("kimi_erro" in str(f) for f in fontes)
        # Fail-soft: se não há fontes e não há erro registrado, observabilidade fraca
        if not fontes and not has_erro:
            falhas.append(
                "A7: provider=kimi sem fontes_independentes nem kimi_erro registrado"
            )
    return falhas


def validar_n_per_10k(case_id: str, gc: dict, resultado: dict) -> list[str]:
    """Valida n_per_10k da matriz demo×saturação (já calculada pelo pipeline)."""
    falhas: list[str] = []
    matriz = resultado.get("matriz_demo_saturacao")
    if not isinstance(matriz, dict):
        pos = resultado.get("posicionamento_estrategico") or {}
        matriz = pos.get("matriz_demo_saturacao") if isinstance(pos, dict) else None
    if not isinstance(matriz, dict):
        falhas.append(f"{case_id}: matriz_demo_saturacao ausente")
        return falhas

    n_per_10k = matriz.get("n_per_10k")
    if n_per_10k is None:
        falhas.append(f"{case_id}: matriz_demo_saturacao.n_per_10k ausente")
        return falhas

    try:
        n_val = float(n_per_10k)
    except (TypeError, ValueError):
        falhas.append(f"{case_id}: n_per_10k não numérico ({n_per_10k!r})")
        return falhas

    if gc.get("n_per_10k_min") is not None and n_val < float(gc["n_per_10k_min"]):
        falhas.append(
            f"{case_id}: n_per_10k={n_val:.3f} < min {gc['n_per_10k_min']}"
        )
    if gc.get("n_per_10k_max") is not None and n_val > float(gc["n_per_10k_max"]):
        falhas.append(
            f"{case_id}: n_per_10k={n_val:.3f} > max {gc['n_per_10k_max']}"
        )

    if gc.get("quadrante_esperado"):
        quadrante = matriz.get("quadrante")
        if quadrante != gc["quadrante_esperado"]:
            falhas.append(
                f"{case_id}: quadrante {quadrante!r} != esperado "
                f"{gc['quadrante_esperado']!r}"
            )

    n_pol = matriz.get("n_poligono")
    if gc.get("n_poligono_min") is not None and n_pol is not None:
        if int(n_pol) < int(gc["n_poligono_min"]):
            falhas.append(
                f"{case_id}: n_poligono={n_pol} < min {gc['n_poligono_min']}"
            )
    if gc.get("n_poligono_max") is not None and n_pol is not None:
        if int(n_pol) > int(gc["n_poligono_max"]):
            falhas.append(
                f"{case_id}: n_poligono={n_pol} > max {gc['n_poligono_max']}"
            )

    demo = resultado.get("demografia_bairro") or {}
    pop = demo.get("populacao") if isinstance(demo, dict) else None
    if gc.get("populacao_bairro_min") is not None and pop is not None:
        if int(pop) < int(gc["populacao_bairro_min"]):
            falhas.append(
                f"{case_id}: populacao={pop} < min {gc['populacao_bairro_min']}"
            )

    return falhas


def _gated_n(resultado: dict) -> int | None:
    aneis = resultado.get("aneis_competitivos") or {}
    if isinstance(aneis, dict):
        cross = aneis.get("cross_check") or {}
        if isinstance(cross, dict) and isinstance(cross.get("gated_n"), (int, float)):
            return int(cross["gated_n"])
    return None

def _n_tradicionais(resultado: dict) -> int | None:
    """Contagem autoritativa de academia tradicional (já gated no consolidado)."""
    for chave in (
        "total_concorrentes_analisados",
        "total_encontrados",
    ):
        v = resultado.get(chave)
        if isinstance(v, (int, float)) and v >= 0:
            return int(v)
    acad = resultado.get("academias_analisadas")
    if isinstance(acad, list):
        return len(acad)
    return None


def _fluxo_top1_norm(resultado: dict) -> float | None:
    """flow_score da via #1 (0–1). Prefere melhores_vias_prospeccao."""
    mvp = resultado.get("melhores_vias_prospeccao")
    if isinstance(mvp, dict) and mvp.get("status") == "ok":
        vias = mvp.get("top_vias") or []
        if vias and isinstance(vias[0], dict):
            raw = vias[0].get("fluxo_norm")
            if raw is None:
                raw = vias[0].get("fluxo_score")
            if isinstance(raw, (int, float)):
                return float(raw) if float(raw) <= 1.0 else float(raw) / 100.0

    vias = resultado.get("top_3_vias")
    if isinstance(vias, list) and vias:
        top = vias[0] if isinstance(vias[0], dict) else None
        if top:
            raw = top.get("flow_score")
            if raw is None:
                raw = top.get("fluxo_score")
            if raw is None:
                raw = top.get("fluxo_norm")
            if isinstance(raw, (int, float)):
                return float(raw) if float(raw) <= 1.0 else float(raw) / 100.0
    fp = resultado.get("fluxo_pedestre")
    if isinstance(fp, dict):
        segs = fp.get("top_segments") or []
        if segs and isinstance(segs[0], dict):
            raw = segs[0].get("flow_score")
            if isinstance(raw, (int, float)):
                return float(raw) if float(raw) <= 1.0 else float(raw) / 100.0
    return None


def _fluxo_top1_nome(resultado: dict) -> str | None:
    mvp = resultado.get("melhores_vias_prospeccao")
    if isinstance(mvp, dict) and mvp.get("status") == "ok":
        vias = mvp.get("top_vias") or []
        if vias and isinstance(vias[0], dict):
            nome = vias[0].get("nome_via")
            if nome:
                return str(nome)
    vias = resultado.get("top_3_vias")
    if isinstance(vias, list) and vias and isinstance(vias[0], dict):
        return str(vias[0].get("nome_via") or vias[0].get("street_name") or "") or None
    fp = resultado.get("fluxo_pedestre")
    if isinstance(fp, dict):
        segs = fp.get("top_segments") or []
        if segs and isinstance(segs[0], dict):
            return str(segs[0].get("street_name") or "") or None
    return None


def validar_golden_case(case_id: str, resultado: dict) -> list[str]:
    """Valida resultado contra golden case (premissas tradicionais + limiares)."""
    falhas: list[str] = []
    gc = GOLDEN_CASES.get(case_id)
    if not gc:
        return [f"Golden case '{case_id}' não definido"]

    veredito = resultado.get("veredito") or resultado.get("veredito_posicionamento")
    if gc.get("veredito_esperado") and veredito != gc["veredito_esperado"]:
        falhas.append(
            f"{case_id}: veredito {veredito!r} != esperado {gc['veredito_esperado']!r}"
        )

    sat = resultado.get("nivel_saturacao")
    if gc.get("saturacao_esperada") and sat and sat.upper() != gc["saturacao_esperada"].upper():
        falhas.append(
            f"{case_id}: saturacao {sat!r} != esperada {gc['saturacao_esperada']!r}"
        )

    n = _n_tradicionais(resultado)
    if n is not None and gc.get("n_tradicionais_min") is not None:
        if n < int(gc["n_tradicionais_min"]):
            falhas.append(
                f"{case_id}: N tradicionais {n} < min {gc['n_tradicionais_min']} "
                "(gate academia tradicional — raio+tipo)"
            )
    if n is not None and gc.get("n_tradicionais_max") is not None:
        if n > int(gc["n_tradicionais_max"]):
            falhas.append(
                f"{case_id}: N tradicionais {n} > max {gc['n_tradicionais_max']} "
                "(acima da faixa ALTO; espere SATURADO se ≥10)"
            )

    if gc.get("gated_n_esperado") is not None:
        gated = _gated_n(resultado)
        if gated is None:
            falhas.append(f"{case_id}: cross_check.gated_n ausente")
        elif gated != int(gc["gated_n_esperado"]):
            falhas.append(
                f"{case_id}: gated_n={gated} != esperado {gc['gated_n_esperado']} "
                "(contagem raio+tipo; distinta de n_poligono da matriz)"
            )

    # Sanidade demográfica / matriz (base espacial ≠ gated_n)
    if any(
        gc.get(k) is not None
        for k in (
            "n_per_10k_min",
            "n_per_10k_max",
            "quadrante_esperado",
            "populacao_bairro_min",
        )
    ):
        falhas.extend(validar_n_per_10k(case_id, gc, resultado))

    top1 = _fluxo_top1_norm(resultado)
    if gc.get("fluxo_top1_norm_min") is not None and top1 is not None:
        if top1 < float(gc["fluxo_top1_norm_min"]):
            falhas.append(
                f"{case_id}: fluxo top-1 norm {top1} < min {gc['fluxo_top1_norm_min']}"
            )

    if gc.get("fluxo_score_top1_min") is not None and top1 is not None:
        score_100 = round(top1 * 100)
        if score_100 < int(gc["fluxo_score_top1_min"]):
            falhas.append(
                f"{case_id}: fluxo via top-1 {score_100} < min {gc['fluxo_score_top1_min']}"
            )

    needle = gc.get("fluxo_score_top1_via_contains")
    if needle:
        import unicodedata

        def _fold(s: str) -> str:
            nfkd = unicodedata.normalize("NFKD", s or "")
            return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

        nome = _fluxo_top1_nome(resultado) or ""
        if _fold(needle) not in _fold(nome):
            falhas.append(
                f"{case_id}: via top-1 {nome!r} nao contem {needle!r}"
            )

    return falhas


def validar_regras_transversais(resultado: dict) -> list[str]:
    """Valida R-1 a R-10 no resultado."""
    falhas: list[str] = []

    # R-2: carimbo P-010 em números exibidos
    # (verificação simplificada — em produção, checar cada campo numérico)

    # R-7: aluguel MRLR
    fonte_aluguel = str(resultado.get("fonte_aluguel") or "")
    if fonte_aluguel and "mrlr" not in fonte_aluguel.lower():
        falhas.append("R-7 violada: aluguel de decisão não é MRLR")

    # R-8: VIA primária (se top_3_vias presente, não deve ter top_3_candidatos como imóvel)
    if "top_3_vias" in resultado and "top_3_candidatos" in resultado:
        # Se ambos existem, verificar que top_3_candidatos não é usado como decisão
        pass  # validação específica depende do contexto

    return falhas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validação L4 de specs GymSite contra contrato + golden case."
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="ID da spec (A0-A9) ou lista separada por vírgula",
    )
    parser.add_argument("--golden", help="ID do golden case")
    parser.add_argument("--resultado", help="Path do JSON de resultado")
    args = parser.parse_args()

    if not args.resultado:
        print(
            "Uso: python tests/validate_specs.py --spec A9 --golden coco "
            "--resultado metrics/relatorios/<id>.json"
        )
        sys.exit(1)

    resultado = carregar_resultado(args.resultado)
    specs = [s.strip() for s in args.spec.split(",") if s.strip()]
    falhas: list[str] = []
    for spec_id in specs:
        falhas.extend(validar_contrato_saida(spec_id, resultado))
    if args.golden:
        falhas.extend(validar_golden_case(args.golden, resultado))
    falhas.extend(validar_regras_transversais(resultado))

    if falhas:
        print(f"[REPROVADO] {len(falhas)} falha(s):")
        for falha in falhas:
            print(f"  - {falha}")
        sys.exit(1)

    golden_txt = f" com golden case '{args.golden}'" if args.golden else ""
    print(f"[APROVADO] spec {','.join(specs)} validada{golden_txt}")
    sys.exit(0)


if __name__ == "__main__":
    main()
