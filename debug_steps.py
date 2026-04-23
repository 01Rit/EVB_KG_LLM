import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print('All steps with timing:')
for s in steps:
    st = s.get('start_time', 0)
    dur = s.get('time_seconds', 0)
    end = st + dur
    print(f"  Step {s['id']:2d}: start={st:4d}, dur={dur:3d}, end={end:4d}, assignee={s.get('assignee'):6s}, {s['component'][:30]}")