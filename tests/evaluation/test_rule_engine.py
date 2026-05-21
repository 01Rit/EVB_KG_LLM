"""Tests for L4 RuleEngine CRUD and graph-pattern matching."""
import pytest
from src.evaluation.rule_engine import RuleEngine
from src.evaluation.models import (
    L4RuleCreate, L4RuleCondition, RuleStatus, Grade,
)


class MockNeo4jClient:
    """Minimal mock for Neo4j client."""

    def execute_query(self, query, params=None):
        return []


@pytest.fixture
def engine():
    return RuleEngine(neo4j_client=MockNeo4jClient())


@pytest.fixture
def sample_create():
    return L4RuleCreate(
        name="螺栓连接易拆卸",
        description="使用螺栓连接的部件易于拆卸",
        conclusion_score=0.8,
        conclusion_grade=Grade.GOOD,
        weight=1.0,
        conditions=[
            L4RuleCondition(
                condition_type="REQUIRES_CONNECTION",
                target_label="螺栓连接",
                effect=0.3,
            ),
        ],
    )


@pytest.fixture
def subgraph():
    return {
        "nodes": [
            {"id": "n1", "name": "电池外壳", "label": "Component"},
            {"id": "n2", "name": "螺栓连接", "label": "Connection"},
            {"id": "n3", "name": "标准扳手", "label": "Tool"},
            {"id": "n4", "name": "可直达", "label": "Feature"},
            {"id": "n5", "name": "安全规范A", "label": "Constraint"},
        ],
        "relationships": [
            {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            {"start": "n1", "end": "n3", "type": "REQUIRES_TOOL"},
            {"start": "n1", "end": "n4", "type": "HAS_FEATURE"},
            {"start": "n1", "end": "n5", "type": "CONSTRAINED_BY"},
        ],
    }


# ── CRUD Tests ──


class TestCRUD:
    def test_create_rule(self, engine, sample_create):
        rule = engine.create_rule(sample_create)
        assert rule.rule_id.startswith("rule_")
        assert rule.name == "螺栓连接易拆卸"
        assert rule.conclusion_score == 0.8
        assert rule.conclusion_grade == Grade.GOOD
        assert rule.status == RuleStatus.ACTIVE
        assert len(rule.conditions) == 1

    def test_get_rules_empty(self, engine):
        rules = engine.get_rules()
        assert rules == []

    def test_get_rules_with_data(self, engine, sample_create):
        engine.create_rule(sample_create)
        engine.create_rule(L4RuleCreate(
            name="规则2",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
        ))
        rules = engine.get_rules()
        assert len(rules) == 2

    def test_get_rules_filter_by_status(self, engine, sample_create):
        rule = engine.create_rule(sample_create)
        engine.update_rule(rule.rule_id, status=RuleStatus.DISABLED)
        active = engine.get_rules(status=RuleStatus.ACTIVE)
        disabled = engine.get_rules(status=RuleStatus.DISABLED)
        assert len(active) == 0
        assert len(disabled) == 1

    def test_get_rule_by_id(self, engine, sample_create):
        created = engine.create_rule(sample_create)
        found = engine.get_rule_by_id(created.rule_id)
        assert found is not None
        assert found.rule_id == created.rule_id
        assert found.name == created.name

    def test_get_rule_by_id_not_found(self, engine):
        result = engine.get_rule_by_id("nonexistent")
        assert result is None

    def test_update_rule(self, engine, sample_create):
        rule = engine.create_rule(sample_create)
        updated = engine.update_rule(rule.rule_id, name="更新后的规则", weight=2.0)
        assert updated is not None
        assert updated.name == "更新后的规则"
        assert updated.weight == 2.0
        assert updated.conclusion_score == 0.8  # unchanged

    def test_update_rule_not_found(self, engine):
        result = engine.update_rule("nonexistent", name="x")
        assert result is None

    def test_delete_rule(self, engine, sample_create):
        rule = engine.create_rule(sample_create)
        assert engine.delete_rule(rule.rule_id) is True
        assert engine.get_rule_by_id(rule.rule_id) is None

    def test_delete_rule_not_found(self, engine):
        assert engine.delete_rule("nonexistent") is False


# ── Condition Matching Tests ──


class TestConditionMatching:
    def test_requires_connection_match(self, engine, subgraph):
        cond = L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")
        rule_create = L4RuleCreate(
            name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED,
            conditions=[cond],
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is True
        assert details[0]["matched"] is True

    def test_requires_connection_no_match(self, engine, subgraph):
        cond = L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接")
        rule_create = L4RuleCreate(
            name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED,
            conditions=[cond],
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is False
        assert details[0]["matched"] is False

    def test_requires_tool_match(self, engine, subgraph):
        cond = L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手")
        rule_create = L4RuleCreate(
            name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED,
            conditions=[cond],
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is True

    def test_requires_structure_match(self, engine, subgraph):
        cond = L4RuleCondition(condition_type="REQUIRES_STRUCTURE", target_label="可直达")
        rule_create = L4RuleCreate(
            name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED,
            conditions=[cond],
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is True

    def test_constrained_by_match(self, engine, subgraph):
        cond = L4RuleCondition(condition_type="CONSTRAINED_BY", target_label="安全规范A")
        rule_create = L4RuleCreate(
            name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED,
            conditions=[cond],
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is True

    def test_unknown_condition_type(self, engine, subgraph):
        cond = L4RuleCondition(condition_type="UNKNOWN_TYPE", target_label="anything")
        rule_create = L4RuleCreate(
            name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED,
            conditions=[cond],
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is False


# ── Rule Matching Tests ──


class TestRuleMatching:
    def test_all_conditions_match(self, engine, subgraph):
        conds = [
            L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
        ]
        rule_create = L4RuleCreate(
            name="multi", conclusion_score=0.9, conclusion_grade=Grade.GOOD,
            conditions=conds,
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is True
        assert len(details) == 2
        assert all(d["matched"] for d in details)

    def test_partial_no_match(self, engine, subgraph):
        conds = [
            L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
        ]
        rule_create = L4RuleCreate(
            name="partial", conclusion_score=0.7, conclusion_grade=Grade.QUALIFIED,
            conditions=conds,
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is False
        assert details[0]["matched"] is True
        assert details[1]["matched"] is False

    def test_no_conditions_always_match(self, engine, subgraph):
        rule_create = L4RuleCreate(
            name="no_conds", conclusion_score=0.5, conclusion_grade=Grade.UNQUALIFIED,
            conditions=[],
        )
        rule = engine.create_rule(rule_create)
        matched, details = engine.match_rule(rule, subgraph)
        assert matched is True
        assert details == []
