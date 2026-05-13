"""
Calculadora ANTT — pisos mínimos de frete (Resolução 6.034/2024).

A ANTT publica anualmente pisos mínimos pra transporte rodoviário de carga
no Brasil. Os valores variam por:
- Tipo de carga (geral, granel, frigorificado, perigoso, lotação, etc.)
- Quantidade de eixos do veículo (2, 3, 4, 5, 6, 7, 9)
- Distância da viagem (R$/km carregado + R$/km vazio)
- Componente fixo (carga/descarga)

Para equipamentos fitness (carga geral, peso 5-25t):
- Caminhão truck (4-5 eixos) é o padrão pra kits M-G
- Bitrem/Rodotrem (6-9 eixos) só pra kits GG (academias grandes/franquias)

⚠️ ATENÇÃO LEGAL: a Resolução ANTT é PISO MÍNIMO. Valores reais de mercado
podem ser SUPERIORES (mas nunca inferiores). Brokers de frete (Vectra Cargo,
JadLog, etc.) cobram margem sobre o piso ANTT.

Atualizar quando ANTT publicar nova resolução (geralmente jan/fev anual).
"""
from __future__ import annotations

from typing import Literal, Optional

TipoCarga = Literal[
    "geral",
    "granel_solido",
    "granel_liquido",
    "frigorificada",
    "perigosa",
    "lotacao",
    "valores",
]

# Tabela ANTT 6.034/2024 — pisos mínimos R$ por km.
# Estrutura: TABELA[tipo_carga][eixos] = (R$/km carregado, R$/km vazio, R$ carga/descarga)
# Componente fixo de carga/descarga aplicado uma vez por viagem.
TABELA_ANTT_2024: dict[str, dict[int, tuple[float, float, float]]] = {
    "geral": {
        2: (3.85, 2.50, 254.13),  # Toco / VUC
        3: (4.74, 3.07, 254.13),  # Truck 3 eixos
        4: (5.93, 3.85, 254.13),  # Truck 4 eixos
        5: (6.72, 4.36, 254.13),  # Carreta simples
        6: (7.39, 4.79, 254.13),  # Bitrem
        7: (7.95, 5.16, 254.13),  # Rodotrem
        9: (9.62, 6.24, 254.13),  # Bitrem articulado
    },
    "granel_solido": {
        2: (3.74, 2.43, 178.94),
        3: (4.61, 2.99, 178.94),
        4: (5.78, 3.75, 178.94),
        5: (6.55, 4.25, 178.94),
        6: (7.21, 4.68, 178.94),
        7: (7.76, 5.04, 178.94),
        9: (9.39, 6.10, 178.94),
    },
    "frigorificada": {
        2: (4.42, 2.87, 286.49),
        3: (5.45, 3.54, 286.49),
        4: (6.82, 4.43, 286.49),
        5: (7.73, 5.02, 286.49),
        6: (8.50, 5.52, 286.49),
        7: (9.15, 5.94, 286.49),
        9: (11.07, 7.18, 286.49),
    },
    "perigosa": {
        2: (4.65, 3.02, 286.49),
        3: (5.73, 3.72, 286.49),
        4: (7.18, 4.66, 286.49),
        5: (8.13, 5.28, 286.49),
        6: (8.94, 5.80, 286.49),
        7: (9.62, 6.24, 286.49),
        9: (11.64, 7.55, 286.49),
    },
    "lotacao": {
        # Lotação = veículo dedicado, mesmas R$/km da geral mas sem componente carga/descarga
        2: (3.85, 2.50, 0.0),
        3: (4.74, 3.07, 0.0),
        4: (5.93, 3.85, 0.0),
        5: (6.72, 4.36, 0.0),
        6: (7.39, 4.79, 0.0),
        7: (7.95, 5.16, 0.0),
        9: (9.62, 6.24, 0.0),
    },
}


