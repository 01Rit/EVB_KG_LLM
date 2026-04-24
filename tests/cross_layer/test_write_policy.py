import pytest

from src.cross_layer.write_policy import WritePolicy
from src.cross_layer.rules import CONFIDENCE_THRESHOLDS, REFERENCE_OF, DEFINITION_OF, CONSTRAINED_BY


class TestWritePolicy:

    def setup_method(self):
        self.policy = WritePolicy(top_k_per_relation=3)

    def test_filter_by_threshold_only_keeps_above_low_threshold(self):
        candidates = [
            {"source_id": "s1", "target_id": "t1", "final_score": 0.95},
            {"source_id": "s1", "target_id": "t2", "final_score": 0.85},
            {"source_id": "s1", "target_id": "t3", "final_score": 0.79},
            {"source_id": "s1", "target_id": "t4", "final_score": 0.50},
        ]

        filtered = self.policy.filter_by_threshold(candidates, REFERENCE_OF, CONFIDENCE_THRESHOLDS)

        assert len(filtered) == 2
        assert all(c["final_score"] >= 0.80 for c in filtered)

    def test_filter_by_threshold_unknown_relation_type_returns_all(self):
        candidates = [
            {"source_id": "s1", "target_id": "t1", "final_score": 0.10},
            {"source_id": "s1", "target_id": "t2", "final_score": 0.20},
        ]

        filtered = self.policy.filter_by_threshold(candidates, "UNKNOWN_RELATION", CONFIDENCE_THRESHOLDS)

        assert len(filtered) == 2

    def test_apply_top_k_groups_by_source_id_and_relation_type(self):
        candidates = [
            {"source_id": "s1", "target_id": "t1", "final_score": 0.95, "relation_type": REFERENCE_OF},
            {"source_id": "s1", "target_id": "t2", "final_score": 0.85, "relation_type": REFERENCE_OF},
            {"source_id": "s1", "target_id": "t3", "final_score": 0.75, "relation_type": REFERENCE_OF},
            {"source_id": "s1", "target_id": "t4", "final_score": 0.65, "relation_type": REFERENCE_OF},
            {"source_id": "s2", "target_id": "t5", "final_score": 0.90, "relation_type": REFERENCE_OF},
            {"source_id": "s2", "target_id": "t6", "final_score": 0.80, "relation_type": REFERENCE_OF},
        ]

        result = self.policy.apply_top_k(candidates, REFERENCE_OF)

        assert len(result) == 5

    def test_top_k_limit_is_respected_per_group(self):
        policy = WritePolicy(top_k_per_relation=2)

        candidates = [
            {"source_id": "s1", "target_id": "t1", "final_score": 0.95},
            {"source_id": "s1", "target_id": "t2", "final_score": 0.85},
            {"source_id": "s1", "target_id": "t3", "final_score": 0.75},
            {"source_id": "s2", "target_id": "t4", "final_score": 0.90},
            {"source_id": "s2", "target_id": "t5", "final_score": 0.80},
            {"source_id": "s2", "target_id": "t6", "final_score": 0.70},
        ]

        result = policy.apply_top_k(candidates, REFERENCE_OF)

        assert len(result) == 4

    def test_top_k_returns_sorted_by_score_within_group(self):
        candidates = [
            {"source_id": "s1", "target_id": "t1", "final_score": 0.60},
            {"source_id": "s1", "target_id": "t2", "final_score": 0.95},
            {"source_id": "s1", "target_id": "t3", "final_score": 0.75},
        ]

        result = self.policy.apply_top_k(candidates, REFERENCE_OF)

        scores = [c["final_score"] for c in result]
        assert scores == [0.95, 0.75, 0.60]

    def test_filter_by_threshold_uses_final_score_if_available(self):
        candidates = [
            {"source_id": "s1", "target_id": "t1", "score": 0.95, "final_score": 0.50},
            {"source_id": "s1", "target_id": "t2", "score": 0.95},
        ]

        filtered = self.policy.filter_by_threshold(candidates, REFERENCE_OF, CONFIDENCE_THRESHOLDS)

        assert len(filtered) == 1
        assert filtered[0]["target_id"] == "t2"

    def test_apply_top_k_with_empty_list(self):
        result = self.policy.apply_top_k([], REFERENCE_OF)
        assert result == []

    def test_apply_top_k_with_less_than_k_per_group(self):
        candidates = [
            {"source_id": "s1", "target_id": "t1", "final_score": 0.95},
            {"source_id": "s1", "target_id": "t2", "final_score": 0.85},
        ]

        result = self.policy.apply_top_k(candidates, REFERENCE_OF)

        assert len(result) == 2
