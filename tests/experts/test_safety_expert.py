import pytest
from src.experts.safety_expert import SafetyExpert
from unittest.mock import MagicMock

def test_safety_expert_inheritance():
    mock_llm = MagicMock()
    expert = SafetyExpert(mock_llm)
    assert expert.expert_name == "安全工程师"
    assert expert.expert_role == "负责评估拆卸过程中的安全风险"

def test_safety_expert_has_base_factors():
    from src.experts.base_expert import BaseExpert
    mock_llm = MagicMock()
    expert = SafetyExpert(mock_llm)
    assert len(expert.H_FACTORS) == 5
    assert len(expert.S_FACTORS) == 4
    assert len(expert.D_FACTORS) == 2