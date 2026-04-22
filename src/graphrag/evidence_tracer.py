from typing import Optional
from src.kg.models import EvidenceNode, EvidenceGraph


class EvidenceTracer:
    def trace_step(self, step: dict, evidence_graph: EvidenceGraph) -> dict:
        step_component = step.get('component', '')
        matching_nodes = [
            n for n in evidence_graph.nodes
            if n.name == step_component or n.id == step_component
        ]
        return {
            'step_id': step.get('id'),
            'evidence_sources': [self._node_to_source(n) for n in matching_nodes]
        }

    def trace_all_steps(self, steps: list[dict], evidence_graph: EvidenceGraph) -> list[dict]:
        result = []
        for step in steps:
            trace_result = self.trace_step(step, evidence_graph)
            step['evidence_sources'] = trace_result['evidence_sources']
            result.append(step)
        return result

    def _node_to_source(self, node: EvidenceNode) -> dict:
        return {
            'node_id': node.id,
            'node_type': node.node_type,
            'name': node.name,
            'text': node.text,
            'properties': node.properties
        }