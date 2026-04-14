from src.graphrag.query_rewriter import QueryRewriter
from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.generator import PlanGenerator
from src.graphrag.feedback import FeedbackLoop
from src.kg.models import EvidenceGraph
from src.utils.llm_client import LLMClient
import logging
import time

logger = logging.getLogger(__name__)


class Planner:
    def __init__(self, llm_client: LLMClient, retriever: MultiPathRetriever):
        self.rewriter = QueryRewriter(llm_client)
        self.retriever = retriever
        self.ranker = EvidenceRanker()
        self.generator = PlanGenerator(llm_client)
        self.feedback = FeedbackLoop(retriever, self.ranker, self.generator)
    
    async def plan(self, query: str, battery_model: str, context: list[str] = None,
                   debug: bool = False) -> dict:
        trace = {'timing': {}} if debug else None
        
        start = time.time()
        if debug:
            trace['start_time'] = start
        
        rewritten_intents = self.rewriter.rewrite(query, context)
        if debug:
            trace['rewritten_queries'] = rewritten_intents
            trace['timing']['rewrite_ms'] = int((time.time() - start) * 1000)
        
        start = time.time()
        evidence_graph = await self.retriever.retrieve(rewritten_intents)
        if debug:
            trace['retrieval_nodes'] = len(evidence_graph.nodes)
            trace['timing']['retrieve_ms'] = int((time.time() - start) * 1000)
        
        ranked_evidence = self.ranker.rank(evidence_graph.nodes, query)
        evidence_graph.nodes = ranked_evidence
        
        start = time.time()
        initial_plan = self.generator.generate(query, evidence_graph, battery_model, context)
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
                'steps': final_plan.get('steps', [])
            }
        }
        
        if debug:
            result['data']['trace'] = trace
        
        return result