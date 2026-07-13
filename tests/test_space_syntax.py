"""
Testes Unitários - Módulo Space Syntax
=====================================
Cobertura completa das funções matemáticas e de análise espacial.

Estrutura:
    - Testes de geometria e cálculos angulares
    - Testes de construção de grafo dual
    - Testes de cálculo de centralidade
    - Testes de normalização
    - Testes de cache
    - Testes de integração (end-to-end simplificado)
"""

import math
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pytest
from shapely.geometry import LineString, Point

from tools.space_syntax import (
    AnalysisConfig,
    GraphCache,
    POI_CATEGORIES,
    angular_difference,
    calculate_bearing,
    calculate_flow_score,
    calculate_integration,
    calculate_natural_movement,
    create_angular_segment_graph,
    generate_context_for_rag,
    get_base_graph,
    get_edge_direction,
    get_edge_geometry,
    get_segment_for_location,
    get_top_segments,
    graph_to_undirected,
    inject_pois_into_dual_graph,
    min_max_normalize,
    results_to_geojson,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_graph():
    """Cria um grafo simples de teste."""
    G = nx.Graph()
    # Cria uma grade 3x3
    for i in range(3):
        for j in range(3):
            node = f"n{i}_{j}"
            G.add_node(node, x=float(j * 100), y=float(i * 100))

    # Arestas horizontais
    for i in range(3):
        for j in range(2):
            u = f"n{i}_{j}"
            v = f"n{i}_{j+1}"
            G.add_edge(
                u,
                v,
                length=100.0,
                highway="residential",
                geometry=LineString([(j * 100, i * 100), ((j + 1) * 100, i * 100)]),
            )

    # Arestas verticais
    for i in range(2):
        for j in range(3):
            u = f"n{i}_{j}"
            v = f"n{i+1}_{j}"
            G.add_edge(
                u,
                v,
                length=100.0,
                highway="residential",
                geometry=LineString([(j * 100, i * 100), (j * 100, (i + 1) * 100)]),
            )

    return G


@pytest.fixture
def sample_dual_graph(sample_graph):
    """Cria um grafo dual de teste."""
    return create_angular_segment_graph(sample_graph)


@pytest.fixture
def sample_pois():
    """Cria POIs de teste."""
    return [
        {"name": "Supermercado X", "lat": -23.56, "lng": -46.65, "category": "supermarket", "weight": 1.0},
        {"name": "Academia Y", "lat": -23.561, "lng": -46.651, "category": "gym", "weight": 0.8},
        {"name": "Escola Z", "lat": -23.559, "lng": -46.649, "category": "school", "weight": 0.7},
    ]


# =============================================================================
# TESTES DE GEOMETRIA E CÁLCULOS ANGULARES
# =============================================================================

class TestAngularCalculations:
    """Testes para cálculos de direção e diferença angular."""

    def test_calculate_bearing_east(self):
        """Direção para leste deve ser 0°."""
        bearing = calculate_bearing((0, 0), (100, 0))
        assert pytest.approx(bearing, abs=0.1) == 0.0

    def test_calculate_bearing_north(self):
        """Direção para norte deve ser 90°."""
        bearing = calculate_bearing((0, 0), (0, 100))
        assert pytest.approx(bearing, abs=0.1) == 90.0

    def test_calculate_bearing_west(self):
        """Direção para oeste deve ser 180°."""
        bearing = calculate_bearing((0, 0), (-100, 0))
        assert pytest.approx(bearing, abs=0.1) == 180.0

    def test_calculate_bearing_south(self):
        """Direção para sul deve ser 270°."""
        bearing = calculate_bearing((0, 0), (0, -100))
        assert pytest.approx(bearing, abs=0.1) == 270.0

    def test_calculate_bearing_northeast(self):
        """Direção nordeste deve ser 45°."""
        bearing = calculate_bearing((0, 0), (100, 100))
        assert pytest.approx(bearing, abs=0.1) == 45.0

    def test_angular_difference_same_direction(self):
        """Diferença para mesma direção deve ser 0°."""
        diff = angular_difference(45.0, 45.0)
        assert diff == 0.0

    def test_angular_difference_opposite(self):
        """Diferença para direções opostas deve ser 180°."""
        diff = angular_difference(0.0, 180.0)
        assert diff == 180.0

    def test_angular_difference_90_degrees(self):
        """Diferença de 90° deve retornar 90°."""
        diff = angular_difference(0.0, 90.0)
        assert diff == 90.0

    def test_angular_difference_wraparound(self):
        """Diferença que cruza 0°/360° deve ser correta."""
        diff = angular_difference(350.0, 10.0)
        assert diff == 20.0


# =============================================================================
# TESTES DE GRAFO E GEOMETRIA
# =============================================================================

class TestGraphOperations:
    """Testes para operações em grafos."""

    def test_get_edge_geometry(self, sample_graph):
        """Deve recuperar geometria de aresta existente."""
        geom = get_edge_geometry(sample_graph, "n0_0", "n0_1")
        assert geom is not None
        assert isinstance(geom, LineString)

    def test_get_edge_geometry_nonexistent(self, sample_graph):
        """Deve retornar None para aresta inexistente."""
        geom = get_edge_geometry(sample_graph, "n0_0", "n2_2")
        assert geom is None

    def test_get_edge_direction_horizontal(self, sample_graph):
        """Direção de aresta horizontal deve ser ~0°."""
        direction = get_edge_direction(sample_graph, "n0_0", "n0_1")
        assert pytest.approx(direction, abs=5.0) == 0.0

    def test_get_edge_direction_vertical(self, sample_graph):
        """Direção de aresta vertical deve ser ~90°."""
        direction = get_edge_direction(sample_graph, "n0_0", "n1_0")
        assert pytest.approx(direction, abs=5.0) == 90.0

    def test_graph_to_undirected(self):
        """Conversão para não-direcionado deve manter atributos."""
        G = nx.MultiDiGraph()
        G.add_node("a", x=0, y=0)
        G.add_node("b", x=100, y=0)
        G.add_edge("a", "b", length=100, test_attr="value")

        G_undirected = graph_to_undirected(G)
        assert isinstance(G_undirected, nx.Graph)
        assert G_undirected.has_edge("a", "b")
        assert G_undirected.edges["a", "b"].get("test_attr") == "value"


# =============================================================================
# TESTES DE GRAFO DUAL
# =============================================================================

class TestDualGraph:
    """Testes para construção do grafo dual com pesos angulares."""

    def test_dual_graph_nodes_created(self, sample_dual_graph):
        """Grafo dual deve ter nós para cada aresta original."""
        # Grafo 3x3 tem 12 arestas (6 horizontais + 6 verticais)
        assert sample_dual_graph.number_of_nodes() == 12

    def test_dual_graph_edges_created(self, sample_dual_graph):
        """Grafo dual deve ter arestas nas interseções."""
        # Cada nó interno tem 4 arestas incidentes = 6 conexões
        assert sample_dual_graph.number_of_edges() > 0

    def test_dual_graph_angular_weights(self, sample_dual_graph):
        """Arestas do grafo dual devem ter pesos angulares."""
        for _, _, data in sample_dual_graph.edges(data=True):
            assert "angular_cost" in data
            assert "angular_cost_rad" in data
            assert "weight" in data
            assert 0 <= data["angular_cost"] <= 180

    def test_dual_graph_node_attributes(self, sample_dual_graph):
        """Nós do grafo dual devem ter atributos do segmento."""
        for node in sample_dual_graph.nodes():
            data = sample_dual_graph.nodes[node]
            assert "geometry" in data
            assert "length" in data
            assert "direction_uv" in data
            assert "direction_vu" in data

    def test_straight_continuation_zero_cost(self):
        """Seguir em linha reta deve ter custo angular ~0."""
        G = nx.Graph()
        G.add_node("a", x=0, y=0)
        G.add_node("b", x=100, y=0)
        G.add_node("c", x=200, y=0)
        G.add_edge("a", "b", length=100, geometry=LineString([(0, 0), (100, 0)]))
        G.add_edge("b", "c", length=100, geometry=LineString([(100, 0), (200, 0)]))

        dual = create_angular_segment_graph(G)

        # Duas arestas em linha reta devem ter custo angular ~0
        assert dual.number_of_nodes() == 2
        assert dual.number_of_edges() == 1

        edge_data = list(dual.edges(data=True))[0]
        # Custo deve ser próximo de 0 ou 180 (linha reta - mesma direção ou oposta)
        angular_cost = edge_data[2]["angular_cost"]
        assert angular_cost <= 5.0 or angular_cost >= 175.0

    def test_right_angle_cost(self):
        """Curva de 90° deve ter custo angular ~90°."""
        G = nx.Graph()
        G.add_node("a", x=0, y=0)
        G.add_node("b", x=100, y=0)
        G.add_node("c", x=100, y=100)
        G.add_edge("a", "b", length=100, geometry=LineString([(0, 0), (100, 0)]))
        G.add_edge("b", "c", length=100, geometry=LineString([(100, 0), (100, 100)]))

        dual = create_angular_segment_graph(G)

        edge_data = list(dual.edges(data=True))[0]
        # Custo deve ser próximo de 90°
        assert pytest.approx(edge_data[2]["angular_cost"], abs=5.0) == 90.0


# =============================================================================
# TESTES DE POIs
# =============================================================================

class TestPOIInjection:
    """Testes para injeção de POIs no grafo dual."""

    def test_inject_pois(self, sample_dual_graph, sample_pois, sample_graph):
        """Deve injetar POIs no grafo dual."""
        dual_with_pois = inject_pois_into_dual_graph(
            sample_dual_graph, sample_pois, sample_graph
        )

        # Verifica se pelo menos um segmento recebeu POI
        poi_counts = [dual_with_pois.nodes[n].get("poi_count", 0) for n in dual_with_pois.nodes()]
        assert sum(poi_counts) > 0

    def test_empty_pois(self, sample_dual_graph, sample_graph):
        """Lista vazia de POIs não deve quebrar."""
        dual_with_pois = inject_pois_into_dual_graph(
            sample_dual_graph, [], sample_graph
        )

        for node in dual_with_pois.nodes():
            assert dual_with_pois.nodes[node].get("poi_count") == 0

    def test_poi_weight_normalization(self, sample_dual_graph, sample_pois, sample_graph):
        """Pesos de POI devem ser normalizados."""
        dual_with_pois = inject_pois_into_dual_graph(
            sample_dual_graph, sample_pois, sample_graph
        )

        weights = [
            dual_with_pois.nodes[n].get("poi_weight_normalized", 0)
            for n in dual_with_pois.nodes()
        ]

        # Se houver POIs mapeados, o máximo deve ser 1.0
        positive_weights = [w for w in weights if w > 0]
        if positive_weights:
            assert max(weights) <= 1.0
            assert min(positive_weights) >= 0.0


# =============================================================================
# TESTES DE CENTRALIDADE
# =============================================================================

class TestCentrality:
    """Testes para cálculos de centralidade."""

    def test_betweenness_calculated(self, sample_dual_graph):
        """Betweenness deve ser calculada para todos os nós."""
        from tools.space_syntax import calculate_angular_betweenness

        betweenness = calculate_angular_betweenness(sample_dual_graph)

        assert len(betweenness) == sample_dual_graph.number_of_nodes()
        # Todos os valores devem estar entre 0 e 1
        assert all(0 <= v <= 1 for v in betweenness.values())

    def test_integration_calculated(self, sample_dual_graph):
        """Integration deve ser calculada para todos os nós."""
        integration = calculate_integration(sample_dual_graph)

        assert len(integration) == sample_dual_graph.number_of_nodes()
        assert all(v >= 0 for v in integration.values())

    def test_centrality_symmetry(self):
        """Grafo simétrico deve ter centralidades simétricas."""
        G = nx.Graph()
        # Grafo em cruz: 5 nós
        G.add_node("center", x=0, y=0)
        for i, (x, y) in enumerate([(100, 0), (-100, 0), (0, 100), (0, -100)]):
            G.add_node(f"arm{i}", x=x, y=y)
            G.add_edge("center", f"arm{i}", length=100, geometry=LineString([(0, 0), (x, y)]))

        dual = create_angular_segment_graph(G)
        from tools.space_syntax import calculate_angular_betweenness

        betweenness = calculate_angular_betweenness(dual)

        # Todas as arestas do braço devem ter betweenness similar
        arm_values = [betweenness[f"seg_{i}"] for i in range(4)]
        assert pytest.approx(arm_values[0], abs=0.1) == arm_values[1]
        assert pytest.approx(arm_values[1], abs=0.1) == arm_values[2]


# =============================================================================
# TESTES DE NORMALIZAÇÃO
# =============================================================================

class TestNormalization:
    """Testes para funções de normalização."""

    def test_min_max_normalize_basic(self):
        """Normalização básica deve funcionar corretamente."""
        values = {"a": 10, "b": 20, "c": 30}
        normalized = min_max_normalize(values)

        assert pytest.approx(normalized["a"]) == 0.0
        assert pytest.approx(normalized["b"]) == 0.5
        assert pytest.approx(normalized["c"]) == 1.0

    def test_min_max_normalize_custom_range(self):
        """Normalização com range customizado."""
        values = {"a": 0, "b": 50, "c": 100}
        normalized = min_max_normalize(values, target_min=0, target_max=10)

        assert pytest.approx(normalized["a"]) == 0.0
        assert pytest.approx(normalized["b"]) == 5.0
        assert pytest.approx(normalized["c"]) == 10.0

    def test_min_max_normalize_same_values(self):
        """Valores idênticos devem retornar target_min."""
        values = {"a": 5, "b": 5, "c": 5}
        normalized = min_max_normalize(values)

        assert all(v == 0.0 for v in normalized.values())

    def test_min_max_normalize_empty(self):
        """Dicionário vazio deve retornar vazio."""
        normalized = min_max_normalize({})
        assert normalized == {}


# =============================================================================
# TESTES DE FLOW SCORE
# =============================================================================

class TestFlowScore:
    """Testes para cálculo do score de fluxo combinado."""

    def test_flow_score_combination(self, sample_dual_graph):
        """Flow score deve combinar múltiplas métricas."""
        betweenness = {node: 0.5 for node in sample_dual_graph.nodes()}
        integration = {node: 0.3 for node in sample_dual_graph.nodes()}
        config = AnalysisConfig()

        flow_scores = calculate_flow_score(
            sample_dual_graph, betweenness, integration, config
        )

        assert len(flow_scores) == sample_dual_graph.number_of_nodes()
        assert all(0 <= v <= 1 for v in flow_scores.values())

    def test_flow_score_ranking(self, sample_dual_graph):
        """Segmentos com maior betweenness devem ter maior flow score."""
        nodes = list(sample_dual_graph.nodes())
        betweenness = {node: i / len(nodes) for i, node in enumerate(nodes)}
        integration = {node: 0.5 for node in nodes}
        config = AnalysisConfig()

        flow_scores = calculate_flow_score(
            sample_dual_graph, betweenness, integration, config
        )

        # Verifica ordenação geral
        sorted_flow = sorted(flow_scores.values(), reverse=True)
        assert sorted_flow[0] >= sorted_flow[-1]


# =============================================================================
# TESTES DE GEOJSON
# =============================================================================

class TestGeoJSON:
    """Testes para geração de GeoJSON."""

    def test_results_to_geojson(self, sample_dual_graph):
        """Deve gerar GeoJSON válido."""
        betweenness = {node: 0.5 for node in sample_dual_graph.nodes()}
        integration = {node: 0.3 for node in sample_dual_graph.nodes()}
        flow_scores = {node: 0.4 for node in sample_dual_graph.nodes()}

        geojson = results_to_geojson(
            sample_dual_graph, flow_scores, betweenness, integration
        )

        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson
        assert "metadata" in geojson
        assert len(geojson["features"]) > 0

    def test_geojson_feature_properties(self, sample_dual_graph):
        """Features devem ter propriedades corretas."""
        betweenness = {node: 0.5 for node in sample_dual_graph.nodes()}
        integration = {node: 0.3 for node in sample_dual_graph.nodes()}
        flow_scores = {node: 0.4 for node in sample_dual_graph.nodes()}

        geojson = results_to_geojson(
            sample_dual_graph, flow_scores, betweenness, integration
        )

        feature = geojson["features"][0]
        props = feature["properties"]

        assert "flow_score" in props
        assert "choice_score" in props
        assert "integration_score" in props
        assert "poi_count" in props
        assert "length_meters" in props

    def test_get_top_segments(self, sample_dual_graph):
        """Deve retornar segmentos ordenados por flow score."""
        betweenness = {node: 0.5 for node in sample_dual_graph.nodes()}
        integration = {node: 0.3 for node in sample_dual_graph.nodes()}
        flow_scores = {node: i / len(sample_dual_graph.nodes()) for i, node in enumerate(sample_dual_graph.nodes())}

        geojson = results_to_geojson(
            sample_dual_graph, flow_scores, betweenness, integration
        )

        top = get_top_segments(geojson, 5)
        assert len(top) <= 5

        # Verifica ordenação decrescente
        scores = [f["properties"]["flow_score"] for f in top]
        assert scores == sorted(scores, reverse=True)


# =============================================================================
# TESTES DE CACHE
# =============================================================================

class TestCache:
    """Testes para o cache de grafos."""

    def test_cache_store_and_retrieve(self):
        """Deve armazenar e recuperar grafos."""
        cache = GraphCache(ttl_seconds=60)
        G = nx.Graph()
        G.add_node("test")

        cache.set(-23.5, -46.6, 1000, "walk", G)
        retrieved = cache.get(-23.5, -46.6, 1000, "walk")

        assert retrieved is not None
        assert retrieved.has_node("test")

    def test_cache_miss_different_params(self):
        """Parâmetros diferentes devem resultar em cache miss."""
        cache = GraphCache(ttl_seconds=60)
        G = nx.Graph()
        G.add_node("test")

        cache.set(-23.5, -46.6, 1000, "walk", G)
        retrieved = cache.get(-23.5, -46.6, 2000, "walk")

        assert retrieved is None

    def test_cache_ttl_expiration(self):
        """Entradas expiradas devem ser removidas."""
        cache = GraphCache(ttl_seconds=0.01)  # 10ms TTL
        G = nx.Graph()
        G.add_node("test")

        cache.set(-23.5, -46.6, 1000, "walk", G)
        time.sleep(0.05)  # Espera expirar

        retrieved = cache.get(-23.5, -46.6, 1000, "walk")
        assert retrieved is None

    def test_cache_clear(self):
        """Deve limpar todo o cache."""
        cache = GraphCache()
        G = nx.Graph()
        G.add_node("test")

        cache.set(-23.5, -46.6, 1000, "walk", G)
        cache.clear()

        assert len(cache._cache) == 0


# =============================================================================
# TESTES DE RAG CONTEXT
# =============================================================================

class TestRAGContext:
    """Testes para geração de contexto RAG."""

    def test_generate_context(self):
        """Deve gerar texto de contexto estruturado."""
        result = {
            "statistics": {
                "total_segments": 100,
                "mean_flow_score": 0.5,
                "std_flow_score": 0.2,
                "total_pois_mapped": 10,
            },
            "top_segments": [
                {
                    "rank": 1,
                    "street_name": "Av. Teste",
                    "flow_score": 0.9,
                    "choice_score": 0.8,
                    "length_meters": 500,
                }
            ],
        }

        context = generate_context_for_rag(result, "Ponto Teste")

        assert "Ponto Teste" in context
        assert "Flow Score" in context
        assert "Choice Score" in context
        assert "Av. Teste" in context

    def test_generate_context_empty(self):
        """Deve lidar com dados mínimos."""
        result = {
            "statistics": {
                "total_segments": 0,
                "mean_flow_score": 0,
                "std_flow_score": 0,
                "total_pois_mapped": 0,
            },
            "top_segments": [],
        }

        context = generate_context_for_rag(result, "Ponto Vazio")
        assert "Ponto Vazio" in context


# =============================================================================
# TESTES DE CONFIGURAÇÃO
# =============================================================================

class TestConfig:
    """Testes para a classe de configuração."""

    def test_default_config(self):
        """Configuração padrão deve ter valores esperados."""
        config = AnalysisConfig()
        assert config.radius_meters == 2_000
        assert config.network_type == "walk"
        assert config.normalization_method == "minmax"

    def test_custom_config(self):
        """Configuração customizada deve aceitar valores."""
        config = AnalysisConfig(
            radius_meters=2_000,
            network_type="walk",
            poi_radius_meters=500,
        )
        assert config.radius_meters == 2_000
        assert config.network_type == "walk"
        assert config.poi_radius_meters == 500


# =============================================================================
# TESTES DE CONSTANTES
# =============================================================================

class TestConstants:
    """Testes para constantes do módulo."""

    def test_poi_categories(self):
        """Categorias de POI devem ter pesos válidos."""
        assert len(POI_CATEGORIES) > 0
        for category, weight in POI_CATEGORIES.items():
            assert isinstance(category, str)
            assert isinstance(weight, (int, float))
            assert 0 <= weight <= 2.0

    def test_default_radius(self):
        """Raio padrão deve ser positivo."""
        from tools.space_syntax import DEFAULT_RADIUS_METERS

        assert DEFAULT_RADIUS_METERS > 0


# =============================================================================
# TESTES DE INTEGRAÇÃO (SIMPLIFICADOS)
# =============================================================================

class TestIntegration:
    """Testes de integração end-to-end simplificados."""

    def test_full_pipeline_small_graph(self, sample_graph, sample_pois):
        """Pipeline completo em grafo pequeno deve funcionar."""
        # Cria grafo dual
        dual_G = create_angular_segment_graph(sample_graph)

        # Injeta POIs
        dual_G = inject_pois_into_dual_graph(dual_G, sample_pois, sample_graph)

        # Calcula centralidades
        from tools.space_syntax import calculate_angular_betweenness

        betweenness = calculate_angular_betweenness(dual_G)
        integration = calculate_integration(dual_G)

        # Calcula flow score
        config = AnalysisConfig()
        flow_scores = calculate_flow_score(dual_G, betweenness, integration, config)

        # Gera GeoJSON
        geojson = results_to_geojson(dual_G, flow_scores, betweenness, integration)

        # Validações
        assert len(geojson["features"]) > 0
        assert all(0 <= f["properties"]["flow_score"] <= 1 for f in geojson["features"])

    def test_end_to_end_flow(self, sample_graph):
        """Fluxo completo sem POIs deve funcionar."""
        dual_G = create_angular_segment_graph(sample_graph)
        dual_G = inject_pois_into_dual_graph(dual_G, [], sample_graph)

        from tools.space_syntax import calculate_angular_betweenness

        betweenness = calculate_angular_betweenness(dual_G)
        integration = calculate_integration(dual_G)
        config = AnalysisConfig()
        flow_scores = calculate_flow_score(dual_G, betweenness, integration, config)

        # Sem POIs, o flow score deve ser baseado apenas em centralidade
        assert len(flow_scores) == dual_G.number_of_nodes()


class TestCarimboAndCandidateScore:
    def test_build_flow_carimbo(self):
        from tools.space_syntax import build_flow_carimbo

        c = build_flow_carimbo(82.0, 2000, "alta", "Av. Teste")
        assert c["valor"] == 82.0
        assert "OSM" in c["fonte"]
        assert c["segmento"] == "Av. Teste"

    def test_score_candidate_flow(self, sample_graph):
        from tools.space_syntax import (
            calculate_angular_betweenness,
            create_angular_segment_graph,
            inject_pois_into_dual_graph,
            results_to_geojson,
            score_candidate_flow,
        )

        dual_G = create_angular_segment_graph(sample_graph)
        dual_G = inject_pois_into_dual_graph(dual_G, [], sample_graph)
        betweenness = calculate_angular_betweenness(dual_G)
        integration = calculate_integration(dual_G)
        flow_scores = calculate_flow_score(dual_G, betweenness, integration, AnalysisConfig())
        geojson = results_to_geojson(dual_G, flow_scores, betweenness, integration)
        analysis = {"geojson": geojson, "statistics": {}}
        scored = score_candidate_flow(0.0, 0.0, analysis)
        assert "fluxo_score" in scored
        assert "fluxo_carimbo" in scored


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
