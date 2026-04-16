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


class MockLLMForObject:
    def generate(self, prompt):
        return '{"entities": [{"name": "BatteryPack", "entity_type": "component", "source_evidence": "电池包是核心部件", "battery_model": "unknown"}], "terms": [{"term_id": "T1", "name": "扭矩", "definition": "旋转力的大小"}]}'


def test_extract_entities_with_types():
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLMForObject())
    result = extractor.extract_entities_with_types("test text")
    assert 'entities' in result
    assert 'terms' in result
    assert len(result['entities']) > 0
    assert result['entities'][0]['name'] == 'BatteryPack'
    assert result['entities'][0]['entity_type'] == 'component'
    assert len(result['terms']) > 0
    assert result['terms'][0]['name'] == '扭矩'