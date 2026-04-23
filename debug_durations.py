import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
print('Duration distribution:')
durations = {}
for s in steps:
    dur = s.get('time_seconds', 0)
    durations[dur] = durations.get(dur, 0) + 1

for dur, count in sorted(durations.items()):
    print(f"  {dur}s: {count} tasks")

print('\nSteps with durations:')
for s in steps:
    print(f"  Step {s['id']}: {s['component'][:30]:30s} time_seconds={s.get('time_seconds')} time_score={s.get('time_score')}")