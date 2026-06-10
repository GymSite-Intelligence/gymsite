"""
Script de benchmark de frete — cálculo de custos de transporte com dados reais da ANTT.

Gera relatório estruturado com:
- Distância rodoviária entre fornecedores e destinos
- Custo estimado por km (baseado em tarifas ANTT 2024)
- Comparativo entre fornecedores por rota
- Histórico de benchmarks com timestamp

Dados ANTT 2024:
- RNDC (Registro Nacional de Transportadores de Cargas)
- Tabela de fretes mínimos por tipo de carga
- Tarifas médias por km rodado

Fonte: https://antt.gov.br/transporte-de-cargas/rndc
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Adiciona raiz do projeto ao path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.distance_matrix_tools import (
    calcular_distancia_rodoviaria,
    distancia_fornecedor_para_cidade,
    FORNECEDORES_ORIGEM,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "frete_benchmark.log", encoding="utf-8"),
    ],
)

# ---------------------------------------------------------------------------
# Tarifas ANTT 2024 (valores médios por km)
# Fonte: https://antt.gov.br/transporte-de-cargas/rndc/tabela-de-fretes
# ---------------------------------------------------------------------------
TARIFAS_ANTT_2024: dict[str, float] = {
    "carga_geral": 0.85,        # R$/km — carga geral (equipamentos fitness)
    "fracionado": 1.20,         # R$/km — carga fracionada (kits menores)
    "lotacao": 0.65,            # R$/km — carga em lotação (grandes volumes)
    "expresso": 1.50,           # R$/km — transporte expresso
}

# ---------------------------------------------------------------------------
# Destinos comuns para benchmark
# ---------------------------------------------------------------------------
DESTINOS_BENCHMARK: dict[str, tuple[float, float]] = {
    "fortaleza_ce": (-3.7172, -38.5433),
    "recife_pe": (-8.0476, -34.8770),
    "salvador_ba": (-12.9714, -38.5124),
    "brasilia_df": (-15.7942, -47.8822),
    "belém_pa": (-1.4558, -48.5044),
    "manaus_am": (-3.1190, -60.0217),
    "porto_alegre_rs": (-30.0346, -51.2177),
    "curitiba_pr": (-25.4284, -49.2733),
    "niteroi_rj": (-22.8834, -43.1034),
    "goiania_go": (-16.6864, -49.2643),
}

# ---------------------------------------------------------------------------
# Funções de cálculo
# ---------------------------------------------------------------------------

def calcular_custo_frete(
    distancia_km: float,
    tipo_carga: str = "carga_geral",
    tarifa_por_km: Optional[float] = None,
) -> dict:
    """
    Calcula custo estimado de frete baseado em distância e tarifa ANTT.

    Args:
        distancia_km: distância rodoviária em km.
        tipo_carga: tipo de carga (chave em TARIFAS_ANTT_2024).
        tarifa_por_km: sobrescreve tarifa padrão se fornecido.

    Returns:
        {
            "distancia_km": float,
            "tipo_carga": str,
            "tarifa_por_km": float,
            "custo_estimado": float,
            "custo_por_aluno": float,  # estimado para 50 alunos
            "fonte_tarifa": str,
        }
    """
    if distancia_km <= 0:
        raise ValueError("distancia_km deve ser positiva")

    if tarifa_por_km is not None:
        tarifa = tarifa_por_km
        fonte = "customizada"
    else:
        tarifa = TARIFAS_ANTT_2024.get(tipo_carga)
        if tarifa is None:
            raise ValueError(
                f"tipo_carga '{tipo_carga}' inválido. "
                f"Opções: {list(TARIFAS_ANTT_2024.keys())}"
            )
        fonte = f"ANTT_2024_{tipo_carga}"

    custo = distancia_km * tarifa

    return {
        "distancia_km": distancia_km,
        "tipo_carga": tipo_carga,
        "tarifa_por_km": tarifa,
        "custo_estimado": round(custo, 2),
        "custo_por_aluno": round(custo / 50, 2),
        "fonte_tarifa": fonte,
    }


def benchmark_fornecedor_destino(
    fornecedor_key: str,
    destino_key: str,
    destino_lat: float,
    destino_lng: float,
    tipo_carga: str = "carga_geral",
) -> dict:
    """
    Executa benchmark completo para rota fornecedor -> destino.

    Returns:
        {
            "fornecedor": str,
            "destino": str,
            "coordenadas_origem": tuple,
            "coordenadas_destino": tuple,
            "distancia": dict | None,
            "custo": dict | None,
            "timestamp": str,
            "status": "sucesso" | "falha_distancia" | "falha_api",
            "erro": str | None,
        }
    """
    origem = FORNECEDORES_ORIGEM.get(fornecedor_key, FORNECEDORES_ORIGEM["default"])

    resultado = {
        "fornecedor": fornecedor_key,
        "destino": destino_key,
        "coordenadas_origem": list(origem),
        "coordenadas_destino": [destino_lat, destino_lng],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pendente",
        "erro": None,
    }

    # 1. Calcula distância
    try:
        distancia = distancia_fornecedor_para_cidade(
            fornecedor_key, destino_lat, destino_lng
        )
        resultado["distancia"] = distancia
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao calcular distância: %s", exc)
        resultado["status"] = "falha_distancia"
        resultado["erro"] = str(exc)
        resultado["custo"] = None
        return resultado

    # 2. Calcula custo se distância disponível
    if distancia and distancia.get("distancia_km"):
        try:
            custo = calcular_custo_frete(
                distancia_km=distancia["distancia_km"],
                tipo_carga=tipo_carga,
            )
            resultado["custo"] = custo
            resultado["status"] = "sucesso"
        except Exception as exc:  # noqa: BLE001
            logger.error("Erro ao calcular custo: %s", exc)
            resultado["status"] = "falha_api"
            resultado["erro"] = str(exc)
            resultado["custo"] = None
    else:
        resultado["status"] = "falha_distancia"
        resultado["erro"] = "Distância não disponível (API ou cache)"
        resultado["custo"] = None

    return resultado


def rodar_benchmark_completo(
    fornecedores: Optional[list[str]] = None,
    destinos: Optional[list[str]] = None,
    tipo_carga: str = "carga_geral",
    output_path: Optional[str] = None,
) -> dict:
    """
    Roda benchmark completo para todos os pares fornecedor/destino.

    Args:
        fornecedores: lista de chaves de fornecedores (default: todos).
        destinos: lista de chaves de destinos (default: todos em DESTINOS_BENCHMARK).
        tipo_carga: tipo de carga para cálculo de tarifa.
        output_path: caminho para salvar resultado JSON.

    Returns:
        {
            "meta": {
                "data_execucao": str,
                "fornecedores": list,
                "destinos": list,
                "tipo_carga": str,
                "total_rotas": int,
                "rotas_sucesso": int,
                "rotas_falha": int,
            },
            "resultados": [dict, ...],
            "resumo_por_fornecedor": {fornecedor: {custo_medio, distancia_media, ...}},
            "resumo_por_destino": {destino: {custo_medio, distancia_media, ...}},
        }
    """
    fornecedores = fornecedores or list(FORNECEDORES_ORIGEM.keys())
    destinos = destinos or list(DESTINOS_BENCHMARK.keys())

    resultados = []
    sucesso = 0
    falha = 0

    logger.info(
        "Iniciando benchmark: %d fornecedores x %d destinos = %d rotas",
        len(fornecedores),
        len(destinos),
        len(fornecedores) * len(destinos),
    )

    for fornecedor_key in fornecedores:
        for destino_key in destinos:
            dest_lat, dest_lng = DESTINOS_BENCHMARK[destino_key]

            resultado = benchmark_fornecedor_destino(
                fornecedor_key=fornecedor_key,
                destino_key=destino_key,
                destino_lat=dest_lat,
                destino_lng=dest_lng,
                tipo_carga=tipo_carga,
            )
            resultados.append(resultado)

            if resultado["status"] == "sucesso":
                sucesso += 1
            else:
                falha += 1

    # Resumos por fornecedor
    resumo_fornecedor: dict[str, dict] = {}
    for fornecedor_key in fornecedores:
        rota_fornecedor = [
            r for r in resultados if r["fornecedor"] == fornecedor_key
        ]
        custos = [
            r["custo"]["custo_estimado"]
            for r in rota_fornecedor
            if r.get("custo")
        ]
        distancias = [
            r["distancia"]["distancia_km"]
            for r in rota_fornecedor
            if r.get("distancia")
        ]

        resumo_fornecedor[fornecedor_key] = {
            "total_rotas": len(rota_fornecedor),
            "rotas_sucesso": len(custos),
            "custo_medio": round(sum(custos) / len(custos), 2) if custos else None,
            "custo_min": round(min(custos), 2) if custos else None,
            "custo_max": round(max(custos), 2) if custos else None,
            "distancia_media_km": round(sum(distancias) / len(distancias), 1) if distancias else None,
        }

    # Resumos por destino
    resumo_destino: dict[str, dict] = {}
    for destino_key in destinos:
        rota_destino = [
            r for r in resultados if r["destino"] == destino_key
        ]
        custos = [
            r["custo"]["custo_estimado"]
            for r in rota_destino
            if r.get("custo")
        ]
        distancias = [
            r["distancia"]["distancia_km"]
            for r in rota_destino
            if r.get("distancia")
        ]

        resumo_destino[destino_key] = {
            "total_rotas": len(rota_destino),
            "rotas_sucesso": len(custos),
            "custo_medio": round(sum(custos) / len(custos), 2) if custos else None,
            "custo_min": round(min(custos), 2) if custos else None,
            "custo_max": round(max(custos), 2) if custos else None,
            "distancia_media_km": round(sum(distancias) / len(distancias), 1) if distancias else None,
        }

    benchmark_completo = {
        "meta": {
            "data_execucao": datetime.now(timezone.utc).isoformat(),
            "fornecedores": fornecedores,
            "destinos": destinos,
            "tipo_carga": tipo_carga,
            "total_rotas": len(resultados),
            "rotas_sucesso": sucesso,
            "rotas_falha": falha,
        },
        "resultados": resultados,
        "resumo_por_fornecedor": resumo_fornecedor,
        "resumo_por_destino": resumo_destino,
    }

    # Salva resultado
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(benchmark_completo, f, ensure_ascii=False, indent=2)
        logger.info("Benchmark salvo em: %s", output_file)

    logger.info(
        "Benchmark concluído: %d sucesso, %d falhas de %d rotas",
        sucesso,
        falha,
        len(resultados),
    )

    return benchmark_completo


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    """Executa benchmark via linha de comando."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark de frete com dados ANTT 2024"
    )
    parser.add_argument(
        "--fornecedores",
        nargs="*",
        default=None,
        help="Fornecedores específicos (default: todos)",
    )
    parser.add_argument(
        "--destinos",
        nargs="*",
        default=None,
        help="Destinos específicos (default: todos)",
    )
    parser.add_argument(
        "--tipo-carga",
        default="carga_geral",
        choices=list(TARIFAS_ANTT_2024.keys()),
        help="Tipo de carga para tarifa",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data" / "frete_benchmark.json"),
        help="Caminho para salvar resultado JSON",
    )

    args = parser.parse_args()

    resultado = rodar_benchmark_completo(
        fornecedores=args.fornecedores,
        destinos=args.destinos,
        tipo_carga=args.tipo_carga,
        output_path=args.output,
    )

    # Imprime resumo no console
    print("\n" + "=" * 60)
    print("BENCHMARK DE FRETE — RESUMO")
    print("=" * 60)
    print(f"Data: {resultado['meta']['data_execucao']}")
    print(f"Total de rotas: {resultado['meta']['total_rotas']}")
    print(f"Sucesso: {resultado['meta']['rotas_sucesso']}")
    print(f"Falhas: {resultado['meta']['rotas_falha']}")
    print(f"Arquivo: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
