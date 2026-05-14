import ast

from src.sequence.cycle_detector import CycleDetector
from src.sequence.topological_sort import TopologicalSort
from src.sequence.time_estimator import TimeEstimator
from src.sequence.island_resolver import IsolatedNodeResolver
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

        logger.info(f"Components: {len(components)}, Cycles detected: {cycle_count}")
        logger.info(f"Component IDs: {[c.get('id') or c.get('name') for c in components]}")
        logger.info(f"Cycles: {cycles}")

        if cycles:
            broken_graph = self.cycle_detector.break_cycles()
        else:
            broken_graph = self.cycle_detector.graph

        self.topological_sort.set_graph(broken_graph)
        sorted_ids = self.topological_sort.sort()

        # 检查重复
        if len(sorted_ids) != len(set(sorted_ids)):
            logger.error(f"DUPLICATE NODES DETECTED in sorted_ids: {[x for x in sorted_ids if sorted_ids.count(x) > 1]}")
            # 去重但保持顺序
            seen = set()
            sorted_ids = [x for x in sorted_ids if not (x in seen or seen.add(x))]
            logger.info(f"After deduplication: {sorted_ids}")

        logger.info(f"Graph nodes: {list(broken_graph.nodes())}")
        logger.info(f"Graph edges: {list(broken_graph.edges())}")
        logger.info(f"Sorted IDs (topological sort): {sorted_ids}")

        isolated_nodes = [n for n in broken_graph.nodes() if broken_graph.in_degree(n) == 0 and broken_graph.out_degree(n) == 0]
        if isolated_nodes:
            logger.info(f"Found {len(isolated_nodes)} isolated nodes: {isolated_nodes}")
            resolver = IsolatedNodeResolver()
            all_node_names = list(broken_graph.nodes())
            existing_edges = list(broken_graph.edges())

            matches = resolver.resolve(isolated_nodes, all_node_names, existing_edges)

            for isolated, connected in matches.items():
                if connected:
                    broken_graph.add_edge(isolated, connected)
                    logger.info(f"Added virtual edge: {isolated} -> {connected}")

            sorted_ids = self.topological_sort.sort()

        parallel_groups = self.topological_sort.get_parallel_groups()

        component_map = {c.get('id', ''): c for c in components}
        component_map.update({c.get('name', ''): c for c in components})

        steps = []
        for step_num, comp_id in enumerate(sorted_ids, 1):
            comp = component_map.get(comp_id, {})
            time = self.time_estimator.estimate_from_component(comp)
            step_data = {
                'step': step_num,
                'id': step_num,  # 新增：兼容 DisassemblyStep
                'component': comp_id,
                'component_name': comp.get('name', comp_id),
                'time_seconds': time,
                'tool_required': comp.get('tool_required', []),
                'safety_level': comp.get('safety_level', 1)
            }
            if comp.get('as_score') is not None:
                step_data['as_score'] = comp.get('as_score')
            if comp.get('h_score') is not None:
                step_data['h_score'] = comp.get('h_score')
            if comp.get('s_score') is not None:
                step_data['s_score'] = comp.get('s_score')
            if comp.get('human_loss') is not None:
                step_data['human_loss'] = comp.get('human_loss')
            if comp.get('robot_loss') is not None:
                step_data['robot_loss'] = comp.get('robot_loss')
            if comp.get('loss_diff') is not None:
                step_data['loss_diff'] = comp.get('loss_diff')
            if comp.get('assignee') is not None:
                step_data['assignee'] = comp.get('assignee')
            steps.append(step_data)

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
        RETURN DISTINCT c.id as id, c.name as name, c.tool_required as tool_required,
               c.safety_level as safety_level, c.precedence as precedence,
               c.as_score as as_score, c.h_weighted_score as h_score,
               c.s_weighted_score as s_score, c.human_loss as human_loss,
               c.robot_loss as robot_loss, c.loss_diff as loss_diff,
               c.assignee as assignee
        '''
        results = self.neo4j.execute_query(cypher, {'model': battery_model})
        logger.info(f"Database returned {len(results)} component records")

        rel_cypher = '''
        MATCH (c1:Component)-[r:RELATES]->(c2:Component)
        WHERE c1.battery_model = $model AND r.type = '必须先于...拆卸'
        RETURN c1.name as head, c2.name as tail, r.type as relation
        '''
        relations = self.neo4j.execute_query(rel_cypher, {'model': battery_model})
        logger.info(f"Database returned {len(relations)} relations")

        return self._parse_components_with_relations(results, relations)

    def _parse_components_with_relations(self, results: List[Dict],
                                        relations: List[Dict]) -> List[Dict]:
        # 收集所有有效的组件标识符（id 和 name 都是组件可被引用的方式）
        valid_ids = set()
        name_to_id = {}
        for r in results:
            r_id = r.get('id', '')
            r_name = r.get('name', '')
            if r_id:
                valid_ids.add(r_id)
            if r_name:
                valid_ids.add(r_name)
                if r_id:
                    name_to_id[r_name] = r_id

        # 构建依赖映射（tail 组件名 -> [head 组件名, ...]）
        # 因为关系 head -> tail 表示 head 必须在 tail 之前拆卸
        # 所以 tail 依赖 head
        dep_map = {}
        for rel in relations:
            head = rel.get('head', '')
            tail = rel.get('tail', '')
            if head and tail:
                if tail not in dep_map:
                    dep_map[tail] = []
                dep_map[tail].append(head)

        components = []
        for r in results:
            comp_id = r.get('id', '')
            name = r.get('name', '')

            precedence = []
            if r.get('precedence'):
                try:
                    precedence = ast.literal_eval(r['precedence']) if isinstance(r['precedence'], str) else r['precedence']
                except (ValueError, SyntaxError):
                    logger.warning(f"Failed to parse precedence for component {comp_id}: {r.get('precedence')}")
                    precedence = []

            rel_deps = dep_map.get(name, [])

            # 标准化依赖引用：将名称引用转换为对应的组件ID
            all_deps_normalized = set()
            for dep in (precedence + rel_deps):
                if not dep:
                    continue
                # 优先使用UUID（如果dep是已知的名称，映射到ID）
                if dep in name_to_id:
                    all_deps_normalized.add(name_to_id[dep])
                elif dep in valid_ids:
                    # dep已经是ID或其他有效标识符
                    all_deps_normalized.add(dep)
                else:
                    # 不在已知组件中，仍保留（可能是外部引用）
                    all_deps_normalized.add(dep)

            all_deps = list(all_deps_normalized)

            logger.info(f"Component {name} (id={comp_id}): precedence={precedence}, rel_deps={rel_deps}, normalized_deps={all_deps}")

            components.append({
                'id': comp_id,
                'name': name,
                'tool_required': r.get('tool_required', []),
                'safety_level': r.get('safety_level', 1),
                'precedence': all_deps,
                'dependencies': all_deps,
                'as_score': r.get('as_score'),
                'h_score': r.get('h_score'),
                's_score': r.get('s_score'),
                'human_loss': r.get('human_loss'),
                'robot_loss': r.get('robot_loss'),
                'loss_diff': r.get('loss_diff'),
                'assignee': r.get('assignee')
            })

        logger.info(f"Parsed {len(components)} components: {[c.get('id') or c.get('name') for c in components]}")
        return components