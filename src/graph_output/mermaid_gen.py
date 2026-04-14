from src.sequence.planner import DisassemblySequence
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class MermaidGenerator:
    def __init__(self):
        self.node_counter = 0

    def generate(self, sequence: DisassemblySequence) -> str:
        lines = ['graph TD']

        node_map = {}

        for step in sequence.steps:
            comp_name = step.get('component', '')
            if not comp_name:
                continue

            node_id = f"N{self.node_counter}"
            node_map[comp_name] = node_id
            self.node_counter += 1

            assignee = step.get('assignee', 'human')
            time = step.get('time_seconds', 0)

            color = 'green' if assignee == 'human' else 'blue'

            label = f"{comp_name}\\n({assignee[:1].upper()}) {time}s"
            lines.append(f'    {node_id}[{{{label}}}]')

        for step in sequence.steps:
            comp_name = step.get('component', '')
            if not comp_name:
                continue

            from_id = node_map.get(comp_name)
            if not from_id:
                continue

            precedence = step.get('precedence', [])
            if precedence:
                for dep in precedence:
                    to_id = node_map.get(dep)
                    if to_id:
                        lines.append(f'    {from_id} --> {to_id}')

        logger.info(f"Generated Mermaid graph with {len(node_map)} nodes")
        return '\\n'.join(lines)

    def generate_parallel(self, parallel_groups: List[List[str]]) -> str:
        lines = ['graph TD']

        for group in parallel_groups:
            if len(group) > 1:
                components = ', '.join(group)
                lines.append(f'    subgraph parallel_{len(lines)}')
                lines.append(f'        {components}')
                lines.append(f'    end')

        return '\\n'.join(lines)