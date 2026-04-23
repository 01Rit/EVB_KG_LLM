import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print('Steps with depends_on:')
for s in steps:
    deps = s.get('depends_on', [])
    print(f"  Step {s['id']:2d}: {s['component'][:25]:25s} depends={deps}")