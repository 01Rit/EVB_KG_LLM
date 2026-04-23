import requests
import json

resp = requests.post(
    'http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': True},
    timeout=120
)
print('Status:', resp.status_code)
data = resp.json()
if data.get('data') and data['data'].get('steps'):
    print('Steps count:', len(data['data']['steps']))
    for step in data['data']['steps'][:3]:
        print(json.dumps(step, indent=2))
else:
    print('Response:', resp.text[:500])