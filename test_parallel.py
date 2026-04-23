import requests

payload = {'battery_model': 'Audi_A3', 'context': [], 'debug': True}
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan', json=payload, timeout=120)
print('Status:', resp.status_code)
data = resp.json()
if 'data' in data and 'parallel_batches' in data['data']:
    batches = data['data']['parallel_batches']
    print(f'Parallel batches: {len(batches)}')
    for b in batches:
        print(f"  Batch {b['batch_id']}: tasks={b['tasks']}, start={b['start_time']}, duration={b['duration']}")
else:
    print('Response keys:', list(data.keys()))
    if 'data' in data:
        print('data keys:', list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data']))