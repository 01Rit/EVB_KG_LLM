from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
results = neo4j.execute_query(
    "MATCH (c {battery_model: 'Audi_A3'}) RETURN c.name, c.time_score, c.as_score LIMIT 10",
    {}
)
print("Components with time_score:")
for r in results:
    print(f"  {r.get('c.name')}: time_score={r.get('c.time_score')}, as_score={r.get('c.as_score')}")
neo4j.close()