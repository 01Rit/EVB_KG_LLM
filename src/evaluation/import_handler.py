"""Import handler: LLM extraction of L4 rules from L2 documents + consistency check."""
import json
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    CandidateRule, L4Rule, L4RuleCreate, L4RuleCondition, Grade, RuleStatus, Dimension,
)

logger = logging.getLogger(__name__)


class ImportHandler:
    """Extracts candidate L4 rules from documents using LLM, validates consistency."""

    EXTRACTION_PROMPT = """你是一个动力电池拆卸领域专家。请从以下文档内容中提取可拆卸性评价规则。

## 评价维度与指标

### 技术维度 (technical) - 8 项指标
1. 拆卸难度：零部件拆卸的难易程度
2. 连接方式：螺栓、卡扣、焊接等连接类型的可拆卸性
3. 工具需求：是否需要专用工具，工具的通用性
4. 结构可达性：零部件是否容易触及和操作
5. 清洗难度：零部件清洗的难易程度
6. 检测复杂度：零部件检测和诊断的复杂程度
7. 修复方案可行性：修复方案的可行性和成熟度
8. 装配精度要求：重新装配时的精度要求

### 经济维度 (economic) - 7 项指标
1. 拆卸时间：完成拆卸所需的时间
2. 人力成本：拆卸和再制造所需的人力成本
3. 工具/设备成本：所需工具和设备的购置/使用成本
4. 零部件回收价值：零部件的残值和再利用价值
5. 场地/耗材费用：场地占用和耗材成本
6. 再制造加工成本：再制造加工的费用
7. 再制造产品售价：再制造后产品的市场售价

### 环境维度 (environmental) - 7 项指标
1. 零部件充足程度：替换零部件的供应充足性
2. 废料产生量：拆卸和再制造过程产生的废料量
3. 污染风险：拆卸过程中的污染风险
4. 资源回收率：材料和零部件的回收利用率
5. 能源消耗：拆卸和再制造过程的能源消耗
6. 政策合规性：是否符合环保法规和政策
7. 客户接受度：客户对再制造产品的接受程度

## 每条规则应包含:
- name: 规则名称（简洁明确）
- description: 规则描述（说明评价依据）
- dimension: 评价维度 ("technical"/"economic"/"environmental")
- conclusion_score: 匹配时的评分 (0-1)
- conclusion_grade: 等级 ("优秀"/"良好"/"合格"/"不可再制造")
- weight: 规则权重 (0.5-2.0，默认1.0)
- fuzzy_threshold: 模糊匹配阈值 (0-1，默认0.6)
- conditions: 条件列表，每项包含 condition_type 和 target_label
  condition_type 可选: REQUIRES_CONNECTION, REQUIRES_TOOL, REQUIRES_STRUCTURE, CONSTRAINED_BY

## 示例

输入: "电池外壳采用螺栓连接，使用标准扳手即可拆卸，拆卸时间约5分钟。"
输出:
[
  {{
    "name": "螺栓连接易拆卸",
    "description": "电池外壳采用螺栓连接方式，拆卸简便快捷",
    "dimension": "technical",
    "conclusion_score": 0.85,
    "conclusion_grade": "优秀",
    "weight": 1.0,
    "fuzzy_threshold": 0.6,
    "conditions": [
      {{"condition_type": "REQUIRES_CONNECTION", "target_label": "螺栓连接"}},
      {{"condition_type": "REQUIRES_TOOL", "target_label": "标准扳手"}}
    ]
  }}
]

输入: "电芯通过焊接固定，需要专用切割工具，拆卸过程产生废料较多。"
输出:
[
  {{
    "name": "焊接连接难拆卸",
    "description": "电芯采用焊接固定，拆卸难度大，需要切割工具",
    "dimension": "technical",
    "conclusion_score": 0.3,
    "conclusion_grade": "不可再制造",
    "weight": 1.0,
    "fuzzy_threshold": 0.6,
    "conditions": [
      {{"condition_type": "REQUIRES_CONNECTION", "target_label": "焊接连接"}},
      {{"condition_type": "REQUIRES_TOOL", "target_label": "专用切割工具"}}
    ]
  }},
  {{
    "name": "焊接拆卸废料多",
    "description": "焊接拆卸过程产生较多废料，环境影响大",
    "dimension": "environmental",
    "conclusion_score": 0.35,
    "conclusion_grade": "合格",
    "weight": 0.8,
    "fuzzy_threshold": 0.5,
    "conditions": [
      {{"condition_type": "REQUIRES_CONNECTION", "target_label": "焊接连接"}}
    ]
  }}
]

文档内容:
{doc_content}

请以 JSON 数组格式返回，不要包含其他内容:"""

    def __init__(self, neo4j_client, llm_client):
        self.neo4j = neo4j_client
        self.llm = llm_client
        self._candidates: dict[str, CandidateRule] = {}

    def extract_from_docs(self, doc_ids: list[str]) -> list[CandidateRule]:
        candidates = []
        for doc_id in doc_ids:
            try:
                doc_content = self._fetch_doc_content(doc_id)
                logger.info(f"Fetched doc content length: {len(doc_content)}")
                prompt = self.EXTRACTION_PROMPT.format(doc_content=doc_content)
                response = self.llm.generate(prompt)
                logger.info(f"LLM response length: {len(response)}")
                cleaned = self._strip_code_blocks(response)
                logger.info(f"Cleaned response length: {len(cleaned)}")
                rules_data = json.loads(cleaned)
                logger.info(f"Parsed {len(rules_data)} rules")
                for rd in rules_data:
                    cand_id = f"cand_{uuid.uuid4().hex[:8]}"
                    conditions = [L4RuleCondition(**c) for c in rd.get("conditions", [])]
                    candidate = CandidateRule(
                        rule_id=cand_id,
                        name=rd.get("name", ""),
                        description=rd.get("description", ""),
                        conclusion_score=rd.get("conclusion_score", 0.5),
                        conclusion_grade=Grade(rd.get("conclusion_grade", "合格")),
                        weight=rd.get("weight", 1.0),
                        conditions=conditions,
                        source_doc_id=doc_id,
                        dimension=Dimension(rd.get("dimension", "technical")),
                        fuzzy_threshold=rd.get("fuzzy_threshold", 0.6),
                    )
                    self._candidates[cand_id] = candidate
                    candidates.append(candidate)
                logger.info(f"Extracted {len(rules_data)} candidates from doc {doc_id}")
            except Exception as e:
                logger.error(f"Failed to extract from doc {doc_id}: {e}")
        return candidates

    def check_consistency(self, candidates: list[CandidateRule]) -> list[CandidateRule]:
        validated = []
        for cand in candidates:
            errors = []
            for cond in cand.conditions:
                exists = self._check_entity_exists(cond.target_label)
                if not exists:
                    errors.append(
                        f"实体 '{cond.target_label}' 在知识图谱中不存在 (条件类型: {cond.condition_type})"
                    )
            updated = cand.model_copy(update={
                "consistency_valid": len(errors) == 0,
                "consistency_errors": errors,
            })
            self._candidates[cand.rule_id] = updated
            validated.append(updated)
        return validated

    def check_duplicates(self, candidates: list[CandidateRule], existing_rules: list[L4Rule]) -> list[CandidateRule]:
        """Check for duplicate rules using three-level dedup."""
        results = []
        for cand in candidates:
            # Level 1: exact name match
            if any(r.name == cand.name for r in existing_rules):
                results.append(cand.model_copy(update={"duplicate_status": "exact_match"}))
                continue

            # Level 2: condition overlap
            cand_conds = set((c.condition_type, c.target_label) for c in cand.conditions)
            overlap_found = False
            for r in existing_rules:
                rule_conds = set((c.condition_type, c.target_label) for c in r.conditions)
                if cand_conds & rule_conds:
                    results.append(cand.model_copy(update={
                        "duplicate_status": "condition_overlap",
                        "duplicate_of": r.rule_id,
                    }))
                    overlap_found = True
                    break

            if not overlap_found:
                results.append(cand)
        return results

    def _strip_code_blocks(self, response: str) -> str:
        """Strip markdown code blocks from LLM response."""
        cleaned = response.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            if lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned = '\n'.join(lines)
        return cleaned

    def _standardize_score(self, candidate: CandidateRule, existing_rules: list) -> CandidateRule:
        """Use LLM to standardize scoring against existing rule base."""
        if not existing_rules:
            return candidate

        existing_summary = "\n".join(
            f"- {r.name}: score={r.conclusion_score}, grade={r.conclusion_grade.value}, dim={r.dimension.value}"
            for r in existing_rules[:20]
        )

        prompt = f"""对比已有规则库评分标准，对候选规则的评分进行标准化调整。

已有规则库:
{existing_summary}

候选规则:
- name: {candidate.name}
- description: {candidate.description}
- dimension: {candidate.dimension.value}
- conclusion_score: {candidate.conclusion_score}
- conclusion_grade: {candidate.conclusion_grade.value}

请返回调整后的 JSON:
{{"conclusion_score": 0.0-1.0, "conclusion_grade": "优秀"/"良好"/"合格"/"不可再制造", "weight": 0.5-2.0}}"""

        try:
            response = self.llm.generate(prompt)
            cleaned = self._strip_code_blocks(response)
            data = json.loads(cleaned)
            return candidate.model_copy(update={
                "conclusion_score": data.get("conclusion_score", candidate.conclusion_score),
                "conclusion_grade": Grade(data.get("conclusion_grade", candidate.conclusion_grade.value)),
                "weight": data.get("weight", candidate.weight),
            })
        except Exception as e:
            logger.warning(f"Score standardization failed: {e}")
            return candidate

    def approve_candidate(self, candidate_id: str) -> Optional[L4Rule]:
        cand = self._candidates.get(candidate_id)
        if not cand:
            return None
        return L4Rule(
            rule_id=cand.rule_id,
            name=cand.name,
            description=cand.description,
            conclusion_score=cand.conclusion_score,
            conclusion_grade=cand.conclusion_grade,
            weight=cand.weight,
            status=RuleStatus.ACTIVE,
            conditions=cand.conditions,
            source_doc_id=cand.source_doc_id,
            dimension=cand.dimension,
            fuzzy_threshold=cand.fuzzy_threshold,
        )

    def reject_candidate(self, candidate_id: str) -> bool:
        if candidate_id in self._candidates:
            del self._candidates[candidate_id]
            return True
        return False

    def get_candidates(self) -> list[CandidateRule]:
        return list(self._candidates.values())

    def _fetch_doc_content(self, doc_id: str) -> str:
        try:
            results = self.neo4j.execute_query(
                "MATCH (d:L2_Document {doc_id: $doc_id}) RETURN d.content AS content",
                {"doc_id": doc_id}
            )
            if results:
                return results[0].get("content", "")
        except Exception as e:
            logger.error(f"Failed to fetch doc {doc_id}: {e}")
        return f"[Document {doc_id} content not available]"

    def _check_entity_exists(self, entity_name: str) -> bool:
        try:
            results = self.neo4j.execute_query(
                "MATCH (n) WHERE n.name = $name RETURN n.name AS name LIMIT 1",
                {"name": entity_name}
            )
            return len(results) > 0
        except Exception as e:
            logger.error(f"Entity existence check failed for '{entity_name}': {e}")
            return False
