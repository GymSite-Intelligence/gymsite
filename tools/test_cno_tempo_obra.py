"""Benchmark tempo obra CNO — obras encerradas."""
from pathlib import Path

from tools.cno_fitness_tools import (
    calcular_benchmark_tempo_obra_cno,
    estimar_previsao_encerramento_obra,
)


def test_benchmark_fortaleza():
    cno = Path(r"C:\Users\marce\Downloads\cno_extract")
    if not cno.is_dir():
        return
    b = calcular_benchmark_tempo_obra_cno(cno_dir=cno)
    assert b["status"] in ("ok", "amostra_insuficiente")
    if b["status"] == "ok":
        assert b["amostra_valida"] >= 1
        assert b["metricas"]["dias_por_m2_mediana"] > 0
        prev = estimar_previsao_encerramento_obra("2023-01-01", 1200.0, b)
        assert prev and prev.get("previsao_encerramento_estimada")


if __name__ == "__main__":
    test_benchmark_fortaleza()
    print("ok")
