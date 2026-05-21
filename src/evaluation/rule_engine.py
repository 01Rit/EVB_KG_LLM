"""L4 Rule Engine: CRUD operations and graph-pattern condition matching."""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from src.evaluation.models import (
    L4Rule, L4RuleCreate, L4RuleCondition, RuleStatus, Grade, Dimension,
)
from src.evaluation.fuzzy_scorer import FuzzyScorer

logger = logging.getLogger(__name__)


class RuleEngine:
    """Manages L4_Rule lifecycle and graph-pattern matching."""

    def __init__(self, neo4j_client, fuzzy_scorer: Optional[FuzzyScorer] = None):
        self.neo4j = neo4j_client
        self.fuzzy_scorer = fuzzy_scorer
        self._rules: dict[str, L4Rule] = {}
        self._load_from_neo4j()

    def _load_from_neo4j(self):
        """Load all L4Rule nodes and their conditions from Neo4j into memory."""
        try:
            rows = self.neo4j.execute_query(
                """
                MATCH (r:L4Rule)
                OPTIONAL MATCH (r)-[rel:HAS_CONDITION]->(c:L4RuleCondition)
                RETURN r.rule_id AS rule_id, r.name AS name, r.description AS description,
                       r.conclusion_score AS conclusion_score, r.conclusion_grade AS conclusion_grade,
                       r.weight AS weight, r.status AS status, r.dimension AS dimension,
                       r.fuzzy_threshold AS fuzzy_threshold, r.source_doc_id AS source_doc_id,
                       r.created_at AS created_at, r.updated_at AS updated_at,
                       collect({
                           condition_type: c.condition_type,
                           target_label: c.target_label,
                           target_id: c.target_id,
                           effect: c.effect,
                           fuzzy_threshold: c.fuzzy_threshold,
                           idx: rel.condition_index
                       }) AS conditions
                """
            )
            for row in rows:
                raw_conds = [c for c in row["conditions"] if c.get("condition_type")]
                raw_conds.sort(key=lambda c: c.get("idx") or 0)
                conditions = [
                    L4RuleCondition(
                        condition_type=c["condition_type"],
                        target_label=c["target_label"],
                        target_id=c.get("target_id"),
                        effect=c.get("effect"),
                        fuzzy_threshold=c.get("fuzzy_threshold", 0.6),
                    )
                    for c in raw_conds
                ]
                rule = L4Rule(
                    rule_id=row["rule_id"],
                    name=row["name"],
                    description=row.get("description", ""),
                    conclusion_score=row["conclusion_score"],
                    conclusion_grade=Grade(row["conclusion_grade"]),
                    weight=row.get("weight", 1.0),
                    status=RuleStatus(row["status"]),
                    conditions=conditions,
                    source_doc_id=row.get("source_doc_id"),
                    dimension=Dimension(row.get("dimension", "technical")),
                    fuzzy_threshold=row.get("fuzzy_threshold", 0.6),
                    created_at=row.get("created_at"),
                    updated_at=row.get("updated_at"),
                )
                self._rules[rule.rule_id] = rule
            if rows:
                logger.info(f"Loaded {len(rows)} L4Rule(s) from Neo4j")
        except Exception as e:
            logger.warning(f"Failed to load L4Rules from Neo4j: {e}")

    def _persist_rule(self, rule: L4Rule):
        """Save a rule and its conditions to Neo4j."""
        now = datetime.now().isoformat()
        if not rule.created_at:
            rule.created_at = now
        rule.updated_at = now

        props = {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "conclusion_score": rule.conclusion_score,
            "conclusion_grade": rule.conclusion_grade.value,
            "weight": rule.weight,
            "status": rule.status.value,
            "dimension": rule.dimension.value,
            "fuzzy_threshold": rule.fuzzy_threshold,
            "source_doc_id": rule.source_doc_id or "",
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
        }
        cond_data = [
            {
                "condition_type": c.condition_type,
                "target_label": c.target_label,
                "target_id": c.target_id or "",
                "effect": c.effect,
                "fuzzy_threshold": c.fuzzy_threshold,
                "idx": i,
            }
            for i, c in enumerate(rule.conditions)
        ]
        try:
            self.neo4j.execute_query(
                """
                MERGE (r:L4Rule {rule_id: $rule_id})
                SET r += $props
                WITH r
                OPTIONAL MATCH (r)-[rel:HAS_CONDITION]->(c:L4RuleCondition)
                DELETE rel, c
                WITH r
                UNWIND $conditions AS cond_data
                CREATE (c:L4RuleCondition {
                    condition_type: cond_data.condition_type,
                    target_label: cond_data.target_label,
                    target_id: cond_data.target_id,
                    effect: cond_data.effect,
                    fuzzy_threshold: cond_data.fuzzy_threshold
                })
                CREATE (r)-[:HAS_CONDITION {condition_index: cond_data.idx}]->(c)
                """,
                {"rule_id": rule.rule_id, "props": props, "conditions": cond_data},
            )
        except Exception as e:
            logger.error(f"Failed to persist L4Rule {rule.rule_id}: {e}")

    def _remove_rule(self, rule_id: str):
        """Delete a rule and its conditions from Neo4j."""
        try:
            self.neo4j.execute_query(
                """
                MATCH (r:L4Rule {rule_id: $rule_id})
                OPTIONAL MATCH (r)-[rel:HAS_CONDITION]->(c:L4RuleCondition)
                DELETE rel, c, r
                """,
                {"rule_id": rule_id},
            )
        except Exception as e:
            logger.error(f"Failed to remove L4Rule {rule_id} from Neo4j: {e}")

    def create_rule(self, data: L4RuleCreate) -> L4Rule:
        rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        rule = L4Rule(
            rule_id=rule_id,
            name=data.name,
            description=data.description,
            conclusion_score=data.conclusion_score,
            conclusion_grade=data.conclusion_grade,
            weight=data.weight,
            status=RuleStatus.ACTIVE,
            conditions=data.conditions,
            source_doc_id=data.source_doc_id,
            dimension=data.dimension,
        )
        self._rules[rule_id] = rule
        self._persist_rule(rule)
        return rule

    def get_rules(self, status: Optional[RuleStatus] = None) -> list[L4Rule]:
        rules = list(self._rules.values())
        if status:
            rules = [r for r in rules if r.status == status]
        return rules

    def get_rule_by_id(self, rule_id: str) -> Optional[L4Rule]:
        return self._rules.get(rule_id)

    def update_rule(self, rule_id: str, **kwargs) -> Optional[L4Rule]:
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        data = rule.model_dump()
        data.update(kwargs)
        updated = L4Rule(**data)
        self._rules[rule_id] = updated
        self._persist_rule(updated)
        return updated

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._remove_rule(rule_id)
            del self._rules[rule_id]
            return True
        return False

    def match_rule(self, rule: L4Rule, subgraph: dict) -> tuple[float, list[dict]]:
        """Check if all conditions of a rule match the given subgraph.

        Returns (score, details) where score is 0.0~1.0 and details is a list of per-condition results.
        """
        details = []
        condition_scores = []

        for cond in rule.conditions:
            score = self._match_condition(cond, subgraph, rule)
            is_match = score >= cond.fuzzy_threshold
            details.append({
                "condition_type": cond.condition_type,
                "target_label": cond.target_label,
                "matched": is_match,
                "fuzzy_score": score,
                "effect": cond.effect,
            })
            condition_scores.append(score)

        rule_score = sum(condition_scores) / len(condition_scores) if condition_scores else 0.0
        rule_matched = rule_score >= rule.fuzzy_threshold if rule.conditions else True

        return rule_score if rule_matched else 0.0, details

    def _match_condition(self, condition: L4RuleCondition, subgraph: dict, rule: L4Rule) -> float:
        """Match a single graph-pattern condition against a subgraph."""
        rel_type_map = {
            "REQUIRES_CONNECTION": "USES_CONNECTION",
            "REQUIRES_TOOL": "REQUIRES_TOOL",
            "REQUIRES_STRUCTURE": "HAS_FEATURE",
            "CONSTRAINED_BY": "CONSTRAINED_BY",
        }

        expected_rel = rel_type_map.get(condition.condition_type)
        if not expected_rel:
            return 0.0

        target_name = condition.target_label
        nodes_by_id = {n["id"]: n for n in subgraph.get("nodes", [])}

        # Try exact match first
        for rel in subgraph.get("relationships", []):
            if rel["type"] != expected_rel:
                continue
            end_node = nodes_by_id.get(rel["end"], {})
            if end_node.get("name") == target_name:
                return 1.0

        # Fuzzy match via FuzzyScorer
        if self.fuzzy_scorer:
            best_score = 0.0
            for rel in subgraph.get("relationships", []):
                if rel["type"] != expected_rel:
                    continue
                end_node = nodes_by_id.get(rel["end"], {})
                actual_name = end_node.get("name", "")
                if not actual_name:
                    continue
                score = self.fuzzy_scorer.score(
                    condition_type=condition.condition_type,
                    target_label=target_name,
                    actual_name=actual_name,
                    actual_labels=", ".join(end_node.get("labels", [])),
                    rule_name=rule.name,
                    rule_description=rule.description,
                    dimension=rule.dimension,
                    conclusion_score=rule.conclusion_score,
                    conclusion_grade=rule.conclusion_grade.value,
                )
                best_score = max(best_score, score)
            return best_score

        return 0.0
