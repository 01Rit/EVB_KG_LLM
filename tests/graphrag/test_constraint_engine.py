import pytest
from src.graphrag.constraint_engine import ConstraintEngine


class TestConstraintEngine:
    def test_infer_bidirectional_constraints_housing_before_cell(self):
        engine = ConstraintEngine()
        components = [
            {'name': 'upper_housing', 'safety_level': 1},
            {'name': 'insulator', 'safety_level': 2},
            {'name': 'cell', 'safety_level': 4}
        ]

        constraints = engine.infer_bidirectional_constraints('test_battery', components)

        before_pairs = [(c['head'], c['tail']) for c in constraints if c['relation'] == 'BEFORE']

        assert ('upper_housing', 'cell') in before_pairs
        assert ('upper_housing', 'insulator') in before_pairs

    def test_is_outer_true(self):
        engine = ConstraintEngine()
        assert engine._is_outer('upper_housing') == True
        assert engine._is_outer('lower_case') == True
        assert engine._is_outer('battery_cover') == True

    def test_is_outer_false(self):
        engine = ConstraintEngine()
        assert engine._is_outer('cell') == False
        assert engine._is_outer('module') == False

    def test_is_inner_true(self):
        engine = ConstraintEngine()
        assert engine._is_inner('cell') == True
        assert engine._is_inner('cmc') == True
        assert engine._is_inner('module') == True

    def test_safety_level_constraint(self):
        engine = ConstraintEngine()
        components = [
            {'name': 'high_safety_part', 'safety_level': 5},
            {'name': 'low_safety_part', 'safety_level': 1}
        ]

        constraints = engine.infer_bidirectional_constraints('test', components)
        before_pairs = [(c['head'], c['tail']) for c in constraints if c['relation'] == 'BEFORE']

        assert ('high_safety_part', 'low_safety_part') in before_pairs