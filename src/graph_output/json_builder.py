from src.sequence.planner import DisassemblySequence
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class JSONBuilder:
    def build(self, sequence: DisassemblySequence, allocations: Optional[List[Dict]] = None) -> Dict:
        if allocations is None:
            allocations = []
        nodes = []
        edges = []

        for step in sequence.steps:
            comp = step.get('component', '')
            if not comp:
                continue

            allocation = None
            if allocations:
                for a in allocations:
                    if a.get('component') == comp:
                        allocation = a
                        break

            nodes.append({
                'id': comp,
                'label': step.get('component_name', comp),
                'assignee': allocation.get('assignee', 'human') if allocation else 'human',
                'time_seconds': step.get('time_seconds', 0),
                'safety_level': step.get('safety_level', 1),
                'tool_required': step.get('tool_required', [])
            })

        for step in sequence.steps:
            comp = step.get('component', '')
            if not comp:
                continue

            precedence = step.get('precedence', [])
            for dep in precedence:
                edges.append({
                    'from': dep,
                    'to': comp,
                    'type': 'PRECEDES'
                })

        parallel_groups = []
        for group in (sequence.parallel_groups or []):
            parallel_groups.append([str(c) for c in group])

        result = {
            'battery_model': sequence.battery_model,
            'total_time_seconds': sequence.total_time_seconds,
            'total_time_minutes': round(sequence.total_time_seconds / 60, 1),
            'cycle_count': sequence.cycle_count,
            'nodes': nodes,
            'edges': edges,
            'parallel_groups': parallel_groups,
            'human_count': sum(1 for n in nodes if n['assignee'] == 'human'),
            'robot_count': sum(1 for n in nodes if n['assignee'] == 'robot')
        }

        logger.info(f"Built JSON graph with {len(nodes)} nodes, {len(edges)} edges")
        return result