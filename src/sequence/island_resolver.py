from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SimilarityMatcher:
    def __init__(self):
        self.threshold = 0.3

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算两个名称的相似度 (0-1)"""
        name1 = name1.lower()
        name2 = name2.lower()

        if name1 == name2:
            return 1.0

        # 编辑距离
        len1, len2 = len(name1), len(name2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # 简单编辑距离
        edit_dist = self._levenshtein_distance(name1, name2)
        max_len = max(len1, len2)
        return 1.0 - (edit_dist / max_len)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def find_best_match(self, isolated_name: str,
                        candidates: List[str]) -> Optional[Tuple[str, float]]:
        """找到最佳匹配返回 (名称, 相似度)"""
        best_score = 0.0
        best_match = None

        for candidate in candidates:
            score = self.calculate_name_similarity(isolated_name, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score >= self.threshold:
            return (best_match, best_score)
        return None


class IsolatedNodeResolver:
    def __init__(self):
        self.matcher = SimilarityMatcher()

    def resolve(self, isolated_nodes: List[str],
                all_nodes: List[str],
                existing_edges: List[Tuple[str, str]]) -> dict[str, Optional[str]]:
        """
        解析孤立节点，尝试连接到相似节点

        Returns: {isolated_id: connected_id or None}
        """
        result = {}
        non_isolated = [n for n in all_nodes if n not in isolated_nodes]

        for isolated in isolated_nodes:
            match = self.matcher.find_best_match(isolated, non_isolated)
            if match:
                result[isolated] = match[0]
                logger.info(f"Isolated node '{isolated}' matched to '{match[0]}' (score: {match[1]:.2f})")
            else:
                result[isolated] = None
                logger.info(f"Isolated node '{isolated}' could not be matched, will be kept as independent step")

        return result