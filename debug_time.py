import requests

# Check existing components and their time_score
resp = requests.get('http://localhost:8000/api/v1/battery-models?search=Audi')
data = resp.json()
print("Battery models:", data)

# Check components for Audi_A3
neo4j_query = '''
MATCH (c:Component {battery_model: 'Audi_A3'})
RETURN c.id, c.name, c.time_score, c.as_score
LIMIT 10
'''

import json
# Just use the API to get components
resp2 = requests.post('http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
result = resp2.json()
print("\nAPI Response time_seconds:")
for step in result.get('data', {}).get('steps', [])[:3]:
    print(f"  {step.get('component')}: time_seconds={step.get('time_seconds')}, time_score={step.get('time_score', 'N/A')}")