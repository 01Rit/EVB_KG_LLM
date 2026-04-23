from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

results = neo4j.execute_query(
    "MATCH (c:Component) RETURN c.battery_model as model, count(c) as count LIMIT 20",
    {}
)

print("Battery models and component counts:")
for r in results:
    print(f"model='{r.get('model')}', count={r.get('count')}")

neo4j.close()