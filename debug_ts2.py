import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print('time_score distribution:')
scores = {}
for s in steps:
    score = s.get('time_score', 'N/A')
    if score != 'N/A':
        score = round(score, 3)
    key = str(score)
    scores[key] = scores.get(key, 0) + 1

for score, count in sorted(scores.items()):
    print(f"  {score}: {count} tasks")

print('\nSteps with time_score:')
for s in steps:
    print(f"  Step {s['id']}: time_score={s.get('time_score')} time_seconds={s.get('time_seconds')}")