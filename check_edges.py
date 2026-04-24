from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

r = neo4j.execute_query("MATCH path = (c:Component {name: 'BJB'})-[r*1..2]-(related) RETURN nodes(path) as nodes, relationships(path) as rels LIMIT 1")
if r:
    print("Result keys:", r[0].keys())
    print("Nodes type:", type(r[0]['nodes']))
    print("Rels type:", type(r[0]['rels']))
    if r[0]['rels']:
        print("First rel type:", type(r[0]['rels'][0]))
        print("First rel dir:", dir(r[0]['rels'][0]))
neo4j.close()
