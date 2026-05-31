"""Smoke test local da integração A9 (sem rodar LLM)."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.a9_positioning_strategist import _parse_json_from_text, _patch_relatorio_json
from gymsite_intelligence.agent import pipeline
from pdf.adapters import relatorio_from_nested_json
from pdf import generate_relatorio_pdf, LayoutId
from db.supabase_writer import write_posicionamento_failsafe


def main() -> None:
    sample = (
        '```json\n'
        '{"veredito_posicionamento": "OCEANO_AZUL", '
        '"framework_errc": {"eliminar": ["Guerra de preço"], "reduzir": [], "aumentar": [], "criar": []}, '
        '"gaps_identificados": [{"gap": "Nutrição", "potencial_ticket": "R$ 250"}], '
        '"recomendacao_ticket": {"ticket_recomendado": 249, "ticket_minimo": 199, "ticket_maximo": 299}, '
        '"justificativa_veredito": "Teste", "markdown": "# Posicionamento"}\n'
        '```'
    )
    parsed = _parse_json_from_text(sample)
    assert parsed["veredito_posicionamento"] == "OCEANO_AZUL"
    print("[ok] parse JSON")

    names = [a.name for a in pipeline.sub_agents]
    assert "PositioningStrategist" in names
    print("[ok] pipeline:", names)

    src = ROOT / "metrics" / "relatorios" / "rpt_1778504133.json"
    if src.is_file():
        tmp_id = "rpt_test_a9_patch"
        tmp = ROOT / "metrics" / "relatorios" / f"{tmp_id}.json"
        shutil.copy(src, tmp)
        _patch_relatorio_json(tmp_id, parsed)
        rel = json.loads(tmp.read_text(encoding="utf-8"))
        assert rel["output_consolidado"]["posicionamento_estrategico"]["veredito_posicionamento"] == "OCEANO_AZUL"
        tmp.unlink()
        print("[ok] patch JSON local")

        rel["output_consolidado"]["posicionamento_estrategico"] = parsed
        model = relatorio_from_nested_json(rel)
        assert model.posicionamento_estrategico is not None
        pdf = generate_relatorio_pdf(model, layout=LayoutId.CLASSIC)
        assert len(pdf) > 5000
        print(f"[ok] PDF gerado ({len(pdf)} bytes)")

    # Supabase no-op sem credenciais
    assert write_posicionamento_failsafe("00000000-0000-0000-0000-000000000001", parsed) in (True, False)
    print("[ok] write_posicionamento_failsafe (no crash)")

    print("\nTodos os smoke tests passaram.")


if __name__ == "__main__":
    main()
