from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ConstraintEngine:
    OUTER_KEYWORDS = ['housing', 'cover', 'shell', 'case', 'cap']
    INNER_KEYWORDS = ['cell', 'module', 'cmc', 'electrode', 'insulator']

    def __init__(self, neo4j_client=None):
        self._neo4j = neo4j_client

    def infer_bidirectional_constraints(self, battery_model: str, components: list[dict]) -> list[dict]:
        constraints = []

        for i, comp in enumerate(components):
            comp_name = comp.get('name', '').lower()
            comp_safety = comp.get('safety_level', 3)

            for j, other_comp in enumerate(components):
                if i >= j:
                    continue

                other_name = other_comp.get('name', '').lower()
                other_safety = other_comp.get('safety_level', 3)

                if self._is_outer(comp_name) and self._is_inner(other_name):
                    constraints.append({
                        'head': comp.get('name'),
                        'relation': 'BEFORE',
                        'tail': other_comp.get('name')
                    })
                elif self._is_outer(other_name) and self._is_inner(comp_name):
                    constraints.append({
                        'head': other_comp.get('name'),
                        'relation': 'BEFORE',
                        'tail': comp.get('name')
                    })

                if comp_safety > other_safety:
                    constraints.append({
                        'head': comp.get('name'),
                        'relation': 'BEFORE',
                        'tail': other_comp.get('name')
                    })

        return constraints

    def _is_outer(self, name: str) -> bool:
        return any(kw in name for kw in self.OUTER_KEYWORDS)

    def _is_inner(self, name: str) -> bool:
        return any(kw in name for kw in self.INNER_KEYWORDS)