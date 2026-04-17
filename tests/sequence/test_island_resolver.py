import pytest
from src.sequence.island_resolver import IsolatedNodeResolver, SimilarityMatcher

def test_similarity_matcher_name_similarity():
    matcher = SimilarityMatcher()
    # "upper_housing" 和 "lower_housing" 应该高相似
    score1 = matcher.calculate_name_similarity("upper_housing", "lower_housing")
    assert score1 > 0.5

    # "upper_housing" 和 "module_1" 应该低相似
    score2 = matcher.calculate_name_similarity("upper_housing", "module_1")
    assert score2 < 0.3

def test_resolve_isolated_nodes():
    resolver = IsolatedNodeResolver()
    isolated = ["cooling_pipe", "module_connector"]
    all_nodes = ["upper_housing", "lower_housing", "insulator", "module"]
    existing_edges = [
        ("upper_housing", "lower_housing"),
        ("insulator", "module")
    ]

    result = resolver.resolve(isolated, all_nodes, existing_edges)
    # cooling_pipe 可能匹配到 upper_housing (相似度)
    # module_connector 可能匹配到 module (类型匹配)
    assert isinstance(result, dict)