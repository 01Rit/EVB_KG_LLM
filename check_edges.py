from src.kg.client import Neo4jClient
from src.config import settings

neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

# Check if REFERENCE_OF is in the subgraph traversal
# depth=2 should traverse: Component -> REFERENCE_OF -> L2_Entity
r = neo4j.execute_query("MATCH path = (c:Component {name: 'BJB'})-[r:REFERENCE_OF*1..2]-(related) RETURN count(path) as path_count")
print("BJB paths via REFERENCE_OF (depth 1-2):", r)

# Check if we can traverse Component -> REFERENCE_OF -> L2_Entity
r2 = neo4j.execute_query("MATCH (c:Component {name: 'BJB'})-[r:REFERENCE_OF]->(e:L2_Entity) RETURN c.name as comp, e.name as entity, e.entity_type as type LIMIT 5")
print("BJB -> REFERENCE_OF -> L2_Entity:", r2)

# Check the labels of nodes returned by get_subgraph
r3 = neo4j.execute_query("MATCH path = (c:Component {name: 'BJB'})-[r*1..2]-(related) UNWIND nodes(path) as n RETURN labels(n)[0] as label, count(*) as cnt GROUP BY label")
print("Node labels in subgraph:", r3)

neo4j.close()
