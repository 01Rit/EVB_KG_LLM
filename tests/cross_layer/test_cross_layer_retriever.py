import pytest
from unittest.mock import MagicMock

from src.graphrag.cross_layer_retriever import CrossLayerRetriever
from src.kg.models import EvidenceGraph, EvidenceNode


class TestCrossLayerRetriever:

    def setup_method(self):
        self.mock_neo4j = MagicMock()
        self.mock_neo4j.execute_query = MagicMock(return_value=[])
        self.mock_neo4j.search_components = MagicMock(return_value=[])
        self.mock_neo4j.search_l2_entities = MagicMock(return_value=[])

    def test_should_trigger_with_fewer_than_5_nodes(self):
        from src.graphrag.cross_layer_retriever import CrossLayerRetriever

        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery", properties={}, text="battery", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n2", name="Cell", properties={}, text="cell", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n3", name="Module", properties={}, text="module", evidence_ids=[]),
            ],
            edges=[]
        )

        assert retriever.should_trigger(graph) is True

    def test_should_trigger_with_5_or_more_nodes_sparse_graph(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery", properties={}, text="battery", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n2", name="Cell", properties={}, text="cell", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n3", name="Module", properties={}, text="module", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n4", name="Pack", properties={}, text="pack", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n5", name="BMS", properties={}, text="bms", evidence_ids=[]),
            ],
            edges=[{"source": "n1", "target": "n2", "relation_type": "CONTAINS"}]
        )

        assert retriever.should_trigger(graph) is True

    def test_should_trigger_with_adequate_coverage(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery Pack", properties={}, text="li-ion battery pack for EV", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n2", name="Cell", properties={}, text="cylindrical cell", evidence_ids=[]),
                EvidenceNode(node_type="Entity", id="n3", name="Voltage", properties={}, text="electrical parameter", evidence_ids=[]),
                EvidenceNode(node_type="Entity", id="n4", name="Capacity", properties={}, text="energy capacity", evidence_ids=[]),
                EvidenceNode(node_type="Entity", id="n5", name="Temperature", properties={}, text="thermal parameter", evidence_ids=[]),
            ],
            edges=[
                {"source": "n1", "target": "n2", "relation_type": "CONTAINS"},
                {"source": "n1", "target": "n3", "relation_type": "HAS_PROPERTY"},
                {"source": "n2", "target": "n4", "relation_type": "HAS_PROPERTY"},
            ]
        )

        intents = ["Battery Pack 的 电压 是 多少"]
        result = retriever.should_trigger(graph, intents)

        assert result is False

    def test_should_trigger_with_low_coverage(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery Pack", properties={}, text="battery pack", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n2", name="Cell", properties={}, text="cell", evidence_ids=[]),
                EvidenceNode(node_type="Entity", id="n3", name="Voltage", properties={}, text="voltage", evidence_ids=[]),
                EvidenceNode(node_type="Entity", id="n4", name="Capacity", properties={}, text="capacity", evidence_ids=[]),
                EvidenceNode(node_type="Entity", id="n5", name="Temperature", properties={}, text="temperature", evidence_ids=[]),
            ],
            edges=[
                {"source": "n1", "target": "n2", "relation_type": "CONTAINS"},
                {"source": "n1", "target": "n3", "relation_type": "HAS_PROPERTY"},
            ]
        )

        intents = ["电池包 拆卸 流程"]
        result = retriever.should_trigger(graph, intents)

        assert result is True

    def test_should_trigger_dense_graph_not_triggered(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery", properties={}, text="battery", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n2", name="Cell", properties={}, text="cell", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n3", name="Module", properties={}, text="module", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n4", name="Pack", properties={}, text="pack", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n5", name="BMS", properties={}, text="bms", evidence_ids=[]),
            ],
            edges=[
                {"source": "n1", "target": "n2", "relation_type": "CONTAINS"},
                {"source": "n1", "target": "n3", "relation_type": "CONTAINS"},
                {"source": "n2", "target": "n3", "relation_type": "CONTAINS"},
                {"source": "n3", "target": "n4", "relation_type": "CONTAINS"},
                {"source": "n4", "target": "n5", "relation_type": "CONTAINS"},
            ]
        )

        result = retriever.should_trigger(graph)

        assert result is False

    def test_should_trigger_with_no_intents(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery", properties={}, text="battery", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n2", name="Cell", properties={}, text="cell", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n3", name="Module", properties={}, text="module", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n4", name="Pack", properties={}, text="pack", evidence_ids=[]),
                EvidenceNode(node_type="Component", id="n5", name="BMS", properties={}, text="bms", evidence_ids=[]),
            ],
            edges=[
                {"source": "n1", "target": "n2", "relation_type": "CONTAINS"},
                {"source": "n1", "target": "n3", "relation_type": "CONTAINS"},
                {"source": "n2", "target": "n3", "relation_type": "CONTAINS"},
            ]
        )

        result = retriever.should_trigger(graph)

        assert result is False

    def test_extract_key_terms_filters_stop_words(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        terms = retriever._extract_key_terms(["如何 拆卸 电池 包", "电池 的 电压 是 什么"])

        assert "如何" not in terms
        assert "拆卸" not in terms
        assert "电池" in terms
        assert "电压" in terms

    def test_calculate_coverage_with_matching_terms(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery Pack", properties={}, text="li-ion battery", evidence_ids=[]),
            ],
            edges=[]
        )

        key_terms = {"Battery", "Pack"}
        coverage = retriever._calculate_coverage(key_terms, graph)

        assert coverage == 1.0

    def test_calculate_coverage_with_partial_matching(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery Pack", properties={}, text="battery pack", evidence_ids=[]),
            ],
            edges=[]
        )

        key_terms = {"Battery", "Voltage", "Temperature"}
        coverage = retriever._calculate_coverage(key_terms, graph)

        assert coverage == pytest.approx(0.333, 0.01)

    def test_calculate_coverage_with_empty_key_terms(self):
        retriever = CrossLayerRetriever(self.mock_neo4j, None, None)

        graph = EvidenceGraph(
            nodes=[
                EvidenceNode(node_type="Component", id="n1", name="Battery", properties={}, text="battery", evidence_ids=[]),
            ],
            edges=[]
        )

        coverage = retriever._calculate_coverage(set(), graph)

        assert coverage == 1.0
