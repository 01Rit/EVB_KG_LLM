from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LLMJudge:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def judge(
        self,
        source_name: str,
        source_type: str,
        source_context: str,
        target_name: str,
        target_type: str,
        target_context: str,
        relation_type: str,
    ) -> Dict:
        if self.llm_client is None:
            logger.warning("LLM client not available, returning default judgment")
            return {
                "decision": "NO",
                "confidence": 0.5,
                "reason": "LLM client not available"
            }

        prompt = f"""You are evaluating whether a cross-layer relation should be created.

Relation Type: {relation_type}

Source Entity:
- Name: {source_name}
- Type: {source_type}
- Context: {source_context}

Target Entity:
- Name: {target_name}
- Type: {target_type}
- Context: {target_context}

Business Constraints:
- Cross-layer relations must follow the defined layer mapping rules
- REFERENCE_OF: L1->L2, linking components to entities/documents/terms
- DEFINITION_OF: L2->L3, linking entities to terms
- CONSTRAINED_BY: L1->L3, linking components to terms directly (Phase 2 only)

Evaluate if this relation is valid and meaningful. Consider:
1. Does the relation type match the layer direction?
2. Are the entity types compatible with the relation type?
3. Is the connection semantically meaningful in the battery disassembly domain?

Respond with JSON containing:
- "decision": "YES" or "NO"
- "confidence": float between 0.0 and 1.0
- "reason": brief explanation
"""

        system_message = "You are a knowledge graph expert specializing in battery disassembly planning."
        
        try:
            response = self.llm_client.generate(prompt, system_message=system_message)
            import json
            result = json.loads(response)
            return {
                "decision": result.get("decision", "NO"),
                "confidence": float(result.get("confidence", 0.5)),
                "reason": result.get("reason", "No reason provided")
            }
        except Exception as e:
            logger.error(f"LLM judgment failed: {e}")
            return {
                "decision": "NO",
                "confidence": 0.5,
                "reason": f"LLM error: {str(e)}"
            }