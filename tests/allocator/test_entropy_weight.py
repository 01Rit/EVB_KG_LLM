import pytest
import numpy as np
from src.allocator.entropy_weight import EntropyWeightCalculator

def test_entropy_weight_calculator_init():
    calc = EntropyWeightCalculator()
    assert calc is not None

def test_normalize_scores():
    calc = EntropyWeightCalculator()
    scores = [1.0, 2.0, 3.0]
    normalized = calc._normalize(scores)
    assert abs(sum(normalized) - 1.0) < 1e-6

def test_entropy_calculation():
    calc = EntropyWeightCalculator()
    p = [0.5, 0.5]
    e = calc._calculate_entropy(p)
    assert 0 <= e <= 1

def test_weight_from_expert_scores():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H1': 1.0, 'H2': 2.0, 'H3': 1.5},
        {'H1': 2.0, 'H2': 1.0, 'H3': 2.5},
        {'H1': 1.5, 'H2': 1.5, 'H3': 2.0},
    ]
    weights = calc.calculate_weights(expert_scores, factor_names=['H1', 'H2', 'H3'])
    assert len(weights) == 3
    assert abs(sum(weights) - 1.0) < 1e-6

def test_calculate_t_score():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H_T': 1.0, 'S_T': 1.5, 'Q_T': 2.0},
        {'H_T': 2.0, 'S_T': 1.0, 'Q_T': 1.5},
        {'H_T': 0.5, 'S_T': 2.0, 'Q_T': 1.0}
    ]
    result = calc.calculate_t_score(expert_scores)
    assert 't_score' in result
    assert 0 <= result['t_score'] <= 3

def test_calculate_t_score_empty():
    calc = EntropyWeightCalculator()
    result = calc.calculate_t_score([])
    assert result['t_score'] == 0

def test_calculate_t_score_default_values():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H_T': 1.0},
        {'S_T': 2.0}
    ]
    result = calc.calculate_t_score(expert_scores)
    assert 'h_time_factor' in result
    assert 's_time_factor' in result
    assert 'q_time_factor' in result

def test_calculate_t_score_boundary():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H_T': 0.0, 'S_T': 0.0, 'Q_T': 0.0},
        {'H_T': 3.0, 'S_T': 3.0, 'Q_T': 3.0}
    ]
    result = calc.calculate_t_score(expert_scores)
    assert 't_score' in result

def test_final_h_score():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H1_visibility': 1.0, 'H2_space_limitation': 2.0, 'H3_object_movement': 1.0, 'H4_ergonomic_impact': 2.0, 'H5_repetitiveness': 1.5,
         'S1_high_voltage': 1.0, 'S2_chemical_reagent': 0.5, 'S3_fire_explosion': 0.5, 'S4_human_injury': 1.0,
         'Lh_human_loss': 1.5, 'Lr_robot_loss': 1.0},
        {'H1_visibility': 2.0, 'H2_space_limitation': 1.0, 'H3_object_movement': 2.0, 'H4_ergonomic_impact': 1.0, 'H5_repetitiveness': 2.5,
         'S1_high_voltage': 2.0, 'S2_chemical_reagent': 1.0, 'S3_fire_explosion': 1.0, 'S4_human_injury': 2.0,
         'Lh_human_loss': 2.0, 'Lr_robot_loss': 1.5},
        {'H1_visibility': 1.5, 'H2_space_limitation': 1.5, 'H3_object_movement': 1.5, 'H4_ergonomic_impact': 1.5, 'H5_repetitiveness': 2.0,
         'S1_high_voltage': 1.5, 'S2_chemical_reagent': 0.75, 'S3_fire_explosion': 0.75, 'S4_human_injury': 1.5,
         'Lh_human_loss': 1.75, 'Lr_robot_loss': 1.25},
    ]
    result = calc.calculate_final_scores(expert_scores)
    assert 0 <= result['h_score'] <= 1
    assert 0 <= result['s_score'] <= 1
    assert 0 <= result['as_score'] <= 1
    assert 'human_loss' in result
    assert 'robot_loss' in result
    assert 'loss_diff' in result
