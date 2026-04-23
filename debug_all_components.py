from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
components = neo4j.get_all_components(battery_model='Audi_A3', top_k=100)
print(f"Total components: {len(components)}")
for c in components[:3]:
    print(f"  {c}")
neo4j.close()