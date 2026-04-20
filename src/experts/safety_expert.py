from src.experts.base_expert import BaseExpert
from src.utils.llm_client import LLMClient


class SafetyExpert(BaseExpert):
    T_FACTORS = ['T_T']

    @property
    def expert_name(self) -> str:
        return "安全工程师"

    @property
    def expert_role(self) -> str:
        return "负责评估拆卸过程中的安全风险"
