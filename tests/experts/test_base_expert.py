import pytest
from unittest.mock import MagicMock
from src.experts.base_expert import BaseExpert
from src.experts.safety_expert import SafetyExpert


def test_base_expert_abstract():
    with pytest.raises(TypeError):
        BaseExpert()


def test_t_factor_exists():
    assert hasattr(BaseExpert, 'T_FACTORS')
    assert 'T_T' in BaseExpert.T_FACTORS
    assert len(BaseExpert.T_FACTORS) == 1


def test_t_factor_description():
    assert 'T_T' in BaseExpert.FACTOR_DESCRIPTIONS
    assert '秒' in BaseExpert.FACTOR_DESCRIPTIONS['T_T']


def test_factor_count():
    assert len(BaseExpert.H_FACTORS) == 5
    assert len(BaseExpert.S_FACTORS) == 4
    assert len(BaseExpert.D_FACTORS) == 2


class TestJsonParsingRobustness:
    def test_markdown_wrapped_json_response(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '```json\n{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}\n```'
        expert = SafetyExpert(mock_llm)
        result = expert.score("Battery壳体")
        assert result['H1_visibility'] == 1.0
        assert result['H2_space_limitation'] == 1.5
        assert result['S1_high_voltage'] == 2.0

    def test_markdown_wrapped_json_without_language_tag(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '```\n{"H1_visibility": 2.0, "H2_space_limitation": 2.5, "H3_object_movement": 1.0, "H4_ergonomic_impact": 1.5, "H5_repetitiveness": 0.5, "S1_high_voltage": 1.0, "S2_chemical_reagent": 1.5, "S3_fire_explosion": 0.5, "S4_human_injury": 2.0, "Lh_human_loss": 1.0, "Lr_robot_loss": 2.0}\n```'
        expert = SafetyExpert(mock_llm)
        result = expert.score("Battery壳体")
        assert result['H1_visibility'] == 2.0
        assert result['H2_space_limitation'] == 2.5

    def test_malformed_json_raises_exception(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = 'This is not JSON at all'
        expert = SafetyExpert(mock_llm)
        with pytest.raises(Exception):
            expert.score("Battery壳体")

    def test_valid_json_response(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}'
        expert = SafetyExpert(mock_llm)
        result = expert.score("Battery壳体")
        assert result['H1_visibility'] == 1.0
        assert result['Lh_human_loss'] == 1.5


class TestTFactor:
    def test_t_factor_in_score_output(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0, "T_T": 2.0}'
        expert = SafetyExpert(mock_llm)
        result = expert.score("Battery壳体")
        assert 'T_T' in result
        assert result['T_T'] == 2.0

    def test_t_factor_default_when_missing(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}'
        expert = SafetyExpert(mock_llm)
        result = expert.score("Battery壳体")
        assert 'T_T' in result
        assert result['T_T'] == 1.5
