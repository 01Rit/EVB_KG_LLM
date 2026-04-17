import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class EntropyWeightCalculator:
    H_FACTOR_NAMES = ['H1_visibility', 'H2_space_limitation', 'H3_object_movement',
                      'H4_ergonomic_impact', 'H5_repetitiveness']

    S_FACTOR_NAMES = ['S1_high_voltage', 'S2_chemical_reagent', 'S3_fire_explosion', 'S4_human_injury']

    D_FACTOR_NAMES = ['Lh_human_loss', 'Lr_robot_loss']

    def __init__(self, k: float = 1.0):
        self.k = k

    def _normalize(self, values: List[float]) -> List[float]:
        total = sum(values)
        if total == 0:
            return [1.0 / len(values)] * len(values)
        return [v / total for v in values]

    def _calculate_entropy(self, p: List[float]) -> float:
        m = len(p)
        k = 1.0 / np.log(m) if m > 1 else 1.0
        entropy = 0.0
        for pi in p:
            if pi > 0:
                entropy -= pi * np.log(pi)
        return k * entropy

    def calculate_weights(self, expert_scores: List[Dict[str, float]],
                          factor_names: List[str]) -> List[float]:
        if len(expert_scores) < 2:
            return [1.0 / len(factor_names)] * len(factor_names)

        factor_values = []
        for fname in factor_names:
            values = [max(0.001, scores.get(fname, 0.0)) for scores in expert_scores]
            normalized = self._normalize(values)
            entropy = self._calculate_entropy(normalized)
            factor_values.append(1.0 - entropy)

        total = sum(factor_values)
        if total == 0:
            return [1.0 / len(factor_names)] * len(factor_names)

        return [fv / total for fv in factor_values]

    def calculate_final_scores(self, expert_scores: List[Dict[str, float]]) -> Dict[str, float]:
        h_weights = self.calculate_weights(expert_scores, self.H_FACTOR_NAMES)
        s_weights = self.calculate_weights(expert_scores, self.S_FACTOR_NAMES)

        h_raw_scores = []
        s_raw_scores = []
        human_losses = []
        robot_losses = []

        for scores in expert_scores:
            h_vals = [max(0.0, min(3.0, scores.get(f, 1.5))) for f in self.H_FACTOR_NAMES]
            s_vals = [max(0.0, min(3.0, scores.get(f, 1.5))) for f in self.S_FACTOR_NAMES]
            h_raw_scores.append(h_vals)
            s_raw_scores.append(s_vals)
            human_losses.append(max(0.0, min(3.0, scores.get('Lh_human_loss', 1.5))))
            robot_losses.append(max(0.0, min(3.0, scores.get('Lr_robot_loss', 1.5))))

        avg_h = np.mean(h_raw_scores, axis=0)
        avg_s = np.mean(s_raw_scores, axis=0)

        h_weighted = sum(v * w for v, w in zip(avg_h, h_weights))
        s_weighted = sum(v * w for v, w in zip(avg_s, s_weights))

        h_score = round(h_weighted / 3.0, 3)
        s_score = round(s_weighted / 3.0, 3)
        as_score = round(0.5 * (h_score + s_score), 3)

        avg_human_loss = round(np.mean(human_losses), 3)
        avg_robot_loss = round(np.mean(robot_losses), 3)

        return {
            'h_score': h_score,
            's_score': s_score,
            'as_score': as_score,
            'human_loss': avg_human_loss,
            'robot_loss': avg_robot_loss,
            'loss_diff': round(avg_human_loss - avg_robot_loss, 3),
        }
