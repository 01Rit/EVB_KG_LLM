import pytest
from src.experts.base_expert import BaseExpert

def test_base_expert_abstract():
    with pytest.raises(TypeError):
        BaseExpert()

def test_factor_count():
    assert len(BaseExpert.H_FACTORS) == 5
    assert len(BaseExpert.S_FACTORS) == 4
    assert len(BaseExpert.D_FACTORS) == 2
