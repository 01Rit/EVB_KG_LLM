from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from src.config import settings
import json

llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)
e = EntityExtractor(llm)

text = "Unscrew the screws of the upper housing. Remove the upper housing."

triplets = e.extract_triplets(text)
print("Triplets:", triplets)
