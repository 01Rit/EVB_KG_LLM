from src.kg.client import Neo4jClient
from src.config import settings
import json

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

cypher = '''
MATCH (c:Component {battery_model: $model})
WHERE c.as_score IS NOT NULL
RETURN c.id as id, c.name as name, c.as_score as as_score
LIMIT 20
'''
results = neo4j.execute_query(cypher, {'model': 'BM-0001'})
print("Components with scores in Neo4j:")
for r in results:
    print(f"  id='{r.get('id')}', name='{r.get('name')}', as_score={r.get('as_score')}")

cypher2 = '''
MATCH (c:Component {battery_model: $model})
RETURN c.id as id, c.name as name
LIMIT 10
'''
results2 = neo4j.execute_query(cypher2, {'model': 'BM-0001'})
print("\nAll components in Neo4j:")
for r in results2:
    print(f"  id='{r.get('id')}', name='{r.get('name')}'")

neo4j.close()