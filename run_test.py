import sys
sys.path.insert(0, '.')
from src.importer.entity_extractor import EntityExtractor

class MockLLM:
    def generate(self, prompt):
        return '[{"name": "BatteryCover", "category": "外壳", "tools": ["螺丝刀"], "safety_level": 1, "dependencies": []}]'

extractor = EntityExtractor(MockLLM())
result = extractor.extract_components("test text")

with open('test_result.txt', 'w', encoding='utf-8') as f:
    f.write(f"Length: {len(result)}\n")
    if len(result) > 0:
        f.write(f"Name: {result[0].get('name', 'N/A')}\n")