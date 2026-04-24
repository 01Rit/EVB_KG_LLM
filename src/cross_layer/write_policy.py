from typing import Dict, List


class WritePolicy:
    def __init__(self, top_k_per_relation: int = 3):
        self.top_k_per_relation = top_k_per_relation

    def filter_by_threshold(
        self,
        candidates: List[Dict],
        relation_type: str,
        thresholds: Dict[str, Dict[str, float]]
    ) -> List[Dict]:
        if relation_type not in thresholds:
            return candidates
        
        thresh = thresholds[relation_type]
        low_threshold = thresh["low"]
        
        filtered = [
            c for c in candidates
            if c.get("final_score", c.get("score", 0.0)) >= low_threshold
        ]
        return filtered

    def apply_top_k(
        self,
        candidates: List[Dict],
        relation_type: str
    ) -> List[Dict]:
        grouped: Dict[tuple, List[Dict]] = {}
        
        for candidate in candidates:
            key = (candidate.get("source_id"), relation_type)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(candidate)
        
        result = []
        for key, group in grouped.items():
            sorted_group = sorted(
                group,
                key=lambda x: x.get("final_score", x.get("score", 0.0)),
                reverse=True
            )
            result.extend(sorted_group[: self.top_k_per_relation])
        
        return result