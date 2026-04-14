from src.utils.llm_client import LLMClient
from typing import Dict
import logging
import json

logger = logging.getLogger(__name__)


class HumanFactorScorer:
    FACTORS = ['visibility', 'space_limit', 'object_movement', 'ergonomic_impact', 'repetitiveness']

    SAFETY_FACTORS = ['high_voltage', 'chemical_risk', 'fire_explosion', 'personal_injury']

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def score_human_factors(self, component_name: str, context: str = '') -> Dict[str, float]:
        prompt = f'''评估部件 {component_name} 的人力操作难度。

上下文信息：{context}

请对以下5个人力因素给出0-1的评分（0=非常容易，1=非常困难）：
1. 可视性(visibility)：操作时是否容易看到
2. 空间限制(space_limit)：操作空间是否受限
3. 物体移动要求(object_movement)：是否需要移动重物
4. 人因工程影响(ergonomic_impact)：是否对人体工程学有挑战
5. 重复性(repetitiveness)：是否需要重复操作

返回JSON格式：
{{"visibility": 0.0-1.0, "space_limit": 0.0-1.0, "object_movement": 0.0-1.0, "ergonomic_impact": 0.0-1.0, "repetitiveness": 0.0-1.0}}
'''

        try:
            result = self.llm.generate(prompt)
            scores = json.loads(result)
            return scores
        except Exception as e:
            logger.error(f"Human factor scoring failed: {e}")
            return {f: 0.5 for f in self.FACTORS}

    def score_safety_factors(self, component_name: str, context: str = '') -> Dict[str, float]:
        prompt = f'''评估部件 {component_name} 的安全风险。

上下文信息：{context}

请对以下4个安全因素给出0-1的评分（0=无风险，1=高风险）：
1. 高压风险(high_voltage)：是否涉及高压电
2. 化学试剂风险(chemical_risk)：是否有腐蚀性/有毒化学物质
3. 火灾爆炸风险(fire_explosion)：是否有起火/爆炸风险
4. 人身伤害风险(personal_injury)：是否可能造成人身伤害

返回JSON格式：
{{"high_voltage": 0.0-1.0, "chemical_risk": 0.0-1.0, "fire_explosion": 0.0-1.0, "personal_injury": 0.0-1.0}}
'''

        try:
            result = self.llm.generate(prompt)
            scores = json.loads(result)
            return scores
        except Exception as e:
            logger.error(f"Safety factor scoring failed: {e}")
            return {f: 0.5 for f in self.SAFETY_FACTORS}

    def score_all(self, component_name: str, context: str = '') -> Dict:
        human_scores = self.score_human_factors(component_name, context)
        safety_scores = self.score_safety_factors(component_name, context)

        return {
            'component': component_name,
            'human_scores': human_scores,
            'safety_scores': safety_scores
        }