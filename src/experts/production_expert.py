from src.experts.base_expert import BaseExpert
from src.utils.llm_client import LLMClient


class ProductionExpert(BaseExpert):
    T_FACTORS = ['T_T']

    @property
    def expert_name(self) -> str:
        return "生产工艺工程师"

    @property
    def expert_role(self) -> str:
        return "负责评估拆卸工艺的复杂度和效率"
