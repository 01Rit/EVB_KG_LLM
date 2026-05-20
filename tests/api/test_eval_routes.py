"""Tests for L4 Evaluation API routes."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.evaluation.models import L4RuleCreate, L4RuleCondition, Grade, RuleStatus


@pytest.fixture
def client():
    # Patch the Neo4j client and its dependencies before import
    with patch("src.api.eval_routes.Neo4jClient") as mock_neo4j_cls, \
         patch("src.api.eval_routes.settings") as mock_settings:
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "test"

        mock_neo4j = MagicMock()
        mock_neo4j.execute_query.return_value = []
        mock_neo4j_cls.return_value = mock_neo4j

        from src.api.eval_routes import router, rule_engine
        from fastapi import FastAPI

        # Clear rules between tests
        rule_engine._rules.clear()

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


# ── Evaluation Tests ──


class TestEvaluation:
    def test_evaluate_design(self, client):
        # Create a rule first
        client.post("/api/v1/evaluation/rules", json={
            "name": "螺栓易拆",
            "conclusion_score": 0.8,
            "conclusion_grade": "高",
            "conditions": [
                {"condition_type": "REQUIRES_CONNECTION", "target_label": "螺栓连接"},
            ],
        })

        subgraph = {
            "nodes": [
                {"id": "n1", "name": "电池外壳", "label": "Component"},
                {"id": "n2", "name": "螺栓连接", "label": "Connection"},
            ],
            "relationships": [
                {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            ],
        }
        resp = client.post("/api/v1/evaluation/evaluate", json={
            "version_id": "v1",
            "subgraph": subgraph,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["overall_score"] == 0.8
        assert data["overall_grade"] == "高"
        assert len(data["rule_matches"]) == 1

    def test_evaluate_no_rules(self, client):
        resp = client.post("/api/v1/evaluation/evaluate", json={
            "version_id": "v1",
            "subgraph": {"nodes": [], "relationships": []},
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["overall_score"] == 0.0


# ── Feedback Tests ──


class TestFeedback:
    def test_generate_feedback(self, client):
        client.post("/api/v1/evaluation/rules", json={
            "name": "r1",
            "conclusion_score": 0.8,
            "conclusion_grade": "高",
            "conditions": [
                {"condition_type": "REQUIRES_CONNECTION", "target_label": "螺栓连接"},
            ],
        })

        assessment = {
            "assessment_id": "assess_001",
            "version_id": "v1",
            "overall_score": 0.5,
            "overall_grade": "中",
            "rule_matches": [
                {
                    "rule_id": "rule_xxx",
                    "rule_name": "r1",
                    "matched": False,
                    "score_contribution": 0.0,
                    "reason": "not matched",
                },
            ],
            "feedback_text": "test",
            "status": "pending_review",
        }
        resp = client.post("/api/v1/evaluation/feedback", json=assessment)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "summary" in data
        assert "suggestions" in data
        assert "risks" in data
