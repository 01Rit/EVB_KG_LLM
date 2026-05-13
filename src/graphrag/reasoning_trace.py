from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ReasoningTrace(BaseModel):
    """迭代级推理追踪器 — 记录每次反馈迭代的检索和推理过程"""
    query: str
    iteration: int
    retrieved_nodes: List[Any] = []
    cross_layer_expansion: Dict[str, List[Any]] = {}  # l1_nodes, l2_nodes, l3_nodes
    confidence_factors: Dict[str, float] = {}  # evidence_coverage, cross_layer_depth, consistency
    confidence: float = 0.0
    reasoning_steps: List[str] = []
    web_results: List[Dict[str, Any]] = []
    missing_evidence: List[str] = []
    target_depth: int = 0  # 0=L1 only, 1=L1→L2, 2=L1→L2→L3
    confidence_result: Optional[Dict[str, Any]] = None  # 层次化置信度结果

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "iteration": self.iteration,
            "retrieved_nodes_count": len(self.retrieved_nodes),
            "cross_layer_expansion": {
                layer: len(nodes) for layer, nodes in self.cross_layer_expansion.items()
            },
            "confidence_factors": self.confidence_factors,
            "confidence": self.confidence,
            "reasoning_steps": self.reasoning_steps,
            "web_results_count": len(self.web_results),
            "missing_evidence": self.missing_evidence,
            "target_depth": self.target_depth,
            "confidence_result": self.confidence_result,
        }
