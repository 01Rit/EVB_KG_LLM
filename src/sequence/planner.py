from src.sequence.cycle_detector import CycleDetector
from src.sequence.topological_sort import TopologicalSort
from src.sequence.time_estimator import TimeEstimator
from src.kg.client import Neo4jClient
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DisassemblySequence(BaseModel):
    battery_model: str
    steps: List[Dict[str, Any]]
    parallel_groups: List[List[str]]
    total_time_seconds: int
    cycle_count: int


class SequencePlanner:
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None):
        self.neo4j = neo4j_client
        self.cycle_detector = CycleDetector()
        self.topological_sort = TopologicalSort()
        self.time_estimator = TimeEstimator()

    def plan(self, battery_model: str, components: List[Dict] = None) -> DisassemblySequence:
        if components is None:
            components = self._load_components(battery_model)

        if not components:
            logger.warning(f"No components found for {battery_model}")
            return DisassemblySequence(
                battery_model=battery_model,
                steps=[],
                parallel_groups=[],
                total_time_seconds=0,
                cycle_count=0
            )

        self.cycle_detector.build_graph(components)
        cycles = self.cycle_detector.detect_cycles()
        cycle_count = len(cycles)

        if cycles:
            broken_graph = self.cycle_detector.break_cycles()
        else:
            broken_graph = self.cycle_detector.graph

        self.topological_sort.set_graph(broken_graph)
        sorted_ids = self.topological_sort.sort()
        parallel_groups = self.topological_sort.get_parallel_groups()

        component_map = {c.get('id', ''): c for c in components}
        component_map.update({c.get('name', ''): c for c in components})

        steps = []
        for step_num, comp_id in enumerate(sorted_ids, 1):
            comp = component_map.get(comp_id, {})
            time = self.time_estimator.estimate_from_component(comp)
            steps.append({
                'step': step_num,
                'component': comp_id,
                'component_name': comp.get('name', comp_id),
                'time_seconds': time,
                'tool_required': comp.get('tool_required', []),
                'safety_level': comp.get('safety_level', 1)
            })

        total_time = sum(s['time_seconds'] for s in steps)

        result = DisassemblySequence(
            battery_model=battery_model,
            steps=steps,
            parallel_groups=parallel_groups,
            total_time_seconds=total_time,
            cycle_count=cycle_count
        )

        logger.info(f"Generated sequence with {len(steps)} steps, {cycle_count} cycles")
        return result

    def _load_components(self, battery_model: str) -> List[Dict]:
        if not self.neo4j:
            return []

        cypher = '''
        MATCH (c:Component {battery_model: $model})
        RETURN c.id as id, c.name as name, c.tool_required as tool_required,
               c.safety_level as safety_level, c.precedence as precedence
        '''

        results = self.neo4j.execute_query(cypher, {'model': battery_model})

        components = []
        for r in results:
            precedence = []
            if r.get('precedence'):
                try:
                    precedence = eval(r['precedence']) if isinstance(r['precedence'], str) else r['precedence']
                except:
                    precedence = []

            components.append({
                'id': r.get('id', ''),
                'name': r.get('name', ''),
                'tool_required': r.get('tool_required', []),
                'safety_level': r.get('safety_level', 1),
                'precedence': precedence
            })

        return components