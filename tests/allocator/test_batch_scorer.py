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