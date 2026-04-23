from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from src.config import settings

llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)
e = EntityExtractor(llm)

prompt = 'Extract triplets. Return JSON: [{"head":"X","relation":"Y","tail":"Z"}]. Unscrew screws of upper housing.'
result = llm.generate(prompt)
print("LLM result:", repr(result))

triplets = e._parse_json_array(result)
print("Parsed:", triplets)

triplets2 = e.extract_triplets("Unscrew screws of upper housing.")
print("Direct extract:", triplets2)
