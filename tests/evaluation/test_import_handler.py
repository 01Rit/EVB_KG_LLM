"""Tests for L4 ImportHandler: LLM extraction, consistency check, approve/reject."""
import json
import pytest
from src.evaluation.import_handler import ImportHandler
from src.evaluation.models import (
    CandidateRule, L4Rule, L4RuleCondition, Grade, RuleStatus, Dimension,
)


class MockLLMClient:
    """Returns a fixed JSON array string of candidate rules."""

    def __init__(self, rules=None):
        self.rules = rules or [
            {
                "name": "螺栓连接易拆卸",
                "description": "使用螺栓连接的部件易于拆卸",
                "dimension": "technical",
                "conclusion_score": 0.8,
                "conclusion_grade": "良好",
                "weight": 1.0,
                "fuzzy_threshold": 0.6,
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
        assert cand.dimension == Dimension.TECHNICAL
        assert cand.fuzzy_threshold == 0.6

    def test_extract_multiple_docs(self):
        llm = MockLLMClient([
            {"name": "规则A", "conclusion_score": 0.7, "conclusion_grade": "合格", "dimension": "economic", "fuzzy_threshold": 0.5},
            {"name": "规则B", "conclusion_score": 0.9, "conclusion_grade": "良好", "dimension": "environmental", "fuzzy_threshold": 0.7},
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

    def test_extract_parses_dimension(self):
        llm = MockLLMClient([
            {"name": "经济规则", "conclusion_score": 0.6, "conclusion_grade": "合格", "dimension": "economic", "fuzzy_threshold": 0.5},
        ])
        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=llm)
        candidates = handler.extract_from_docs(["doc1"])
        assert candidates[0].dimension == Dimension.ECONOMIC
        assert candidates[0].fuzzy_threshold == 0.5

    def test_extract_parses_environmental_dimension(self):
        llm = MockLLMClient([
            {"name": "环境规则", "conclusion_score": 0.7, "conclusion_grade": "良好", "dimension": "environmental", "fuzzy_threshold": 0.7},
        ])
        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=llm)
        candidates = handler.extract_from_docs(["doc1"])
        assert candidates[0].dimension == Dimension.ENVIRONMENTAL
        assert candidates[0].fuzzy_threshold == 0.7

    def test_extract_defaults_dimension_technical(self):
        llm = MockLLMClient([
            {"name": "默认规则", "conclusion_score": 0.5, "conclusion_grade": "合格"},
        ])
        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=llm)
        candidates = handler.extract_from_docs(["doc1"])
        assert candidates[0].dimension == Dimension.TECHNICAL
        assert candidates[0].fuzzy_threshold == 0.6

    def test_extract_strips_code_blocks(self):
        class CodeBlockLLM:
            def generate(self, prompt, **kwargs):
                return '```json\n[{"name": "test", "conclusion_score": 0.5, "conclusion_grade": "合格", "dimension": "technical"}]\n```'

        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=CodeBlockLLM())
        candidates = handler.extract_from_docs(["doc1"])
        assert len(candidates) == 1
        assert candidates[0].name == "test"


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
            {"name": "无条件规则", "conclusion_score": 0.5, "conclusion_grade": "合格", "conditions": [], "dimension": "technical", "fuzzy_threshold": 0.6},
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
        assert rule.dimension == Dimension.TECHNICAL
        assert rule.fuzzy_threshold == 0.6

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

    def test_approve_preserves_dimension_and_fuzzy_threshold(self):
        llm = MockLLMClient([
            {"name": "环境规则", "conclusion_score": 0.7, "conclusion_grade": "良好", "dimension": "environmental", "fuzzy_threshold": 0.75, "conditions": []},
        ])
        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=llm)
        candidates = handler.extract_from_docs(["doc1"])
        cand_id = candidates[0].rule_id
        rule = handler.approve_candidate(cand_id)
        assert rule.dimension == Dimension.ENVIRONMENTAL
        assert rule.fuzzy_threshold == 0.75


# ── Strip Code Blocks Tests ──


class TestStripCodeBlocks:
    def test_strip_json_code_block(self, handler):
        response = '```json\n[{"name": "test"}]\n```'
        result = handler._strip_code_blocks(response)
        assert result == '[{"name": "test"}]'

    def test_strip_plain_code_block(self, handler):
        response = '```\n[{"name": "test"}]\n```'
        result = handler._strip_code_blocks(response)
        assert result == '[{"name": "test"}]'

    def test_no_code_block(self, handler):
        response = '[{"name": "test"}]'
        result = handler._strip_code_blocks(response)
        assert result == '[{"name": "test"}]'

    def test_strip_with_extra_whitespace(self, handler):
        response = '  ```json\n[{"name": "test"}]\n```  '
        result = handler._strip_code_blocks(response)
        assert result == '[{"name": "test"}]'


# ── Standardize Score Tests ──


