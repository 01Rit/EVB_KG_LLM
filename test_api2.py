import requests
import json

resp = requests.post(
    'http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'BM-0001', 'context': [], 'debug': True},
    timeout=120
)
data = resp.json()
if data.get('data') and data['data'].get('steps'):
    for step in data['data']['steps']:
        scores = {k: v for k, v in step.items()
                  if k in ('as_score', 'h_score', 's_score', 'human_loss', 'robot_loss', 'loss_diff', 'assignee')}
        print(f"Step {step['id']}: {step['component']} -> scores: {scores}")