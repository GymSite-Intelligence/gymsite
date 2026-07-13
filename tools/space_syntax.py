"""
Space Syntax - Angular Segment Analysis
Módulo de cálculo de fluxo natural baseado em morfologia urbana.

Implementa a lógica de Sintaxe Espacial com Custo Angular para previsão
de fluxo de pedestres e veículos no projeto GymSite Intelligence.

Base teórica:
    - Hillier, B. & Hanson, J. (1984). The Social Logic of Space
    - Hillier, B. (1996). Space is the Machine
    - Turner, A. (2007). From axial to road-centre lines: a new familiarity

Fórmula matemática:
    Cost(P) = sum(theta(e_i, e_{i+1})) para i=1 ate k-1
    onde theta é o ângulo de deflexão entre segmentos consecutivos
"""

from __future__ import annotations

import json
import logging
import math
import time
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
from shapely.geometry import LineString, Point, mapping

# Configura osmnx
ox.settings.use_cache = True
ox.settings.log_console = False
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger("space_syntax")


# =============================================================================
# CONSTANTES E CONFIGURAÇÕES
# =============================================================================

EARTH_RADIUS_METERS = 6_371_000
DEFAULT_RADIUS_METERS = 2_000
DEFAULT_NETWORK_TYPE = "walk"
ATTRACTIVENESS_ALPHA = 0.33
ATTRACTIVENESS_BETA = 0.33
ATTRACTIVENESS_GAMMA = 0.34
GOOGLE_PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

OVERPASS_POI_TAGS: Dict[str, Tuple[str, float, str]] = {
    "supermarket": ("shop", 1.0, "emp"),
    "shopping_mall": ("shop", 1.5, "emp"),
    "gym": ("leisure", 0.8, "emp"),
    "school": ("amenity", 0.7, "emp"),
    "university": ("amenity", 0.9, "emp"),
    "hospital": ("amenity", 0.8, "emp"),
    "restaurant": ("amenity", 0.7, "emp"),
    "office": ("office", 0.8, "emp"),
    "bus_station": ("amenity", 0.9, "transp"),
    "subway_station": ("railway", 1.2, "transp"),
}

