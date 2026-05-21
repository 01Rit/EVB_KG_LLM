"""Import handler: LLM extraction of L4 rules from L2 documents + consistency check."""
import json
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    CandidateRule, L4Rule, L4RuleCreate, L4RuleCondition, Grade, RuleStatus,
)

logger = logging.getLogger(__name__)


class ImportHandler:
    """Extracts candidate L4 rules from documents using LLM, validates consistency."""

    EXTRACTION_PROMPT = """你是一个动力电池拆卸领域专家。请从以下文档内容中提取可拆卸性评价规则。

每条规则应包含:
- name: 规则名称
- description: 规则描述
- conclusion_score: 匹配时的评分 (0-1)
- conclusion_grade: 等级 ("优秀"/"良好"/"合格"/"不可再制造")
- weight: 规则权重 (默认1.0)
- conditions: 条件列表，每项包含 condition_type 和 target_label
  condition_type 可选: REQUIRES_CONNECTION, REQUIRES_TOOL, REQUIRES_STRUCTURE, CONSTRAINED_BY

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
                # Strip markdown code blocks if present
                cleaned = response.strip()
                if cleaned.startswith('```'):
                    # Remove first line (```json or ```)
                    lines = cleaned.split('\n')
                    if lines[0].strip().startswith('```'):
                        lines = lines[1:]
                    # Remove last line (```)
                    if lines and lines[-1].strip() == '```':
                        lines = lines[:-1]
                    cleaned = '\n'.join(lines)
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
