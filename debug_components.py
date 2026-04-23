import sys
sys.path.insert(0, '/app')
from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
results = neo4j.execute_query(
    "MATCH (c:Component {battery_model: 'Audi_A3'}) RETURN c.name, c.source_type LIMIT 10",
    {}
)
print("Components:")
for r in results:
    print(f"  name='{r.get('name')}', source_type='{r.get('source_type')}'")
neo4j.close()