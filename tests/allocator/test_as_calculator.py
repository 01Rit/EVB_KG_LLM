import pytest
from src.allocator.as_calculator import ASCalculator


def test_as_calculator_import():
    assert ASCalculator is not None


def test_calculate_as():
    calculator = ASCalculator()
    h_scores = {'visibility': 0.3, 'space_limit': 0.5, 'object_movement': 0.2, 'ergonomic_impact': 0.4, 'repetitiveness': 0.1}
    s_scores = {'high_voltage': 0.6, 'chemical_risk': 0.2, 'fire_explosion': 0.1, 'personal_injury': 0.3}
    result = calculator.calculate_as(h_scores, s_scores)
    assert 0 <= result <= 1


def test_determine_assignee_robot():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.7) == 'robot'


def test_determine_assignee_human():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.3) == 'human'


def test_determine_assignee_cost_based():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.5, human_loss=80, robot_loss=100) == 'human'


def test_determine_assignee_uses_loss_diff():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.5, human_loss=80, robot_loss=100) == 'human'
    assert calculator.determine_assignee(0.5, human_loss=100, robot_loss=80) == 'robot'
    assert calculator.determine_assignee(0.5, human_loss=100, robot_loss=100) == 'robot'