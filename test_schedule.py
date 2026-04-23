import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
for s in steps[:7]:
    print(f"Step {s['id']}: start={s['start_time']}, dur={s['time_seconds']}, assignee={s['assignee']}")