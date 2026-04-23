# src/graphrag/remanufacturing_scorer.py
from typing import Optional

PATHWAY_ORDER = ['discard', 'recycle', 'remanufacture', 'repair', 'reuse']

PATHWAY_WEIGHTS = {
    'discard':        {'state': 0.1, 'value': 0.1, 'env': 0.8},
    'recycle':        {'state': 0.2, 'value': 0.3, 'env': 0.5},
    'remanufacture':  {'state': 0.4, 'value': 0.4, 'env': 0.2},
    'repair':         {'state': 0.6, 'value': 0.2, 'env': 0.2},
    'reuse':          {'state': 0.8, 'value': 0.1, 'env': 0.1},
}


class RemanufacturingScorer:
    def __init__(self):
        self.pathway_order = PATHWAY_ORDER
        self.weights = PATHWAY_WEIGHTS

    def score_pathway(self, component: dict, battery_model: str) -> dict:
        state_score = self._calc_state_score(component)
        value_score = self._calc_value_score(component)
        env_score = self._calc_environment_score(component)

        final_scores = {}
        for pathway in self.pathway_order:
            w = self.weights[pathway]
            final_scores[pathway] = (
                state_score * w['state'] +
                value_score * w['value'] +
                env_score * w['env']
            )

        recommended = max(final_scores, key=final_scores.get)

        return {
            'recommended': recommended,
            'confidence': round(final_scores[recommended], 3),
            'scores': {k: round(v, 3) for k, v in final_scores.items()}
        }

    def _calc_state_score(self, component: dict) -> float:
        safety_level = component.get('safety_level', 3)
        return min(safety_level / 5.0, 1.0)

    def _calc_value_score(self, component: dict) -> float:
        value = component.get('value_score', 0.5)
        return float(value) if value else 0.5

    def _calc_environment_score(self, component: dict) -> float:
        carbon = component.get('carbon_footprint', 0.5)
        return 1.0 - min(float(carbon) if carbon else 0.5, 1.0)

    def score_all_steps(self, steps: list[dict], battery_model: str) -> list[dict]:
        for step in steps:
            component_name = step.get('component', '')
            component_data = {
                'safety_level': step.get('safety_level', 3),
                'value_score': step.get('value_score', 0.5),
                'carbon_footprint': step.get('carbon_footprint', 0.5)
            }
            result = self.score_pathway(component_data, battery_model)
            step['remanufacturing_pathway'] = result['recommended']
            step['pathway_confidence'] = result['confidence']
            step['pathway_scores'] = result['scores']
        return steps