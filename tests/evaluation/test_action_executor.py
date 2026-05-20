"""Tests for ActionExecutor."""
import pytest
from src.evaluation.action_executor import ActionExecutor
from src.evaluation.models import (
    OptimizationAction, OptimizationActionCreate, ActionOperation, ActionStatus,
)


@pytest.fixture
def executor():
    return ActionExecutor()


@pytest.fixture
def sample_subgraph():
    return {
        "nodes": [
            {"id": "n1", "labels": ["Component"], "name": "Battery"},
            {"id": "n2", "labels": ["Component"], "name": "Cover"},
            {"id": "n3", "labels": ["Tool"], "name": "Screwdriver"},
        ],
        "relationships": [
            {"start": "n1", "end": "n2", "type": "HAS_PART"},
            {"start": "n1", "end": "n3", "type": "REQUIRES_TOOL"},
        ],
    }


class TestCreateAndGetActions:
    def test_create_action(self, executor):
        data = OptimizationActionCreate(
            operation=ActionOperation.ADD_NODE,
            target_label="Component",
            payload={"name": "NewPart"},
        )
        action = executor.create_action("assess_1", data)
        assert action.action_id.startswith("act_")
        assert action.assessment_id == "assess_1"
        assert action.operation == ActionOperation.ADD_NODE
        assert action.status == ActionStatus.PROPOSED

    def test_get_actions(self, executor):
        data = OptimizationActionCreate(
            operation=ActionOperation.ADD_NODE,
            payload={"name": "X"},
        )
        executor.create_action("assess_1", data)
        executor.create_action("assess_1", data)
        executor.create_action("assess_2", data)
        actions = executor.get_actions("assess_1")
        assert len(actions) == 2
        assert all(a.assessment_id == "assess_1" for a in actions)


class TestAddNode:
    def test_add_node_to_subgraph(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.ADD_NODE,
            target_label="Component",
            payload={"id": "n4", "name": "NewCell"},
        )
        result = executor.apply_action(sample_subgraph, action)
        assert len(result["nodes"]) == 4
        ids = [n["id"] for n in result["nodes"]]
        assert "n4" in ids
        new_node = next(n for n in result["nodes"] if n["id"] == "n4")
        assert "Component" in new_node.get("labels", [])
        assert new_node["name"] == "NewCell"

    def test_add_node_generates_id_if_missing(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.ADD_NODE,
            target_label="Component",
            payload={"name": "NoIdNode"},
        )
        result = executor.apply_action(sample_subgraph, action)
        assert len(result["nodes"]) == 4
        new_node = [n for n in result["nodes"] if n.get("name") == "NoIdNode"][0]
        assert new_node["id"].startswith("new_")


class TestRemoveNode:
    def test_remove_node(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.REMOVE_NODE,
            target_id="n2",
        )
        result = executor.apply_action(sample_subgraph, action)
        assert len(result["nodes"]) == 2
        ids = [n["id"] for n in result["nodes"]]
        assert "n2" not in ids

    def test_remove_node_removes_its_relationships(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.REMOVE_NODE,
            target_id="n2",
        )
        result = executor.apply_action(sample_subgraph, action)
        for rel in result["relationships"]:
            assert rel["start"] != "n2" and rel["end"] != "n2"


class TestModifyProperty:
    def test_modify_property(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.MODIFY_PROPERTY,
            target_id="n1",
            payload={"property": "name", "new_value": "LargeBattery"},
        )
        result = executor.apply_action(sample_subgraph, action)
        node = next(n for n in result["nodes"] if n["id"] == "n1")
        assert node["name"] == "LargeBattery"


class TestAddRel:
    def test_add_relationship(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.ADD_REL,
            payload={"start": "n2", "end": "n3", "type": "MOUNTED_ON"},
        )
        result = executor.apply_action(sample_subgraph, action)
        assert len(result["relationships"]) == 3
        types = [(r["start"], r["end"], r["type"]) for r in result["relationships"]]
        assert ("n2", "n3", "MOUNTED_ON") in types


