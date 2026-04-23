import sys
sys.path.insert(0, 'D:/KG_project/Final4.14')

results = []

try:
    from src.utils.tokenizer import encode_string_by_tiktoken, truncate_by_token_size
    results.append("PASS: tokenizer")
except Exception as e:
    results.append(f"FAIL: tokenizer - {e}")

try:
    from src.graphrag.community import CommunityDetector
    results.append("PASS: community")
except Exception as e:
    results.append(f"FAIL: community - {e}")

try:
    from src.graphrag.global_query import GlobalQueryEngine
    results.append("PASS: global_query")
except Exception as e:
    results.append(f"FAIL: global_query - {e}")

try:
    from src.graphrag.ranker import EvidenceRanker
    results.append("PASS: ranker")
except Exception as e:
    results.append(f"FAIL: ranker - {e}")

try:
    from src.graphrag.generator import PlanGenerator
    results.append("PASS: generator")
except Exception as e:
    results.append(f"FAIL: generator - {e}")

try:
    from src.graphrag.planner import Planner
    results.append("PASS: planner")
except Exception as e:
    results.append(f"FAIL: planner - {e}")

with open('D:/KG_project/Final4.14/import_test_result.txt', 'w') as f:
    f.write('\n'.join(results))