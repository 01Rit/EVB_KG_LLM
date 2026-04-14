from src.graph_output.mermaid_gen import MermaidGenerator
from src.graph_output.json_builder import JSONBuilder
from src.sequence.planner import DisassemblySequence
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class GraphOutput(BaseModel):
    mermaid: str
    graph_json: Dict


class GraphOutputGenerator:
    def __init__(self):
        self.mermaid_gen = MermaidGenerator()
        self.json_builder = JSONBuilder()

    def generate(self, sequence: DisassemblySequence,
                allocations: Optional[List[Dict]] = None) -> GraphOutput:
        mermaid = self.mermaid_gen.generate(sequence)

        if sequence.parallel_groups:
            parallel_mermaid = self.mermaid_gen.generate_parallel(sequence.parallel_groups)
            mermaid += '\n\n' + parallel_mermaid

        json_output = self.json_builder.build(sequence, allocations)

        return GraphOutput(
            mermaid=mermaid,
            graph_json=json_output
        )