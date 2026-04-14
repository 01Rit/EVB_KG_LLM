import pytest
import sys
sys.path.insert(0, '.')

def test_entity_extractor_import():
    from src.importer.entity_extractor import EntityExtractor
    assert EntityExtractor is not None


class MockLLM:
    def generate(self, prompt):
        return '[{"name": "BatteryCover", "category": "外壳", "tools": ["螺丝刀"], "safety_level": 1, "dependencies": []}]'


def test_entity_extractor_initialization():
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLM())
    assert extractor.llm is not None


def test_extract_components():
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLM())
    result = extractor.extract_components("test text")
    assert len(result) > 0
    assert result[0]['name'] == 'BatteryCover'