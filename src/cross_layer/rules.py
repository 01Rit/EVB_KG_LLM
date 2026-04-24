from typing import Dict, List, Tuple

REFERENCE_OF = "REFERENCE_OF"
DEFINITION_OF = "DEFINITION_OF"
CONSTRAINED_BY = "CONSTRAINED_BY"

RELATION_TYPE_MAPPING: Dict[str, Dict] = {
    REFERENCE_OF: {
        "source_layer": "L1",
        "target_layer": "L2",
        "allowed_pairs": [
            ("Component", "Component"),
            ("Component", "Document"),
            ("Component", "Term"),
            ("Document", "Entity"),
            ("Document", "Term"),
        ],
    },
    DEFINITION_OF: {
        "source_layer": "L2",
        "target_layer": "L3",
        "allowed_pairs": [
            ("Entity", "Term"),
            ("Term", "Entity"),
        ],
    },
    CONSTRAINED_BY: {
        "source_layer": "L1",
        "target_layer": "L3",
        "allowed_pairs": [
            ("Component", "Term"),
        ],
    },
}

CONFIDENCE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    REFERENCE_OF: {"high": 0.92, "low": 0.80},
    DEFINITION_OF: {"high": 0.90, "low": 0.75},
    CONSTRAINED_BY: {"high": 0.88, "low": 0.70},
}


class CrossLayerRules:
    def __init__(self):
        self.relation_mapping = RELATION_TYPE_MAPPING
        self.thresholds = CONFIDENCE_THRESHOLDS

    def is_valid_relation_type(
        self, source_type: str, target_type: str, relation_type: str
    ) -> bool:
        if relation_type not in self.relation_mapping:
            return False
        mapping = self.relation_mapping[relation_type]
        pair = (source_type, target_type)
        return pair in mapping["allowed_pairs"]

    def is_valid_direction(
        self, source_layer: str, target_layer: str, relation_type: str
    ) -> bool:
        if relation_type not in self.relation_mapping:
            return False
        mapping = self.relation_mapping[relation_type]
        return (
            mapping["source_layer"] == source_layer
            and mapping["target_layer"] == target_layer
        )

    def get_confidence_band(self, score: float, relation_type: str) -> str:
        if relation_type not in self.thresholds:
            return "low"
        thresh = self.thresholds[relation_type]
        if score >= thresh["high"]:
            return "high"
        elif score >= thresh["low"]:
            return "medium"
        return "low"