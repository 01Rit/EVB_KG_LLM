import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print('First 10 steps with timing:')
for s in steps[:10]:
    print(f"  Step {s['id']}: {s['component'][:20]:20s} assignee={s['assignee']:6s} start={s['start_time']} dur={s['duration']}")

batches = data['data'].get('parallel_batches', [])
print(f'\nParallel batches: {len(batches)}')