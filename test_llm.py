from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from src.config import settings

llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)
e = EntityExtractor(llm)

text = "i. Unscrew the screws of the upper housing (A). ii. Remove the upper housing (1) and the insulator (2)."

triplets = e.extract_triplets(text)
print("Triplets:", triplets)
