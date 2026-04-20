from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class TimeEstimator:
    MTM_BASE_SECONDS = 85

    TOOL_SWITCH_TIMES = {
        'screwdriver': 5,
        'wrench': 5,
        'plier': 3,
        'hammer': 2,
        'heat_gun': 10,
        'extractor': 8,
        'none': 0
    }

    POSITION_TIMES = {
        'easy': 5,
        'medium': 15,
        'difficult': 30
    }

    def __init__(self):
        self.default_tool_switch = 5
        self.default_position = 15

    def calculate_time(self, operation_time_score: float = 1.0,
                   tool_switch_time: int = 0,
                   position_move_time: int = 0) -> int:
        if tool_switch_time == 0:
            tool_switch_time = self.default_tool_switch
        if position_move_time == 0:
            position_move_time = self.default_position

        score = operation_time_score

        time_seconds = (score / 5) * self.MTM_BASE_SECONDS + tool_switch_time + position_move_time

        return int(time_seconds)

    def calculate_time_from_score(self, time_score: float) -> int:
        if time_score is None:
            time_score = 1.5
        base_time = (time_score / 3) * self.MTM_BASE_SECONDS
        return int(base_time)

    def estimate_from_component(self, component: Dict) -> int:
        time_score = component.get('time_score', 1.5)
        return self.calculate_time_from_score(time_score)

    def estimate_sequence_time(self, components: List[Dict]) -> Dict:
        total_time = 0
        details = []

        for comp in components:
            comp_id = comp.get('id', '') or comp.get('name', '')
            time = self.estimate_from_component(comp)
            total_time += time
            details.append({'component': comp_id, 'time': time})

        return {
            'total_seconds': total_time,
            'total_minutes': round(total_time / 60, 1),
            'details': details
        }