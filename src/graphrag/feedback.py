from typing import Optional

from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.generator import PlanGenerator
from src.kg.models import EvidenceGraph
import logging

logger = logging.getLogger(__name__)


class FeedbackLoop:
    def __init__(self, retriever: MultiPathRetriever, ranker: EvidenceRanker,
                 generator: PlanGenerator, max_iterations: int = 3):
        self.retriever = retriever
        self.ranker = ranker
        self.generator = generator
        self.max_iterations = max_iterations
    
    async def refine(self, query: str, initial_plan: dict, evidence: EvidenceGraph,
                     battery_model: str, context: Optional[list[str]] = None) -> tuple[dict, EvidenceGraph, int]:
        iteration_count = 0
        
        for iteration in range(self.max_iterations):
            iteration_count += 1
            logger.info(f'Feedback iteration {iteration_count}')
            
            missing_evidence = self._extract_missing_evidence(initial_plan, evidence)
            
            if not missing_evidence:
                logger.info(f'No missing evidence, stopping at iteration {iteration_count}')
                break
            
            new_nodes = await self._retrieve_missing(missing_evidence)
            evidence.expand(new_nodes)
            
            initial_plan = self.generator.regenerate(query, evidence, battery_model, context)
        
        return initial_plan, evidence, iteration_count
    
    def _extract_missing_evidence(self, plan: dict, evidence: EvidenceGraph) -> list[str]:
        missing = []
        plan_steps = plan.get('steps', [])
        
        evidence_ids = {node.id for node in evidence.nodes}
        
        for step in plan_steps:
            step_evidence = step.get('evidence', [])
            if not step_evidence or all(e not in evidence_ids for e in step_evidence):
                component = step.get('component', '')
                if component:
                    missing.append(component)
        
        return missing[:10]
    
    async def _retrieve_missing(self, missing_items: list[str]) -> list:
        all_nodes = []
        for item in missing_items:
            components = await self.retriever._retrieve_components(item, 5)
            all_nodes.extend(components)
        return all_nodes