from pydantic import BaseModel
from typing import List, Optional


class ReasoningLink(BaseModel):
    """推理链中的一个论点 — 绑定具体证据"""
    claim: str                      # 论点文本
    evidence_id: str                # 证据节点ID（如 "L2:doc:Assembly_Guide:12"）
    evidence_name: str               # 证据名称
    evidence_layer: int             # 1=L1, 2=L2, 3=L3
    evidence_snippet: str            # 证据原文片段
    confidence: float               # 本论点置信度 0-1


class StepReasoningChain(BaseModel):
    """一个拆卸步骤的完整推理链"""
    step_id: str
    links: List[ReasoningLink]
    overall_reasoning: str          # 汇总推理文本

    def to_display_dict(self) -> dict:
        """转换为前端展示格式"""
        return {
            "step_id": self.step_id,
            "chains": [
                {
                    "claim": link.claim,
                    "source": f"L{link.evidence_layer}:{link.evidence_name}",
                    "snippet": link.evidence_snippet,
                    "confidence": link.confidence,
                }
                for link in self.links
            ],
            "overall": self.overall_reasoning,
        }


class ConfidenceResult(BaseModel):
    """层次化置信度结果"""
    overall: float
    grade: str  # "PASS" | "WARN_CONSISTENCY" | "FAIL_DEPTH" | "FAIL_COVERAGE"
    evidence_coverage: float
    cross_layer_depth: float
    consistency: float
    method: str = "hierarchical_gates"

    @staticmethod
    def compute(factors: dict) -> "ConfidenceResult":
        """
        层次化置信度判断。
        三个因子是递进门槛，而非可公度的加权项。
        """
        coverage = factors.get("evidence_coverage", 0.0)
        depth = factors.get("cross_layer_depth", 0.0)
        consistency = factors.get("consistency", 0.0)

        if coverage < 0.3:
            grade = "FAIL_COVERAGE"
            overall = 0.25
        elif depth < 0.33:
            grade = "FAIL_DEPTH"
            overall = 0.45
        elif consistency < 0.5:
            grade = "WARN_CONSISTENCY"
            overall = 0.65
        else:
            grade = "PASS"
            overall = 0.85

        return ConfidenceResult(
            overall=overall,
            grade=grade,
            evidence_coverage=coverage,
            cross_layer_depth=depth,
            consistency=consistency,
        )
