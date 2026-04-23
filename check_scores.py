import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print('Current time_score distribution:')
scores = {}
for s in steps:
    score = s.get('time_score', 'N/A')
    key = str(round(score, 2)) if isinstance(score, float) else 'N/A'
    scores[key] = scores.get(key, 0) + 1
for score, count in sorted(scores.items()):
    print(f"  {score}: {count} tasks")

print('\nSteps with time_score:')
for s in steps[:10]:
    print(f"  Step {s['id']}: time_score={s.get('time_score')} time_seconds={s.get('time_seconds')}")