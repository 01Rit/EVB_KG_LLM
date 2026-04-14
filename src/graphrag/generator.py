from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PlanGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def generate(self, query: str, evidence: EvidenceGraph, 
                 battery_model: str, context: Optional[list[str]] = None) -> dict:
        context_str = ', '.join(context) if context else '无'
        evidence_text = evidence.to_text()
        
        prompt = f'''任务: 为电池型号 {battery_model} 生成拆卸方案
用户查询: {query}
工作环境上下文: {context_str}

参考证据:
{evidence_text}

请生成拆卸步骤列表，格式如下:
- 步骤序号
- 部件名称
- 具体操作
- 所需工具
- 安全等级
- 证据来源

请以JSON数组格式返回，每个元素包含: id, component, action, tool, safety_level, evidence'''

        try:
            result = self.llm.generate_json(prompt, ['steps'])
            logger.info(f'Generated plan with {len(result.get("steps", []))} steps')
            return result
        except Exception as e:
            logger.error(f'Plan generation failed: {e}')
            return {'error': str(e), 'steps': []}
    
    def regenerate(self, query: str, evidence: EvidenceGraph, 
                   battery_model: str, context: Optional[list[str]] = None) -> dict:
        return self.generate(query, evidence, battery_model, context)