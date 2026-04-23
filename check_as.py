import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print("Steps with AS and assignee:")
for s in steps:
    as_val = s.get('as_score')
    as_str = f"{as_val:.3f}" if isinstance(as_val, (int, float)) else str(as_val)
    print(f"Step {s['id']}: {s['component'][:25]:25s} AS={as_str} assignee={s.get('assignee', 'N/A')}")