"""L4 Rule Engine: CRUD operations and graph-pattern condition matching."""
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    L4Rule, L4RuleCreate, L4RuleCondition, RuleStatus, Grade,
)

logger = logging.getLogger(__name__)


class RuleEngine:
    """Manages L4_Rule lifecycle and graph-pattern matching."""

    def __init__(self, neo4j_client):
        self.neo4j = neo4j_client
        self._rules: dict[str, L4Rule] = {}

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
        )
        self._rules[rule_id] = rule
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
        return updated

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def match_rule(self, rule: L4Rule, subgraph: dict) -> tuple[bool, list[dict]]:
        """Check if all conditions of a rule match the given subgraph.

        Returns (matched, details) where details is a list of per-condition results.
        """
        details = []
        all_matched = True

        for cond in rule.conditions:
            is_match = self._match_condition(cond, subgraph)
            details.append({
                "condition_type": cond.condition_type,
                "target_label": cond.target_label,
                "matched": is_match,
                "effect": cond.effect,
            })
            if not is_match:
                all_matched = False

        return all_matched, details

    def _match_condition(self, condition: L4RuleCondition, subgraph: dict) -> bool:
        """Match a single graph-pattern condition against a subgraph."""
        rel_type_map = {
            "REQUIRES_CONNECTION": "USES_CONNECTION",
            "REQUIRES_TOOL": "REQUIRES_TOOL",
            "REQUIRES_STRUCTURE": "HAS_FEATURE",
            "CONSTRAINED_BY": "CONSTRAINED_BY",
        }

        expected_rel = rel_type_map.get(condition.condition_type)
        if not expected_rel:
            logger.warning(f"Unknown condition type: {condition.condition_type}")
            return False

        target_name = condition.target_label
        nodes_by_id = {n["id"]: n for n in subgraph.get("nodes", [])}

        for rel in subgraph.get("relationships", []):
            if rel["type"] != expected_rel:
                continue
            end_node = nodes_by_id.get(rel["end"], {})
            if end_node.get("name") == target_name:
                return True

        return False
