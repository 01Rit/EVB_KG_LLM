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


class MockLLMStable:
    """Mock LLM that returns consistent triplet output."""
    def generate(self, prompt):
        return '''[
  {"head": "电池包", "tail": "模组", "relation": "是...的子部件", "head_tool": "扭矩扳手", "head_safety": 2, "tail_tool": "绝缘工具", "tail_safety": 3},
  {"head": "模组", "tail": "电芯", "relation": "是...的子部件", "head_tool": "绝缘工具", "head_safety": 3, "tail_tool": "拆卸夹具", "tail_safety": 4},
  {"head": "上盖板", "tail": "模组", "relation": "必须先于...拆卸", "head_tool": "螺丝刀", "head_safety": 1, "tail_tool": "绝缘工具", "tail_safety": 3}
]'''


def test_extract_triplets_stability():
    """Test that same text produces consistent triplet output."""
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLMStable())

    text = "拆卸Audi A3电池包，先拆上盖板，再拆绝缘层，最后取出模组和电芯"
    result1 = extractor.extract_triplets(text, filename="test.txt")
    result2 = extractor.extract_triplets(text, filename="test.txt")

    assert len(result1) > 0
    assert len(result1) == len(result2)
    # All triplets should be identical
    for t1, t2 in zip(result1, result2):
        assert t1['head'] == t2['head']
        assert t1['tail'] == t2['tail']
        assert t1['relation'] == t2['relation']


def test_extract_triplets_relation_type_distinction():
    """Test that relation types are correctly distinguished."""
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLMStable())

    text = "电池包包含模组，模组包含电芯，盖板必须先于模组拆卸"
    triplets = extractor.extract_triplets(text)

    relations = {t['relation'] for t in triplets}
    assert '是...的子部件' in relations
    assert '必须先于...拆卸' in relations


def test_extract_triplets_no_false_relationships():
    """Test that cross-level false relationships are filtered."""
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLMStable())

    text = "上盖板必须先于电芯拆卸"  # False: these are not adjacent levels
    triplets = extractor.extract_triplets(text)

    for t in triplets:
        if t['relation'] == '必须先于...拆卸':
            head, tail = t['head'], t['tail']
            # Heads and tails should not be "盖板" and "电芯" directly
            assert not (head == '上盖板' and tail == '电芯'), "False relationship detected"