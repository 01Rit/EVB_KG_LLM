import pytest
from unittest.mock import MagicMock, patch
from src.allocator.batch_scorer import BatchScorer

def test_batch_scorer_init():
    mock_llm = MagicMock()
    mock_neo4j = MagicMock()
    scorer = BatchScorer(mock_llm, mock_neo4j)
    assert scorer is not None

def test_score_single_component():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0}'
    mock_neo4j = MagicMock()
    scorer = BatchScorer(mock_llm, mock_neo4j)
    result = scorer.score_component("Battery壳体", "EV-500")
    assert 'h_score' in result
    assert 's_score' in result
    assert 'as_score' in result
    assert 'human_loss' in result
    assert 'robot_loss' in result
    assert 'loss_diff' in result
    assert 'assignee' in result
    assert 'expert_A_scores' in result
    assert 'expert_B_scores' in result
    assert 'expert_C_scores' in result


def test_score_component_with_neo4j_context():
    """Test that batch_scorer enriches context from Neo4j when available."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0, "T_T": 1}'

    mock_neo4j = MagicMock()
    mock_neo4j.get_component_by_name.return_value = {
        'name': 'Battery壳体',
        'battery_model': 'EV-500',
        'tool_required': '扭矩扳手',
        'safety_level': '2'
    }
    mock_neo4j.get_component_relationships.return_value = {
        'neighbors': [
            {'neighbor_name': '模组', 'relation_type': 'RELATES'}
        ]
    }

    scorer = BatchScorer(mock_llm, mock_neo4j)
    result = scorer.score_component("Battery壳体", "EV-500")

    mock_neo4j.get_component_by_name.assert_called_once_with("Battery壳体", "EV-500")
    mock_neo4j.get_component_relationships.assert_called_once_with("Battery壳体", "EV-500")

    calls = mock_llm.generate.call_args_list
    assert len(calls) == 3
    for call in calls:
        prompt = call[0][0]
        assert 'Battery壳体' in prompt
        assert '扭矩扳手' in prompt or 'EV-500' in prompt

    assert 'as_score' in result
    assert result['as_score'] > 0


def test_score_component_no_neo4j_fallback():
    """Test that batch_scorer works when Neo4j is not available."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0, "T_T": 1}'

    scorer = BatchScorer(mock_llm, neo4j_client=None)
    result = scorer.score_component("Battery壳体", "EV-500")

    assert 'as_score' in result
    assert 'expert_A_scores' in result