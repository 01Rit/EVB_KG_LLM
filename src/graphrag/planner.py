from typing import Optional
from src.graphrag.query_rewriter import QueryRewriter
from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.generator import PlanGenerator
from src.graphrag.feedback import FeedbackLoop
from src.graphrag.community import CommunityDetector
from src.graphrag.global_query import GlobalQueryEngine
from src.kg.models import EvidenceGraph
from src.utils.llm_client import LLMClient
from src.sequence.time_estimator import TimeEstimator
import logging
import time

logger = logging.getLogger(__name__)


class Planner:
    def __init__(self, llm_client: LLMClient, retriever: MultiPathRetriever, neo4j_client=None,
                 milvus_client=None, use_constraint_retriever: bool = False):
        self.rewriter = QueryRewriter(llm_client)
        self.ranker = EvidenceRanker()
        self.generator = PlanGenerator(llm_client)
        self._neo4j_client = neo4j_client

        if neo4j_client:
            from src.graphrag.cross_layer_retriever import CrossLayerRetriever
            self.cross_layer_retriever = CrossLayerRetriever(neo4j_client, milvus_client, llm_client)
        else:
            self.cross_layer_retriever = None

        if use_constraint_retriever and neo4j_client:
            from src.graphrag.constraint_engine import ConstraintEngine
            from src.graphrag.constrained_retriever import ConstraintAwareRetriever
            constraint_engine = ConstraintEngine(neo4j_client)
            self.retriever = ConstraintAwareRetriever(neo4j_client, None, constraint_engine)
        else:
            self.retriever = retriever

        self.llm_client = llm_client
        self.feedback = FeedbackLoop(self.retriever, self.ranker, self.generator, llm_client)

        if neo4j_client:
            community_detector = CommunityDetector(neo4j_client, llm_client)
            self.global_engine = GlobalQueryEngine(neo4j_client, llm_client, community_detector)
        else:
            self.global_engine = None

    def _enrich_steps_with_scores(self, steps: list, battery_model: str, all_components: list = None) -> list:
        """Enrich steps with scoring data from Neo4j.

        Args:
            steps: LLM 生成的拆卸步骤
            battery_model: 电池型号
            all_components: 从 Neo4j 检索的组件列表（EvidenceNode 或 dict）
        """
        if not steps or not self._neo4j_client:
            return steps

        try:
            # 从 Neo4j 获取评分数据
            cypher = '''
            MATCH (c:Component {battery_model: $model})
            WHERE c.as_score IS NOT NULL
            RETURN c.id as id, c.name as name, c.as_score as as_score, c.h_weighted_score as h_score,
                   c.s_weighted_score as s_score, c.human_loss as human_loss,
                   c.robot_loss as robot_loss, c.loss_diff as loss_diff, c.assignee as assignee,
                   c.time_score as time_score
            '''
            results = self._neo4j_client.execute_query(cypher, {'model': battery_model})
            score_map_by_id = {r.get('id', ''): r for r in results if r.get('id')}
            score_map_by_name = {r.get('name', ''): r for r in results if r.get('name')}

            # 建立 evidence_graph 节点映射（用于中英文匹配）
            node_name_to_scores = {}
            if all_components:
                for comp in all_components:
                    if hasattr(comp, 'name'):
                        node_name = comp.name
                    elif isinstance(comp, dict):
                        node_name = comp.get('name', '')
                    else:
                        continue
                    if node_name:
                        # 尝试通过 ID 查找对应的 scores
                        if hasattr(comp, 'id'):
                            comp_id = comp.id
                        elif isinstance(comp, dict):
                            comp_id = comp.get('id', '')
                        else:
                            comp_id = ''
                        if comp_id in score_map_by_id:
                            node_name_to_scores[node_name] = score_map_by_id[comp_id]
                        elif node_name in score_map_by_name:
                            node_name_to_scores[node_name] = score_map_by_name[node_name]

            enriched_steps = []
            for step in steps:
                component = step.get('component', '')
                scores = score_map_by_id.get(component, {})
                if not scores:
                    scores = score_map_by_name.get(component, {})
                if not scores and node_name_to_scores:
                    # 尝试通过模糊匹配查找 scores
                    component_lower = component.lower().replace('_', ' ').replace('-', ' ')
                    for node_name, sc in node_name_to_scores.items():
                        node_name_lower = node_name.lower().replace('_', ' ').replace('-', ' ')
                        if component_lower in node_name_lower or node_name_lower in component_lower:
                            scores = sc
                            break
                        # 尝试关键词匹配
                        component_words = set(component_lower.split('_'))
                        node_words = set(node_name_lower.split('_'))
                        if component_words & node_words and len(component_words & node_words) >= 1:
                            scores = sc
                            break
                if scores:
                    full_name = scores.get('name', component)
                    scores_for_merge = {k: v for k, v in scores.items() if k not in ('id', 'name')}
                    step = {**step, **scores_for_merge, 'component_name': full_name}
                else:
                    step['component_name'] = component
                enriched_steps.append(step)
            return enriched_steps
        except Exception as e:
            logger.warning(f'Failed to enrich steps with scores: {e}')
            return steps

    def _enrich_steps_with_remanufacturing(self, steps: list, battery_model: str) -> list:
        from src.graphrag.remanufacturing_scorer import RemanufacturingScorer
        scorer = RemanufacturingScorer()
        return scorer.score_all_steps(steps, battery_model)
    
    async def plan(self, query: str, battery_model: str, context: Optional[list[str]] = None,
                   mode: str = "local", debug: bool = False) -> dict:
        """Execute planning query.
        
        Args:
            mode: "local" for entity-focused retrieval, "global" for community-based Map-Reduce
        """
        if mode == "global":
            return await self._plan_global(query, battery_model, context, debug)
        return await self._plan_local(query, battery_model, context, debug)

    async def _plan_global(self, query: str, battery_model: str,
                          context: Optional[list[str]], debug: bool) -> dict:
        """Global query using community detection and Map-Reduce."""
        if not self.global_engine:
            return {'code': 1, 'message': 'Global query not available', 'data': {}}

        trace = {'timing': {}} if debug else None
        start = time.time()

        result = self.global_engine.query(query)

        if debug:
            trace['timing']['total_ms'] = int((time.time() - start) * 1000)

        response = {
            'code': 0,
            'message': 'Success',
            'data': {
                'response': result.get('response', ''),
                'mode': 'global'
            }
        }

        if debug:
            response['data']['trace'] = trace

        return response

    async def _plan_local(self, query: str, battery_model: str,
                          context: Optional[list[str]], debug: bool) -> dict:
        """Local query using entity-focused retrieval."""
        trace = {'timing': {}} if debug else None
        
        start = time.time()
        if debug:
            trace['start_time'] = start
        
        try:
            rewritten_intents = self.rewriter.rewrite(query, context)
            if not rewritten_intents:
                rewritten_intents = [query]
        except Exception as e:
            logger.warning(f'Rewrite failed, using original: {e}')
            rewritten_intents = [query]
        if debug:
            trace['rewritten_queries'] = rewritten_intents
            trace['timing']['rewrite_ms'] = int((time.time() - start) * 1000)
        
        start = time.time()
        evidence_graph = await self.retriever.retrieve(rewritten_intents, battery_model=battery_model)

        all_components = self.retriever.get_all_components(battery_model)
        all_relations = self.retriever.get_all_relations(battery_model)

        kg_context = self._format_kg_context(all_components, all_relations)

        if debug:
            trace['retrieval_nodes'] = len(evidence_graph.nodes)
            trace['timing']['retrieve_ms'] = int((time.time() - start) * 1000)
            trace['all_components_count'] = len(all_components)
            trace['all_relations_count'] = len(all_relations)

        start = time.time()

        if self.cross_layer_retriever and self.cross_layer_retriever.linker:
            if self.cross_layer_retriever.should_trigger(evidence_graph, rewritten_intents):
                try:
                    cross_layer_graph = self.cross_layer_retriever.retrieve_cross_layer(
                        battery_model=battery_model,
                        intents=rewritten_intents
                    )
                    if cross_layer_graph and cross_layer_graph.nodes:
                        existing_ids = {n.id for n in evidence_graph.nodes}
                        for node in cross_layer_graph.nodes:
                            if node.id not in existing_ids:
                                evidence_graph.nodes.append(node)
                        for edge in cross_layer_graph.edges:
                            evidence_graph.edges.append(edge)
                        if debug:
                            trace['cross_layer_triggered'] = True
                            trace['cross_layer_nodes_added'] = len(cross_layer_graph.nodes)
                            trace['cross_layer_edges_added'] = len(cross_layer_graph.edges)
                    else:
                        if debug:
                            trace['cross_layer_triggered'] = True
                            trace['cross_layer_triggered_but_no_results'] = True
                except Exception as e:
                    logger.warning(f"Cross-layer retrieval failed: {e}")
                    if debug:
                        trace['cross_layer_error'] = str(e)
            else:
                if debug:
                    trace['cross_layer_triggered'] = False
                    trace['cross_layer_skip_reason'] = 'graph_sufficient'

        if evidence_graph.nodes:
            ranked_evidence = self.ranker.rank(evidence_graph.nodes, query)
            evidence_graph.nodes = ranked_evidence
        else:
            ranked_evidence = []
        
        start = time.time()
        initial_plan = self.generator.generate(query, evidence_graph, battery_model, context, kg_context)

        # 新增：证据追溯
        from src.graphrag.evidence_tracer import EvidenceTracer
        tracer = EvidenceTracer()

        if initial_plan.get('steps'):
            initial_plan['steps'] = tracer.trace_all_steps(initial_plan['steps'], evidence_graph)

        if debug:
            trace['timing']['generate_ms'] = int((time.time() - start) * 1000)
        
        start = time.time()
        final_plan, evidence_graph, reasoning_traces = await self.feedback.refine(
            query, initial_plan, evidence_graph, battery_model, rewritten_intents, context
        )

        steps = final_plan.get('steps', [])
        steps = self._enrich_steps_with_scores(steps, battery_model, all_components)
        steps = self._enrich_steps_with_remanufacturing(steps, battery_model)

        time_estimator = TimeEstimator()
        for step in steps:
            time_score = step.get('time_score') or 1.5
            step['time_seconds'] = time_estimator.calculate_time_from_score(time_score)

        total_time_seconds = sum(s['time_seconds'] for s in steps)

        parallel_batches = compute_parallel_batches(steps)
        total_time_seconds = max((b['start_time'] + b['duration'] for b in parallel_batches), default=0)

        if debug:
            trace['timing']['feedback_ms'] = int((time.time() - start) * 1000)
            trace['iteration_count'] = iterations
            trace['final_evidence_count'] = len(evidence_graph.nodes)
            trace['timing']['total_ms'] = int((time.time() - trace['start_time']) * 1000)
            trace['evidence_graph'] = {
                'nodes': [{'id': n.id, 'type': n.node_type, 'name': n.name} for n in evidence_graph.nodes[:20]],
                'edges': evidence_graph.edges[:20]
            }

        # 计算最终置信度
        final_confidence = 0.0
        if reasoning_traces:
            final_confidence = reasoning_traces[-1].confidence if reasoning_traces[-1].confidence else 0.0

        result = {
            'code': 0,
            'message': 'Success',
            'data': {
                'steps': steps,
                'parallel_batches': parallel_batches,
                'total_time_seconds': total_time_seconds,
                'mode': 'local',
                'reasoning_traces': [t.to_dict() for t in reasoning_traces],
                'total_feedback_iterations': len(reasoning_traces),
                'final_confidence': final_confidence,
            }
        }

        if debug:
            result['data']['trace'] = trace

        return result

    def _format_kg_context(self, components: list, relations: list) -> str:
        if not components:
            return "No components found in knowledge graph."

        lines = ["=== Knowledge Graph Context ==="]
        lines.append(f"\n## Components ({len(components)} total):")
        for c in components[:20]:
            if hasattr(c, 'name'):
                name = c.name
            else:
                name = c.get('name', 'Unknown')
            lines.append(f"- {name}")

        if relations:
            lines.append(f"\n## Relations ({len(relations)} total):")
            for r in relations[:20]:
                head = r.get('head', '')
                rel = r.get('relation', '')
                tail = r.get('tail', '')
                lines.append(f"- {head} --[{rel}]--> {tail}")

        return "\n".join(lines)


