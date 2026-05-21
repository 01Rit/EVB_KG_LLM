"""Tests for VersionManager."""
import json
import pytest
from unittest.mock import MagicMock

from src.evaluation.version_manager import VersionManager
from src.evaluation.models import DesignVersionCreate, VersionStatus


def make_mock_neo4j(component_names: dict[str, str] = None):
    """Create a mock Neo4j client that returns component data.

    Args:
        component_names: {component_id: component_name} mapping
    """
    component_names = component_names or {}

    def execute_query(query, params=None):
        params = params or {}
        # Component lookup by id
        if "MATCH (c:Component {id:" in query or "MATCH (c:Component {id: $id})" in query:
            cid = params.get("id") or params.get("cid")
            if cid and cid in component_names:
                return [{"name": component_names[cid], "attrs": "{}"}]
            return []
        # RELATES relationship lookup
        if "RELATES" in query:
            return []
        return []

    client = MagicMock()
    client.execute_query = MagicMock(side_effect=execute_query)
    return client


@pytest.fixture
def vm():
    neo4j = make_mock_neo4j({"c1": "组件A", "c2": "组件B", "a": "组件A", "b": "组件B", "c": "组件C"})
    return VersionManager(neo4j)


class TestCreateVersion:
    def test_returns_version_with_correct_fields(self, vm):
        data = DesignVersionCreate(
            design_name="battery_v1",
            component_ids=["c1", "c2"],
        )
        v = vm.create_version(data)
        assert v.version_id.startswith("v_")
        assert v.design_name == "battery_v1"
        assert v.version_number == 1
        assert v.status == VersionStatus.DRAFT
        assert v.component_count == 2

    def test_version_number_increments(self, vm):
        data = DesignVersionCreate(design_name="d", component_ids=["c1"])
        v1 = vm.create_version(data)
        v2 = vm.create_version(data)
        assert v2.version_number == v1.version_number + 1


class TestListVersions:
    def test_returns_all_versions(self, vm):
        vm.create_version(DesignVersionCreate(design_name="d1", component_ids=["c1"]))
        vm.create_version(DesignVersionCreate(design_name="d2", component_ids=["c2"]))
        assert len(vm.list_versions()) == 2

    def test_filters_by_design_name(self, vm):
        vm.create_version(DesignVersionCreate(design_name="d1", component_ids=["c1"]))
        vm.create_version(DesignVersionCreate(design_name="d2", component_ids=["c2"]))
        result = vm.list_versions(design_name="d1")
        assert len(result) == 1
        assert result[0].design_name == "d1"


class TestGetVersionDetail:
    def test_returns_detail_with_components(self, vm):
        data = DesignVersionCreate(
            design_name="d",
            component_ids=["c1", "c2"],
        )
        v = vm.create_version(data)
        detail = vm.get_version_detail(v.version_id)
        assert detail is not None
        assert len(detail.components) == 2

    def test_returns_none_for_nonexistent(self, vm):
        assert vm.get_version_detail("nonexistent") is None


class TestGetSubgraph:
    def test_returns_correct_nodes(self, vm):
        data = DesignVersionCreate(
            design_name="d",
            component_ids=["c1"],
        )
        v = vm.create_version(data)
        sg = vm.get_subgraph(v.version_id)
        node_ids = {n["id"] for n in sg["nodes"]}
        assert "c1" in node_ids
        # Node should have name from Neo4j
        c1_node = next(n for n in sg["nodes"] if n["id"] == "c1")
        assert c1_node["name"] == "组件A"
        assert "eval_attributes" in c1_node

    def test_returns_empty_for_nonexistent(self, vm):
        sg = vm.get_subgraph("nonexistent")
        assert sg == {"nodes": [], "relationships": []}


class TestUpdateVersionStatus:
    def test_changes_status(self, vm):
        v = vm.create_version(DesignVersionCreate(design_name="d", component_ids=["c1"]))
        updated = vm.update_version_status(v.version_id, VersionStatus.EVALUATED)
        assert updated is not None
        assert updated.status == VersionStatus.EVALUATED

    def test_returns_none_for_nonexistent(self, vm):
        assert vm.update_version_status("nonexistent", VersionStatus.EVALUATED) is None


class TestDiffVersions:
    def test_detects_added_and_removed_nodes(self, vm):
        v1 = vm.create_version(DesignVersionCreate(
            design_name="d", component_ids=["a", "b"],
        ))
        v2 = vm.create_version(DesignVersionCreate(
            design_name="d", component_ids=["b", "c"],
        ))
        diff = vm.diff_versions(v1.version_id, v2.version_id)
        added_ids = {n["id"] for n in diff["added"]["nodes"]}
        removed_ids = {n["id"] for n in diff["removed"]["nodes"]}
        assert "c" in added_ids
        assert "a" in removed_ids

    def test_detects_added_and_removed_rels(self, vm):
        v1 = vm.create_version(DesignVersionCreate(
            design_name="d", component_ids=["a", "b"],
        ))
        vm._subgraphs[v1.version_id]["relationships"] = [
            {"start": "a", "end": "b", "type": "NEXT"},
        ]
        v2 = vm.create_version(DesignVersionCreate(
            design_name="d", component_ids=["a", "b"],
        ))
        vm._subgraphs[v2.version_id]["relationships"] = [
            {"start": "b", "end": "a", "type": "PREV"},
        ]
        diff = vm.diff_versions(v1.version_id, v2.version_id)
        added_types = {r["type"] for r in diff["added"]["relationships"]}
        removed_types = {r["type"] for r in diff["removed"]["relationships"]}
        assert "PREV" in added_types
        assert "NEXT" in removed_types

    def test_empty_versions(self, vm):
        v1 = vm.create_version(DesignVersionCreate(design_name="d", component_ids=[]))
        v2 = vm.create_version(DesignVersionCreate(design_name="d", component_ids=[]))
        diff = vm.diff_versions(v1.version_id, v2.version_id)
        assert diff["added"] == {"nodes": [], "relationships": []}
        assert diff["removed"] == {"nodes": [], "relationships": []}
        assert diff["modified"] == []
