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

        if neo4j_client:
            community_detector = CommunityDetector(neo4j_client, llm_client)
            self.global_engine = GlobalQueryEngine(neo4j_client, llm_client, community_detector)
        else:
            self.global_engine = None
    
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
                'steps': final_plan.get('steps', []),
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