import sys
sys.path.insert(0, 'D:/KG_project/Final4.14')

try:
    from src.utils.tokenizer import encode_string_by_tiktoken, truncate_by_token_size
    print("PASS: tokenizer imported")
except Exception as e:
    print(f"FAIL: tokenizer - {e}")

try:
    from src.graphrag.community import CommunityDetector
    print("PASS: community imported")
except Exception as e:
    print(f"FAIL: community - {e}")

try:
    from src.graphrag.global_query import GlobalQueryEngine
    print("PASS: global_query imported")
except Exception as e:
    print(f"FAIL: global_query - {e}")

try:
    from src.graphrag.ranker import EvidenceRanker
    print("PASS: ranker imported")
except Exception as e:
    print(f"FAIL: ranker - {e}")

try:
    from src.graphrag.generator import PlanGenerator
    print("PASS: generator imported")
except Exception as e:
    print(f"FAIL: generator - {e}")

try:
    from src.graphrag.planner import Planner
    print("PASS: planner imported")
except Exception as e:
    print(f"FAIL: planner - {e}")