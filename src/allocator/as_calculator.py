from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ASCalculator:
    DEFAULT_H_WEIGHTS = [0.2, 0.2, 0.2, 0.2, 0.2]

    DEFAULT_S_WEIGHTS = [0.25, 0.25, 0.25, 0.25]

    def __init__(self, h_weights: List[float] = None, s_weights: List[float] = None):
        self.h_weights = h_weights or self.DEFAULT_H_WEIGHTS
        self.s_weights = s_weights or self.DEFAULT_S_WEIGHTS

    def calculate_as(self, h_scores: Dict[str, float], s_scores: Dict[str, float]) -> float:
        h_keys = ['visibility', 'space_limit', 'object_movement', 'ergonomic_impact', 'repetitiveness']
        s_keys = ['high_voltage', 'chemical_risk', 'fire_explosion', 'personal_injury']

        h_vals = [h_scores.get(k, 0.5) for k in h_keys]
        s_vals = [s_scores.get(k, 0.5) for k in s_keys]

        h_weighted = sum(v * w for v, w in zip(h_vals, self.h_weights))
        s_weighted = sum(v * w for v, w in zip(s_vals, self.s_weights))

        as_score = 0.5 * (h_weighted + s_weighted)

        logger.info(f"Calculated AS score: {as_score:.3f}")
        return round(as_score, 3)

    def calculate_as_from_combined(self, combined_scores: Dict) -> float:
        h_scores = combined_scores.get('human_scores', {})
        s_scores = combined_scores.get('safety_scores', {})

        return self.calculate_as(h_scores, s_scores)

    def determine_assignee(self, as_score: float,
                         robot_cost: float = 100.0,
                         human_cost: float = 80.0) -> str:
        if as_score > 0.6:
            return 'robot'
        elif as_score < 0.4:
            return 'human'
        else:
            return 'robot' if robot_cost < human_cost else 'human'