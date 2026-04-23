from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from src.config import settings

llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)
e = EntityExtractor(llm)

text = """i. Unscrew the screws of the upper housing (A).
ii. Remove the upper housing (1) and the insulator (2).
iii. Cut anchorages of high voltage cables (B) and unscrew the screws that connect the BJB to the casing (C).
iv. Disconnect the plugging cable between BJB and CMCs-BMC (3), and remove the BJB (4) together with the cables attached thereto (5).
v. Remove the side plastic links of the modules (6).
vi. Remove the upper and lower fasteners of the modules (7).
vii. Remove the modules (8).
viii. Remove the lower insulator (9).
ix. Remove the upper transverse covers (10) and the lower housing shell (11).
x. Remove the plugging wires connecting the CMCs with BMC (12).
xi. Remove the cooling plates (13).
xii. Remove the cooling pipes (14)."""

print("Testing triplet extraction...")
triplets = e.extract_triplets(text)
print(f"Extracted {len(triplets)} triplets")
for t in triplets[:5]:
    print(f"  {t}")