class TestRemoveRel:
    def test_remove_relationship(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.REMOVE_REL,
            payload={"start": "n1", "end": "n3", "type": "REQUIRES_TOOL"},
        )
        result = executor.apply_action(sample_subgraph, action)
        assert len(result["relationships"]) == 1
        assert result["relationships"][0]["type"] == "HAS_PART"


class TestSwapConnection:
    def test_swap_connection(self, executor, sample_subgraph):
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.SWAP_CONNECTION,
            payload={
                "remove_rel": {"start": "n1", "end": "n3", "type": "REQUIRES_TOOL"},
                "add_rel": {"start": "n1", "end": "n2", "type": "REQUIRES_TOOL"},
            },
        )
        result = executor.apply_action(sample_subgraph, action)
        assert len(result["relationships"]) == 2
        types = [(r["start"], r["end"], r["type"]) for r in result["relationships"]]
        assert ("n1", "n3", "REQUIRES_TOOL") not in types
        assert ("n1", "n2", "REQUIRES_TOOL") in types


class TestNoMutation:
    def test_apply_action_does_not_mutate_original(self, executor, sample_subgraph):
        original_len_nodes = len(sample_subgraph["nodes"])
        original_len_rels = len(sample_subgraph["relationships"])
        action = OptimizationAction(
            action_id="act_test",
            assessment_id="a1",
            operation=ActionOperation.ADD_NODE,
            target_label="Component",
            payload={"name": "Ghost"},
        )
        result = executor.apply_action(sample_subgraph, action)
        assert len(result["nodes"]) == original_len_nodes + 1
        assert len(sample_subgraph["nodes"]) == original_len_nodes
        assert len(sample_subgraph["relationships"]) == original_len_rels


class TestApplyActions:
    def test_apply_multiple_actions(self, executor, sample_subgraph):
        actions = [
            OptimizationAction(
                action_id="act_1",
                assessment_id="a1",
                operation=ActionOperation.ADD_NODE,
                target_label="Component",
                payload={"id": "n5", "name": "Cell"},
                status=ActionStatus.PROPOSED,
            ),
            OptimizationAction(
                action_id="act_2",
                assessment_id="a1",
                operation=ActionOperation.REMOVE_NODE,
                target_id="n3",
                status=ActionStatus.PROPOSED,
            ),
            OptimizationAction(
                action_id="act_3",
                assessment_id="a1",
                operation=ActionOperation.MODIFY_PROPERTY,
                target_id="n1",
                payload={"property": "name", "new_value": "ModifiedBattery"},
                status=ActionStatus.APPLIED,
            ),
        ]
        result = executor.apply_actions(sample_subgraph, actions)
        # n5 added (PROPOSED), n3 removed (PROPOSED), n1 NOT modified (APPLIED skipped)
        ids = [n["id"] for n in result["nodes"]]
        assert "n5" in ids
        assert "n3" not in ids
        node1 = next(n for n in result["nodes"] if n["id"] == "n1")
        assert node1["name"] == "Battery"


class TestMarkStatus:
    def test_mark_applied(self, executor):
        data = OptimizationActionCreate(
            operation=ActionOperation.ADD_NODE,
            payload={"name": "X"},
        )
        action = executor.create_action("a1", data)
        updated = executor.mark_applied(action.action_id)
        assert updated is not None
        assert updated.status == ActionStatus.APPLIED

    def test_mark_rejected(self, executor):
        data = OptimizationActionCreate(
            operation=ActionOperation.ADD_NODE,
            payload={"name": "X"},
        )
        action = executor.create_action("a1", data)
        updated = executor.mark_rejected(action.action_id)
        assert updated is not None
        assert updated.status == ActionStatus.REJECTED

    def test_mark_nonexistent_returns_none(self, executor):
        assert executor.mark_applied("nonexistent") is None
        assert executor.mark_rejected("nonexistent") is None
