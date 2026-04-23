from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
results = neo4j.execute_query(
    "MATCH (c {battery_model: 'Audi_A3'}) WHERE c.time_score IS NULL RETURN c.name, c.time_score",
    {}
)
print('Components without time_score:', len(results))
for r in results:
    print(f"  {r.get('c.name')}")
neo4j.close()