def calcular_piso_antt(
    distancia_km: float,
    eixos: int = 5,
    tipo_carga: TipoCarga = "geral",
    retorno_vazio: bool = True,
) -> dict:
    """
    Calcula piso mínimo de frete conforme Resolução ANTT 6.034/2024.

    Args:
        distancia_km: distância em km da origem ao destino
        eixos: quantidade de eixos (2, 3, 4, 5, 6, 7, 9). Default 5 = carreta simples.
        tipo_carga: ver type literal TipoCarga (default "geral").
        retorno_vazio: se True, soma R$/km vazio na volta (one-way).

    Returns:
        Dict com componentes do cálculo + total + fonte.
    """
    tabela = TABELA_ANTT_2024.get(tipo_carga, TABELA_ANTT_2024["geral"])
    # Snap eixos ao mais próximo disponível
    eixos_disp = sorted(tabela.keys())
    if eixos not in eixos_disp:
        eixos = min(eixos_disp, key=lambda x: abs(x - eixos))

    cc, cv, carga_desc = tabela[eixos]
    valor_ida = cc * distancia_km
    valor_volta = (cv * distancia_km) if retorno_vazio else 0.0
    total = valor_ida + valor_volta + carga_desc

    return {
        "piso_total": round(total, 2),
        "ida_carregado": round(valor_ida, 2),
        "volta_vazia": round(valor_volta, 2),
        "carga_descarga": round(carga_desc, 2),
        "distancia_km": distancia_km,
        "eixos": eixos,
        "tipo_carga": tipo_carga,
        "retorno_vazio": retorno_vazio,
        "rkm_carregado": cc,
        "rkm_vazio": cv,
        "fonte": "Piso mínimo Resolução ANTT 6.034/2024",
        "aviso": (
            "Piso MÍNIMO legal. Brokers de frete fitness (Vectra Cargo, "
            "JadLog) cobram margem sobre este valor — espere 15-30% acima."
        ),
    }


# ─────────────────────────────────────────────────────────────────────
# Estimativa pra equipamentos fitness
# ─────────────────────────────────────────────────────────────────────

# Distâncias aproximadas das origens dos principais fornecedores fitness
# até capitais brasileiras. Pré-calculado pra evitar chamada de Geocoding API
# no cálculo. Valores em km (Google Maps rota terrestre).
#
# Origens:
# - Movement: Cotia/SP (sede + fábrica)
# - Athletic Works: Caxias do Sul/RS
# - Life Fitness BR: Pinhais/PR (Curitiba metro)
# - RHS / Movement extras: Rio Claro/SP
# - Eleiko / Rogue / Concept2: Santos/SP (porto de importação)
#
# Pra simplificar, usamos "São Paulo capital" como proxy de origem
# (mediana logística — Cotia, Rio Claro e Santos ficam a < 100km).
DISTANCIA_SP_CAPITAL_KM: dict[str, float] = {
    "AC": 3800,  # Rio Branco
    "AL": 2200,  # Maceió
    "AP": 4400,  # Macapá (parte rodoviária + balsa)
    "AM": 4000,  # Manaus (via Porto Velho)
    "BA": 1960,  # Salvador
    "CE": 2900,  # Fortaleza
    "DF": 1015,  # Brasília
    "ES": 880,   # Vitória
    "GO": 925,   # Goiânia
    "MA": 2840,  # São Luís
    "MT": 1620,  # Cuiabá
    "MS": 1010,  # Campo Grande
    "MG": 580,   # Belo Horizonte
    "PA": 2940,  # Belém
    "PB": 2520,  # João Pessoa
    "PR": 408,   # Curitiba
    "PE": 2660,  # Recife
    "PI": 2720,  # Teresina
    "RJ": 430,   # Rio de Janeiro
    "RN": 2680,  # Natal
    "RS": 1110,  # Porto Alegre
    "RO": 2400,  # Porto Velho
    "RR": 4540,  # Boa Vista
    "SC": 700,   # Florianópolis
    "SP": 0,     # São Paulo (origem)
    "SE": 2100,  # Aracaju
    "TO": 1780,  # Palmas
}


def estimar_distancia_sp_para_uf(uf: str) -> float:
    """Distância aproximada São Paulo capital → capital da UF (rodoviária)."""
    return DISTANCIA_SP_CAPITAL_KM.get(uf.upper(), 1500.0)


