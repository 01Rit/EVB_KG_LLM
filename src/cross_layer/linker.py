from typing import Dict, List, Optional
import logging

from src.cross_layer.embedder import CrossLayerEmbedder
from src.cross_layer.rules import CrossLayerRules, CONFIDENCE_THRESHOLDS
from src.cross_layer.llm_judge import LLMJudge
from src.cross_layer.write_policy import WritePolicy

logger = logging.getLogger(__name__)


class CrossLayerLinker:
    def __init__(
        self,
        neo4j_client,
        milvus_client=None,
        llm_client=None,
        top_k_per_relation: int = 3
    ):
        self.neo4j = neo4j_client
        self.embedder = CrossLayerEmbedder(milvus_client)
        self.rules = CrossLayerRules()
        self.llm_judge = LLMJudge(llm_client) if llm_client else None
        self.write_policy = WritePolicy(top_k_per_relation=top_k_per_relation)

    def run_pipeline(
        self,
        source_node_id: str,
        source_name: str,
        source_type: str,
        source_layer: str,
        source_context: str,
        target_layer: str,
        relation_type: str
    ) -> List[Dict]:
        candidates = self._step1_embed_recall(
            source_node_id, source_name, source_type, source_context, target_layer, relation_type
        )
        
        candidates = self._step2_hard_rule_filter(
            candidates, source_type, target_layer, relation_type
        )
        
        candidates = self._step3_llm_judge(
            candidates, source_name, source_type, source_context, relation_type
        )
        
        candidates = self._step4_write_policy(candidates, relation_type)
        
        return candidates

    def run_pipeline_batch(
        self,
        sources: List[Dict],
        target_layer: str,
        relation_type: str
    ) -> List[Dict]:
        """Process multiple source nodes in batch for efficiency."""
        all_candidates = []
        for source in sources:
            try:
                candidates = self.run_pipeline(
                    source_node_id=source.get('id', ''),
                    source_name=source.get('name', ''),
                    source_type=source.get('type', 'Entity'),
                    source_layer=source.get('layer', 'L2'),
                    source_context=source.get('context', ''),
                    target_layer=target_layer,
                    relation_type=relation_type
                )
                all_candidates.extend(candidates)
            except Exception as e:
                logger.error(f"Batch pipeline failed for source {source.get('name', '')}: {e}")
                continue
        return all_candidates

    def _step1_embed_recall(
        self,
        source_node_id: str,
        source_name: str,
        source_type: str,
        source_context: str,
        target_layer: str,
        relation_type: str
    ) -> List[Dict]:
        candidates = self.embedder.recall_candidates(
            entity_name=source_name,
            entity_type=source_type,
            target_layer=target_layer,
            target_relation=relation_type,
            top_k=30
        )

        for c in candidates:
            c["source_id"] = source_node_id
            c["relation_type"] = relation_type

        return candidates

    def _step2_hard_rule_filter(
        self,
        candidates: List[Dict],
        source_type: str,
        target_layer: str,
        relation_type: str
    ) -> List[Dict]:
        filtered = []
        for c in candidates:
            target_type = c.get("target_type", "")
            
            if not self.rules.is_valid_relation_type(
                source_type, target_type, relation_type
            ):
                continue
            
            if not self.rules.is_valid_direction(
                c.get("layer", ""), target_layer, relation_type
            ):
                continue
            
            filtered.append(c)
        
        return filtered

    def _step3_llm_judge(
        self,
        candidates: List[Dict],
        source_name: str,
        source_type: str,
        source_context: str,
        relation_type: str
    ) -> List[Dict]:
        if self.llm_judge is None or self.llm_judge.llm_client is None:
            for c in candidates:
                c["final_score"] = c.get("score", 0.0)
                c["decision"] = "NO"
            return candidates
        
        judged = []
        for c in candidates:
            band = self.rules.get_confidence_band(c.get("score", 0.0), relation_type)
            
            if band == "high":
                c["final_score"] = c.get("score", 0.0)
                c["decision"] = "YES"
                judged.append(c)
            elif band == "medium":
                result = self.llm_judge.judge(
                    source_name=source_name,
                    source_type=source_type,
                    source_context=source_context,
                    target_name=c.get("target_name", ""),
                    target_type=c.get("target_type", ""),
                    target_context=c.get("target_context", ""),
                    relation_type=relation_type
                )
                c["final_score"] = result.get("confidence", 0.0)
                c["decision"] = result.get("decision", "NO")
                c["reason"] = result.get("reason", "")
                judged.append(c)
            # low band: skip entirely
        
        return judged

    def _step4_write_policy(
        self,
        candidates: List[Dict],
        relation_type: str
    ) -> List[Dict]:
        filtered = self.write_policy.filter_by_threshold(
            candidates, relation_type, CONFIDENCE_THRESHOLDS
        )
        
        result = self.write_policy.apply_top_k(filtered, relation_type)
        
        return result

    def write_relations(self, relations: List[Dict], relation_type: str) -> int:
        if not relations or not self.neo4j:
            return 0
        
        count = 0
        for rel in relations:
            if rel.get("decision") != "YES":
                continue
            
            source_id = rel.get("source_id")
            target_id = rel.get("target_id")
            
            if not source_id or not target_id:
                continue
            
            cypher = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            MERGE (source)-[r:{relation_type}]->(target)
            SET r.score = $score
            """
            
            try:
                self.neo4j.execute_query(
                    cypher,
                    {"source_id": source_id, "target_id": target_id, "score": rel.get("final_score", 0.0)}
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to write relation {source_id}->{target_id}: {e}")
        
        return count