class TestStandardizeScore:
    def test_standardize_adjusts_score(self):
        class AdjustLLM:
            def generate(self, prompt, **kwargs):
                return json.dumps({"conclusion_score": 0.75, "conclusion_grade": "良好", "weight": 1.2})

        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=AdjustLLM())
        candidate = CandidateRule(
            rule_id="cand_test",
            name="测试规则",
            description="测试描述",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            dimension=Dimension.TECHNICAL,
        )
        existing = [L4Rule(
            rule_id="rule_1",
            name="已有规则",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            dimension=Dimension.TECHNICAL,
        )]
        result = handler._standardize_score(candidate, existing)
        assert result.conclusion_score == 0.75
        assert result.conclusion_grade == Grade.GOOD
        assert result.weight == 1.2

    def test_standardize_returns_original_on_empty_existing(self, handler):
        candidate = CandidateRule(
            rule_id="cand_test",
            name="测试规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            dimension=Dimension.TECHNICAL,
        )
        result = handler._standardize_score(candidate, [])
        assert result.conclusion_score == 0.5
        assert result.conclusion_grade == Grade.QUALIFIED

    def test_standardize_returns_original_on_llm_error(self):
        class ErrorLLM:
            def generate(self, prompt, **kwargs):
                raise RuntimeError("LLM error")

        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=ErrorLLM())
        candidate = CandidateRule(
            rule_id="cand_test",
            name="测试规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            dimension=Dimension.TECHNICAL,
        )
        existing = [L4Rule(
            rule_id="rule_1",
            name="已有规则",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            dimension=Dimension.TECHNICAL,
        )]
        result = handler._standardize_score(candidate, existing)
        assert result.conclusion_score == 0.5
        assert result.conclusion_grade == Grade.QUALIFIED

    def test_standardize_limits_existing_to_20(self):
        class CheckLLM:
            def __init__(self):
                self.last_prompt = ""

            def generate(self, prompt, **kwargs):
                self.last_prompt = prompt
                return json.dumps({"conclusion_score": 0.6, "conclusion_grade": "合格", "weight": 1.0})

        llm = CheckLLM()
        handler = ImportHandler(neo4j_client=MockNeo4jClient(), llm_client=llm)
        candidate = CandidateRule(
            rule_id="cand_test",
            name="测试规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            dimension=Dimension.TECHNICAL,
        )
        # Create 25 existing rules
        existing = [
            L4Rule(
                rule_id=f"rule_{i}",
                name=f"规则{i}",
                conclusion_score=0.5,
                conclusion_grade=Grade.QUALIFIED,
                dimension=Dimension.TECHNICAL,
            )
            for i in range(25)
        ]
        handler._standardize_score(candidate, existing)
        # Should only include first 20 in the prompt
        assert "规则20" not in llm.last_prompt
        assert "规则0" in llm.last_prompt


# ── Check Duplicates Tests ──


class TestCheckDuplicates:
    def test_exact_name_match(self, handler):
        candidates = [CandidateRule(
            rule_id="cand_new",
            name="已有规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            dimension=Dimension.TECHNICAL,
        )]
        existing = [L4Rule(
            rule_id="rule_old",
            name="已有规则",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            dimension=Dimension.TECHNICAL,
        )]
        results = handler.check_duplicates(candidates, existing)
        assert len(results) == 1
        assert results[0].duplicate_status == "exact_match"

    def test_condition_overlap(self, handler):
        candidates = [CandidateRule(
            rule_id="cand_new",
            name="新规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            dimension=Dimension.TECHNICAL,
            conditions=[L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")],
        )]
        existing = [L4Rule(
            rule_id="rule_old",
            name="旧规则",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            dimension=Dimension.TECHNICAL,
            conditions=[L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")],
        )]
        results = handler.check_duplicates(candidates, existing)
        assert len(results) == 1
        assert results[0].duplicate_status == "condition_overlap"
        assert results[0].duplicate_of == "rule_old"

    def test_no_duplicate(self, handler):
        candidates = [CandidateRule(
            rule_id="cand_new",
            name="新规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            dimension=Dimension.TECHNICAL,
            conditions=[L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="卡扣连接")],
        )]
        existing = [L4Rule(
            rule_id="rule_old",
            name="旧规则",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            dimension=Dimension.TECHNICAL,
            conditions=[L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")],
        )]
        results = handler.check_duplicates(candidates, existing)
        assert len(results) == 1
        assert results[0].duplicate_status is None
        assert results[0].duplicate_of is None

    def test_empty_existing_rules(self, handler):
        candidates = [CandidateRule(
            rule_id="cand_new",
            name="新规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            dimension=Dimension.TECHNICAL,
        )]
        results = handler.check_duplicates(candidates, [])
        assert len(results) == 1
        assert results[0].duplicate_status is None

    def test_multiple_candidates_mixed(self, handler):
        candidates = [
            CandidateRule(
                rule_id="cand_1",
                name="已有规则",
                conclusion_score=0.5,
                conclusion_grade=Grade.QUALIFIED,
                dimension=Dimension.TECHNICAL,
            ),
            CandidateRule(
                rule_id="cand_2",
                name="新规则",
                conclusion_score=0.6,
                conclusion_grade=Grade.QUALIFIED,
                dimension=Dimension.ECONOMIC,
                conditions=[L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="专用工具")],
            ),
        ]
        existing = [
            L4Rule(
                rule_id="rule_1",
                name="已有规则",
                conclusion_score=0.8,
                conclusion_grade=Grade.GOOD,
                dimension=Dimension.TECHNICAL,
            ),
            L4Rule(
                rule_id="rule_2",
                name="其他规则",
                conclusion_score=0.7,
                conclusion_grade=Grade.GOOD,
                dimension=Dimension.TECHNICAL,
                conditions=[L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="专用工具")],
            ),
        ]
        results = handler.check_duplicates(candidates, existing)
        assert len(results) == 2
        assert results[0].duplicate_status == "exact_match"
        assert results[1].duplicate_status == "condition_overlap"
        assert results[1].duplicate_of == "rule_2"
