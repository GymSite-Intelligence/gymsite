"""
Valida consistência dos dados CNO no relatório vs. golden case.

Ground truth em expected_output.json → chave `cno_validation`.

Opcional: snapshot `cno_cruzamento_cnpj.json` na pasta do caso (fluxo CNPJ→CNO
municipal) quando `validar_supplemento` estiver ativo no golden.
"""
from __future__ import annotations

from typing import Any

from eval.evaluators.base import EvalResult

_DPM2_MIN = 0.04
_DPM2_MAX = 4.0
_METODOS_CLASSIFICACAO = frozenset({"keyword", "cnpj_cnae", "cnpj_cnae_area_atipica"})


def _get_obras_block(report: dict) -> dict:
    oc = report.get("output_consolidado") or report
    block = oc.get("obras_cno_em_curso")
    return block if isinstance(block, dict) else {}


def _get_cruzamento(report: dict) -> dict:
    oc = report.get("output_consolidado") or report
    mc = oc.get("market_context") or {}
    if isinstance(mc.get("market_context"), dict):
        mc = mc["market_context"]
    for key in ("fatos_parque_cnpj", "fatos_mercado", "dados_parque_cnpj"):
        fatos = mc.get(key)
        if isinstance(fatos, dict):
            cruz = fatos.get("cruzamento_cno")
            if isinstance(cruz, dict):
                return cruz
    cruz = mc.get("cruzamento_cno")
    return cruz if isinstance(cruz, dict) else {}


def _get_cno_supplement(supplement: dict[str, Any] | None) -> dict:
    if not supplement:
        return {}
    for key in ("cno_cruzamento_cnpj.json", "cno_cruzamento_cnpj", "cno_live.json"):
        block = supplement.get(key)
        if isinstance(block, dict) and block.get("status") == "ok":
            return block
    return {}


def _obras_no_bairro(obras: list[dict], bairro_chave: str | None) -> list[dict]:
    if not bairro_chave:
        return obras
    alvo = bairro_chave.strip().lower()
    out = []
    for o in obras:
        b = (o.get("bairro_chave") or o.get("bairro") or "").strip().lower()
        if b == alvo or alvo in b or b in alvo:
            out.append(o)
    return out


def _total_municipio_golden(cno_golden: dict) -> int | None:
    for key in (
        "total_obras_em_curso_municipio",
        "total_obras_em_curso_municipio_fitness",
    ):
        if cno_golden.get(key) is not None:
            return int(cno_golden[key])
    return None


def _validate_metodo_classificacao(
    obras_list: list[dict],
    cno_golden: dict,
    issues: list[dict[str, Any]],
) -> None:
    """Valida metodo_classificacao nas obras e alerta keyword-only em bairros sensíveis."""
    revisar_bairros = {
        (b or "").strip().lower()
        for b in (cno_golden.get("revisar_keyword_em_bairros") or [])
    }
    warn_keyword_only = cno_golden.get("warn_keyword_only") is True

    for ref in cno_golden.get("obras_em_curso_bairro") or []:
        cno_id = ref.get("cno")
        if not cno_id:
            continue
        match = next((o for o in obras_list if o.get("cno") == cno_id), None)
        if not match:
            continue
        exp_metodo = ref.get("metodo_classificacao")
        permitidos = ref.get("metodos_permitidos")
        actual = match.get("metodo_classificacao")
        if exp_metodo and actual and actual != exp_metodo:
            issues.append(
                {
                    "field": f"obra.{cno_id}.metodo_classificacao",
                    "expected": exp_metodo,
                    "actual": actual,
                    "message": "Método de classificação divergente do golden",
                    "severity": "fail",
                }
            )
        if permitidos and actual and actual not in permitidos:
            issues.append(
                {
                    "field": f"obra.{cno_id}.metodo_classificacao",
                    "expected": permitidos,
                    "actual": actual,
                    "message": "Método fora da lista permitida no golden",
                    "severity": "fail",
                }
            )
        if actual and actual not in _METODOS_CLASSIFICACAO:
            issues.append(
                {
                    "field": f"obra.{cno_id}.metodo_classificacao",
                    "expected": sorted(_METODOS_CLASSIFICACAO),
                    "actual": actual,
                    "message": "metodo_classificacao desconhecido",
                    "severity": "fail",
                }
            )

    for obra in obras_list:
        metodo = obra.get("metodo_classificacao")
        if not metodo:
            continue
        if metodo not in _METODOS_CLASSIFICACAO:
            issues.append(
                {
                    "field": f"obra.{obra.get('cno')}.metodo_classificacao",
                    "expected": sorted(_METODOS_CLASSIFICACAO),
                    "actual": metodo,
                    "message": "metodo_classificacao inválido na lista municipal",
                    "severity": "fail",
                }
            )
        bairro = (obra.get("bairro_chave") or obra.get("bairro") or "").strip().lower()
        if metodo == "keyword" and (warn_keyword_only or (revisar_bairros and bairro in revisar_bairros)):
            issues.append(
                {
                    "field": f"obra.{obra.get('cno')}.metodo_classificacao",
                    "expected": "cnpj_cnae ou revisão manual",
                    "actual": metodo,
                    "message": (
                        f"Obra classificada só por keyword no bairro {bairro or '?'} — "
                        "revisar manualmente (SPE/construtora)"
                    ),
                    "severity": "warn",
                }
            )


