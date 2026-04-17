import pytest
from src.experts.production_expert import ProductionExpert
from unittest.mock import MagicMock

def test_production_expert_inheritance():
    mock_llm = MagicMock()
    expert = ProductionExpert(mock_llm)
    assert expert.expert_name == "生产工艺工程师"
    assert expert.expert_role == "负责评估拆卸工艺的复杂度和效率"

def test_production_expert_has_base_factors():
    from src.experts.base_expert import BaseExpert
    mock_llm = MagicMock()
    expert = ProductionExpert(mock_llm)
    assert len(expert.H_FACTORS) == 5
    assert len(expert.S_FACTORS) == 4
    assert len(expert.D_FACTORS) == 2
