"""L4 Rule Engine: CRUD operations and graph-pattern condition matching."""
import logging
import uuid
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
