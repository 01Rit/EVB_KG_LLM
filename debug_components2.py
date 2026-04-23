from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
results = neo4j.execute_query(
    "MATCH (c {battery_model: 'Audi_A3'}) RETURN c.id, c.name, c.source_type LIMIT 5",
    {}
)
print("Components:")
for r in results:
    print(f"  id='{r.get('c.id')}', name='{r.get('c.name')}', source_type='{r.get('c.source_type')}'")
neo4j.close()