def estimar_eixos_por_kit_valor(valor_kit: float) -> int:
    """
    Estima quantos eixos o caminhão precisa baseado no valor do kit.

    Regra empírica (peso ≈ valor):
    - Kit < R$ 200k  → truck 4 eixos (volume médio)
    - Kit < R$ 800k  → carreta 5 eixos (padrão academia M)
    - Kit < R$ 2M    → bitrem 6 eixos (academia G ou multi-cargo)
    - Kit > R$ 2M    → rodotrem 7-9 eixos (GG / multi-unidade)
    """
    if valor_kit < 200_000:
        return 4
    if valor_kit < 800_000:
        return 5
    if valor_kit < 2_000_000:
        return 6
    return 7


def calcular_frete_kit_equipamentos(
    valor_kit: float,
    uf_destino: str,
    distancia_km: float | None = None,
    destino_lat: float | None = None,
    destino_lng: float | None = None,
    fornecedor_principal: str = "default",
) -> dict:
    """
    Estima frete do kit de equipamentos do fornecedor até a cidade alvo.

    Resolução de distância (3 níveis):
    1. `distancia_km` fornecido pelo chamador → usa direto.
    2. `destino_lat/lng` fornecidos → Google Distance Matrix (real, rodoviário).
    3. Senão → fallback `estimar_distancia_sp_para_uf(uf_destino)` (dict fixo).

    Args:
        valor_kit: valor total do kit (usado pra estimar eixos)
        uf_destino: sigla da UF (ex: "CE", "SP")
        distancia_km: override explícito (km)
        destino_lat, destino_lng: ativa Google Distance Matrix se fornecidos
        fornecedor_principal: chave em FORNECEDORES_ORIGEM (ver
            distance_matrix_tools). Default "default" = São Paulo capital.

    Returns:
        Dict com valor estimado de frete + breakdown ANTT + fonte_distancia.
    """
    fonte_distancia: str = "estimativa_por_uf"

    if distancia_km is not None:
        fonte_distancia = "informada_pelo_chamador"
    elif destino_lat is not None and destino_lng is not None:
        try:
            from tools.distance_matrix_tools import distancia_fornecedor_para_cidade
            res = distancia_fornecedor_para_cidade(
                fornecedor_principal, destino_lat, destino_lng
            )
            if res:
                distancia_km = res["distancia_km"]
                fonte_distancia = res.get("fonte") or "google_distance_matrix"
        except Exception as _exc:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "frete: fallback distancia (DM falhou) -- %s", _exc
            )

    if distancia_km is None:
        distancia_km = estimar_distancia_sp_para_uf(uf_destino)

    eixos = estimar_eixos_por_kit_valor(valor_kit)

    piso = calcular_piso_antt(
        distancia_km=distancia_km,
        eixos=eixos,
        tipo_carga="geral",
        retorno_vazio=True,
    )

    # Aplica margem típica de broker fitness (~20% sobre o piso)
    valor_estimado_real = piso["piso_total"] * 1.20

    return {
        "frete_piso_antt": piso["piso_total"],
        "frete_estimado_real": round(valor_estimado_real, 2),
        "margem_broker_pct": 0.20,
        "distancia_km": distancia_km,
        "fonte_distancia": fonte_distancia,
        "fornecedor_principal": fornecedor_principal,
        "eixos": eixos,
        "tipo_veiculo": _label_veiculo(eixos),
        "pct_do_capex_equipamentos": round((valor_estimado_real / valor_kit) * 100, 1)
            if valor_kit > 0 else 0,
        "breakdown_antt": piso,
        "fonte": "Resolução ANTT 6.034/2024 + margem broker fitness",
        "aviso": (
            "Frete estimado: piso ANTT + 20% margem típica de broker. "
            "Cotação real pode variar conforme volume, sazonalidade e roteiro. "
            "Para cotação executiva, consultar Vectra Cargo (especializada em "
            "frete fitness no Brasil)."
        ),
    }


def _label_veiculo(eixos: int) -> str:
    return {
        2: "VUC (toco)",
        3: "Truck 3 eixos",
        4: "Truck 4 eixos",
        5: "Carreta simples (5 eixos)",
        6: "Bitrem (6 eixos)",
        7: "Rodotrem (7 eixos)",
        9: "Bitrem articulado (9 eixos)",
    }.get(eixos, f"{eixos} eixos")
