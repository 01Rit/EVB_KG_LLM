from pydantic import BaseModel
from typing import Optional, Any


class Component(BaseModel):
    id: str
    name: str
    battery_model: str
    tool_required: list[str] = []
    safety_level: int = 1
    preconditions: list[str] = []
    estimated_time: int = 0
    metadata: dict[str, Any] = {}


class Document(BaseModel):
    doc_id: str
    title: str
    source: str
    source_type: str
    content: str
    metadata: dict[str, Any] = {}


class Term(BaseModel):
    term_id: str
    definition: str
    units: Optional[str] = None
    related_components: list[str] = []


class EvidenceNode(BaseModel):
    node_type: str
    id: str
    name: str
    properties: dict[str, Any]
    relationships: list[str] = []
    text: str
    evidence_ids: list[str] = []


class EvidenceGraph(BaseModel):
    nodes: list[EvidenceNode] = []
    edges: list[dict] = []
    
    def expand(self, new_nodes: list[EvidenceNode]):
        existing_ids = {n.id for n in self.nodes}
        for node in new_nodes:
            if node.id not in existing_ids:
                self.nodes.append(node)
    
    def to_text(self) -> str:
        lines = []
        for node in self.nodes:
            lines.append(f'[{node.node_type}: {node.name}] - {node.text}')
        if self.edges:
            lines.append('\n--- Relations ---')
            for edge in self.edges[:50]:
                s = edge.get('start') or edge.get('source') or '?'
                e = edge.get('end') or edge.get('target') or '?'
                t = edge.get('type') or edge.get('relation_type') or '?'
                lines.append(f'  {s} --[{t}]--> {e}')
        return '\n'.join(lines)