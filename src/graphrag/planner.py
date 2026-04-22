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
    def __init__(self, llm_client: LLMClient, retriever: MultiPathRetriever, neo4j_client=None):
        self.rewriter = QueryRewriter(llm_client)
        self.retriever = retriever
        self.ranker = EvidenceRanker()
        self.generator = PlanGenerator(llm_client)
        self.feedback = FeedbackLoop(retriever, self.ranker, self.generator)
        self._neo4j_client = neo4j_client

        if neo4j_client:
            community_detector = CommunityDetector(neo4j_client, llm_client)
            self.global_engine = GlobalQueryEngine(neo4j_client, llm_client, community_detector)
        else:
            self.global_engine = None

    def _enrich_steps_with_scores(self, steps: list, battery_model: str) -> list:
        """Enrich steps with scoring data from Neo4j."""
        if not steps or not self._neo4j_client:
            return steps

        try:
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

            enriched_steps = []
            for step in steps:
                component = step.get('component', '')
                scores = score_map_by_id.get(component, {})
                if not scores:
                    scores = score_map_by_name.get(component, {})
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
        
        if evidence_graph.nodes:
            ranked_evidence = self.ranker.rank(evidence_graph.nodes, query)
            evidence_graph.nodes = ranked_evidence
        else:
            ranked_evidence = []
        
        start = time.time()
        initial_plan = self.generator.generate(query, evidence_graph, battery_model, context, kg_context)
        if debug:
            trace['timing']['generate_ms'] = int((time.time() - start) * 1000)
        
        start = time.time()
        final_plan, evidence_graph, iterations = await self.feedback.refine(
            query, initial_plan, evidence_graph, battery_model, context
        )

        steps = final_plan.get('steps', [])
        steps = self._enrich_steps_with_scores(steps, battery_model)

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

        result = {
            'code': 0,
            'message': 'Success',
            'data': {
                'steps': steps,
                'parallel_batches': parallel_batches,
                'total_time_seconds': total_time_seconds,
                'mode': 'local'
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
    """调度任务：考虑depends_on依赖 + 资源约束（人类串行，机器人串行）"""
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

    return steps