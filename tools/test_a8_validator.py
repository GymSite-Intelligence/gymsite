#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


async def test_aprovado_sem_candidatos():
    from agents.a8_validator import A8ValidadorCruzado

    v = A8ValidadorCruzado()
    out = await v.validar(
        "# Veredito: APROVADO\n\nScore bairro 8.5",
        {},
        relatorio={
            "output_consolidado": {
                "veredito": "APROVADO",
                "score_bairro": 8.5,
                "total_concorrentes_analisados": 0,
                "top_3_candidatos": [],
            }
        },
    )
    assert out["revisar_manual"] or any(
        a.get("severidade") == "CRITICO" for a in out["alertas"]
    )
    print("test_aprovado_sem_candidatos ok", out["status_validacao"])


if __name__ == "__main__":
    asyncio.run(test_aprovado_sem_candidatos())
