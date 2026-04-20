from abc import ABC, abstractmethod
from typing import Dict, List
from src.utils.llm_client import LLMClient
import json
import logging
import re

logger = logging.getLogger(__name__)


class BaseExpert(ABC):
    H_FACTORS = ['H1_visibility', 'H2_space_limitation', 'H3_object_movement',
                 'H4_ergonomic_impact', 'H5_repetitiveness']

    S_FACTORS = ['S1_high_voltage', 'S2_chemical_reagent', 'S3_fire_explosion', 'S4_human_injury']

    D_FACTORS = ['Lh_human_loss', 'Lr_robot_loss']

    T_FACTORS = ['T_T']

    FACTOR_DESCRIPTIONS = {
        'H1_visibility': '0=完全可见, 3=完全遮挡',
        'H2_space_limitation': '0=宽敞, 3=完全限制',
        'H3_object_movement': '0=≤1kg, 3=≥15kg',
        'H4_ergonomic_impact': '0=舒适, 3=极度不适',
        'H5_repetitiveness': '0=<5次, 3=>30次',
        'S1_high_voltage': '0=无风险, 3=极高风险',
        'S2_chemical_reagent': '0=无风险, 3=高风险',
        'S3_fire_explosion': '0=无风险, 3=高风险',
        'S4_human_injury': '0=无风险, 3=高风险',
        'Lh_human_loss': '0=无损失, 3=严重损伤',
        'Lr_robot_loss': '0=无损失, 3=严重损伤',
        'T_T': '0=短暂操作(<10秒), 1=短时操作(10-30秒), 2=中时操作(30-60秒), 3=长时间操作(>60秒)',
    }

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @property
    @abstractmethod
    def expert_name(self) -> str:
        """Return expert name."""
        pass

    @property
    @abstractmethod
    def expert_role(self) -> str:
        """Return expert role description."""
        pass

    def build_scoring_prompt(self, component_name: str, context: str = '') -> str:
        factor_list = '\n'.join([f"- {f}: {self.FACTOR_DESCRIPTIONS[f]}" for f in self.H_FACTORS + self.S_FACTORS + self.D_FACTORS + self.T_FACTORS])

        return f'''你是{self.expert_name}（{self.expert_role}）。

评估部件 {component_name} 的拆卸评分因素。

上下文信息：{context if context else '无'}

请对以下因素给出0-3的评分：
{factor_list}

返回JSON格式（所有值必须是0-3的整数或浮点数）：
{{"H1_visibility": 0-3, "H2_space_limitation": 0-3, "H3_object_movement": 0-3, "H4_ergonomic_impact": 0-3, "H5_repetitiveness": 0-3, "S1_high_voltage": 0-3, "S2_chemical_reagent": 0-3, "S3_fire_explosion": 0-3, "S4_human_injury": 0-3, "Lh_human_loss": 0-3, "Lr_robot_loss": 0-3, "T_T": 0-3}}
'''

    def _extract_json(self, response: str) -> str:
        response = response.strip()
        code_block_match = re.match(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return response

    def score(self, component_name: str, context: str = '') -> Dict[str, float]:
        prompt = self.build_scoring_prompt(component_name, context)
        result = self.llm.generate(prompt)
        all_factors = self.H_FACTORS + self.S_FACTORS + self.D_FACTORS + self.T_FACTORS

        for attempt in range(2):
            try:
                json_str = self._extract_json(result) if attempt == 0 else result
                scores = json.loads(json_str)
                validated = {}
                for f in all_factors:
                    val = scores.get(f, 1.5)
                    validated[f] = max(0.0, min(3.0, float(val)))
                return validated
            except json.JSONDecodeError as e:
                if attempt == 0:
                    logger.warning(f"{self.expert_name} first parse attempt failed: {e}, response: {result[:500]}")
                    continue
                logger.error(f"{self.expert_name} scoring failed after retry: {e}, response: {result[:500]}")
                raise
