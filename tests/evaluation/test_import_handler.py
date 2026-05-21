"""Tests for L4 ImportHandler: LLM extraction, consistency check, approve/reject."""
import json
import pytest
from src.evaluation.import_handler import ImportHandler
from src.evaluation.models import (
    CandidateRule, L4Rule, L4RuleCondition, Grade, RuleStatus,
)


class MockLLMClient:
    """Returns a fixed JSON array string of candidate rules."""

    def __init__(self, rules=None):
        self.rules = rules or [
            {
                "name": "螺栓连接易拆卸",
                "description": "使用螺栓连接的部件易于拆卸",
                "conclusion_score": 0.8,
                "conclusion_grade": "良好",
                "weight": 1.0,
                "conditions": [
                    {
                        "condition_type": "REQUIRES_CONNECTION",
                        "target_label": "螺栓连接",
                    },
                ],
            },
        ]

    def generate(self, prompt, temperature=0.1, max_tokens=2000):
        return json.dumps(self.rules, ensure_ascii=False)


class MockNeo4jClient:
    """Configurable mock for Neo4j client."""

    def __init__(self, query_results=None):
        self.query_results = query_results or {}

    def execute_query(self, query, params=None):
        params = params or {}
        for key, value in self.query_results.items():
            if key in params:
                return value
        return []


@pytest.fixture
def handler():
    return ImportHandler(
        neo4j_client=MockNeo4jClient(),
        llm_client=MockLLMClient(),
    )


# ── Extraction Tests ──


class TestExtractFromDocs:
    def test_extract_returns_candidates(self, handler):
        candidates = handler.extract_from_docs(["doc_001"])
        assert len(candidates) == 1
        cand = candidates[0]
        assert cand.rule_id.startswith("cand_")
        assert cand.name == "螺栓连接易拆卸"
        assert cand.conclusion_score == 0.8
        assert cand.conclusion_grade == Grade.GOOD
        assert len(cand.conditions) == 1
        assert cand.conditions[0].condition_type == "REQUIRES_CONNECTION"
        assert cand.source_doc_id == "doc_001"

    def test_extract_multiple_docs(self):
        llm = MockLLMClient([
            {"name": "规则A", "conclusion_score": 0.7, "conclusion_grade": "合格"},
            {"name": "规则B", "conclusion_score": 0.9, "conclusion_grade": "良好"},
        ])
        handler = ImportHandler(
            neo4j_client=MockNeo4jClient(),
            llm_client=llm,
        )
        candidates = handler.extract_from_docs(["doc1", "doc2"])
        # 2 rules per doc x 2 docs = 4
        assert len(candidates) == 4

    def test_extract_on_llm_error(self):
        class BadLLM:
            def generate(self, prompt, **kwargs):
                raise RuntimeError("LLM unavailable")

        handler = ImportHandler(
            neo4j_client=MockNeo4jClient(),
            llm_client=BadLLM(),
        )
        candidates = handler.extract_from_docs(["doc_fail"])
        assert candidates == []

    def test_get_candidates_after_extract(self, handler):
        handler.extract_from_docs(["doc_001"])
        stored = handler.get_candidates()
        assert len(stored) == 1
        assert isinstance(stored[0], CandidateRule)


# ── Consistency Tests ──


class TestCheckConsistency:
    def test_valid_when_entity_exists(self, handler):
        candidates = handler.extract_from_docs(["doc_001"])
        neo4j_exists = MockNeo4jClient(query_results={"name": [{"name": "螺栓连接"}]})
        handler.neo4j = neo4j_exists
        validated = handler.check_consistency(candidates)
        assert len(validated) == 1
        assert validated[0].consistency_valid is True
        assert validated[0].consistency_errors == []

    def test_invalid_when_entity_missing(self, handler):
        candidates = handler.extract_from_docs(["doc_001"])
        neo4j_empty = MockNeo4jClient(query_results={"name": []})
        handler.neo4j = neo4j_empty
        validated = handler.check_consistency(candidates)
        assert len(validated) == 1
        assert validated[0].consistency_valid is False
        assert len(validated[0].consistency_errors) == 1
        assert "螺栓连接" in validated[0].consistency_errors[0]

    def test_no_conditions_always_valid(self):
        llm = MockLLMClient([
            {"name": "无条件规则", "conclusion_score": 0.5, "conclusion_grade": "合格", "conditions": []},
        ])
        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=llm)
        candidates = handler.extract_from_docs(["doc1"])
        validated = handler.check_consistency(candidates)
        assert validated[0].consistency_valid is True
        assert validated[0].consistency_errors == []


# ── Approve / Reject Tests ──


class TestApproveReject:
    def test_approve_candidate(self, handler):
        candidates = handler.extract_from_docs(["doc_001"])
        cand_id = candidates[0].rule_id
        rule = handler.approve_candidate(cand_id)
        assert rule is not None
        assert isinstance(rule, L4Rule)
        assert rule.rule_id == cand_id
        assert rule.name == "螺栓连接易拆卸"
        assert rule.status == RuleStatus.ACTIVE
        assert rule.conclusion_score == 0.8

    def test_approve_nonexistent_returns_none(self, handler):
        result = handler.approve_candidate("no_such_id")
        assert result is None

    def test_reject_candidate(self, handler):
        candidates = handler.extract_from_docs(["doc_001"])
        cand_id = candidates[0].rule_id
        assert handler.reject_candidate(cand_id) is True
        assert handler.get_candidates() == []

    def test_reject_nonexistent_returns_false(self, handler):
        assert handler.reject_candidate("no_such_id") is False

    def test_approve_preserves_conditions(self, handler):
        candidates = handler.extract_from_docs(["doc_001"])
        cand_id = candidates[0].rule_id
        rule = handler.approve_candidate(cand_id)
        assert len(rule.conditions) == 1
        assert rule.conditions[0].target_label == "螺栓连接"
