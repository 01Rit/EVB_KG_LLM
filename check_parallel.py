import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print("Steps with depends_on:")
for s in steps:
    print(f"Step {s['id']}: {s['component'][:30]:30s} depends={s.get('depends_on', [])}, time={s.get('time_seconds', 0)}")