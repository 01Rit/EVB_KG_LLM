"""Tests for L4 Evaluation API routes."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    with patch("src.api.eval_routes.Neo4jClient") as mock_neo4j_cls, \
         patch("src.api.eval_routes.LLMClient") as mock_llm_cls, \
         patch("src.api.eval_routes.settings") as mock_settings:
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "test"
        mock_settings.openai_api_key = "sk-test"
        mock_settings.openai_base_url = "http://localhost:8080"
        mock_settings.llm_model = "test-model"

        mock_neo4j = MagicMock()
        mock_neo4j.execute_query.return_value = []
        mock_neo4j_cls.return_value = mock_neo4j
        mock_llm_cls.return_value = MagicMock()

        from src.api.eval_routes import router, closed_loop
        from fastapi import FastAPI

        # Clear rules between tests
        closed_loop.rule_engine._rules.clear()

        app = FastAPI()
        app.include_router(router)
        yield TestClient(app)


# ── Rule CRUD Tests ──


class TestRuleCRUD:
    def test_create_rule(self, client):
        resp = client.post("/api/v1/evaluation/rules", json={
            "name": "螺栓易拆",
            "description": "螺栓连接便于拆卸",
            "conclusion_score": 0.8,
            "conclusion_grade": "高",
            "weight": 1.0,
            "conditions": [
                {"condition_type": "REQUIRES_CONNECTION", "target_label": "螺栓连接"},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "螺栓易拆"
        assert data["data"]["status"] == "active"
        assert data["data"]["rule_id"].startswith("rule_")

    def test_list_rules_empty(self, client):
        resp = client.get("/api/v1/evaluation/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 0

    def test_list_rules_with_data(self, client):
        client.post("/api/v1/evaluation/rules", json={
            "name": "rule1", "conclusion_score": 0.5, "conclusion_grade": "中",
        })
        client.post("/api/v1/evaluation/rules", json={
            "name": "rule2", "conclusion_score": 0.7, "conclusion_grade": "高",
        })
        resp = client.get("/api/v1/evaluation/rules")
        assert resp.json()["data"]["total"] == 2

    def test_list_rules_filter_status(self, client):
        r = client.post("/api/v1/evaluation/rules", json={
            "name": "rule1", "conclusion_score": 0.5, "conclusion_grade": "中",
        }).json()["data"]
        rule_id = r["rule_id"]
        client.put(f"/api/v1/evaluation/rules/{rule_id}", json={"status": "disabled"})

        resp = client.get("/api/v1/evaluation/rules?status=active")
        assert resp.json()["data"]["total"] == 0

        resp = client.get("/api/v1/evaluation/rules?status=disabled")
        assert resp.json()["data"]["total"] == 1

    def test_get_rule(self, client):
        r = client.post("/api/v1/evaluation/rules", json={
            "name": "rule1", "conclusion_score": 0.5, "conclusion_grade": "中",
        }).json()["data"]
        rule_id = r["rule_id"]

        resp = client.get(f"/api/v1/evaluation/rules/{rule_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["rule_id"] == rule_id

    def test_get_rule_not_found(self, client):
        resp = client.get("/api/v1/evaluation/rules/nonexistent")
        assert resp.status_code == 404

    def test_update_rule(self, client):
        r = client.post("/api/v1/evaluation/rules", json={
            "name": "rule1", "conclusion_score": 0.5, "conclusion_grade": "中",
        }).json()["data"]
        rule_id = r["rule_id"]

        resp = client.put(f"/api/v1/evaluation/rules/{rule_id}", json={"name": "更新后"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "更新后"

    def test_update_rule_not_found(self, client):
        resp = client.put("/api/v1/evaluation/rules/nonexistent", json={"name": "x"})
        assert resp.status_code == 404

    def test_update_rule_no_fields(self, client):
        r = client.post("/api/v1/evaluation/rules", json={
            "name": "rule1", "conclusion_score": 0.5, "conclusion_grade": "中",
        }).json()["data"]
        resp = client.put(f"/api/v1/evaluation/rules/{r['rule_id']}", json={})
        assert resp.status_code == 400

    def test_delete_rule(self, client):
        r = client.post("/api/v1/evaluation/rules", json={
            "name": "rule1", "conclusion_score": 0.5, "conclusion_grade": "中",
        }).json()["data"]
        rule_id = r["rule_id"]

        resp = client.delete(f"/api/v1/evaluation/rules/{rule_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    def test_delete_rule_not_found(self, client):
        resp = client.delete("/api/v1/evaluation/rules/nonexistent")
        assert resp.status_code == 404


# ── Assessment Tests ──


class TestAssessment:
    def test_assess_version(self, client):
        # Create a rule first
        client.post("/api/v1/evaluation/rules", json={
            "name": "螺栓易拆",
            "conclusion_score": 0.8,
            "conclusion_grade": "高",
            "conditions": [
                {"condition_type": "REQUIRES_CONNECTION", "target_label": "螺栓连接"},
            ],
        })

        # Create a version with component/connection IDs
        resp = client.post("/api/v1/evaluation/versions", json={
            "design_name": "Audi A3",
            "component_ids": ["电池外壳"],
            "connection_ids": ["螺栓连接"],
        })
        version_id = resp.json()["data"]["version_id"]

        # Assess
        resp = client.post("/api/v1/evaluation/assess", json={"version_id": version_id})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["overall_score"] == 0.8
        assert data["overall_grade"] == "高"
        assert len(data["rule_matches"]) == 1

    def test_get_assessment(self, client):
        # Create version and assess
        client.post("/api/v1/evaluation/rules", json={
            "name": "r1", "conclusion_score": 0.5, "conclusion_grade": "中",
        })
        resp = client.post("/api/v1/evaluation/versions", json={
            "design_name": "test", "version_number": 1,
            "subgraph": {"nodes": [], "relationships": []},
        })
        version_id = resp.json()["data"]["version_id"]
        assess_resp = client.post("/api/v1/evaluation/assess", json={"version_id": version_id})
        assessment_id = assess_resp.json()["data"]["assessment_id"]

        resp = client.get(f"/api/v1/evaluation/assessments/{assessment_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["assessment_id"] == assessment_id


# ── Version Tests ──


class TestVersions:
    def test_create_version(self, client):
        resp = client.post("/api/v1/evaluation/versions", json={
            "design_name": "Audi A3",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["design_name"] == "Audi A3"
        assert data["version_id"].startswith("v_")

    def test_list_versions(self, client):
        resp = client.get("/api/v1/evaluation/versions")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] >= 0

    def test_get_version(self, client):
        resp = client.post("/api/v1/evaluation/versions", json={
            "design_name": "test",
        })
        vid = resp.json()["data"]["version_id"]
        resp = client.get(f"/api/v1/evaluation/versions/{vid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["version_id"] == vid


# ── Predict Tests ──


class TestPredict:
    def test_predict_design(self, client):
        client.post("/api/v1/evaluation/rules", json={
            "name": "螺栓易拆",
            "conclusion_score": 0.8,
            "conclusion_grade": "高",
            "conditions": [
                {"condition_type": "REQUIRES_CONNECTION", "target_label": "螺栓连接"},
            ],
        })

        resp = client.post("/api/v1/evaluation/predict", json={
            "connection_types": ["螺栓连接"],
            "tool_requirements": [],
            "structure_features": [],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["predicted_score"] == 0.8
        assert data["predicted_grade"] == "高"
        assert len(data["matched_rules"]) == 1
        assert data["risk_factors"] == []

    def test_predict_no_rules(self, client):
        resp = client.post("/api/v1/evaluation/predict", json={
            "connection_types": ["螺栓连接"],
            "tool_requirements": [],
            "structure_features": [],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["predicted_score"] == 0.0
