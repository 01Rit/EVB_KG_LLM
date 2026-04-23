import sys
sys.path.insert(0, 'D:/KG_project/Final4.14')

from unittest.mock import MagicMock
from src.experts.safety_expert import SafetyExpert

def test_markdown_wrapped_json_response():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '```json\n{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}\n```'
    expert = SafetyExpert(mock_llm)
    result = expert.score("Battery壳体")
    assert result['H1_visibility'] == 1.0, f"Expected 1.0, got {result['H1_visibility']}"
    assert result['H2_space_limitation'] == 1.5, f"Expected 1.5, got {result['H2_space_limitation']}"
    assert result['S1_high_voltage'] == 2.0, f"Expected 2.0, got {result['S1_high_voltage']}"
    print("test_markdown_wrapped_json_response: PASSED")

def test_malformed_json_raises_exception():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = 'This is not JSON at all'
    expert = SafetyExpert(mock_llm)
    try:
        result = expert.score("Battery壳体")
        print("test_malformed_json_raises_exception: FAILED - no exception raised")
    except Exception as e:
        print(f"test_malformed_json_raises_exception: PASSED (raised {type(e).__name__})")

def test_valid_json_response():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}'
    expert = SafetyExpert(mock_llm)
    result = expert.score("Battery壳体")
    assert result['H1_visibility'] == 1.0, f"Expected 1.0, got {result['H1_visibility']}"
    assert result['Lh_human_loss'] == 1.5, f"Expected 1.5, got {result['Lh_human_loss']}"
    print("test_valid_json_response: PASSED")

if __name__ == "__main__":
    test_markdown_wrapped_json_response()
    test_malformed_json_raises_exception()
    test_valid_json_response()
    print("\nAll tests passed!")