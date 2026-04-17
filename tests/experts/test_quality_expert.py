import pytest
from src.experts.quality_expert import QualityExpert
from unittest.mock import MagicMock

def test_quality_expert_inheritance():
    mock_llm = MagicMock()
    expert = QualityExpert(mock_llm)
    assert expert.expert_name == "质量检测专家"
    assert expert.expert_role == "负责评估拆卸过程中的质量控制和损伤风险"

def test_quality_expert_has_base_factors():
    from src.experts.base_expert import BaseExpert
    mock_llm = MagicMock()
    expert = QualityExpert(mock_llm)
    assert len(expert.H_FACTORS) == 5
    assert len(expert.S_FACTORS) == 4
    assert len(expert.D_FACTORS) == 2