def _validate_cruzamento_supplement(
    supplement_block: dict,
    cno_golden: dict,
    issues: list[dict[str, Any]],
) -> None:
    ent_golden = cno_golden.get("cruzamento_entrantes")
    if isinstance(ent_golden, dict):
        ent_actual = supplement_block.get("entrantes_municipio") or {}
        tol = int(ent_golden.get("tolerance", 3))
        for key in ("total", "com_match_cno", "sem_match_cno"):
            exp = ent_golden.get(key)
            if exp is None:
                continue
            act = ent_actual.get(key)
            if act is not None and abs(int(act) - int(exp)) > tol:
                issues.append(
                    {
                        "field": f"cruzamento.entrantes_municipio.{key}",
                        "expected": exp,
                        "actual": act,
                        "message": f"Contagem entrantes municipal divergente (tol ±{tol})",
                        "severity": "fail",
                    }
                )

    resumo_golden = cno_golden.get("cruzamento_resumo_match_supplemento") or cno_golden.get(
        "cruzamento_resumo_match"
    )
    if resumo_golden and supplement_block.get("resumo_match"):
        resumo = supplement_block.get("resumo_match") or {}
        tol = int(cno_golden.get("cruzamento_resumo_tolerance", 2))
        for key, expected in resumo_golden.items():
            actual = resumo.get(key)
            if actual is not None and abs(int(actual) - int(expected)) > tol:
                issues.append(
                    {
                        "field": f"cruzamento.resumo_match.{key}",
                        "expected": expected,
                        "actual": actual,
                        "message": "Contagem cruzamento CNPJ×CNO (supplement) divergente",
                        "severity": "fail",
                    }
                )


