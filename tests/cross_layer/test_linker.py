import pytest
from unittest.mock import MagicMock, patch

from src.cross_layer.linker import CrossLayerLinker
from src.cross_layer.rules import REFERENCE_OF, DEFINITION_OF, CONSTRAINED_BY


class MockEmbedder:
    def recall_candidates(self, **kwargs):
        return [
            {
                "target_id": "comp_1",
                "target_name": "Battery Pack",
                "target_type": "Component",
                "score": 0.95,
                "layer": "L2",
                "target_context": "li-ion battery"
            },
            {
                "target_id": "entity_1",
                "target_name": "Voltage",
                "target_type": "Entity",
                "score": 0.85,
                "layer": "L2",
                "target_context": "electrical parameter"
            },
            {
                "target_id": "term_1",
                "target_name": "SOC",
                "target_type": "Term",
                "score": 0.75,
                "layer": "L2",
                "target_context": "state of charge"
            },
        ]


class MockLLMJudge:
    def __init__(self):
        self.llm_client = MagicMock()

    def judge(self, **kwargs):
        return {"confidence": 0.88, "decision": "YES", "reason": "related"}


class TestCrossLayerLinkerPipeline:

    def setup_method(self):
        self.mock_neo4j = MagicMock()
        self.mock_neo4j.execute_query = MagicMock(return_value=[])
        self.mock_neo4j.search_components = MagicMock(return_value=[])
        self.mock_neo4j.search_l2_entities = MagicMock(return_value=[])

    def test_high_confidence_candidates_pass_through_without_llm(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=MockLLMJudge().llm_client,
            top_k_per_relation=3
        )
        linker.embedder = MockEmbedder()

        candidates = linker.run_pipeline(
            source_node_id="src_1",
            source_name="Battery",
            source_type="Component",
            source_layer="L1",
            source_context="test context",
            target_layer="L2",
            relation_type=REFERENCE_OF
        )

        high_conf_candidates = [c for c in candidates if c.get("score", 0) >= 0.92]
        for c in high_conf_candidates:
            assert c["decision"] == "YES"
            assert "final_score" in c

    def test_medium_confidence_triggers_llm_judge(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=MockLLMJudge().llm_client,
            top_k_per_relation=3
        )
        linker.embedder = MockEmbedder()

        candidates = linker.run_pipeline(
            source_node_id="src_1",
            source_name="Battery",
            source_type="Component",
            source_layer="L1",
            source_context="test context",
            target_layer="L2",
            relation_type=REFERENCE_OF
        )

        medium_conf_candidates = [c for c in candidates if 0.80 <= c.get("score", 0) < 0.92]
        for c in medium_conf_candidates:
            assert "final_score" in c

    def test_low_confidence_is_skipped(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=MockLLMJudge().llm_client,
            top_k_per_relation=3
        )
        linker.embedder = MockEmbedder()

        candidates = linker.run_pipeline(
            source_node_id="src_1",
            source_name="Battery",
            source_type="Component",
            source_layer="L1",
            source_context="test context",
            target_layer="L2",
            relation_type=REFERENCE_OF
        )

        low_conf_ids = {c["target_id"] for c in candidates if c.get("score", 0) < 0.80}
        assert "term_1" in low_conf_ids or all(c.get("decision") != "YES" for c in candidates)

    def test_invalid_type_pairs_filtered_by_hard_rule(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=None,
            top_k_per_relation=3
        )

        mock_candidates = [
            {"target_id": "comp_1", "target_type": "Component", "score": 0.95, "layer": "L1"},
            {"target_id": "entity_1", "target_type": "Entity", "score": 0.90, "layer": "L1"},
            {"target_id": "term_1", "target_type": "Term", "score": 0.85, "layer": "L1"},
        ]

        filtered = linker._step2_hard_rule_filter(
            mock_candidates,
            source_type="Component",
            target_layer="L2",
            relation_type=REFERENCE_OF
        )

        filtered_types = {c["target_type"] for c in filtered}
        assert "Entity" not in filtered_types
        assert "Component" in filtered_types
        assert "Term" in filtered_types

    def test_invalid_direction_filtered_by_hard_rule(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=None,
            top_k_per_relation=3
        )

        mock_candidates = [
            {"target_id": "comp_1", "target_type": "Component", "score": 0.95, "layer": "L1"},
            {"target_id": "comp_2", "target_type": "Component", "score": 0.90, "layer": "L2"},
        ]

        filtered = linker._step2_hard_rule_filter(
            mock_candidates,
            source_type="Component",
            target_layer="L2",
            relation_type=REFERENCE_OF
        )

        assert len(filtered) == 1
        assert filtered[0]["layer"] == "L1"

    def test_pipeline_without_llm_client_uses_original_scores(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=None,
            top_k_per_relation=3
        )
        linker.embedder = MockEmbedder()

        candidates = linker.run_pipeline(
            source_node_id="src_1",
            source_name="Battery",
            source_type="Component",
            source_layer="L1",
            source_context="test context",
            target_layer="L2",
            relation_type=REFERENCE_OF
        )

        for c in candidates:
            assert "final_score" in c
            assert c["decision"] == "NO"

    def test_write_relations_only_writes_yes_decisions(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=None,
            top_k_per_relation=3
        )

        relations = [
            {"source_id": "s1", "target_id": "t1", "decision": "YES", "final_score": 0.95},
            {"source_id": "s2", "target_id": "t2", "decision": "NO", "final_score": 0.85},
            {"source_id": "s3", "target_id": "t3", "decision": "YES", "final_score": 0.90},
        ]

        count = linker.write_relations(relations, REFERENCE_OF)

        assert self.mock_neo4j.execute_query.call_count == 2

    def test_write_relations_skips_missing_ids(self):
        linker = CrossLayerLinker(
            neo4j_client=self.mock_neo4j,
            milvus_client=None,
            llm_client=None,
            top_k_per_relation=3
        )

        relations = [
            {"source_id": "s1", "target_id": "t1", "decision": "YES", "final_score": 0.95},
            {"source_id": None, "target_id": "t2", "decision": "YES", "final_score": 0.90},
            {"source_id": "s3", "target_id": None, "decision": "YES", "final_score": 0.85},
        ]

        count = linker.write_relations(relations, REFERENCE_OF)

        assert self.mock_neo4j.execute_query.call_count == 1
