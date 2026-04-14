from src.allocator.scorer import HumanFactorScorer
from src.allocator.as_calculator import ASCalculator
from src.utils.llm_client import LLMClient
from src.sequence.planner import DisassemblySequence
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AllocationResult(BaseModel):
    battery_model: str
    allocations: List[Dict[str, Any]]
    human_count: int
    robot_count: int
    total_time_seconds: int


class HumanRobotAllocator:
    def __init__(self, llm_client: LLMClient):
        self.scorer = HumanFactorScorer(llm_client)
        self.calculator = ASCalculator()

    def allocate(self, sequence: DisassemblySequence) -> AllocationResult:
        battery_model = sequence.battery_model
        allocations = []
        human_count = 0
        robot_count = 0

        for step in sequence.steps:
            component_name = step.get('component_name', '')
            context = f"操作: {step.get('action', '拆卸')}, 工具: {step.get('tool_required', [])}"

            try:
                scores = self.scorer.score_all(component_name, context)
                as_score = self.calculator.calculate_as_from_combined(scores)
                assignee = self.calculator.determine_assignee(as_score)
            except Exception as e:
                logger.warning(f"Scoring failed for {component_name}: {e}")
                as_score = 0.5
                assignee = 'human'

            if assignee == 'human':
                human_count += 1
            else:
                robot_count += 1

            allocations.append({
                'step': step.get('step'),
                'component': component_name,
                'as_score': as_score,
                'assignee': assignee,
                'time_seconds': step.get('time_seconds', 0)
            })

        total_time = sum(a['time_seconds'] for a in allocations)

        result = AllocationResult(
            battery_model=battery_model,
            allocations=allocations,
            human_count=human_count,
            robot_count=robot_count,
            total_time_seconds=total_time
        )

        logger.info(f"Allocated {human_count} human, {robot_count} robot tasks")
        return result