# Categorias de POIs relevantes para academias ( pesos de atração )
POI_CATEGORIES = {
    "supermarket": 1.0,
    "shopping_mall": 1.5,
    "gym": 0.8,
    "school": 0.7,
    "university": 0.9,
    "hospital": 0.8,
    "pharmacy": 0.6,
    "restaurant": 0.7,
    "cafe": 0.6,
    "bus_station": 0.9,
    "subway_station": 1.2,
    "bank": 0.5,
    "office": 0.8,
    "residential": 0.4,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FlowResult:
    """Resultado do cálculo de fluxo para uma aresta (segmento de rua)."""
    edge_id: Tuple
    geometry: LineString
    flow_score: float
    choice_score: float
    integration_score: float
    poi_density: float
    length_meters: float
    angular_cost: float


@dataclass
class AnalysisConfig:
    """Configuração para análise de sintaxe espacial."""
    radius_meters: int = DEFAULT_RADIUS_METERS
    network_type: str = DEFAULT_NETWORK_TYPE
    poi_radius_meters: int = 1_000
    max_pois: int = 60
    angular_weight: float = 1.0
    poi_weight: float = 0.5
    normalization_method: str = "minmax"
    include_walk: bool = True
    include_drive: bool = False
    alpha_pop: float = ATTRACTIVENESS_ALPHA
    beta_emp: float = ATTRACTIVENESS_BETA
    gamma_transp: float = ATTRACTIVENESS_GAMMA


# =============================================================================
# CACHE EM MEMÓRIA
# =============================================================================

class GraphCache:
    """Cache simples em memória para grafos OSM por região."""

    def __init__(self, ttl_seconds: int = 3_600):
        self._cache: Dict[str, Dict] = {}
        self._timestamps: Dict[str, float] = {}
        self._ttl = ttl_seconds

    def _key(self, lat: float, lng: float, radius: int, network_type: str) -> str:
        """Gera chave única para o cache."""
        return f"{lat:.5f}_{lng:.5f}_{radius}_{network_type}"

    def get(
        self, lat: float, lng: float, radius: int, network_type: str
    ) -> Optional[nx.MultiDiGraph]:
        """Recupera grafo do cache se válido."""
        key = self._key(lat, lng, radius, network_type)
        if key in self._cache:
            if time.time() - self._timestamps[key] < self._ttl:
                logger.info(f"Cache hit para região: {key}")
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(
        self, lat: float, lng: float, radius: int, network_type: str, graph: nx.MultiDiGraph
    ) -> None:
        """Armazena grafo no cache."""
        key = self._key(lat, lng, radius, network_type)
        self._cache[key] = graph
        self._timestamps[key] = time.time()
        logger.info(f"Grafo armazenado no cache: {key}")

    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()
        self._timestamps.clear()


# Instância global do cache
_graph_cache = GraphCache()


# =============================================================================
# FUNÇÕES DE EXTRAÇÃO DE GRAFO (OSMnx)
# =============================================================================

def get_base_graph(
    lat: float,
    lng: float,
    radius: int = DEFAULT_RADIUS_METERS,
    network_type: str = DEFAULT_NETWORK_TYPE,
    use_cache: bool = True,
) -> nx.MultiDiGraph:
    """
    Extrai o grafo de ruas do OpenStreetMap para uma região circular.

    Args:
        lat: Latitude do ponto central
        lng: Longitude do ponto central
        radius: Raio em metros para extração
        network_type: Tipo de rede (drive, walk, all_private, etc.)
        use_cache: Se True, utiliza cache em memória

    Returns:
        Grafo direcionado do NetworkX com atributos geométricos

    Raises:
        ValueError: Se não for possível extrair o grafo
    """
    # Tenta recuperar do cache
    if use_cache:
        cached = _graph_cache.get(lat, lng, radius, network_type)
        if cached is not None:
            return cached

    try:
        logger.info(f"Extraindo grafo OSM: ({lat}, {lng}) raio={radius}m")
        start_time = time.time()

        # Extrai grafo combinado (drive + walk se necessário)
        G = ox.graph_from_point(
            center_point=(lat, lng),
            dist=radius,
            network_type=network_type,
            simplify=True,
            retain_all=False,
        )

        # Projeta para CRS local (UTM) para medidas precisas em metros
        G = ox.project_graph(G)

        # Adiciona atributos de comprimento se não existirem
        G = ox.distance.add_edge_lengths(G)

        elapsed = time.time() - start_time
        logger.info(
            f"Grafo extraído: {G.number_of_nodes()} nós, "
            f"{G.number_of_edges()} arestas em {elapsed:.2f}s"
        )

        # Armazena no cache
        if use_cache:
            _graph_cache.set(lat, lng, radius, network_type, G)

        return G

    except Exception as e:
        logger.error(f"Falha na extração do grafo OSM: {e}")
        raise ValueError(f"Não foi possível extrair o grafo para ({lat}, {lng}): {e}")


def graph_to_undirected(G: nx.MultiDiGraph) -> nx.Graph:
    """
    Converte grafo direcionado para não-direcionado para análise de segmentos.

    Args:
        G: Grafo direcionado do OSMnx

    Returns:
        Grafo não-direcionado simples
    """
    # Converte para não-direcionado, mantendo atributos
    G_undirected = nx.Graph()

    for u, v, data in G.edges(data=True):
        if not G_undirected.has_edge(u, v):
            G_undirected.add_edge(u, v, **data)

    # Copia atributos dos nós
    for node, data in G.nodes(data=True):
        if node in G_undirected:
            G_undirected.nodes[node].update(data)

    return G_undirected


# =============================================================================
# CONSTRUÇÃO DO GRAFO DUAL (SEGMENT GRAPH)
# =============================================================================

def calculate_bearing(
    point1: Tuple[float, float], point2: Tuple[float, float]
) -> float:
    """
    Calcula o azimute (direção) entre dois pontos em graus.

    Args:
        point1: (x, y) coordenadas do ponto inicial
        point2: (x, y) coordenadas do ponto final

    Returns:
        Azimute em graus (0-360)
    """
    x1, y1 = point1
    x2, y2 = point2

    dx = x2 - x1
    dy = y2 - y1

    bearing = math.degrees(math.atan2(dy, dx))
    if bearing < 0:
        bearing += 360

    return bearing


def angular_difference(angle1: float, angle2: float) -> float:
    """
    Calcula a diferença angular mínima entre duas direções.

    Args:
        angle1: Primeiro ângulo em graus
        angle2: Segundo ângulo em graus

    Returns:
        Diferença angular em graus (0-180)
    """
    diff = abs(angle1 - angle2) % 360
    if diff > 180:
        diff = 360 - diff
    return diff


def get_edge_geometry(
    G: nx.Graph, u: Any, v: Any
) -> Optional[LineString]:
    """
    Recupera a geometria (LineString) de uma aresta.

    Args:
        G: Grafo NetworkX
        u: Nó origem
        v: Nó destino

    Returns:
        LineString da aresta ou None
    """
    if G.has_edge(u, v):
        data = G.edges[u, v]
        if "geometry" in data:
            return data["geometry"]
        # Se não tiver geometria, cria linha reta entre os nós
        u_x, u_y = G.nodes[u].get("x", 0), G.nodes[u].get("y", 0)
        v_x, v_y = G.nodes[v].get("x", 0), G.nodes[v].get("y", 0)
        return LineString([(u_x, u_y), (v_x, v_y)])
    return None


def get_edge_direction(G: nx.Graph, u: Any, v: Any) -> float:
    """
    Calcula a direção de uma aresta (segmento de rua).

    Args:
        G: Grafo NetworkX
        u: Nó origem
        v: Nó destino

    Returns:
        Direção em graus (0-360)
    """
    geom = get_edge_geometry(G, u, v)
    if geom is None:
        return 0.0

    # Usa o primeiro e último ponto da geometria para direção
    coords = list(geom.coords)
    if len(coords) < 2:
        coords = [(G.nodes[u].get("x", 0), G.nodes[u].get("y", 0)),
                  (G.nodes[v].get("x", 0), G.nodes[v].get("y", 0))]

    return calculate_bearing(coords[0], coords[-1])


def create_angular_segment_graph(G: nx.Graph) -> nx.Graph:
    """
    Constrói o grafo dual (segment graph) com pesos angulares.

    No grafo dual:
        - Cada aresta do grafo original vira um nó
        - Conexões entre arestas adjacentes vêm arestas no grafo dual
        - O peso é o ângulo de deflexão entre segmentos

    Args:
        G: Grafo não-direcionado de ruas

    Returns:
        Grafo dual onde nós são segmentos e pesos são ângulos de deflexão

    Fórmula:
        Cost(P) = sum(theta(e_i, e_{i+1})) para i=1 até k-1
    """
    logger.info("Construindo grafo dual com pesos angulares...")
    start_time = time.time()

    # Grafo dual
    dual_G = nx.Graph()

    # Mapeia arestas do grafo original para IDs de segmento
    segment_map: Dict[Tuple, str] = {}
    segment_count = 0

    # Cria nós no grafo dual para cada aresta do grafo original
    for u, v, data in G.edges(data=True):
        segment_id = f"seg_{segment_count}"
        segment_map[(u, v)] = segment_id
        segment_map[(v, u)] = segment_id  # Aresta não-direcionada

        # Geometria e atributos
        geom = get_edge_geometry(G, u, v)
        length = data.get("length", 0)

        # Direção do segmento
        direction_uv = get_edge_direction(G, u, v)
        direction_vu = (direction_uv + 180) % 360

        # Filtra atributos que já foram passados explicitamente
        excluded_keys = {"geometry", "length", "u", "v"}
        extra_attrs = {k: v for k, v in data.items() if k not in excluded_keys}

        dual_G.add_node(
            segment_id,
            u=u,
            v=v,
            geometry=geom,
            length=length,
            direction_uv=direction_uv,
            direction_vu=direction_vu,
            original_edge=(u, v),
            **extra_attrs,
        )
        segment_count += 1

    # Cria arestas no grafo dual para interseções
    for node in G.nodes():
        # Pega todas as arestas incidentes neste nó
        incident_edges = []
        for neighbor in G.neighbors(node):
            seg_id = segment_map.get((node, neighbor))
            if seg_id is not None:
                incident_edges.append(seg_id)

        # Conecta todos os pares de arestas incidentes com peso angular
        n_incident = len(incident_edges)
        for i in range(n_incident):
            for j in range(i + 1, n_incident):
                seg1_id = incident_edges[i]
                seg2_id = incident_edges[j]

                # Calcula ângulo de deflexão
                seg1_data = dual_G.nodes[seg1_id]
                seg2_data = dual_G.nodes[seg2_id]

                # Determina direção correta de cada segmento em relação ao nó de interseção
                if seg1_data["u"] == node:
                    dir1 = seg1_data["direction_uv"]
                else:
                    dir1 = seg1_data["direction_vu"]

                if seg2_data["u"] == node:
                    dir2 = seg2_data["direction_uv"]
                else:
                    dir2 = seg2_data["direction_vu"]

                angular_cost = angular_difference(dir1, dir2)

                # Converte para radianos para a fórmula matemática
                angular_cost_rad = math.radians(angular_cost)

                # Adiciona aresta no grafo dual com peso angular
                # 0 = seguir reto (menor custo), 180 = retorno (maior custo)
                dual_G.add_edge(
                    seg1_id,
                    seg2_id,
                    angular_cost=angular_cost,
                    angular_cost_rad=angular_cost_rad,
                    weight=angular_cost_rad,  # Para algoritmos de shortest path
                    intersection_node=node,
                )

    elapsed = time.time() - start_time
    logger.info(
        f"Grafo dual construído: {dual_G.number_of_nodes()} segmentos, "
        f"{dual_G.number_of_edges()} conexões em {elapsed:.2f}s"
    )

    return dual_G


# =============================================================================
# INJEÇÃO DE POIs (PONTOS DE INTERESSE)
# =============================================================================

def fetch_pois_from_overpass(
    lat: float,
    lng: float,
    radius: int = 1_000,
    max_pois: int = 60,
) -> List[Dict]:
    """Busca POIs de atração e transporte via Overpass (sem custo Google)."""
    import httpx

    user_agent = "GymSite-Intelligence/1.0 (fluxo pedestre; contacto vectracargo.com.br)"
    overpass_url = "https://overpass-api.de/api/interpreter"
    raio = max(200, min(int(radius), 3000))
    query = f"""
    [out:json][timeout:25];
    (
      node(around:{raio},{lat},{lng})["shop"];
      way(around:{raio},{lat},{lng})["shop"];
      node(around:{raio},{lat},{lng})["amenity"~"school|university|hospital|restaurant|bus_station"];
      way(around:{raio},{lat},{lng})["amenity"~"school|university|hospital|restaurant|bus_station"];
      node(around:{raio},{lat},{lng})["leisure"="fitness_centre"];
      way(around:{raio},{lat},{lng})["leisure"="fitness_centre"];
      node(around:{raio},{lat},{lng})["railway"="station"];
      way(around:{raio},{lat},{lng})["railway"="station"];
      node(around:{raio},{lat},{lng})["public_transport"="stop_position"];
      way(around:{raio},{lat},{lng})["public_transport"="stop_position"];
    );
    out center {max_pois};
    """
    pois: List[Dict] = []
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": user_agent}) as client:
            response = client.post(overpass_url, data={"data": query})
        if response.status_code != 200:
            logger.warning("Overpass POI HTTP %s", response.status_code)
            return pois
        elements = response.json().get("elements") or []
        for el in elements[:max_pois]:
            tags = el.get("tags") or {}
            plat = el.get("lat")
            plng = el.get("lon")
            if plat is None or plng is None:
                center = el.get("center") or {}
                plat = center.get("lat")
                plng = center.get("lon")
            if plat is None or plng is None:
                continue
            category = "office"
            weight = 0.7
            poi_class = "emp"
            if tags.get("leisure") == "fitness_centre" or tags.get("amenity") == "gym":
                category, weight, poi_class = "gym", 0.8, "emp"
            elif tags.get("shop") in ("supermarket", "mall", "department_store"):
                category, weight, poi_class = "supermarket", 1.0, "emp"
            elif tags.get("amenity") == "bus_station":
                category, weight, poi_class = "bus_station", 0.9, "transp"
            elif tags.get("railway") == "station" or tags.get("station") == "subway":
                category, weight, poi_class = "subway_station", 1.2, "transp"
            elif tags.get("public_transport"):
                category, weight, poi_class = "bus_station", 0.9, "transp"
            elif tags.get("amenity") in ("school", "university", "hospital", "restaurant"):
                category = tags["amenity"]
                weight = POI_CATEGORIES.get(category, 0.7)
                poi_class = "emp"
            pois.append({
                "name": tags.get("name") or tags.get("brand") or category,
                "lat": float(plat),
                "lng": float(plng),
                "category": category,
                "weight": weight,
                "poi_class": poi_class,
                "fonte": "overpass_osm",
            })
    except Exception as exc:
        logger.error("Overpass POI falhou: %s", exc)
    logger.info("POIs Overpass: %d", len(pois))
    return pois


def build_flow_carimbo(
    fluxo_score: float,
    radius_meters: int,
    confianca: str = "alta",
    segment_name: str = "",
) -> Dict[str, Any]:
    return {
        "valor": round(fluxo_score, 1),
        "base": f"segmento mais próximo · raio {radius_meters} m",
        "fonte": "OSM malha viária + IBGE Censo 2022 + Overpass POIs",
        "janela": "malha estática · censo 2022",
        "metodo": "angular segment analysis (Choice + Integration)",
        "confianca": confianca,
        "segmento": segment_name,
    }


def apply_population_weights_to_dual_graph(
    dual_G: nx.Graph,
    lat: float,
    lng: float,
    radius_meters: int,
    config: AnalysisConfig,
) -> nx.Graph:
    """Injeta peso populacional por segmento via censo_setor no entorno."""
    try:
        from tools.censo_setor_tools import demografia_setor_censo
        censo = demografia_setor_censo(lat, lng, raio_m=radius_meters)
    except Exception as exc:
        logger.warning("censo_setor indisponível: %s", exc)
        censo = None
    pop_total = int((censo or {}).get("populacao") or 0)
    n_setores = int((censo or {}).get("n_setores") or 0)
    pop_factor = min(1.0, pop_total / 50_000) if pop_total > 0 else 0.0
    for node in dual_G.nodes():
        dual_G.nodes[node]["population_weight"] = pop_factor * config.alpha_pop
        dual_G.nodes[node]["censo_populacao"] = pop_total
        dual_G.nodes[node]["censo_setores"] = n_setores
    return dual_G


def pois_from_competidores(competidores: List[Dict]) -> List[Dict]:
    """Converte concorrentes geocodados do relatório em POIs ponderados."""
    pois: List[Dict] = []
    for comp in competidores:
        if not isinstance(comp, dict):
            continue
        clat = comp.get("lat")
        clng = comp.get("lng")
        if clat is None or clng is None:
            continue
        pois.append({
            "name": comp.get("nome") or comp.get("name") or "Concorrente",
            "lat": float(clat),
            "lng": float(clng),
            "category": "gym",
            "weight": 0.8,
            "poi_class": "emp",
            "fonte": "relatorio_competidores",
        })
    return pois


def inject_pois_into_dual_graph(
    dual_G: nx.Graph,
    pois: List[Dict],
    original_G: nx.Graph,
    project_to_crs: Optional[Any] = None,
) -> nx.Graph:
    """
    Mapeia POIs para o segmento de rua mais próximo no grafo dual.

    Args:
        dual_G: Grafo dual de segmentos
        pois: Lista de POIs com coordenadas
        original_G: Grafo original do OSMnx (com CRS)
        project_to_crs: CRS do grafo projetado

    Returns:
        Grafo dual com atributos de densidade de POI nos segmentos
    """
    logger.info(f"Injetando {len(pois)} POIs no grafo dual...")

    # Inicializa densidade de POI em todos os segmentos
    for node in dual_G.nodes():
        dual_G.nodes[node]["poi_count"] = 0
        dual_G.nodes[node]["poi_weight"] = 0.0
        dual_G.nodes[node]["poi_details"] = []

    if not pois:
        return dual_G

    # Para cada POI, encontra o segmento mais próximo
    for poi in pois:
        try:
            lat, lng = poi["lat"], poi["lng"]
            poi_point = Point(lng, lat)

            # Projetar ponto se necessário
            if project_to_crs is not None:
                gdf_poi = gpd.GeoDataFrame(geometry=[poi_point], crs="EPSG:4326")
                gdf_poi = gdf_poi.to_crs(project_to_crs)
                poi_point = gdf_poi.geometry.iloc[0]

            # Encontra o segmento mais próximo
            min_distance = float("inf")
            nearest_segment = None

            for seg_id in dual_G.nodes():
                seg_data = dual_G.nodes[seg_id]
                geom = seg_data.get("geometry")
                if geom is not None:
                    distance = poi_point.distance(geom)
                    if distance < min_distance:
                        min_distance = distance
                        nearest_segment = seg_id

            # Atribui peso ao segmento mais próximo (decaimento com distância)
            if nearest_segment is not None and min_distance < 200:  # Max 200m
                decay_factor = math.exp(-min_distance / 100)  # Decaimento exponencial
                weighted_poi = poi["weight"] * decay_factor

                dual_G.nodes[nearest_segment]["poi_count"] += 1
                dual_G.nodes[nearest_segment]["poi_weight"] += weighted_poi
                dual_G.nodes[nearest_segment]["poi_details"].append(poi)

        except Exception as e:
            logger.warning(f"Erro ao mapear POI {poi.get('name', 'unknown')}: {e}")
            continue

    # Normaliza pesos de POI
    poi_weights = [
        dual_G.nodes[n]["poi_weight"]
        for n in dual_G.nodes()
        if dual_G.nodes[n]["poi_weight"] > 0
    ]

    if poi_weights:
        max_weight = max(poi_weights)
        for node in dual_G.nodes():
            if max_weight > 0:
                dual_G.nodes[node]["poi_weight_normalized"] = (
                    dual_G.nodes[node]["poi_weight"] / max_weight
                )
            else:
                dual_G.nodes[node]["poi_weight_normalized"] = 0.0

    logger.info("Injeção de POIs concluída")
    return dual_G


# =============================================================================
# CÁLCULO DE CHOICE (BETWEENNESS CENTRALITY)
# =============================================================================

def calculate_angular_betweenness(
    dual_G: nx.Graph,
    poi_sources: Optional[List[str]] = None,
    poi_targets: Optional[List[str]] = None,
    weight_attribute: str = "angular_cost_rad",
) -> Dict[str, float]:
    """
    Calcula Betweenness Centrality ponderada por custo angular.

    Esta é a métrica principal de Space Syntax (Choice).
    Mede quantos caminhos mais curtos passam por cada segmento.

    Args:
        dual_G: Grafo dual com pesos angulares
        poi_sources: Lista de IDs de segmentos que são origens (POIs)
        poi_targets: Lista de IDs de segmentos que são destinos
        weight_attribute: Atributo de peso para shortest path

    Returns:
        Dicionário {segment_id: betweenness_score}

    Fórmula:
        C_B(v) = sum(sigma_st(v) / sigma_st) para s,t em V
        onde sigma_st é o número de caminhos mais curtos de s a t
        e sigma_st(v) é quantos passam por v
    """
    logger.info("Calculando Betweenness Centrality angular...")
    start_time = time.time()

    # Se não foram especificadas origens/destinos, usa todos os nós
    if poi_sources is None:
        poi_sources = list(dual_G.nodes())
    if poi_targets is None:
        poi_targets = list(dual_G.nodes())

    # Filtra apenas nós que existem no grafo
    poi_sources = [s for s in poi_sources if s in dual_G]
    poi_targets = [t for t in poi_targets if t in dual_G]

    if len(poi_sources) < 2:
        logger.warning("Poucos nós para cálculo de betweenness")
        return {node: 0.0 for node in dual_G.nodes()}

    try:
        # Calcula betweenness centrality com peso angular
        betweenness = nx.betweenness_centrality(
            dual_G,
            k=min(len(poi_sources), 500),  # Amostragem para performance
            weight=weight_attribute,
            normalized=True,
            endpoints=False,
        )

        # Se tivermos POIs específicos, calcula betweenness restrita
        if len(poi_sources) < len(dual_G) or len(poi_targets) < len(dual_G):
            betweenness_poi = nx.betweenness_centrality_subset(
                dual_G,
                sources=poi_sources,
                targets=poi_targets,
                weight=weight_attribute,
                normalized=True,
            )

            # Combina as duas métricas
            for node in betweenness:
                betweenness[node] = 0.6 * betweenness.get(node, 0) + 0.4 * betweenness_poi.get(node, 0)

    except Exception as e:
        logger.error(f"Erro no cálculo de betweenness: {e}")
        betweenness = {node: 0.0 for node in dual_G.nodes()}

    elapsed = time.time() - start_time
    logger.info(f"Betweenness calculada para {len(betweenness)} segmentos em {elapsed:.2f}s")

    return betweenness


def calculate_integration(
    dual_G: nx.Graph,
    weight_attribute: str = "angular_cost_rad",
    radius: Optional[int] = None,
) -> Dict[str, float]:
    """
    Calcula Integration (closeness centrality) dos segmentos.

    Mede quão acessível é cada segmento em relação a todos os outros.

    Args:
        dual_G: Grafo dual
        weight_attribute: Atributo de peso
        radius: Raio de análise em graus (None = global)

    Returns:
        Dicionário {segment_id: integration_score}
    """
    logger.info("Calculando Integration (closeness centrality)...")

    try:
        if radius is not None:
            # Closeness com raio limitado
            integration = {}
            for node in dual_G.nodes():
                # Caminhos curtos dentro do raio
                lengths = nx.single_source_dijkstra_path_length(
                    dual_G, node, cutoff=radius, weight=weight_attribute
                )
                if len(lengths) > 1:
                    avg_distance = sum(lengths.values()) / (len(lengths) - 1)
                    integration[node] = 1.0 / avg_distance if avg_distance > 0 else 0
                else:
                    integration[node] = 0.0
        else:
            # Closeness global
            integration = nx.closeness_centrality(dual_G, distance=weight_attribute)

    except Exception as e:
        logger.error(f"Erro no cálculo de integration: {e}")
        integration = {node: 0.0 for node in dual_G.nodes()}

    logger.info(f"Integration calculada para {len(integration)} segmentos")
    return integration


# =============================================================================
# NORMALIZAÇÃO E SCORES FINAIS
# =============================================================================

def min_max_normalize(
    values: Dict[str, float], target_min: float = 0.0, target_max: float = 1.0
) -> Dict[str, float]:
    """
    Normaliza valores usando Min-Max Scaling.

    Args:
        values: Dicionário de valores
        target_min: Valor mínimo desejado
        target_max: Valor máximo desejado

    Returns:
        Dicionário com valores normalizados
    """
    if not values:
        return {}

    min_val = min(values.values())
    max_val = max(values.values())

    if max_val == min_val:
        return {k: target_min for k in values}

    normalized = {}
    for key, val in values.items():
        normalized[key] = target_min + (val - min_val) / (max_val - min_val) * (target_max - target_min)

    return normalized


def calculate_flow_score(
    dual_G: nx.Graph,
    betweenness: Dict[str, float],
    integration: Dict[str, float],
    config: AnalysisConfig,
) -> Dict[str, float]:
    """
    Calcula o score de fluxo final combinando múltiplas métricas.

    Fórmula:
        Flow Score = w1 * Choice + w2 * Integration + w3 * POI_Density

    Args:
        dual_G: Grafo dual com atributos
        betweenness: Scores de betweenness centrality
        integration: Scores de integration
        config: Configuração da análise

    Returns:
        Dicionário {segment_id: flow_score}
    """
    logger.info("Calculando scores de fluxo finais...")

    # Normaliza métricas individuais
    norm_betweenness = min_max_normalize(betweenness)
    norm_integration = min_max_normalize(integration)

    # Extrai pesos de POI
    poi_weights = {
        node: dual_G.nodes[node].get("poi_weight_normalized", 0.0)
        for node in dual_G.nodes()
    }
    norm_poi = min_max_normalize(poi_weights)

    # Combina métricas
    flow_scores = {}
    w_choice = 0.5  # Peso do Choice
    w_integration = 0.3  # Peso da Integration
    w_poi = 0.2  # Peso dos POIs

    for node in dual_G.nodes():
        choice_val = norm_betweenness.get(node, 0)
        integration_val = norm_integration.get(node, 0)
        poi_val = norm_poi.get(node, 0)
        pop_val = dual_G.nodes[node].get("population_weight", 0.0)

        flow_score = (
            w_choice * choice_val
            + w_integration * integration_val
            + w_poi * poi_val
            + config.alpha_pop * pop_val
        )

        flow_scores[node] = flow_score

    # Normaliza score final
    return min_max_normalize(flow_scores)


# =============================================================================
# OUTPUT GEOJSON
# =============================================================================

def results_to_geojson(
    dual_G: nx.Graph,
    flow_scores: Dict[str, float],
    betweenness: Dict[str, float],
    integration: Dict[str, float],
    crs: Optional[Any] = None,
    carimbo: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    Converte resultados para formato GeoJSON.

    Args:
        dual_G: Grafo dual com geometrias
        flow_scores: Scores de fluxo normalizados
        betweenness: Scores de betweenness
        integration: Scores de integration

    Returns:
        FeatureCollection GeoJSON
    """
    features = []
    rows: List[Dict[str, Any]] = []

    for node in dual_G.nodes():
        seg_data = dual_G.nodes[node]
        geom = seg_data.get("geometry")

        if geom is None:
            continue

        try:
            geojson_geom = mapping(geom)
        except Exception:
            continue

        props = {
            "segment_id": node,
            "flow_score": round(flow_scores.get(node, 0), 4),
            "choice_score": round(betweenness.get(node, 0), 4),
            "integration_score": round(integration.get(node, 0), 4),
            "poi_count": seg_data.get("poi_count", 0),
            "poi_weight": round(seg_data.get("poi_weight_normalized", 0), 4),
            "length_meters": round(seg_data.get("length", 0), 2),
            "street_name": seg_data.get("name", ""),
            "highway_type": seg_data.get("highway", ""),
            "population_weight": round(seg_data.get("population_weight", 0), 4),
        }
        if carimbo:
            props["carimbo"] = carimbo
        rows.append({"geometry": geom, "properties": props})

    if rows and crs is not None:
        try:
            gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)
            gdf_wgs84 = gdf.to_crs("EPSG:4326")
            for _, row in gdf_wgs84.iterrows():
                features.append({
                    "type": "Feature",
                    "geometry": mapping(row.geometry),
                    "properties": dict(row["properties"]),
                })
        except Exception as exc:
            logger.warning("Reprojeção WGS84 falhou: %s", exc)
            for row in rows:
                features.append({
                    "type": "Feature",
                    "geometry": mapping(row["geometry"]),
                    "properties": row["properties"],
                })
    else:
        for row in rows:
            features.append({
                "type": "Feature",
                "geometry": mapping(row["geometry"]),
                "properties": row["properties"],
            })

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "analysis_type": "angular_segment_analysis",
            "total_segments": len(features),
            "calculation_method": "betweenness_centrality_angular_weighted",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "attribution": "© OpenStreetMap contributors",
            "carimbo": carimbo,
        },
        "features": features,
    }

    return geojson


def get_top_segments(
    geojson: Dict, n: int = 10
) -> List[Dict]:
    """
    Retorna os N segmentos com maior score de fluxo.

    Args:
        geojson: FeatureCollection GeoJSON
        n: Número de segmentos a retornar

    Returns:
        Lista de features ordenadas por flow_score
    """
    features = geojson.get("features", [])
    sorted_features = sorted(
        features,
        key=lambda f: f.get("properties", {}).get("flow_score", 0),
        reverse=True,
    )
    return sorted_features[:n]


# =============================================================================
# FUNÇÃO PRINCIPAL DE ANÁLISE
# =============================================================================

def unavailable_flow_result(motivo: str) -> Dict[str, Any]:
    return {
        "success": False,
        "confianca": "indisponivel",
        "motivo": motivo,
        "geojson": {"type": "FeatureCollection", "features": []},
        "statistics": {},
        "top_segments": [],
        "pois_analyzed": 0,
    }


def score_candidate_flow(
    lat: float,
    lng: float,
    analysis_result: Dict[str, Any],
    radius_meters: int = DEFAULT_RADIUS_METERS,
) -> Dict[str, Any]:
    segment = get_segment_for_location(lat, lng, analysis_result)
    if not segment:
        return {
            "fluxo_score": None,
            "fluxo_norm": None,
            "fluxo_confianca": "indisponivel",
            "fluxo_carimbo": build_flow_carimbo(0, radius_meters, "indisponivel"),
        }
    flow_norm = float(segment.get("flow_score") or 0)
    fluxo_score = round(flow_norm * 100, 1)
    confianca = "alta" if flow_norm >= 0.5 else "media" if flow_norm >= 0.25 else "baixa"
    return {
        "fluxo_score": fluxo_score,
        "fluxo_norm": round(flow_norm, 4),
        "fluxo_segmento": segment.get("street_name") or "",
        "fluxo_confianca": confianca,
        "fluxo_carimbo": build_flow_carimbo(
            fluxo_score,
            radius_meters,
            confianca,
            segment.get("street_name") or "",
        ),
    }


def calculate_natural_movement(
    lat: float,
    lng: float,
    google_places_api_key: Optional[str] = None,
    config: Optional[AnalysisConfig] = None,
    custom_pois: Optional[List[Dict]] = None,
    competidores: Optional[List[Dict]] = None,
) -> Dict:
    """
    Função principal que executa a análise completa de fluxo natural.

    Pipeline:
        1. Extrai grafo OSM para a região
        2. Converte para grafo não-direcionado
        3. Constrói grafo dual com pesos angulares
        4. Busca e injeta POIs
        5. Calcula Betweenness Centrality (Choice)
        6. Calcula Integration (Closeness)
        7. Combina métricas em Flow Score
        8. Retorna resultado como GeoJSON

    Args:
        lat: Latitude do ponto central
        lng: Longitude do ponto central
        google_places_api_key: Chave da API Google Places (opcional)
        config: Configuração da análise (usa padrão se None)
        custom_pois: Lista de POIs personalizados (opcional)

    Returns:
        Dicionário com GeoJSON, estatísticas e segmentos principais
    """
    if config is None:
        config = AnalysisConfig()

    logger.info(
        f"Iniciando análise de fluxo natural: ({lat}, {lng}) "
        f"raio={config.radius_meters}m"
    )
    total_start = time.time()

    # -------------------------------------------------------------------------
    # PASSO 1: Extrai grafo base do OpenStreetMap
    # -------------------------------------------------------------------------
    G = get_base_graph(lat, lng, config.radius_meters, config.network_type)

    # Converte para não-direcionado
    G_undirected = graph_to_undirected(G)

    # -------------------------------------------------------------------------
    # PASSO 2: Constrói grafo dual com custo angular
    # -------------------------------------------------------------------------
    dual_G = create_angular_segment_graph(G_undirected)

    # -------------------------------------------------------------------------
    # PASSO 3: Busca e injeta POIs
    # -------------------------------------------------------------------------
    pois: List[Dict] = list(custom_pois or [])
    pois.extend(pois_from_competidores(competidores or []))
    if not pois:
        pois = fetch_pois_from_overpass(
            lat, lng, config.poi_radius_meters, config.max_pois
        )

    crs = G.graph.get("crs", None)
    dual_G = inject_pois_into_dual_graph(dual_G, pois, G_undirected, crs)
    dual_G = apply_population_weights_to_dual_graph(
        dual_G, lat, lng, config.radius_meters, config
    )

    # -------------------------------------------------------------------------
    # PASSO 4: Calcula Choice (Betweenness Centrality)
    # -------------------------------------------------------------------------
    # Identifica segmentos com POIs como origens/destinos prioritários
    poi_segments = [
        node
        for node in dual_G.nodes()
        if dual_G.nodes[node].get("poi_count", 0) > 0
    ]

    betweenness = calculate_angular_betweenness(
        dual_G,
        poi_sources=poi_segments if poi_segments else None,
        poi_targets=poi_segments if poi_segments else None,
    )

    # -------------------------------------------------------------------------
    # PASSO 5: Calcula Integration (Closeness)
    # -------------------------------------------------------------------------
    integration = calculate_integration(dual_G)

    # -------------------------------------------------------------------------
    # PASSO 6: Calcula Flow Score combinado
    # -------------------------------------------------------------------------
    flow_scores = calculate_flow_score(dual_G, betweenness, integration, config)

    flow_values = list(flow_scores.values())
    mean_flow = round(float(np.mean(flow_values)), 4) if flow_values else 0.0
    carimbo = build_flow_carimbo(
        round(mean_flow * 100, 1),
        config.radius_meters,
        "alta" if mean_flow >= 0.4 else "media",
    )

    geojson = results_to_geojson(
        dual_G, flow_scores, betweenness, integration, crs=crs, carimbo=carimbo
    )

    # Estatísticas
    flow_values = list(flow_scores.values())
    stats = {
        "total_segments": len(flow_scores),
        "mean_flow_score": round(np.mean(flow_values), 4),
        "median_flow_score": round(np.median(flow_values), 4),
        "std_flow_score": round(np.std(flow_values), 4),
        "max_flow_score": round(max(flow_values), 4),
        "min_flow_score": round(min(flow_values), 4),
        "total_pois_mapped": sum(
            dual_G.nodes[n].get("poi_count", 0) for n in dual_G.nodes()
        ),
        "analysis_radius_meters": config.radius_meters,
        "processing_time_seconds": round(time.time() - total_start, 2),
    }

    # Segmentos principais
    top_segments = get_top_segments(geojson, 10)

    result = {
        "success": True,
        "confianca": carimbo.get("confianca", "alta"),
        "carimbo": carimbo,
        "geojson": geojson,
        "statistics": stats,
        "top_segments": [
            {
                "rank": i + 1,
                "flow_score": seg.get("properties", {}).get("flow_score"),
                "choice_score": seg.get("properties", {}).get("choice_score"),
                "street_name": seg.get("properties", {}).get("street_name", ""),
                "length_meters": seg.get("properties", {}).get("length_meters"),
            }
            for i, seg in enumerate(top_segments)
        ],
        "pois_analyzed": len(pois),
    }

    total_elapsed = time.time() - total_start
    logger.info(f"Análise completa em {total_elapsed:.2f}s")

    return result


# =============================================================================
# FUNÇÕES AUXILIARES PARA INTEGRAÇÃO
# =============================================================================

def get_segment_for_location(
    lat: float,
    lng: float,
    geojson_result: Dict,
) -> Optional[Dict]:
    """
    Encontra o segmento de rua mais próximo de uma coordenada.

    Args:
        lat: Latitude
        lng: Longitude
        geojson_result: Resultado da análise em formato GeoJSON

    Returns:
        Propriedades do segmento mais próximo
    """
    point = Point(lng, lat)
    features = geojson_result.get("geojson", {}).get("features", [])

    min_distance = float("inf")
    nearest_segment = None

    for feature in features:
        geom = feature.get("geometry")
        if geom:
            try:
                line = LineString(geom.get("coordinates", []))
                distance = point.distance(line)
                if distance < min_distance:
                    min_distance = distance
                    nearest_segment = feature.get("properties", {})
            except Exception:
                continue

    if nearest_segment:
        nearest_segment["distance_to_point_meters"] = round(min_distance * 111_000, 2)

    return nearest_segment


def generate_context_for_rag(
    analysis_result: Dict,
    location_name: str = "o ponto analisado",
) -> str:
    """
    Gera texto descritivo para injeção no contexto do RAG/ADK.

    Args:
        analysis_result: Resultado da análise
        location_name: Nome do local

    Returns:
        Texto descritivo para o agente
    """
    stats = analysis_result.get("statistics", {})
    top = analysis_result.get("top_segments", [])

    context = f"""### Análise de Sintaxe Espacial - {location_name}

**Visão Geral:**
A análise de fluxo natural mapeou {stats.get('total_segments', 0)} segmentos de ruas na região.
O score médio de fluxo é {stats.get('mean_flow_score', 0):.2f} (desvio padrão: {stats.get('std_flow_score', 0):.2f}).
Foram identificados {stats.get('total_pois_mapped', 0)} pontos de interesse mapeados na malha viária.

**Interpretação dos Scores:**
- **Flow Score**: Medida combinada de entre-centralidade (Choice), integração e densidade de POIs.
  Valores próximos a 1.0 indicam artérias principais de fluxo natural.
- **Choice Score**: Entre-centralidade angular. Segmentos com alto Choice são "caminhos obrigatórios"
  que conectam múltiplas origens e destinos.
- **Integration Score**: Acessibilidade do segmento. Valores altos indicam fácil acesso de qualquer
  ponto da rede.

**Principais Artérias de Fluxo:**
"""
    for seg in top[:5]:
        context += f"""
{seg['rank']}. **{seg.get('street_name', 'Rua não nomeada')}**
   - Flow Score: {seg.get('flow_score', 0):.3f}
   - Choice Score: {seg.get('choice_score', 0):.3f}
   - Comprimento: {seg.get('length_meters', 0):.0f}m
"""

    context += f"""
**Conclusão para Viabilidade Comercial:**
O ponto é {'excelente' if stats.get('mean_flow_score', 0) > 0.6 else 'bom' if stats.get('mean_flow_score', 0) > 0.4 else 'moderado'} para captação de fluxo natural de pedestres. {"A alta entre-centralidade indica que a localização funciona como conector natural entre polos de atração." if stats.get('mean_flow_score', 0) > 0.5 else "Recomenda-se análise complementar de acessibilidade veicular."}
"""

    return context


if __name__ == "__main__":
    # Teste simples
    logging.basicConfig(level=logging.INFO)

    # Coordenadas de exemplo: Av. Paulista, São Paulo
    test_lat, test_lng = -23.5617, -46.6560

    print("Executando análise de teste...")
    result = calculate_natural_movement(test_lat, test_lng)

    print(f"\nEstatísticas:")
    for key, val in result["statistics"].items():
        print(f"  {key}: {val}")

    print(f"\nTop 5 Segmentos:")
    for seg in result["top_segments"][:5]:
        print(f"  {seg['rank']}. {seg.get('street_name', 'N/A')}: {seg['flow_score']:.3f}")
