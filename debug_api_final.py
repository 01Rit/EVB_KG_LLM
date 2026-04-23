import requests
import json

resp = requests.post(
    'http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': True},
    timeout=120
)
print('Status:', resp.status_code)
data = resp.json()
if data.get('data') and data['data'].get('steps'):
    print(f"\nSteps ({len(data['data']['steps'])} steps, total {data['data'].get('total_time_seconds', 0)}s):")
    for step in data['data']['steps'][:5]:
        print(f"  Step {step['id']}: {step.get('component', 'N/A')}")
        print(f"    time_seconds={step.get('time_seconds')}, time_score={step.get('time_score', 'N/A')}")
        print(f"    assignee={step.get('assignee')}")