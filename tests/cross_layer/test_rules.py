import pytest
from src.cross_layer.rules import (
    CrossLayerRules,
    RELATION_TYPE_MAPPING,
    CONFIDENCE_THRESHOLDS,
    REFERENCE_OF,
    DEFINITION_OF,
    CONSTRAINED_BY,
)


class TestCrossLayerRules:
    def setup_method(self):
        self.rules = CrossLayerRules()

    def test_is_valid_relation_type_reference_of_valid_pairs(self):
        assert self.rules.is_valid_relation_type("Component", "Component", REFERENCE_OF) is True
        assert self.rules.is_valid_relation_type("Component", "Document", REFERENCE_OF) is True
        assert self.rules.is_valid_relation_type("Component", "Term", REFERENCE_OF) is True
        assert self.rules.is_valid_relation_type("Document", "Entity", REFERENCE_OF) is True
        assert self.rules.is_valid_relation_type("Document", "Term", REFERENCE_OF) is True

    def test_is_valid_relation_type_reference_of_invalid_pairs(self):
        assert self.rules.is_valid_relation_type("Component", "Entity", REFERENCE_OF) is False
        assert self.rules.is_valid_relation_type("Entity", "Component", REFERENCE_OF) is False
        assert self.rules.is_valid_relation_type("Term", "Component", REFERENCE_OF) is False

    def test_is_valid_relation_type_definition_of_valid_pairs(self):
        assert self.rules.is_valid_relation_type("Entity", "Term", DEFINITION_OF) is True
        assert self.rules.is_valid_relation_type("Term", "Entity", DEFINITION_OF) is True

    def test_is_valid_relation_type_definition_of_invalid_pairs(self):
        assert self.rules.is_valid_relation_type("Component", "Term", DEFINITION_OF) is False
        assert self.rules.is_valid_relation_type("Entity", "Component", DEFINITION_OF) is False

    def test_is_valid_relation_type_constrained_by_valid_pairs(self):
        assert self.rules.is_valid_relation_type("Component", "Term", CONSTRAINED_BY) is True

    def test_is_valid_relation_type_constrained_by_invalid_pairs(self):
        assert self.rules.is_valid_relation_type("Entity", "Term", CONSTRAINED_BY) is False
        assert self.rules.is_valid_relation_type("Component", "Entity", CONSTRAINED_BY) is False

    def test_is_valid_relation_type_unknown_relation(self):
        assert self.rules.is_valid_relation_type("Component", "Component", "UNKNOWN") is False

    def test_is_valid_direction_reference_of(self):
        assert self.rules.is_valid_direction("L1", "L2", REFERENCE_OF) is True
        assert self.rules.is_valid_direction("L2", "L1", REFERENCE_OF) is False
        assert self.rules.is_valid_direction("L1", "L3", REFERENCE_OF) is False

    def test_is_valid_direction_definition_of(self):
        assert self.rules.is_valid_direction("L2", "L3", DEFINITION_OF) is True
        assert self.rules.is_valid_direction("L3", "L2", DEFINITION_OF) is False
        assert self.rules.is_valid_direction("L1", "L2", DEFINITION_OF) is False

    def test_is_valid_direction_constrained_by(self):
        assert self.rules.is_valid_direction("L1", "L3", CONSTRAINED_BY) is True
        assert self.rules.is_valid_direction("L3", "L1", CONSTRAINED_BY) is False
        assert self.rules.is_valid_direction("L1", "L2", CONSTRAINED_BY) is False

    def test_is_valid_direction_unknown_relation(self):
        assert self.rules.is_valid_direction("L1", "L2", "UNKNOWN") is False

    def test_get_confidence_band_reference_of_high(self):
        assert self.rules.get_confidence_band(0.95, REFERENCE_OF) == "high"
        assert self.rules.get_confidence_band(0.92, REFERENCE_OF) == "high"

    def test_get_confidence_band_reference_of_medium(self):
        assert self.rules.get_confidence_band(0.91, REFERENCE_OF) == "medium"
        assert self.rules.get_confidence_band(0.85, REFERENCE_OF) == "medium"
        assert self.rules.get_confidence_band(0.80, REFERENCE_OF) == "medium"

    def test_get_confidence_band_reference_of_low(self):
        assert self.rules.get_confidence_band(0.79, REFERENCE_OF) == "low"
        assert self.rules.get_confidence_band(0.50, REFERENCE_OF) == "low"

    def test_get_confidence_band_definition_of(self):
        assert self.rules.get_confidence_band(0.95, DEFINITION_OF) == "high"
        assert self.rules.get_confidence_band(0.87, DEFINITION_OF) == "medium"
        assert self.rules.get_confidence_band(0.74, DEFINITION_OF) == "low"

    def test_get_confidence_band_constrained_by(self):
        assert self.rules.get_confidence_band(0.90, CONSTRAINED_BY) == "high"
        assert self.rules.get_confidence_band(0.80, CONSTRAINED_BY) == "medium"
        assert self.rules.get_confidence_band(0.69, CONSTRAINED_BY) == "low"

    def test_get_confidence_band_unknown_relation(self):
        assert self.rules.get_confidence_band(0.95, "UNKNOWN") == "low"

    def test_confidence_thresholds_values(self):
        assert CONFIDENCE_THRESHOLDS[REFERENCE_OF]["high"] == 0.92
        assert CONFIDENCE_THRESHOLDS[REFERENCE_OF]["low"] == 0.80
        assert CONFIDENCE_THRESHOLDS[DEFINITION_OF]["high"] == 0.90
        assert CONFIDENCE_THRESHOLDS[DEFINITION_OF]["low"] == 0.75
        assert CONFIDENCE_THRESHOLDS[CONSTRAINED_BY]["high"] == 0.88
        assert CONFIDENCE_THRESHOLDS[CONSTRAINED_BY]["low"] == 0.70

    def test_relation_type_mapping_structure(self):
        assert RELATION_TYPE_MAPPING[REFERENCE_OF]["source_layer"] == "L1"
        assert RELATION_TYPE_MAPPING[REFERENCE_OF]["target_layer"] == "L2"
        assert ("Component", "Component") in RELATION_TYPE_MAPPING[REFERENCE_OF]["allowed_pairs"]
        assert RELATION_TYPE_MAPPING[CONSTRAINED_BY]["source_layer"] == "L1"
        assert RELATION_TYPE_MAPPING[CONSTRAINED_BY]["target_layer"] == "L3"