def compute_parallel_batches(steps):
    """调度任务：考虑depends_on依赖 + 资源约束（人类串行，机器人串行）

    返回 ParallelBatch[] 格式，而非 steps[]
    """
    if not steps:
        return []

    sorted_steps = sorted(steps, key=lambda s: s.get('id', 0))

    human_time = 0
    robot_time = 0

    for step in sorted_steps:
        duration = step.get('time_seconds', 0)
        assignee = step.get('assignee', 'human')
        deps = step.get('depends_on', [])

        # 计算依赖完成时间
        dep_end_time = 0
        for dep_id in deps:
            dep_step = next((s for s in sorted_steps if s.get('id') == dep_id), None)
            if dep_step:
                dep_end = dep_step.get('start_time', 0) + dep_step.get('time_seconds', 0)
                dep_end_time = max(dep_end_time, dep_end)

        if assignee == 'robot':
            start_time = max(robot_time, dep_end_time)
            step['start_time'] = start_time
            robot_time = start_time + duration
        else:  # human
            start_time = max(human_time, dep_end_time)
            step['start_time'] = start_time
            human_time = start_time + duration

        step['duration'] = duration

    # 构建真正的并行批次
    # 按 start_time 分组，同一时刻开始的任务组成一个批次
    batches = []
    batch_map = {}  # start_time -> batch_index

    for step in sorted_steps:
        st = step.get('start_time', 0)
        if st not in batch_map:
            batch_map[st] = len(batches)
            batches.append({
                'batch_id': len(batches) + 1,
                'tasks': [],
                'start_time': st,
                'duration': 0
            })
        batch_idx = batch_map[st]
        batches[batch_idx]['tasks'].append(step.get('id'))
        batches[batch_idx]['duration'] = max(batches[batch_idx]['duration'], step.get('duration', 0))

    return batches