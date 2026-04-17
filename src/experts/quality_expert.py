from src.experts.base_expert import BaseExpert
from src.utils.llm_client import LLMClient


class QualityExpert(BaseExpert):
    @property
    def expert_name(self) -> str:
        return "质量检测专家"

    @property
    def expert_role(self) -> str:
        return "负责评估拆卸过程中的质量控制和损伤风险"
