import sys
sys.path.insert(0, '.')
from unittest.mock import MagicMock
from src.experts.safety_expert import SafetyExpert

mock_llm = MagicMock()
expert = SafetyExpert(mock_llm)

# Test 1: expert_name
assert expert.expert_name == "安全工程师", f"Expected '安全工程师', got {expert.expert_name}"
print("Test 1 passed: expert_name")

# Test 2: expert_role
assert expert.expert_role == "负责评估拆卸过程中的安全风险", f"Expected '负责评估拆卸过程中的安全风险', got {expert.expert_role}"
print("Test 2 passed: expert_role")

# Test 3: H_FACTORS count
assert len(expert.H_FACTORS) == 5, f"Expected 5, got {len(expert.H_FACTORS)}"
print("Test 3 passed: H_FACTORS count")

# Test 4: S_FACTORS count
assert len(expert.S_FACTORS) == 4, f"Expected 4, got {len(expert.S_FACTORS)}"
print("Test 4 passed: S_FACTORS count")

# Test 5: D_FACTORS count
assert len(expert.D_FACTORS) == 2, f"Expected 2, got {len(expert.D_FACTORS)}"
print("Test 5 passed: D_FACTORS count")

print("\nAll tests passed!")
