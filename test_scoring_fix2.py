import sys
sys.path.insert(0, 'D:/KG_project/Final4.14')
sys.stdout = open('D:/KG_project/Final4.14/test_output.txt', 'w')

from unittest.mock import MagicMock
from src.experts.safety_expert import SafetyExpert
from src.experts.production_expert import ProductionExpert
from src.experts.quality_expert import QualityExpert
from src.allocator.batch_scorer import BatchScorer
from src.allocator.entropy_weight import EntropyWeightCalculator

# Test 1: Markdown-wrapped JSON should parse correctly
print("Test 1: Markdown-wrapped JSON parsing", flush=True)
mock_llm = MagicMock()
mock_llm.generate.return_value = '```json\n{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}\n```'
expert = SafetyExpert(mock_llm)
result = expert.score("Battery壳体")
print(f"  H1_visibility: {result['H1_visibility']} (expected 1.0)", flush=True)
assert result['H1_visibility'] == 1.0
print("  PASSED", flush=True)

# Test 2: Valid JSON should parse correctly
print("\nTest 2: Valid JSON parsing", flush=True)
mock_llm = MagicMock()
mock_llm.generate.return_value = '{"H1_visibility": 2.0, "H2_space_limitation": 2.5, "H3_object_movement": 1.0, "H4_ergonomic_impact": 1.5, "H5_repetitiveness": 0.5, "S1_high_voltage": 1.0, "S2_chemical_reagent": 1.5, "S3_fire_explosion": 0.5, "S4_human_injury": 2.0, "Lh_human_loss": 1.0, "Lr_robot_loss": 2.0}'
expert = ProductionExpert(mock_llm)
result = expert.score("Battery壳体")
print(f"  H1_visibility: {result['H1_visibility']} (expected 2.0)", flush=True)
assert result['H1_visibility'] == 2.0
print("  PASSED", flush=True)

# Test 3: Malformed JSON should raise exception
print("\nTest 3: Malformed JSON raises exception", flush=True)
mock_llm = MagicMock()
mock_llm.generate.return_value = 'This is not JSON at all'
expert = QualityExpert(mock_llm)
try:
    result = expert.score("Battery壳体")
    print("  FAILED: no exception raised", flush=True)
except Exception as e:
    print(f"  Exception raised: {type(e).__name__}", flush=True)
    print("  PASSED", flush=True)

# Test 4: Three experts with different scores
print("\nTest 4: Three experts with different scores", flush=True)
mock_llm = MagicMock()
def side_effect(prompt):
    if "安全工程师" in prompt:
        return '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}'
    elif "生产工艺工程师" in prompt:
        return '{"H1_visibility": 2.0, "H2_space_limitation": 2.5, "H3_object_movement": 1.0, "H4_ergonomic_impact": 1.5, "H5_repetitiveness": 0.5, "S1_high_voltage": 1.0, "S2_chemical_reagent": 1.5, "S3_fire_explosion": 0.5, "S4_human_injury": 2.0, "Lh_human_loss": 1.0, "Lr_robot_loss": 2.0}'
    else:
        return '{"H1_visibility": 0.5, "H2_space_limitation": 1.0, "H3_object_movement": 1.5, "H4_ergonomic_impact": 0.5, "H5_repetitiveness": 1.0, "S1_high_voltage": 1.5, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 1.0, "S4_human_injury": 0.5, "Lh_human_loss": 2.0, "Lr_robot_loss": 0.5}'

mock_llm.generate.side_effect = side_effect
scorer = BatchScorer(mock_llm, None)
result = scorer.score_component("Battery壳体", "EV-500")

print(f"  Expert A scores H1: {result['expert_A_scores']['H1_visibility']} (expected 1.0)", flush=True)
print(f"  Expert B scores H1: {result['expert_B_scores']['H1_visibility']} (expected 2.0)", flush=True)
print(f"  Expert C scores H1: {result['expert_C_scores']['H1_visibility']} (expected 0.5)", flush=True)
print(f"  h_score: {result['h_score']}", flush=True)
print(f"  s_score: {result['s_score']}", flush=True)
print(f"  as_score: {result['as_score']}", flush=True)

assert result['expert_A_scores']['H1_visibility'] == 1.0
assert result['expert_B_scores']['H1_visibility'] == 2.0
assert result['expert_C_scores']['H1_visibility'] == 0.5
print("  PASSED", flush=True)

print("\n" + "="*50, flush=True)
print("All tests passed!", flush=True)
print("="*50, flush=True)