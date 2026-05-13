from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph
from src.utils.tokenizer import encode_string_by_tiktoken, tokens_to_text
from typing import Optional
import logging

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 6000


class PlanGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def _truncate_evidence(self, evidence: EvidenceGraph, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
        """Truncate evidence text to fit within token limit."""
        text = evidence.to_text()
        tokens = encode_string_by_tiktoken(text)
        if len(tokens) <= max_tokens:
            return text
        return tokens_to_text(tokens[:max_tokens])
    
    def generate(self, query: str, evidence: EvidenceGraph,
                 battery_model: str, context: Optional[list[str]] = None,
                 kg_context: str = None) -> dict:
        context_str = ', '.join(context) if context else '无'
        evidence_text = self._truncate_evidence(evidence)
        kg_info = kg_context if kg_context else evidence_text

        prompt = f'''任务: 为电池型号 {battery_model} 生成拆卸方案

用户查询: {query}
工作环境上下文: {context_str}

{kg_info}

【重要提示】
拆卸顺序规则：
1. 先拆上壳体(upper housing)、下壳体(lower housing)、绝缘层(insulator)等外层保护部件
2. 最后拆电芯(cells, modules, CMC) 和核心部件
3. 每一步需要说明依赖的前置步骤（如：必须先拆X才能拆Y）

【关键要求】
- 部件名称 (component) 必须使用【知识图谱组件列表】中的原始名称，不要自行翻译或简化
- 如果列表中没有完全匹配的部件，请选择最接近的部件名称
- 同一拆卸步骤中的多个操作应该分开成多个步骤

请生成拆卸步骤列表，格式如下:
- 步骤序号 (id)
- 部件名称 (component) - 使用知识图谱中的原始名称
- 具体操作 (action) - 描述如何拆卸，如 "拆卸上壳体"
- 所需工具 (tool) - 列出所需工具
- 安全等级 (safety_level) - 1-5的数字
- 依赖步骤 (depends_on) - 哪些步骤必须先完成（只写步骤id）
- 置信度 (confidence) - 本步骤的置信度 (0-1)
- 证据IDs (evidence_ids) - 本步骤使用的证据节点ID列表
- 推理链 (reasoning_chain) - 本步骤的推理过程，包含:
  - links: 论点列表，每个论点包含:
    - claim: 论点文本（如"为什么选择这个部件"）
    - evidence_id: 证据节点ID
    - evidence_name: 证据名称
    - evidence_layer: 证据所在层 (1=L1组件, 2=L2文档, 3=L3术语)
    - evidence_snippet: 证据原文片段
    - confidence: 本论点置信度 (0-1)
  - overall_reasoning: 本步骤的综合推理总结

请以JSON格式返回，包含steps数组，每个元素包含: id, component, action, tool, safety_level, depends_on, confidence, evidence_ids, reasoning_chain

重要：reasoning_chain.links 中的 evidence_id 必须是来自上述知识图谱中的真实节点ID，不要编造。'''

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
