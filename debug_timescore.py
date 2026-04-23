import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print('time_score distribution:')
scores = {}
for s in steps:
    score = s.get('time_score', 'N/A')
    scores[score] = scores.get(score, 0) + 1
for score, count in sorted(str(s) for s in scores.keys()):
    print(f"  {score}: {count} tasks")

print('\nSteps with time_score:')
for s in steps:
    score = s.get('time_score', 'N/A')
    print(f"  Step {s['id']}: time_score={score} time_seconds={s.get('time_seconds')}")