def evaluate_cno_consistency(
    report: dict,
    golden: dict,
    *,
    supplement: dict[str, Any] | None = None,
) -> EvalResult:
    cno_golden = golden.get("cno_validation")
    if not cno_golden:
        return EvalResult(status="SKIP", evaluator="cno", reason="Sem cno_validation no golden case")

    supplement_block = _get_cno_supplement(supplement)
    only_supplement = (
        cno_golden.get("required") is False
        and cno_golden.get("validar_supplemento") is True
        and bool(supplement_block)
    )
    if cno_golden.get("required") is False and not only_supplement:
        return EvalResult(status="SKIP", evaluator="cno", reason=cno_golden.get("nota") or "CNO opcional neste caso")

    issues: list[dict[str, Any]] = []
    obras_section = _get_obras_block(report)
    expected_status = cno_golden.get("expected_status", "ok")
    actual_status = obras_section.get("status") or ("ok" if obras_section.get("obras") else "")

    if not only_supplement:
        if expected_status == "ok" and actual_status != "ok":
            issues.append(
                {
                    "field": "obras_cno_em_curso.status",
                    "expected": "ok",
                    "actual": actual_status or "(vazio)",
                    "message": "Seção CNO ausente ou não configurada",
                    "severity": "fail",
                }
            )

    if only_supplement or actual_status == "ok" or obras_section.get("obras"):
        if not only_supplement:
            total_report = obras_section.get("total_obras_em_curso")
            if total_report is None:
                total_report = len(obras_section.get("obras") or [])

            total_golden = _total_municipio_golden(cno_golden)
            tol = int(cno_golden.get("obras_count_tolerance", 2))
            if total_golden is not None and abs(int(total_report) - int(total_golden)) > tol:
                issues.append(
                    {
                        "field": "total_obras_em_curso_municipio",
                        "expected": total_golden,
                        "actual": total_report,
                        "message": f"Divergência >{tol} obras em curso no município",
                        "severity": "fail",
                    }
                )

            bairro_chave = cno_golden.get("bairro_chave")
            obras_list = obras_section.get("obras") or []
            no_bairro = _obras_no_bairro(obras_list, bairro_chave)
            expected_bairro = cno_golden.get("total_obras_em_curso_bairro")
            if expected_bairro is None:
                expected_bairro = cno_golden.get("total_obras_em_curso_bairro_itai_pira")
            if expected_bairro is not None and len(no_bairro) != int(expected_bairro):
                issues.append(
                    {
                        "field": "total_obras_em_curso_bairro",
                        "expected": expected_bairro,
                        "actual": len(no_bairro),
                        "message": f"Obras em curso no bairro {bairro_chave or '?'}",
                        "severity": "fail",
                    }
                )

            expected_obras = cno_golden.get("obras_em_curso_bairro") or []
            for ref in expected_obras:
                cno_id = ref.get("cno")
                match = next((o for o in obras_list if o.get("cno") == cno_id), None)
                if not match:
                    issues.append(
                        {
                            "field": "obras_em_curso_bairro",
                            "expected": ref,
                            "actual": None,
                            "message": f"Obra CNO {cno_id} não encontrada na lista municipal",
                            "severity": "fail",
                        }
                    )
                    continue
                exp_area = ref.get("area_m2")
                if exp_area is not None and abs(float(match.get("area_m2") or 0) - float(exp_area)) > 1.0:
                    issues.append(
                        {
                            "field": f"obra.{cno_id}.area_m2",
                            "expected": exp_area,
                            "actual": match.get("area_m2"),
                            "message": "Área m² divergente",
                            "severity": "fail",
                        }
                    )

            _validate_metodo_classificacao(obras_list, cno_golden, issues)

            bench = obras_section.get("benchmark_tempo_obra") or {}
            if bench.get("status") == "ok":
                dpm2 = (bench.get("metricas") or {}).get("dias_por_m2_mediana")
                exp_dpm2 = cno_golden.get("benchmark_dias_por_m2_mediana")
                tol_dpm2 = float(cno_golden.get("benchmark_dias_por_m2_tolerance", 0.05))
                if dpm2 is not None and (dpm2 < _DPM2_MIN or dpm2 > _DPM2_MAX):
                    issues.append(
                        {
                            "field": "dias_por_m2_mediana",
                            "expected": f"{_DPM2_MIN}-{_DPM2_MAX}",
                            "actual": dpm2,
                            "message": "Benchmark dias/m² fora da faixa plausível",
                            "severity": "fail",
                        }
                    )
                if exp_dpm2 is not None and dpm2 is not None and abs(float(dpm2) - float(exp_dpm2)) > tol_dpm2:
                    issues.append(
                        {
                            "field": "dias_por_m2_mediana",
                            "expected": exp_dpm2,
                            "actual": dpm2,
                            "message": f"Mediana dias/m² fora da tolerância ±{tol_dpm2}",
                            "severity": "fail",
                        }
                    )

        cruz_golden = cno_golden.get("cruzamento_resumo_match")
        if cruz_golden and not supplement_block:
            cruz = _get_cruzamento(report)
            resumo = cruz.get("resumo_match") or {}
            for key, expected in cruz_golden.items():
                actual = resumo.get(key)
                if actual is not None and int(actual) != int(expected):
                    issues.append(
                        {
                            "field": f"cruzamento.resumo_match.{key}",
                            "expected": expected,
                            "actual": actual,
                            "message": "Contagem cruzamento CNPJ×CNO divergente",
                            "severity": "fail",
                        }
                    )

        ref_enc = cno_golden.get("obra_referencia_encerrada_bairro")
        if ref_enc and not supplement_block:
            cruz = _get_cruzamento(report)
            refs = cruz.get("obras_referencia") or []
            cno_id = ref_enc.get("cno")
            hit = next((r for r in refs if r.get("cno") == cno_id), None)
            if not hit:
                issues.append(
                    {
                        "field": "obra_referencia_encerrada_bairro",
                        "expected": ref_enc,
                        "actual": refs,
                        "message": "Obra encerrada de referência ausente em cruzamento_cno",
                        "severity": "fail",
                    }
                )
            elif ref_enc.get("area_m2") and abs(float(hit.get("area_m2") or 0) - float(ref_enc["area_m2"])) > 1.0:
                issues.append(
                    {
                        "field": "obra_referencia_encerrada_bairro.area_m2",
                        "expected": ref_enc["area_m2"],
                        "actual": hit.get("area_m2"),
                        "message": "Área obra encerrada divergente",
                        "severity": "fail",
                    }
                )

    if supplement_block:
        _validate_cruzamento_supplement(supplement_block, cno_golden, issues)

    fails = [i for i in issues if i.get("severity", "fail") != "warn"]
    warns = [i for i in issues if i.get("severity") == "warn"]

    if not issues:
        return EvalResult(status="PASS", evaluator="cno")
    if fails:
        status: str = "WARN" if len(fails) <= 2 else "FAIL"
    elif warns:
        status = "WARN"
    else:
        status = "PASS"
    return EvalResult(status=status, evaluator="cno", issues=issues)


class CNOConsistencyEval:
    """Wrapper compatível com runner futuro."""

    def evaluate(
        self,
        report: dict,
        golden: dict,
        *,
        supplement: dict[str, Any] | None = None,
    ) -> EvalResult:
        return evaluate_cno_consistency(report, golden, supplement=supplement)
